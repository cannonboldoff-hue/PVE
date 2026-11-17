"""Fusion: Evidence + Meaning -> Observed. One owner per field; disagreements are kept, never averaged away."""
from typing import Any, get_args

from pydantic import BaseModel, Field

from .. import ir
from ..ir import F
from .meaning import VOCAB, SlotMeaning, TransitionMeaning

# field -> evidence track that owns it; fields not listed are owned by the model.
# timing and geometry always come from evidence; these are the semantic fields a track can also measure.
EVIDENCE_OWNER = {"media": "still", "camera": "camera", "layout": "layout"}
CONFLICT_FACTOR = 0.5  # owner's conf is multiplied by this when the other source disagrees
UNMEASURED_FACTOR = 0.7
LAYER_CONF = 0.4  # ceiling for a layer only the video AI saw
LAYER_LOSS = {"shape_mask": "", "cutout": "cutout: drawn only when the shot's cut-out clip (alpha) is supplied",
              "moving_layer": "moving layer: drawn only when the layer's picture or clip is supplied",
              "other": "layer not rendered"}
LAYER_RENDER = {"shape_mask": "ffmpeg:geq", "cutout": "overlay:layer", "moving_layer": "overlay:layer", "other": ""}
MASK_SHAPES = ("circle", "ellipse", "rect", "rounded_rect", "heart")
MEASURED_LAYER_CONF = 0.7
MATCH_CUT_CONF = 0.6  # the video AI's match cut is believed from this confidence
SURE_CLASS = 0.8  # a measured transition class at or above this keeps its name over the model's  # evidence-owned field with no measurement yet: the model's value, trusted less


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
    layers: list[ir.Layer] = Field(default_factory=list)
    effects: list[ir.Effect] = Field(default_factory=list)
    overlays: list[ir.Overlay] = Field(default_factory=list)
    narrative: dict = Field(default_factory=dict)
    style: list[dict] = Field(default_factory=list)  # legacy per-slot style notes for styles.py
    conflicts: list[Conflict] = Field(default_factory=list)
    dropped: dict[str, str] = Field(default_factory=dict)  # evidence id -> why no template field uses it


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


def name_transitions(trans: list[ir.Transition], named: list[TransitionMeaning] | None) -> list[Conflict]:
    """Window from evidence, name from the model unless the measured class is sure and different. 'cut' and
    'other' from the model never replace a measured gradual class (the model's word stays in the conflict)."""
    from ..render import capabilities

    by = {(m.after_slot, m.start, m.end): m for m in named or [] if m.answer.confidence > 0}
    out = []
    for k, t in enumerate(trans):
        m = by.get((t.after_slot, t.start, t.end))
        if m is None or m.answer.value == t.type.value:
            if m is not None:
                t.type.conf = max(t.type.conf, m.answer.confidence)
            continue
        ans, measured = m.answer, t.type
        if measured.conf >= SURE_CLASS or ans.value in ("cut", "other"):
            out.append(Conflict(path=f"transitions.{k}.type", owner=measured.source, kept=measured.value,
                                other=ans.value if ans.value != "other" else ans.note, other_source=m.provider,
                                evidence=measured.evidence))
            continue
        out.append(Conflict(path=f"transitions.{k}.type", owner=m.provider, kept=ans.value, other=measured.value,
                            other_source=measured.source, evidence=measured.evidence))
        t.type = F[ir.TransitionType](value=ans.value, raw={"note": ans.note, "measured": measured.value,
                                                            "signals": measured.raw}, conf=ans.confidence,
                                      source=m.provider, evidence=measured.evidence)
        t.render, t.loss = capabilities.transition(ans.value)
    return out


def _box(raw) -> ir.Box | None:
    try:
        x, y, w, h = (min(1.0, max(0.0, float(raw[k]))) for k in "xywh")
    except (KeyError, TypeError, ValueError):
        return None
    return ir.Box(x=x, y=y, w=min(w, 1 - x), h=min(h, 1 - y)) if w > 0 and h > 0 else None


