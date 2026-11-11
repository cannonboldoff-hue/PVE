"""Fusion: Evidence + Meaning -> Observed. One owner per field; disagreements are kept, never averaged away."""
from typing import Any, get_args

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


FONT_FOR_CLASS = {"sans": "Arial", "serif": "Georgia", "script": "Segoe Script", "display": "Impact",
                  "mono": "Courier New"}
READ_CPS = 15  # characters per second a viewer reads; caps a swapped text's length by its display time
SAFE_W = 0.9  # share of the frame width a line may use


class Observed(BaseModel):
    source: ir.Source
    slots: list[ir.Slot]
    transitions: list[ir.Transition] = Field(default_factory=list)
    texts: list[ir.TextEvent] = Field(default_factory=list)
    effects: list[ir.Effect] = Field(default_factory=list)
    overlays: list[ir.Overlay] = Field(default_factory=list)
    narrative: dict = Field(default_factory=dict)
    style: list[dict] = Field(default_factory=list)  # legacy per-slot style notes for styles.py
    conflicts: list[Conflict] = Field(default_factory=list)


def slots_from_cuts(source: ir.Source, ev: ir.Evidence) -> tuple[list[ir.Slot], list[ir.Transition]]:
    """Slots tile [0, n_frames) with boundaries at the measured shot changes. With the transitions track, each
    boundary carries its window and coarse class (a gradual one sits mid-window); without it, every cut is hard."""
    from ..render import capabilities

    items = sorted(ev.track("transitions"), key=lambda i: i.data["frame"])
    if not items:
        items = [ir.Item(id=i.id, track="cuts", start=i.data["frame"], end=i.data["frame"], conf=i.conf,
                         data={"frame": i.data["frame"], "type": "cut", "cuts": []}) for i in ev.track("cuts")]
        items.sort(key=lambda i: i.data["frame"])
    bounds = [0, *[i.data["frame"] for i in items], source.n_frames]
    slots = [ir.Slot(id=f"s{k + 1:02d}", start=a, end=b) for k, (a, b) in enumerate(zip(bounds[:-1], bounds[1:]))]
    trans = []
    for k, i in enumerate(items):
        kind = i.data.get("type", "cut")
        render, loss = capabilities.transition(kind)
        trans.append(ir.Transition(after_slot=slots[k].id, start=i.start, end=i.end,
                                   type=F[ir.TransitionType](value=kind, raw=i.data, conf=i.conf, source=i.track,
                                                             evidence=[i.id, *i.data.get("cuts", [])]),
                                   render=render, loss=loss))
    return slots, trans


def _measured(ev: ir.Evidence, track: str, slot: ir.Slot) -> ir.Item | None:
    """The track's item covering most of the slot, if any."""
    best, cover = None, 0
    for i in ev.track(track):
        c = min(i.end, slot.end) - max(i.start, slot.start)
        if c > cover and "value" in i.data:
            best, cover = i, c
    return best if best and cover * 2 >= slot.frames else None


def max_chars(text: str, box_w: float, frames: int) -> int:
    """Longest swap that fits: lines as wide as the safe area at the measured character width, and readable in the
    display time. Never below the reference's own length."""
    lines = text.split("\n")
    char_w = box_w / max(1, max(len(x) for x in lines))
    width_cap = int(SAFE_W / max(char_w, 1e-3)) * len(lines)
    read_cap = int(READ_CPS * frames / ir.FPS)
    return max(len(text), min(width_cap, read_cap))


