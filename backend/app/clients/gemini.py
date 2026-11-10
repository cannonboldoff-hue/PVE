"""Gemini video understanding, direct to Google (google-genai). Sync; callers wrap in asyncio.to_thread.
Free-tier content may be used for training: only send reels the user owns (docs/mvp-plan.md 7)."""
import json
import time
from functools import lru_cache
from pathlib import Path

from .. import config

UPLOAD_TIMEOUT = 300


@lru_cache
def _client():
    from google import genai

    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set (see .env.example)")
    return genai.Client(api_key=config.GEMINI_API_KEY)


def models() -> list[str]:
    """Model names this key can call with generateContent; check GEMINI_MODEL against this before wiring."""
    return [m.name.removeprefix("models/") for m in _client().models.list()
            if "generateContent" in (m.supported_actions or [])]


def model() -> str:
    if not config.GEMINI_MODEL:
        raise RuntimeError("GEMINI_MODEL is not set; pick one from clients.gemini.models()")
    return config.GEMINI_MODEL


def describe(clip_path: str | Path, prompt: str, schema: dict) -> dict:
    """Upload one clip, ask for JSON matching schema at temperature 0, delete the upload."""
    from google.genai import types

    c = _client()
    f = c.files.upload(file=str(clip_path))
    try:
        t0 = time.time()
        while f.state and f.state.name == "PROCESSING":
            if time.time() - t0 > UPLOAD_TIMEOUT:
                raise RuntimeError("Gemini file processing timed out")
            time.sleep(2)
            f = c.files.get(name=f.name)
        if f.state and f.state.name == "FAILED":
            raise RuntimeError(f"Gemini could not process {clip_path}: {f.error}")
        r = c.models.generate_content(
            model=model(), contents=[f, prompt],
            config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                               response_json_schema=schema))
        return json.loads(r.text)
    finally:
        try:
            c.files.delete(name=f.name)
        except Exception:
            pass  # best effort; uploads expire on their own
