"""AI Verifier: technical checks (mcp-video) -> content check (Pegasus) -> LLM judge. Cheapest first."""
import asyncio
import json
from pathlib import Path

from ..clients import openrouter, twelvelabs, video
from ..models import JudgeResult, Plan

CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject_in_frame": {"type": "boolean"}, "captions_readable": {"type": "boolean"},
        "pacing_close_to_reference": {"type": "boolean"}, "notes": {"type": "string"},
    },
    "required": ["subject_in_frame", "captions_readable", "pacing_close_to_reference", "notes"],
}
MAX_CAPTION_CHARS = 70


def _content(path: Path, reference: dict) -> dict:
    aid = twelvelabs.upload_asset(str(path))
    try:
        prompt = (
            "This is a vertical short-form video. Answer only about these things: (1) does the main subject stay "
            "fully in frame throughout; (2) are the on-screen captions readable over the footage (contrast, size, "
            "not cut off); (3) is the pacing close to this reference style: "
            f"{reference.get('pacing', '')} / {reference.get('overall_style', '')}. Put specifics, with timestamps, in notes."
        )
        return twelvelabs.analyze(aid, prompt, CONTENT_SCHEMA)
    finally:
        twelvelabs.delete_asset(aid)


async def verify(plan: Plan, final: Path, duration: float, brief: dict, reference: dict) -> tuple[JudgeResult, dict, dict | None]:
    tech = await asyncio.to_thread(video.tech_checks, final, duration)
    long = [s.shot_id for s in plan.shots if len(s.caption) > MAX_CAPTION_CHARS]
    tech["caption_length"] = {"ok": not long, "detail": f"too long in shots {long}" if long else "ok"}
    tech_ok = all(c["ok"] for c in tech.values())
    content = await asyncio.to_thread(_content, final, reference) if tech_ok else None  # layer 2 needs a clean render

    msg = (
        "You verify a rendered Reel draft. Inputs are structured check results; decide PASS or REPAIR.\n"
        f"Brief: {json.dumps(brief)}\nPlan: {plan.model_dump_json()}\nTechnical checks: {json.dumps(tech)}\n"
        f"Content check: {json.dumps(content) if content else 'skipped because a technical check failed'}\n\n"
        "PASS only if every check is ok and the content check has no problems. For each problem add an issue "
        "tied to a shot_id and list fixes as patch ops {shot_id, field, value}. Allowed fields: in, out (seconds "
        "in the source clip), speed (0.5-2), caption, cap_start, cap_end (seconds inside the shot), transition, "
        "fit (cover or blur_fit: use blur_fit when the subject is cropped out by the 9:16 fill), animation (none, "
        "zoom_in, zoom_out), caption_animation (none, fade, pop, slide_up), caption_color (#RRGGBB), caption_size (36-140), caption_position (top, center, bottom), clip (an asset id), drop. Write `summary` in plain language for a non-expert."
    )
    msgs_ = [{"role": "user", "content": msg}]
    j = await openrouter.chat_json(msgs_, JudgeResult)
    if j.verdict == "REPAIR" and not any(i.fixes for i in j.issues):  # a REPAIR without fixes can't be acted on
        msgs_ += [{"role": "assistant", "content": j.model_dump_json()},
                  {"role": "user", "content": "Your REPAIR has no patch ops. Return issues that each carry at least one fix, "
                                              "or PASS if nothing here can be fixed with patch ops."}]
        j = await openrouter.chat_json(msgs_, JudgeResult)
    bad_content = content and not (content["subject_in_frame"] and content["captions_readable"] and content["pacing_close_to_reference"])
    if (not tech_ok or bad_content) and j.verdict == "PASS":  # code enforces what the checks already say
        j.verdict = "REPAIR"
    return j, tech, content
