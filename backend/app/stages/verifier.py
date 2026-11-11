"""AI Verifier: technical checks (mcp-video) -> content check (Pegasus) -> LLM judge. Cheapest first."""
import asyncio
import json
import shutil
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


SAFE = (0.03, 0.97)  # text boxes must stay inside this share of the frame
CUT_TOL = 2  # frames


def lint(plan: Plan) -> dict:
    """Layer 0: the plan itself. Every shot has a clip on disk, frames add up, text stays in the safe area."""
    out = {}
    gone = [s.shot_id for s in plan.shots if not Path(s.path).exists()]
    out["clips"] = {"ok": not gone, "detail": f"missing files for shots {gone}" if gone else "ok"}
    if plan.n_frames is not None:
        n = sum(s.frames or 0 for s in plan.shots) - sum(t["frames"] for t in plan.transitions)
        out["frames"] = {"ok": n == plan.n_frames, "detail": f"{n} frames planned for {plan.n_frames}"}

    def extent(e):  # the new words at the reference's size: width scales with the longest line, centred
        b = e["keys"][0]["box"]
        longest = lambda t: max((len(x) for x in (t or " ").splitlines() or [" "]), default=1)  # noqa: E731
        w = b["w"] * longest(e["text"]["value"]) / max(1, longest(e["text"].get("raw") or e["text"]["value"]))
        return b["x"] + b["w"] / 2 - w / 2, b["y"], w, b["h"]

    outside = [e["id"] for e in plan.texts for x, y, w, h in [extent(e)]
               if x < SAFE[0] or y < SAFE[0] or x + w > SAFE[1] or y + h > SAFE[1]]
    out["text_safe_area"] = {"ok": not outside, "detail": f"outside the safe area: {outside}" if outside else "ok"}
    return out


def structure(plan: Plan, final: Path, template) -> dict:
    """Layer 2: the render measured with the analysis instruments, against the template. New footage and new words
    are expected; boundaries, transition windows and text timing are not allowed to move."""
    from .. import config, db, evidence, ir
    from . import compare
    from .analyze import ingest

    src = ingest(final)
    try:
        ev = evidence.run_all(src.key, only=["cuts", "transitions", "text", "text_anim"])
    finally:
        if not config.KEEP_REFS:
            shutil.rmtree(ir.ref_dir(src.key), ignore_errors=True)
            db.run("DELETE FROM refs WHERE key=?", (src.key,))
    want = [s.start for s in template.slots[1:]]
    got = [i.data["frame"] for i in ev.track("transitions")]
    p, r, _, mae = compare.match_events(got, want, CUT_TOL)
    out = {"boundaries": {"ok": r >= 0.9, "detail": f"{round(r * len(want))} of {len(want)} shot changes in place "
                                                       f"(mean error {mae:.1f} frames)"}}
    if plan.texts:
        spans: list[tuple[int, int]] = []
        prev = None
        for e in sorted(plan.texts, key=lambda e: e["start"]):
            # the same words in the same place back to back read as one caption on screen
            if prev and e["start"] <= spans[-1][1] and e["text"]["value"] == prev["text"]["value"] and                     compare.box_iou(e["keys"][0]["box"], prev["keys"][0]["box"]) > 0.8:
                spans[-1] = (spans[-1][0], e["end"])
            else:
                spans.append((e["start"], e["end"]))
            prev = e
        seen = [(i.start, i.end) for i in ev.track("text_anim")] or [(i.start, i.end) for i in ev.track("text")]
        tp, tr, _, tmae = compare.match_spans(seen, spans, 0.5)
        out["text_timing"] = {"ok": tr >= 0.8, "detail": f"{round(tr * len(spans))} of {len(spans)} text events at "
                                                           f"their frames (mean error {tmae:.1f}); planned {spans}, "
                                                           f"seen {seen[:8]} {[i.data['text'] for i in ev.track('text')][:8]}; planned words {[e['text']['value'] for e in plan.texts]}"}
    return out


async def verify(plan: Plan, final: Path, duration: float, brief: dict, reference: dict,
                 template=None) -> tuple[JudgeResult, dict, dict | None]:
    ref_audio = plan.music_path if plan.audio_mode == "reference" else None
    pre = lint(plan) if template is not None else {}
    tech = await asyncio.to_thread(video.tech_checks, final, duration, ref_audio)
    tech = {**{f"plan_{k}": v for k, v in pre.items()}, **tech}
    if template is not None and all(c["ok"] for c in tech.values()):
        tech |= {f"structure_{k}": v for k, v in (await asyncio.to_thread(structure, plan, final, template)).items()}
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
