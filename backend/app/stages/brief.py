"""Creative Brief and Shot Specs: LLM steps with schema-validated output."""
import json
from typing import get_args

from .. import db
from ..clients import openrouter
from ..models import Brief, ShotContentList, ShotSpec
from . import memory, styles

SYS = "You are a short-form video producer. Reply with JSON only."


def brief_input(key: str, analysis: dict) -> dict:
    """What the brief prompt sees: a compact template summary for IR templates, the analysis for legacy ones."""
    from .. import ir
    from . import extract

    row = db.one("SELECT template, shots FROM templates WHERE key=?", (key,))
    if row and row.get("template"):
        t = ir.Template.model_validate(row["template"])
        return {"pacing": analysis.get("pacing", ""), **extract.summary(t, [ShotSpec.model_validate(s) for s in row["shots"]])}
    return analysis


async def make_brief(analysis: dict, goal: str) -> Brief:
    prefs = memory.prefs()
    msg = (
        f"Reference Reel analysis:\n{json.dumps(analysis)}\n\nUser goal: {goal or '(not stated)'}\n"
        f"Known user preferences (use as defaults unless the goal says otherwise): {json.dumps(prefs)}\n\n"
        "Write the creative brief for a new 9:16 Reel in the same style: what to keep from the reference "
        "(pacing, style, structure, transitions), what to change (subject, text, product), target length in "
        "seconds (default: the reference length), tone, caption language, and media: 'photo' if the user says they "
        "have photos or images, 'video' if clips, else 'mixed'."
    )
    return await openrouter.chat_json([{"role": "system", "content": SYS}, {"role": "user", "content": msg}], Brief)


def merge_brief(old: dict, changes: dict) -> Brief:
    return Brief.model_validate({**old, **changes})


_TRANSITIONS = set(get_args(ShotSpec.model_fields["transition_out"].annotation))
_CAP_ANIM = {"fade", "pop", "slide_up"}


def shotspec(i: int, s: dict) -> ShotSpec:
    """One analysed shot (legacy SHOT schema fields) -> ShotSpec: camera, transition, fit, animation, caption style
    and timing, colour grade, collage layout."""
    s = {**s, **{k: s.get(k) or "" for k in ("description", "subject", "action")}}
    bg = (s.get("background") or "").lower()
    motion = (s.get("frame_motion") or "").lower()
    cap = (s.get("caption_animation") or "").lower().replace(" ", "_")
    tr = (s.get("transition_out") or "").lower().replace(" ", "")
    cs, ce = styles.caption_timing(s)
    lay, collage = styles.layout(s)
    return ShotSpec(
        shot_id=i, start=s["start"], end=s["end"], purpose=s["description"], subject=s["subject"], action=s["action"],
        caption_style=styles.caption_style(s), caption_start=cs, caption_end=ce, grade=styles.grade(s),
        layout=lay, collage=collage, asset_type="photo" if lay == "collage" else "video",
        camera=s.get("camera") or "", camera_motion=s.get("camera_motion") or "", text=s.get("on_screen_text") or "",
        transition_out=tr if tr in _TRANSITIONS else "cut", background=s.get("background") or "",
        fit="blur_fit" if any(w in bg for w in ("blur", "inset", "collage")) else "cover",
        animation="zoom_in" if "zoom in" in motion else "zoom_out" if "zoom out" in motion else "none",
        caption_animation=cap if cap in _CAP_ANIM else "none", overlay=s.get("overlays") or "")


def extract_template(analysis: dict) -> list[ShotSpec]:
    """Legacy analyses only: deterministic, brief-independent structure from the whole-video analysis."""
    return retime([shotspec(i, s) for i, s in enumerate(analysis["shots"], 1)])


def save_template(key: str, analysis: dict) -> None:
    """Upsert the template for a reference; structure only changes when the analysis changes.
    IR analyses (ref_key set) store the Template as source of truth and the ShotSpecs derived from it."""
    from .. import ir
    from . import extract

    title = (analysis.get("overall_style") or key)[:60]
    if analysis.get("ref_key") and (t := ir.load(analysis["ref_key"], "template", ir.Template)):
        shots = [s.model_dump() for s in extract.to_shotspecs(t, analysis["shots"])]
        delta = ir.load(analysis["ref_key"], "delta", ir.Delta)
        db.run("INSERT OR REPLACE INTO templates(key,title,shots,analysis_version,template,delta,ir_version,created) "
               "VALUES(?,?,?,?,?,?,?,?)",
               (key, title, json.dumps(shots), analysis.get("v"), t.model_dump_json(),
                delta.model_dump_json() if delta else None, t.v, db.now()))
        return
    shots = [s.model_dump() for s in extract_template(analysis)]
    db.run("INSERT OR REPLACE INTO templates(key,title,shots,analysis_version,created) VALUES(?,?,?,?,?)",
           (key, title, json.dumps(shots), analysis.get("v"), db.now()))


def load_ir(key: str | None):
    """The project's IR Template, or None for legacy templates."""
    from .. import ir

    row = db.one("SELECT template FROM templates WHERE key=?", (key,)) if key else None
    return ir.Template.model_validate(row["template"]) if row and row.get("template") else None


def get_template(key: str, analysis: dict) -> list[ShotSpec]:
    t = db.one("SELECT shots FROM templates WHERE key=?", (key,))
    if not t:  # project analysed before templates existed
        save_template(key, analysis)
        t = db.one("SELECT shots FROM templates WHERE key=?", (key,))
    return [ShotSpec.model_validate(s) for s in t["shots"]]


async def fill_shots(template: list[ShotSpec], brief: dict) -> list[ShotSpec]:
    """Apply the brief to the template: the LLM rewrites content only; structure is copied from the template."""
    slots = [{"slot": s.shot_id, "seconds": round(s.duration, 2), "purpose": s.purpose, "subject": s.subject,
              "action": s.action, "camera": s.camera, "camera_motion": s.camera_motion, "text": s.text} for s in template]
    msg = (
        f"Template slots (the reference's structure):\n{json.dumps(slots)}\n\nBrief:\n{json.dumps(brief)}\n\n"
        "Return `shots`: exactly one entry per slot, same order. Rewrite the content for the new Reel's topic: purpose, "
        "subject, action, direction (what the user should do), asset_type ('photo' or 'video': follow the brief's media; "
        "for 'mixed' use photo when the slot is a still), text (caption in the brief's caption language; empty if the slot "
        "has none or captions are off). Keep each slot's role and timing in mind. Describe subject and action concretely "
        "so they can be searched for in the user's own footage."
    )
    out = await openrouter.chat_json([{"role": "system", "content": SYS}, {"role": "user", "content": msg}], ShotContentList)
    if len(out.shots) != len(template):
        raise ValueError(f"expected {len(template)} shots for the template, got {len(out.shots)}")
    return [t.model_copy(update=c.model_dump()) for t, c in zip(template, out.shots)]


def retime(shots: list[ShotSpec]) -> list[ShotSpec]:
    """Renumber and make the timeline contiguous, keeping each shot's own length."""
    t = 0.0
    for i, s in enumerate(shots, 1):
        s.shot_id, d = i, s.duration
        s.start, s.end = round(t, 2), round(t + d, 2)
        t += d
    return shots
