"""Production Plan: approved shot->clip mapping as a timeline, plus the one patch applier
shared by chat revisions and verifier repairs."""
from collections.abc import Callable

from ..models import CaptionStyle, Match, PatchOp, Plan, PlanShot, ShotSpec

CAP_PAD = 0.2


def shake_of(s) -> dict | list | None:
    """What the renderer shakes for an ir.Slot: the measured windows when there are any, else the slot summary."""
    return [w.model_dump() for w in s.shake_windows] or s.shake or None


def camera_moves(s, template) -> bool:
    """The slot's view path is worth redoing: a classified move, or a measured zoom punch inside a static shot
    (path noise on a static shot is not redone)."""
    if s.camera.value != "static":
        return True
    return bool(s.camera_path) and any(e.type.value == "zoom_punch" and s.start <= e.start < s.end
                                       for e in template.effects)


def tile_params_of(s) -> list[dict]:
    """Every box of a multi-box ir.Slot with its own measured timing and motion (empty: boxes use the slot's)."""
    return [{"speed_curve": list(t.speed), "freeze": list(t.freeze), "reverse": t.reverse or (k == 0 and s.reverse),
             "camera_path": [x.model_dump(mode="json") for x in t.camera_path] if t.camera != "static" else [],
             "shake": [w.model_dump() for w in t.shake_windows] or None}
            for k, t in enumerate(s.tiles)]


def build(shots: list[dict], matches: list[dict], assets: dict[str, dict], music_path: str | None, captions: bool,
          template=None) -> Plan:
    """template (ir.Template): frame-exact timing pinned to the reference; skipped slots' frames go to a neighbour
    so the total stays n_frames and the reference audio stays in sync."""
    by_shot = {m["shot_id"]: Match(**m) for m in matches}
    slot_frames = {k + 1: s.end - s.start for k, s in enumerate(template.slots)} if template else {}
    out, orphan = [], 0
    for raw in shots:
        s = ShotSpec(**raw)
        m = by_shot.get(s.shot_id)
        if s.skipped or not m or not m.asset_id or m.asset_id not in assets:
            if template:
                if out:
                    out[-1].frames += slot_frames[s.shot_id]
                else:
                    orphan += slot_frames[s.shot_id]
            continue
        if template:  # the slot's exact length, plus any leading skipped slots
            s = s.model_copy(update={"end": s.start + (slot_frames[s.shot_id] + orphan) / 30})
        seg = max(0.1, m.end - m.start)
        if seg >= s.duration:
            src_out, speed = m.start + s.duration, 1.0
        else:  # source segment shorter than the slot: slow down, never below 0.5x
            src_out, speed = m.end, max(0.5, seg / s.duration)
        ps = PlanShot(shot_id=s.shot_id, asset_id=m.asset_id, path=assets[m.asset_id]["path"],
                      src_in=m.start, src_out=src_out, speed=speed, caption=s.text, transition=s.transition_out,
                      fit=s.fit, animation=s.animation, caption_animation=s.caption_animation,
                      caption_style=s.caption_style, grade=s.grade)
        if template:
            ps.frames, orphan = slot_frames[s.shot_id] + orphan, 0
            ps.transition = "cut"  # M2: transitions are rebuilt from the template (M6), not from ShotSpec
            ps.caption = ""  # on-screen text comes from the template's measured text events (plan.texts)
            slot = template.slots[s.shot_id - 1]
            if slot.speed != [(0.0, 1.0)] or slot.freeze or slot.reverse:  # speed ramp, freeze, reverse
                ps.speed_curve, ps.freeze, ps.reverse = list(slot.speed), list(slot.freeze), slot.reverse
            if camera_moves(slot, template):  # the reference's camera move, redone on the new clip
                ps.camera_path = [k.model_dump(mode="json") for k in slot.camera_path]
            ps.shake = shake_of(slot)  # shake also sits on otherwise static shots (zoom + shake, shake on a hit)
        lay = template.slots[s.shot_id - 1].layout if template else None
        boxes = template.slots[s.shot_id - 1].layout_boxes if template else []
        if lay is not None and lay.value in ("split_v", "split_h", "pip", "collage", "letterbox", "blur_fill") and boxes:
            ps.layout_boxes = [b.model_dump() for b in boxes]  # the reference's own boxes, one clip each
            ps.tiles = [assets[a]["path"] for a in m.extra_assets if a in assets][: len(boxes) - 1]
            ps.tile_params = tile_params_of(template.slots[s.shot_id - 1])
            _continue_tiles(ps, out[-1] if out else None, template.slots[s.shot_id - 1])
            ps.fit = "blur_fit" if lay.value == "blur_fill" else ps.fit

        elif s.layout == "collage":
            tiles = [assets[a]["path"] for a in m.extra_assets if a in assets][: s.collage.tiles - 1]
            if tiles:  # one tile alone is just a single shot
                ps.collage, ps.tiles = s.collage, tiles
        if template and template.slots[s.shot_id - 1].colour:
            ps.colour = template.slots[s.shot_id - 1].colour.model_dump()
        if template and not ps.layout_boxes:
            ps.mask = slot_mask(template, template.slots[s.shot_id - 1])
        _fit_caption(ps)
        _custom_caption_timing(ps, s)
        out.append(ps)
    plan = Plan(shots=out, music_path=music_path, captions=captions)
    if template and out:
        plan.n_frames = template.n_frames
        assert sum(p.frames for p in out) == template.n_frames, "slot frames must add up to the reference length"
        plan.texts = plan_texts(template, shots) if captions else []
        plan.effects = [e.model_dump(mode="json") for e in template.effects if e.render]
        plan.layer_clips = layer_clips(template, out, by_shot, assets)
        apply_transitions(plan, template)
    return plan


