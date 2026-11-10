"""Observed reel -> Template, and the adapter from Template to the ShotSpec list the brief/fill/match steps use."""
from .. import ir
from ..ir import Template
from ..models import ShotSpec
from .fusion import Observed

VERSION = 2  # 2: built from Observed (typed meaning, M3); 1: cut-only (M2)
SWAP_FIELDS = ("subject", "action")  # content: rewritten for the new reel; everything else is structure (keep)
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
    return Template(v=VERSION, key=obs.source.key, n_frames=obs.source.n_frames, audio=audio, slots=slots,
                    transitions=[t.model_copy(deep=True) for t in obs.transitions], narrative=dict(obs.narrative),
                    low_conf=low)


def to_shotspecs(t: Template, legacy_fields: list[dict]) -> list[ShotSpec]:
    """The template as ShotSpecs for the existing UI and match steps. Timing comes from frames, never the model."""
    from . import brief

    out = []
    for k, slot in enumerate(t.slots):
        s = dict(legacy_fields[k]) if k < len(legacy_fields) and legacy_fields[k] else {}
        s.pop("caption_start", None), s.pop("caption_end", None)  # model timestamps are ignored entirely
        s.setdefault("description", slot.function.value)
        s.setdefault("subject", slot.subject.value)
        s.setdefault("action", slot.action.value)
        s.setdefault("camera", slot.angle.value)
        s.setdefault("layout", "collage" if slot.layout.value == "collage" else "single")
        if slot.layout.value == "blur_fill":
            s.setdefault("background", "blurred backdrop")
        s["transition_out"] = "cut"  # M2: every boundary is a hard cut
        spec = brief.shotspec(k + 1, {**s, "start": ir.f2s(slot.start), "end": ir.f2s(slot.end)})
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
