import json
from typing import AsyncIterator, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .. import config

T = TypeVar("T", bound=BaseModel)
URL = "https://openrouter.ai/api/v1/chat/completions"


def _headers() -> dict:
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set (see .env.example)")
    return {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}


async def chat_json(messages: list[dict], model_cls: type[T]) -> T:
    """JSON-schema output validated with pydantic; one retry that includes the validation error."""
    msgs = list(messages)
    for attempt in range(2):
        body = {
            "model": config.OPENROUTER_MODEL,
            "messages": msgs,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": model_cls.__name__, "strict": False, "schema": model_cls.model_json_schema()}},
        }
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(URL, headers=_headers(), json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"OpenRouter {r.status_code}: {r.text[:300]}")
        text = r.json()["choices"][0]["message"]["content"] or ""
        try:
            return model_cls.model_validate_json(text)
        except (ValidationError, ValueError) as e:
            if attempt:
                raise RuntimeError(f"LLM returned invalid {model_cls.__name__}: {e}") from e
            msgs += [{"role": "assistant", "content": text},
                     {"role": "user", "content": f"That JSON failed validation: {e}\nReturn corrected JSON only."}]
    raise AssertionError("unreachable")


async def chat_stream(messages: list[dict], tools: list[dict] | None = None) -> AsyncIterator[dict]:
    """Yields {'token': str} deltas, then one {'tool_calls': [...]} if the model called tools."""
    body = {"model": config.OPENROUTER_MODEL, "messages": messages, "stream": True}
    if tools:
        body["tools"] = tools
    calls: dict[int, dict] = {}
    async with httpx.AsyncClient(timeout=None) as c:
        async with c.stream("POST", URL, headers=_headers(), json=body) as r:
            if r.status_code >= 400:
                raise RuntimeError(f"OpenRouter {r.status_code}: {(await r.aread()).decode()[:300]}")
            async for line in r.aiter_lines():
                if not line.startswith("data: ") or line.endswith("[DONE]"):
                    continue
                delta = json.loads(line[6:])["choices"][0]["delta"]
                if delta.get("content"):
                    yield {"token": delta["content"]}
                for tc in delta.get("tool_calls") or []:
                    cur = calls.setdefault(tc["index"], {"id": "", "name": "", "arguments": ""})
                    cur["id"] = tc.get("id") or cur["id"]
                    f = tc.get("function") or {}
                    cur["name"] += f.get("name") or ""
                    cur["arguments"] += f.get("arguments") or ""
    if calls:
        yield {"tool_calls": [calls[i] for i in sorted(calls)]}