def slot_mask(template, slot) -> dict | None:
    """The slot's shape mask (frames relative to the slot), when the template has one there."""
    x = next((x for x in template.layers if x.kind.value == "shape_mask" and x.render and x.keys
              and slot.start <= x.start < slot.end), None)
    if x is None:
        return None
    return {"shape": x.shape, "bg": x.bg, "keys": [{"frame": k.frame - slot.start, "box": k.box.model_dump()}
                                                   for k in x.keys]}


def layer_clips(template, shots: list[PlanShot], by_shot: dict, assets: dict) -> list[dict]:
    """Cut-out and moving layers: each takes the next extra clip the user supplied for its slot after the slot's
    layout tiles (a cut-out wants a clip with alpha). Layers without a supplied clip are not drawn (their loss says so)."""
    out = []
    for p in shots:
        slot = template.slots[p.shot_id - 1]
        m = by_shot.get(p.shot_id)
        spare = [assets[a]["path"] for a in (m.extra_assets if m else []) if a in assets][len(p.tiles):]
        for x in template.layers:
            if x.kind.value not in ("cutout", "moving_layer") or not x.keys or not slot.start <= x.start < slot.end:
                continue
            if not spare:
                break
            out.append({"path": spare.pop(0), "start": x.start, "end": x.end, "above_text": x.above_text,
                        "keys": [{"frame": k.frame, "box": k.box.model_dump()} for k in x.keys]})
    return out


def _continue_tiles(ps: PlanShot, prev: PlanShot | None, slot) -> None:
    """A box that keeps playing across the cut takes the previous shot's clip for that box, from where it stopped."""
    if prev is None or prev.shot_id != ps.shot_id - 1 or len(prev.layout_boxes) != len(ps.layout_boxes):
        return
    # shortcut: assumes the box played at 1x in the previous shot; use shot.footage() of its curve if ramps show up
    secs = (prev.frames or 0) / 30
    for t in slot.tiles:
        if not t.continues or t.box >= len(ps.tile_params):
            continue
        if t.box == 0:
            ps.asset_id, ps.path, ps.src_in = prev.asset_id, prev.path, prev.src_in + secs
            ps.src_out = ps.src_in + ps.duration
        elif t.box - 1 < len(prev.tiles):
            while len(ps.tiles) < t.box:
                ps.tiles.append(prev.tiles[len(ps.tiles)] if len(ps.tiles) < len(prev.tiles) else prev.path)
            ps.tiles[t.box - 1] = prev.tiles[t.box - 1]
            prev_in = float((prev.tile_params[t.box] if t.box < len(prev.tile_params) else {}).get("in") or 0.0)
            ps.tile_params[t.box]["in"] = prev_in + secs


def apply_transitions(plan: Plan, template) -> None:
    """The template's transition windows between kept, adjacent slots. A window [a, b) around boundary c makes the
    left clip run on to b and the right clip start at a; both share those b - a frames (tail / lead), so
    sum(frames) - sum(window lengths) stays n_frames."""
    plan.transitions = []
    by_slot = {t.after_slot: t for t in template.transitions}
    for i, (p, q) in enumerate(zip(plan.shots, plan.shots[1:])):
        if q.shot_id != p.shot_id + 1:  # a skipped slot sits between: its frames went to p, keep a hard cut
            continue
        t = by_slot.get(template.slots[p.shot_id - 1].id)
        if not t or t.end <= t.start or not t.render:
            continue
        c = template.slots[q.shot_id - 1].start
        pre, post, n = c - t.start, t.end - c, t.end - t.start
        if p.frames + post - p.lead - n < 0 or q.frames + pre - n < 0:  # window wider than a shot: hard cut
            continue
        p.frames, p.tail = p.frames + post, n
        q.frames, q.lead = q.frames + pre, n
        q.src_in = max(0.0, q.src_in - pre / 30)
        plan.transitions.append({"after": i, "start": t.start, "end": t.end, "frames": n, "type": t.type.value,
                                 "render": t.render, "loss": t.loss})


