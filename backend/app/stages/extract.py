"""Observed reel -> Template, and the adapter from Template to the ShotSpec list the brief/fill/match steps use."""
from typing import Literal, get_args

from pydantic import BaseModel, Field

from .. import ir
from ..ir import Template
from ..models import ShotSpec
from .fusion import Observed

VERSION = 4  # 4: trend styles (tiles, shake windows, words, layers, match cuts); 3: text events (M4); 2: typed
# meaning (M3); 1: cut-only (M2)
SWAP_FIELDS = ("subject", "action")  # content: rewritten for the new reel; everything else is structure (keep)
MULTI_LAYOUTS = ("split_v", "split_h", "pip", "collage")  # layouts that take one clip per box
CONF_ASK = 0.5  # fields below this go to template.low_conf for a user confirm


def build(obs: Observed, audio: str = "") -> Template:
    """Observed -> Template with default bindings. Timing, frames and measured values are copied, never changed."""
    slots = [s.model_copy(deep=True) for s in obs.slots]
    low = []
    for k, s in enumerate(slots):
        for name in ("media", "role", "function", "subject", "action", "shot_size", "angle", "layout", "camera"):
            f = getattr(s, name)
            f.binding = "swap" if name in SWAP_FIELDS else "keep"
            if f.source and f.conf < CONF_ASK:
                low.append(f"slots.{k}.{name}")
    texts = [t.model_copy(deep=True) for t in obs.texts]
    for k, t in enumerate(texts):
        t.text.binding = "swap"
        for name in ("anim_in", "anim_out", "role"):
            getattr(t, name).binding = "keep"
            if getattr(t, name).conf < CONF_ASK and getattr(t, name).value != "none":
                low.append(f"texts.{k}.{name}")
    return Template(v=VERSION, key=obs.source.key, n_frames=obs.source.n_frames, audio=audio, slots=slots,
                    transitions=[t.model_copy(deep=True) for t in obs.transitions], texts=texts,
                    effects=[e.model_copy(deep=True) for e in obs.effects],
                    overlays=[o.model_copy(deep=True) for o in obs.overlays],
                    layers=[x.model_copy(deep=True) for x in obs.layers],
                    narrative=dict(obs.narrative), low_conf=low, dropped=dict(obs.dropped))


def slot_index(t: Template, frame: int) -> int:
    return next((k for k, s in enumerate(t.slots) if s.start <= frame < s.end), len(t.slots) - 1)


def slot_texts(t: Template) -> list[list[dict]]:
    """Per slot, the text events that start in it: [{id, role, original, max_chars}] (what the fill step rewrites)."""
    out: list[list[dict]] = [[] for _ in t.slots]
    for e in t.texts:
        d = {"id": e.id, "role": e.role.value, "original": e.text.raw or e.text.value, "max_chars": e.max_chars}
        if e.highlight and e.anim_in.value != "word_highlight":  # the reference colours its key words
            d["highlighted_words"] = [w.i for w in e.words]
        out[slot_index(t, e.start)].append(d)
    return out


def to_shotspecs(t: Template, legacy_fields: list[dict]) -> list[ShotSpec]:
    """The template as ShotSpecs for the existing UI and match steps. Timing comes from frames, never the model."""
    from . import brief

    out = []
    per_slot = slot_texts(t)
    for k, slot in enumerate(t.slots):
        s = dict(legacy_fields[k]) if k < len(legacy_fields) and legacy_fields[k] else {}
        if t.texts:  # measured text replaces the model's transcription
            s["on_screen_text"] = " / ".join(x["original"].replace("\n", " ") for x in per_slot[k])
        s.pop("caption_start", None), s.pop("caption_end", None)  # model timestamps are ignored entirely
        s.setdefault("description", slot.function.value)
        s.setdefault("subject", slot.subject.value)
        s.setdefault("action", slot.action.value)
        s.setdefault("camera", slot.angle.value)
        if slot.requirement and slot.requirement.instructions:  # the template's shot list (match cuts, boxes, cut-outs)
            s.setdefault("direction", "; ".join(slot.requirement.instructions))
        multi = slot.layout.value in MULTI_LAYOUTS and len(slot.layout_boxes) > 1
        s["layout"] = "collage" if multi else s.get("layout", "single")  # the match step finds a clip per box
        if multi:
            s["collage_tiles"] = len(slot.layout_boxes)
        if slot.layout.value == "blur_fill":
            s.setdefault("background", "blurred backdrop")
        tr = next((x for x in t.transitions if x.after_slot == slot.id), None)
        s["transition_out"] = tr.render.split(":", 1)[1] if tr and tr.render else "cut"  # display only; unknown -> cut
        spec = brief.shotspec(k + 1, {**s, "start": ir.f2s(slot.start), "end": ir.f2s(slot.end)})
        spec.texts = [{"id": x["id"], "text": x["original"]} for x in per_slot[k]]
        out.append(spec)
    return out


