"""Observed reel -> Template, and the adapter from Template to the ShotSpec list the brief/fill/match steps use."""
from .. import ir
from ..ir import Template
from ..models import ShotSpec
from .fusion import Observed

VERSION = 3  # 3: text events (M4); 2: built from Observed (typed meaning, M3); 1: cut-only (M2)
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
                    narrative=dict(obs.narrative), low_conf=low)


def slot_index(t: Template, frame: int) -> int:
    return next((k for k, s in enumerate(t.slots) if s.start <= frame < s.end), len(t.slots) - 1)


def slot_texts(t: Template) -> list[list[dict]]:
    """Per slot, the text events that start in it: [{id, role, original, max_chars}] (what the fill step rewrites)."""
    out: list[list[dict]] = [[] for _ in t.slots]
    for e in t.texts:
        out[slot_index(t, e.start)].append({"id": e.id, "role": e.role.value, "original": e.text.raw or e.text.value,
                                            "max_chars": e.max_chars})
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