def plan_texts(template, shots: list[dict]) -> list[dict]:
    """Template text events with the new words from the filled shots. A slot whose only event was edited through
    the shot card's single text field takes that edit."""
    words, keys = {}, {}
    for raw in shots:
        s = ShotSpec(**raw)
        evs = s.texts
        if len(evs) == 1 and s.text.strip() and s.text.strip() != evs[0]["text"].replace("\n", " ").strip():
            evs = [{**evs[0], "text": s.text.strip()}]
        words |= {x["id"]: x["text"] for x in evs}
        keys |= {x["id"]: x["key_words"] for x in evs if x.get("key_words")}
    out = []
    for e in template.texts:
        d = e.model_dump(mode="json")
        d["text"]["value"] = words.get(e.id, e.text.value)
        if e.id in keys:
            d["key_words"] = keys[e.id]
        out.append(d)
    return out


def _fit_caption(ps: PlanShot) -> None:
    ps.cap_start = CAP_PAD
    ps.cap_end = max(ps.cap_start + 0.3, ps.duration - CAP_PAD)


def _custom_caption_timing(ps: PlanShot, s: ShotSpec) -> None:
    """Use the reference's caption timing when the shot spec has it (seconds after the shot starts)."""
    if s.caption_start is not None:
        ps.cap_start = min(max(0.0, s.caption_start), ps.duration - 0.3)
    if s.caption_end is not None:
        ps.cap_end = min(ps.duration, max(ps.cap_start + 0.3, s.caption_end))


def total_duration(plan: Plan) -> float:
    if plan.n_frames is not None:  # clips overlap inside transition windows
        return plan.n_frames / 30
    return sum(s.duration for s in plan.shots)


def apply_patches(plan: Plan, ops: list[PatchOp], resolve_asset: Callable[[str], dict | None]) -> list[str]:
    """Apply ops in place. Returns notes for ops that were rejected (unknown shot, bad value)."""
    notes = []
    for op in ops:
        shot = next((s for s in plan.shots if s.shot_id == op.shot_id), None)
        if not shot:
            notes.append(f"shot {op.shot_id} not in plan")
            continue
        try:
            _apply(plan, shot, op, resolve_asset)
        except (ValueError, TypeError) as e:
            notes.append(f"shot {op.shot_id} {op.field}: {e}")
    return notes


def _apply(plan: Plan, shot: PlanShot, op: PatchOp, resolve_asset) -> None:
    v = op.value
    f = op.field
    if f == "drop":
        if shot.frames is not None:  # frame-exact plan: a neighbour takes the frames so the audio stays in sync
            if len(plan.shots) == 1:
                raise ValueError("cannot drop the only shot")
            i = plan.shots.index(shot)
            plan.shots[i - 1 if i else 1].frames += shot.frames
        plan.shots.remove(shot)
    elif f == "in":
        shot.src_in = max(0.0, float(v))
        if shot.src_out <= shot.src_in + 0.2:
            raise ValueError("in must stay before out")
        _fit_caption(shot)
    elif f == "out":
        if float(v) <= shot.src_in + 0.2:
            raise ValueError("out must stay after in")
        shot.src_out = float(v)
        _fit_caption(shot)
    elif f == "speed":
        shot.speed = min(2.0, max(0.5, float(v)))
        _fit_caption(shot)
    elif f == "caption":
        shot.caption = str(v or "")
    elif f == "cap_start":
        shot.cap_start = min(max(0.0, float(v)), shot.duration - 0.3)
    elif f == "cap_end":
        shot.cap_end = min(shot.duration, max(shot.cap_start + 0.3, float(v)))
    elif f == "caption_color":
        shot.caption_style = CaptionStyle.model_validate({**shot.caption_style.model_dump(), "color": str(v)})
    elif f == "caption_size":
        shot.caption_style = CaptionStyle.model_validate({**shot.caption_style.model_dump(), "size": int(float(v))})
    elif f == "caption_position":
        shot.caption_style = CaptionStyle.model_validate({**shot.caption_style.model_dump(), "position": str(v)})
    elif f in ("transition", "fit", "animation", "caption_animation"):
        attr = "transition" if f == "transition" else f
        setattr(shot, attr, getattr(PlanShot.model_validate({**shot.model_dump(), attr: str(v)}), attr))  # enum-checked
    elif f == "clip":
        a = resolve_asset(str(v))
        if not a:
            raise ValueError(f"unknown clip {v}")
        shot.asset_id, shot.path = a["id"], a["path"]
        shot.src_in, shot.src_out, shot.speed = 0.0, min(a["duration"], shot.duration), 1.0
        _fit_caption(shot)