def texts_from_evidence(ev: ir.Evidence, meaning: list[SlotMeaning] | None = None) -> list[ir.TextEvent]:
    from . import styles

    anim = {i.data["text_id"]: i for i in ev.track("text_anim")}
    said = {t["id"]: (t, m) for m in meaning or [] for t in m.texts}
    out = []
    for k, i in enumerate(sorted(ev.track("text"), key=lambda i: i.start)):
        a = anim.get(i.id)
        start, end = (a.start, a.end) if a else (i.start, i.end)
        st = i.data.get("style", {})
        t, m = said.get(i.id, ({}, None))
        fclass = t.get("font_class") if t.get("font_class") in FONT_FOR_CLASS else None
        font = FONT_FOR_CLASS[fclass] if fclass else styles._font((m.style if m else {}).get("caption_font", ""))
        role = t.get("role") if t.get("role") in get_args(ir.TextRole) else ("other" if t.get("role") else "caption")
        box = ir.Box(**(st.get("ink") or i.data["box"]))  # tight glyph box when measured
        ids = [i.id, *([a.id] if a else [])]
        anim_in = a.data["in"] if a else "none"
        anim_out = a.data["out"] if a else "none"
        out.append(ir.TextEvent(
            id=f"t{k + 1:02d}", start=start, end=end,
            text=F[str](value=i.data["text"], raw=i.data["text"], conf=i.conf, source="ocr", evidence=ids, binding="swap"),
            role=F[ir.TextRole](value=role, raw=t.get("role"), conf=0.7 if t else 0.3, source=m.provider if m else ""),
            keys=[ir.Key(frame=i.data.get("steady", i.start), box=box),
                  *[ir.Key(frame=f, box=ir.Box(x=x, y=y, w=w, h=h)) for f, x, y, w, h in i.data.get("boxes", [])]],
            style=ir.TextStyle(font_class=fclass or "sans", font=font, size=st.get("size", box.h),
                               fill=st.get("fill") or "#FFFFFF", outline=st.get("outline"), box=st.get("box"),
                               align=st.get("align", "center")),
            anim_in=F[ir.TextAnim](value=anim_in, raw=t.get("anim_note"), conf=a.data["in_conf"] if a else 0.3,
                                   source="text_anim", evidence=ids[1:]),
            anim_out=F[ir.TextAnim](value=anim_out, conf=a.data["out_conf"] if a else 0.3, source="text_anim",
                                    evidence=ids[1:]),
            anim_in_frames=a.data["in_frames"] if a else 0, anim_out_frames=a.data["out_frames"] if a else 0,
            max_chars=max_chars(i.data["text"], box.w, end - start)))
    return out


def effects_from_evidence(ev: ir.Evidence) -> list[ir.Effect]:
    from ..render import capabilities

    out = []
    for k, i in enumerate(sorted(ev.track("effects"), key=lambda i: i.start)):
        render, loss = capabilities.effect(i.data["type"])
        out.append(ir.Effect(id=f"e{k + 1:02d}", type=F[ir.EffectType](value=i.data["type"], raw=i.data, conf=i.conf,
                                                                       source="effects", evidence=[i.id]),
                             start=i.start, end=i.end, strength=i.data.get("strength", 1.0),
                             params={x: v for x, v in i.data.items() if x not in ("type", "strength")},
                             render=render, loss=loss))
    return out


def fuse(source: ir.Source, ev: ir.Evidence, meaning: list[SlotMeaning] | None = None,
         reel: dict | None = None) -> Observed:
    slots, trans = slots_from_cuts(source, ev)
    obs = Observed(source=source, slots=slots, transitions=trans, texts=texts_from_evidence(ev, meaning),
                   effects=effects_from_evidence(ev),
                   overlays=[ir.Overlay(id=f"o{k + 1:02d}", kind=F[ir.OverlayKind](value=i.data["kind"], raw=i.data,
                                                                                    conf=i.conf, source="overlays",
                                                                                    evidence=[i.id]),
                                        start=i.start, end=i.end, keys=[ir.Key(frame=i.start, box=ir.Box(**i.data["box"]))])
                             for k, i in enumerate(ev.track("overlays"))],
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
        lay = _measured(ev, "layout", slot)
        if lay is not None:
            slot.layout_boxes = [ir.Box(**b) for b in lay.data["boxes"]]
            slot.evidence.append(lay.id)
        col = next((i for i in ev.track("colour") if i.start == slot.start), None)
        if col is not None:
            slot.colour = ir.ColourTarget(**col.data)
            slot.evidence.append(col.id)
        sp = next((i for i in ev.track("speed") if i.start == slot.start), None)
        if sp is not None:
            slot.speed = [tuple(x) for x in sp.data["curve"]]
            slot.freeze = [tuple(x) for x in sp.data["freeze"]]
            slot.evidence.append(sp.id)
        cam = _measured(ev, "camera", slot)
        if cam is not None:  # geometry is evidence-only: the measured view path and shake
            slot.evidence.append(cam.id)
            slot.camera_path = [ir.Key(frame=int(f), box=ir.Box(x=cx - 0.5 / sc, y=cy - 0.5 / sc, w=1 / sc, h=1 / sc),
                                       scale=sc, rotation=rot) for f, sc, cx, cy, rot in cam.data.get("path", [])]
            shake = cam.data.get("shake") or {}
            slot.shake = shake if slot.camera.value in ("shake", "handheld") or shake.get("amp", 0) > 0.003 else None
    return obs
