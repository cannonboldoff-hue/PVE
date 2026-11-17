"""Template -> what footage each slot needs."""
from .. import ir
from ..render.shot import footage


def footage_frames(slot: ir.Slot, lead: int = 0, tail: int = 0) -> int:
    """Source frames the slot consumes: the area under its speed curve over its length plus the transition
    overlaps (at the curve's end speeds), minus freezes (a held frame uses no extra footage)."""
    first, last = slot.speed[0][1], sorted(slot.speed)[-1][1]
    return footage(slot.frames, slot.speed, slot.freeze) + round(lead * first) + round(tail * last)


# camera moves the renderer redoes on any clip: the clip itself can be still
REPRODUCED = {"static", "zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "handheld", "shake"}


def overlaps(t: ir.Template) -> list[tuple[int, int]]:
    """(lead, tail) transition window lengths per slot."""
    win = {x.after_slot: x.end - x.start for x in t.transitions}
    out = []
    for k, s in enumerate(t.slots):
        lead = win.get(t.slots[k - 1].id, 0) if k else 0
        out.append((lead, win.get(s.id, 0)))
    return out


def _orient(box: ir.Box | None) -> str:
    return "any" if box is None else ("landscape" if box.w * 1080 > box.h * 1920 else "portrait")


def _tile_req(s: ir.Slot, k: int, box: ir.Box, lead: int, tail: int) -> ir.Requirement:
    """One extra box of a multi-box slot (box 0 is the slot's own requirement)."""
    tile = s.tiles[k] if k < len(s.tiles) else None
    frames = footage(s.frames, tile.speed, tile.freeze) if tile else s.frames + lead + tail
    lines = [f"Box {k + 1}: {tile.role if tile and tile.role else 'its own clip'}, "
             f"{_orient(box)}, at least {frames / ir.FPS:.1f} s"]
    if tile and tile.continues:
        lines.append(f"Box {k + 1} keeps playing from the previous shot: use one longer clip, not a new one")
    return ir.Requirement(media="video", orientation=_orient(box), footage_frames=frames, instructions=lines,
                          hard={"media": "video", "min_seconds": round(frames / ir.FPS, 2)},
                          soft={"orientation": _orient(box), "role": tile.role if tile else ""})


def instructions(t: ir.Template, k: int, media: str, need: int) -> list[str]:
    """Plain-language shot list lines for slot k: what to bring and how to frame it."""
    s, out = t.slots[k], []
    what = {"photo": "a photo", "cutout": "a clip", "video": "a clip"}[media]
    out.append(f"Shot {k + 1}: {what} of {s.subject.value or 'your subject'}"
               + (f" ({s.action.value})" if s.action.value else "") + f", at least {need / ir.FPS:.1f} s")
    prev = next((x for x in t.transitions if k and x.after_slot == t.slots[k - 1].id), None)
    if prev is not None and prev.params.get("match_cut"):
        out.append(f"Match cut from shot {k}: keep the subject in the same spot and size as in shot {k}, change the "
                   "scene, outfit or location")
    for x in t.layers:
        if not s.start <= x.start < s.end:
            continue
        if x.kind.value == "cutout":
            out.append("Also bring the subject cut out on a transparent background (WebM or MOV with alpha; a PNG "
                       "loses its alpha): " + ("it is drawn in front of the on-screen text" if x.above_text else
                                               "it is drawn over the footage"))
        elif x.kind.value == "moving_layer":
            out.append(f"Also bring the picture or clip that moves across the frame ({x.shape or x.kind.raw or 'layer'})")
    if s.reverse:
        out.append("Film the action forwards: it is played backwards")
    return out


def derive(t: ir.Template) -> list[ir.Requirement]:
    """Per slot: what footage it needs. Hard: media type and minimum source length. Soft: framing, subject, motion.
    Instructions: the shot list the user films or picks to."""
    out = []
    for k, (s, (lead, tail)) in enumerate(zip(t.slots, overlaps(t))):
        need = footage_frames(s, lead, tail)
        multi = s.layout.value in ("split_v", "split_h", "pip", "letterbox", "blur_fill", "collage") and s.layout_boxes
        box = s.layout_boxes[0] if multi else None
        orient = _orient(box)
        media = "photo" if s.media.value == "photo" else "video"
        cam = s.camera.value if s.camera.value not in REPRODUCED else "static"
        tiles = [_tile_req(s, j, b, lead, tail) for j, b in enumerate(s.layout_boxes) if j] if multi else []
        lines = instructions(t, k, media, need)
        if s.tiles and s.tiles[0].role:
            lines[0] += f" (box 1: {s.tiles[0].role})"
        out.append(ir.Requirement(
            media=media, orientation=orient, footage_frames=need, shot_size=s.shot_size.value,
            camera_from_clip=cam, subject_role=s.role.value, movement=s.action.value,
            hard={"media": media, "min_seconds": round(need / ir.FPS, 2)},
            soft={"shot_size": s.shot_size.value, "subject": s.subject.value, "orientation": orient},
            instructions=lines + [x for r in tiles for x in r.instructions], tiles=tiles))
    return out


def apply(t: ir.Template) -> ir.Template:
    for s, r in zip(t.slots, derive(t)):
        s.requirement = r
    return t
