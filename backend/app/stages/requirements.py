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


def derive(t: ir.Template) -> list[ir.Requirement]:
    """Per slot: what footage it needs. Hard: media type and minimum source length. Soft: framing, subject, motion."""
    out = []
    for s, (lead, tail) in zip(t.slots, overlaps(t)):
        need = footage_frames(s, lead, tail)
        box = s.layout_boxes[0] if s.layout.value in ("split_v", "split_h", "pip", "letterbox", "blur_fill",
                                                        "collage") and s.layout_boxes else None
        orient = "any" if box is None else ("landscape" if box.w * 1080 > box.h * 1920 else "portrait")
        media = "photo" if s.media.value == "photo" else "video"
        cam = s.camera.value if s.camera.value not in REPRODUCED else "static"
        out.append(ir.Requirement(
            media=media, orientation=orient, footage_frames=need, shot_size=s.shot_size.value,
            camera_from_clip=cam, subject_role=s.role.value, movement=s.action.value,
            hard={"media": media, "min_seconds": round(need / ir.FPS, 2)},
            soft={"shot_size": s.shot_size.value, "subject": s.subject.value, "orientation": orient}))
    return out


def apply(t: ir.Template) -> ir.Template:
    for s, r in zip(t.slots, derive(t)):
        s.requirement = r
    return t
