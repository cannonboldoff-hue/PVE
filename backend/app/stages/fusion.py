"""Fusion: Evidence + Meaning -> Observed. One owner per field; disagreements are kept, never averaged away."""
from typing import Any

from pydantic import BaseModel, Field

from .. import ir
from ..ir import F
from .meaning import VOCAB, SlotMeaning

# field -> evidence track that owns it; fields not listed are owned by the model.
# timing and geometry always come from evidence; these are the semantic fields a track can also measure.
EVIDENCE_OWNER = {"media": "still", "camera": "camera", "layout": "layout"}
CONFLICT_FACTOR = 0.5  # owner's conf is multiplied by this when the other source disagrees
UNMEASURED_FACTOR = 0.7  # evidence-owned field with no measurement yet: the model's value, trusted less


class Conflict(BaseModel):
    path: str  # "slots.0.camera"
    owner: str  # source whose value was kept
    kept: Any
    other: Any
    other_source: str
    evidence: list[str] = Field(default_factory=list)


class Observed(BaseModel):
    source: ir.Source
    slots: list[ir.Slot]
    transitions: list[ir.Transition] = Field(default_factory=list)
    narrative: dict = Field(default_factory=dict)
    style: list[dict] = Field(default_factory=list)  # legacy per-slot style notes for styles.py
    conflicts: list[Conflict] = Field(default_factory=list)


def slots_from_cuts(source: ir.Source, ev: ir.Evidence) -> tuple[list[ir.Slot], list[ir.Transition]]:
    """Slots tile [0, n_frames) with boundaries at the cut frames; every boundary starts as a hard cut."""
    items = sorted(ev.track("cuts"), key=lambda i: i.data["frame"])
    bounds = [0, *[i.data["frame"] for i in items], source.n_frames]
    slots = [ir.Slot(id=f"s{k + 1:02d}", start=a, end=b) for k, (a, b) in enumerate(zip(bounds[:-1], bounds[1:]))]
    trans = [ir.Transition(after_slot=slots[k].id, start=i.data["frame"], end=i.data["frame"],
                           type=F[ir.TransitionType](value="cut", raw=i.data, conf=i.conf, source="cuts",
                                                     evidence=[i.id]))
             for k, i in enumerate(items)]
    return slots, trans


def _measured(ev: ir.Evidence, track: str, slot: ir.Slot) -> ir.Item | None:
    """The track's item covering most of the slot, if any."""
    best, cover = None, 0
    for i in ev.track(track):
        c = min(i.end, slot.end) - max(i.start, slot.start)
        if c > cover and "value" in i.data:
            best, cover = i, c
    return best if best and cover * 2 >= slot.frames else None


def fuse(source: ir.Source, ev: ir.Evidence, meaning: list[SlotMeaning] | None = None,
         reel: dict | None = None) -> Observed:
    slots, trans = slots_from_cuts(source, ev)
    obs = Observed(source=source, slots=slots, transitions=trans,
                   narrative={k: v for k, v in (reel or {}).items() if k != "error"})
    by_slot = {m.slot: m for m in meaning or []}
    for k, slot in enumerate(slots):
        m = by_slot.get(slot.id)
        obs.style.append(m.style if m else {})
        for name, vocab in VOCAB.items():
            ans = m.fields.get(name) if m else None
            model_val = F(value=ans.value, raw=ans.note, conf=ans.confidence, source=m.provider) if ans else None
            track = EVIDENCE_OWNER.get(name)
            item = _measured(ev, track, slot) if track else None
            if item is not None:  # evidence owns it and measured it
                val = F(value=item.data["value"], raw=item.data, conf=item.conf, source=track, evidence=[item.id])
                if model_val is not None and model_val.value != val.value and model_val.conf > 0:
                    val.conf *= CONFLICT_FACTOR
                    obs.conflicts.append(Conflict(path=f"slots.{k}.{name}", owner=track, kept=val.value,
                                                  other=model_val.value, other_source=model_val.source,
                                                  evidence=[item.id]))
            elif model_val is not None:
                val = model_val
                if track:
                    val.conf *= UNMEASURED_FACTOR
            else:
                continue
            setattr(slot, name, getattr(slot, name).__class__(**val.model_dump()))  # keeps the field's typed F[...]
    return obs