def layers_from_meaning(meaning: list[SlotMeaning] | None) -> list[ir.Layer]:
    """Masks, cutouts and moving layers from the video AI: a box per end of the shot, low confidence, a loss."""
    out = []
    for m in meaning or []:
        for x in m.layers:
            box = _box(x.get("box"))
            if box is None:
                continue
            end = _box(x.get("end_box")) or box
            kind = x.get("kind") if x.get("kind") in get_args(ir.LayerKind) else "other"
            conf = min(LAYER_CONF, max(0.0, float(x.get("confidence") or 0.5)))
            out.append(ir.Layer(id=f"l{len(out) + 1:02d}", start=m.start, end=m.end, shape=str(x.get("shape") or ""),
                                kind=F[ir.LayerKind](value=kind, raw=x.get("note") or x.get("kind"), conf=conf,
                                                     source=m.provider),
                                keys=[ir.Key(frame=m.start, box=box), *([ir.Key(frame=m.end - 1, box=end)]
                                                                       if end != box else [])],
                                above_text=bool(x.get("in_front_of_text")) and kind == "cutout",
                                render=LAYER_RENDER[kind], loss=LAYER_LOSS[kind]))
    return out


def mask_shape(word: str, fill: float | None = None) -> tuple[str, str]:
    """(shape the renderer draws, loss) from the video AI's word, or the measured fill share of the box."""
    w = word.lower().replace(" ", "_").replace("-", "_")
    for s in ("rounded_rect", "heart", "circle", "ellipse", "oval", "rect", "square"):
        if s in w:
            return {"oval": "ellipse", "square": "rect"}.get(s, s), ""
    if fill is not None:
        return ("rect" if fill > 0.9 else "ellipse"), ""
    return "ellipse", f"shape '{word}' drawn as an ellipse" if word else ""


def measured_layers(ev: ir.Evidence, slots: list[ir.Slot], layers: list[ir.Layer], key: str | None,
                    dropped: dict[str, str]) -> None:
    """Back the video AI's layers with measurements: a shape mask takes the measured box and background; a mask
    nobody named but clearly not a rectangle (letterbox and splits are) is added; moving layers are tracked."""
    for i in ev.track("masks"):
        slot = next((s for s in slots if s.start <= i.start < s.end), None)
        said = next((x for x in layers if x.kind.value == "shape_mask" and x.start < i.end and x.end > i.start), None)
        if said is None and (i.data.get("fill", 1) > 0.88 or (slot and slot.layout.value not in ("single", "other"))):
            dropped[i.id] = "flat static border around a rectangle: a layout (letterbox / split), not a shape mask"
            continue
        box = ir.Box(**i.data["box"])
        shape, loss = mask_shape(said.shape if said else "", i.data.get("fill"))
        if said is None:
            said = ir.Layer(id=f"l{len(layers) + 1:02d}", start=i.start, end=i.end, keys=[],
                            kind=F[ir.LayerKind](value="shape_mask", conf=0.0, source="masks"),
                            render=LAYER_RENDER["shape_mask"])
            layers.append(said)
        said.keys, said.shape, said.bg, said.loss = [ir.Key(frame=i.start, box=box)], shape, i.data.get("bg"), loss
        said.kind.conf = max(said.kind.conf, MEASURED_LAYER_CONF)
        said.kind.evidence.append(i.id)
    for x in layers:
        if x.kind.value == "shape_mask" and not x.kind.evidence:
            x.shape, x.loss = mask_shape(x.shape)
    if not key:
        return
    moving = [x for x in layers if x.kind.value in ("moving_layer", "cutout") and x.keys]
    if not moving:
        return
    try:
        from ..evidence import masks
        from ..evidence.frames import load

        _, rgb = load(key)
    except Exception:  # no proxy (tests, a dropped reference): keep the video AI's two keys
        return
    for x in moving:
        path = masks.track_box(rgb[x.start:x.end], x.keys[0].box)
        if len(path) > 2:
            x.keys = [ir.Key(frame=x.start + f, box=b) for f, b in path]
            x.kind.conf = max(x.kind.conf, 0.5)


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


TILT_MIN = 8.0  # degrees of 3D tilt the video AI must report before the text is drawn tilted
# video AI words for an animation the pixels could not tell apart from a fade
ANIM_NOTE = {"bounce": "bounce", "highlight": "word_highlight"}
REVERSE_CONF = 0.6  # the video AI's "plays backwards" is believed from this confidence (nothing measures it)
AI_EFFECT_CONF = 0.5  # ... and an effect it names, when no measurement covers that type there