def summary(t: Template, shots: list[ShotSpec]) -> dict:
    """Compact description of the template for the brief prompt (no raw analysis, no truncation needed)."""
    return {
        "slots": len(t.slots), "length_seconds": round(ir.f2s(t.n_frames), 2), "has_reference_audio": bool(t.audio),
        "shots": [{"slot": k + 1, "seconds": round(ir.f2s(s.frames), 2), "role": s.role.value,
                   "function": s.function.value, "subject": s.subject.value, "text": sp.text}
                  for k, (s, sp) in enumerate(zip(t.slots, shots))],
        "narrative": t.narrative,
    }


# ---- M10: decisions by an LLM, applied by code ----

class FieldDecision(BaseModel):
    path: str = Field(description="e.g. slots.0.subject, texts.2, effects.1, overlays.0")
    binding: Literal["keep", "swap", "drop"]
    reason: str


class SlotIntent(BaseModel):
    slot: str
    role: str
    function: str = Field(description="one line: what this shot does for the viewer")


class Decisions(BaseModel):
    fields: list[FieldDecision] = Field(default_factory=list)
    slots: list[SlotIntent] = Field(default_factory=list)


DECIDE_PROMPT = (
    "This is a measured short-form reel, as JSON. Decide what a reusable template keeps from it. For each field path "
    "that is content (who or what is shown, on-screen words, stickers) answer swap; for structure and style (timing, "
    "transitions, camera, layout, look, effects) answer keep; answer drop for things that only make sense for this one "
    "video (a watermark, a username, a one-off joke) and say why. Give each slot a role (hook, establish, detail, "
    "action, reveal, reaction, payoff, cta, other) and a one-line function. You cannot change timing or measurements.")


def compact(obs: Observed) -> dict:
    return {
        "slots": [{"id": s.id, "frames": s.frames, "role": s.role.value, "function": s.function.value,
                   "subject": s.subject.value, "action": s.action.value, "camera": s.camera.value,
                   "layout": s.layout.value} for s in obs.slots],
        "texts": [{"path": f"texts.{k}", "text": e.text.value, "role": e.role.value} for k, e in enumerate(obs.texts)],
        "effects": [{"path": f"effects.{k}", "type": e.type.value} for k, e in enumerate(obs.effects)],
        "overlays": [{"path": f"overlays.{k}", "kind": o.kind.value} for k, o in enumerate(obs.overlays)],
        "transitions": [x.type.value for x in obs.transitions], "narrative": obs.narrative,
    }


def apply_decisions(t: Template, d: Decisions) -> Template:
    """Bindings, roles and functions only; timing, frames and measured values cannot change. Drops are listed."""
    before = [(s.start, s.end) for s in t.slots], t.n_frames
    roles = set(get_args(ir.Role))
    for intent in d.slots:
        s = next((x for x in t.slots if x.id == intent.slot), None)
        if s is None:
            continue
        s.role = s.role.__class__(value=intent.role if intent.role in roles else "other", raw=intent.role,
                                  conf=0.7, source="llm", evidence=s.role.evidence, binding="keep")
        s.function = s.function.__class__(value=intent.function, raw=intent.function, conf=0.7, source="llm",
                                          evidence=s.function.evidence, binding="keep")
    drop_texts, drop_effects, drop_overlays = set(), set(), set()
    for f in d.fields:
        parts = f.path.split(".")
        try:
            k = int(parts[1])
        except (IndexError, ValueError):
            continue
        if parts[0] == "slots" and len(parts) == 3 and k < len(t.slots) and parts[2] in SEMANTIC:
            getattr(t.slots[k], parts[2]).binding = f.binding if f.binding != "drop" else "keep"
        elif parts[0] == "texts" and k < len(t.texts):
            if f.binding == "drop":
                drop_texts.add(k)
                t.dropped |= {i: f.reason for i in t.texts[k].text.evidence}
            else:
                t.texts[k].text.binding = f.binding
        elif parts[0] == "effects" and k < len(t.effects) and f.binding == "drop":
            drop_effects.add(k)
            t.dropped |= {i: f.reason for i in t.effects[k].type.evidence}
        elif parts[0] == "overlays" and k < len(t.overlays):
            if f.binding == "drop":
                drop_overlays.add(k)
                t.dropped |= {i: f.reason for i in t.overlays[k].kind.evidence}
            else:
                t.overlays[k].binding = f.binding
    t.texts = [e for k, e in enumerate(t.texts) if k not in drop_texts]
    t.effects = [e for k, e in enumerate(t.effects) if k not in drop_effects]
    t.overlays = [o for k, o in enumerate(t.overlays) if k not in drop_overlays]
    assert ([(s.start, s.end) for s in t.slots], t.n_frames) == before, "decisions must not change timing"
    return t


SEMANTIC = ("media", "role", "function", "subject", "action", "shot_size", "angle", "layout", "camera")


def decide(obs: Observed, audio: str = "") -> Template:
    """build() then one LLM pass for bindings and intent (skipped without an LLM key: default bindings stay)."""
    import asyncio
    import json

    from .. import config
    from ..clients import openrouter

    t = build(obs, audio)
    if not config.OPENROUTER_API_KEY:
        return t
    msgs = [{"role": "system", "content": "Reply with JSON only."},
            {"role": "user", "content": f"{DECIDE_PROMPT}\n\n{json.dumps(compact(obs))}"}]
    return apply_decisions(t, asyncio.run(openrouter.chat_json(msgs, Decisions)))