def _note_anim(note) -> str:
    n = str(note or "").lower()
    return next((k for k in ANIM_NOTE if k in n), "")


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
        in_conf, in_src = (a.data["in_conf"] if a else 0.3), "text_anim"
        lit, revealed = i.data.get("lit") or [], i.data.get("words") or []
        words = [ir.Word(i=w["i"], start=w["start"], fill=w.get("fill")) for w in (lit or revealed)]
        if lit and len({w["start"] for w in lit}) >= 2:  # measured: the colour moves through the words
            anim_in, in_conf, in_src = "word_highlight", 0.75, "text"
        elif revealed:  # measured: whole words appear one after another
            anim_in, in_conf, in_src = "typewriter", 0.75, "text"
        elif anim_in in ("none", "fade") and (note := ANIM_NOTE.get(_note_anim(t.get("anim_note")))):
            anim_in, in_conf, in_src = note, 0.3, m.provider if m else ""  # the video AI's word, measurement silent
        rot = float(i.data.get("rotation") or 0.0)
        by_frame = {int(f): a_ for f, a_ in i.data.get("angles", [])}
        tilt = {"rx": float(t.get("tilt_x") or 0), "ry": float(t.get("tilt_y") or 0)}
        out.append(ir.TextEvent(
            id=f"t{k + 1:02d}", start=start, end=end,
            text=F[str](value=i.data["text"], raw=i.data["text"], conf=i.conf, source="ocr", evidence=ids, binding="swap"),
            role=F[ir.TextRole](value=role, raw=t.get("role"), conf=0.7 if t else 0.3, source=m.provider if m else ""),
            keys=[ir.Key(frame=i.data.get("steady", i.start), box=box, rotation=rot),
                  *[ir.Key(frame=f, box=ir.Box(x=x, y=y, w=w, h=h), rotation=by_frame.get(int(f), rot) if rot else 0.0)
                    for f, x, y, w, h in i.data.get("boxes", [])]],
            style=ir.TextStyle(font_class=fclass or "sans", font=font, size=st.get("size", box.h),
                               fill=st.get("fill") or "#FFFFFF", outline=st.get("outline"), box=st.get("box"),
                               align=st.get("align", "center")),
            words=words, highlight=i.data.get("highlight"),
            perspective=tilt if abs(tilt["rx"]) >= TILT_MIN or abs(tilt["ry"]) >= TILT_MIN else None,
            anim_in=F[ir.TextAnim](value=anim_in, raw=t.get("anim_note"), conf=in_conf,
                                   source=in_src, evidence=ids[1:] if in_src == "text_anim" else [i.id]),
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
         reel: dict | None = None, named: list[TransitionMeaning] | None = None) -> Observed:
    slots, trans = slots_from_cuts(source, ev)
    renamed = name_transitions(trans, named)
    obs = Observed(source=source, slots=slots, transitions=trans, texts=texts_from_evidence(ev, meaning), layers=layers_from_meaning(meaning),
                   effects=effects_from_evidence(ev),
                   overlays=[ir.Overlay(id=f"o{k + 1:02d}", kind=F[ir.OverlayKind](value=i.data["kind"], raw=i.data,
                                                                                    conf=i.conf, source="overlays",
                                                                                    evidence=[i.id]),
                                        start=i.start, end=i.end, keys=[ir.Key(frame=i.start, box=ir.Box(**i.data["box"]))])
                             for k, i in enumerate(ev.track("overlays"))],
                   narrative={k: v for k, v in (reel or {}).items() if k != "error"}, conflicts=renamed)
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
            slot.shake_windows = [ir.ShakeWindow(start=int(a), end=int(b), amp=amp, hz=hz)
                                  for a, b, amp, hz in cam.data.get("shake_windows", [])]
            if slot.shake_windows:  # it shakes in bursts: the windows say where, the summary would shake it all
                slot.shake = None
            for a, p, b, ratio in cam.data.get("punches", []):  # drawn by the camera path; listed so it is named
                obs.effects.append(ir.Effect(
                    id=f"e{len(obs.effects) + 1:02d}", start=cam.start + int(a), end=cam.start + int(b) + 1,
                    type=F[ir.EffectType](value="zoom_punch", raw={"peak": cam.start + int(p), "scale": ratio},
                                          conf=0.7, source="camera", evidence=[cam.id]),
                    strength=ratio, params={"peak": cam.start + int(p), "scale": ratio}, render="camera"))
        if m and m.reverse and m.reverse.value == "yes" and m.reverse.confidence >= REVERSE_CONF:
            slot.reverse = True  # reverse shake = this plus the shake windows
        if m:
            effects_from_meaning(obs, m, slot)
        tiles = _measured(ev, "tiles", slot)
        if tiles is not None and len(slot.layout_boxes) > 1:
            slot.tiles = [ir.Tile(box=t["box"], speed=[tuple(x) for x in t.get("curve", [(0.0, 1.0)])],
                                  freeze=[tuple(x) for x in t.get("freeze", [])], camera=t.get("camera", "static"),
                                  camera_path=[ir.Key(frame=int(f), box=ir.Box(x=cx - 0.5 / sc, y=cy - 0.5 / sc,
                                                                               w=1 / sc, h=1 / sc), scale=sc, rotation=rot)
                                               for f, sc, cx, cy, rot in t.get("path", [])],
                                  shake_windows=[ir.ShakeWindow(start=int(a), end=int(b), amp=amp, hz=hz)
                                                 for a, b, amp, hz in t.get("shake_windows", [])],
                                  continues=bool(t.get("continues")))
                          for t in tiles.data["tiles"]]
            slot.evidence.append(tiles.id)
        for x in (m.tiles if m else []):  # what each box shows, for the shot list
            if 0 <= x["box"] < len(slot.tiles):
                slot.tiles[x["box"]].role = str(x.get("role") or "")
    measured_layers(ev, slots, obs.layers, source.key, obs.dropped)
    used = {x for s in slots for x in s.evidence}
    for i in ev.track("tiles"):  # a tiles item whose slot's layout ended up single: nothing uses its boxes
        if i.id not in used:
            obs.dropped[i.id] = "per-box motion of a layout the slot did not keep"
    match_cuts(ev, slots, trans, by_slot)
    return obs


def match_cuts(ev: ir.Evidence, slots: list[ir.Slot], trans: list[ir.Transition], by_slot: dict) -> None:
    """Flag the boundaries where the subject stays put while the scene changes, measured or named by the video AI."""
    measured = {i.data["frame"]: i for i in ev.track("match_cuts")}
    for k, t in enumerate(trans):
        nxt = slots[k + 1] if k + 1 < len(slots) else None
        if nxt is None:
            continue
        i = measured.get(nxt.start)
        said = getattr(by_slot.get(nxt.id), "match_cut_in", None)
        ai = bool(said and said.value == "yes" and said.confidence >= MATCH_CUT_CONF)
        if i is None and not ai:
            continue
        t.params["match_cut"] = True
        t.params["match_conf"] = round(min(1.0, (i.conf if i else 0) + (0.3 if ai else 0) + (0.2 if i and ai else 0)), 2)
        if i is not None:
            t.params["match_box"] = i.data["box"]
            t.type.evidence.append(i.id)


def effects_from_meaning(obs: Observed, m: SlotMeaning, slot: ir.Slot) -> None:
    """Effects the video AI names that no measurement found at that time (glow, glitch, scanlines ...)."""
    from ..render import capabilities

    for x in m.effects:
        kind = x["type"] if x["type"] in get_args(ir.EffectType) else "other"
        conf = min(1.0, max(0.0, float(x.get("confidence") or 0.5)))
        try:
            a = slot.start + ir.s2f(float(x.get("start_s") or 0))
            b = slot.start + ir.s2f(float(x.get("end_s") or 0))
        except (TypeError, ValueError):
            continue
        a, b = max(slot.start, a), min(slot.end, max(b, a + 1))
        if conf < AI_EFFECT_CONF or kind in ("shake", "zoom_punch") or b <= a:  # those two the camera track measures
            continue
        if any(e.type.value == kind and e.start < b and e.end > a for e in obs.effects):
            continue  # measured already: the measurement owns its timing
        render, loss = capabilities.effect(kind)
        obs.effects.append(ir.Effect(id=f"e{len(obs.effects) + 1:02d}", start=a, end=b, render=render, loss=loss,
                                     type=F[ir.EffectType](value=kind, raw=x, conf=conf * UNMEASURED_FACTOR,
                                                           source=m.provider)))
