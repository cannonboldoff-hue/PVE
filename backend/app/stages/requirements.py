"""Template -> what footage each slot needs."""
from .. import ir
from ..render.shot import footage


def footage_frames(slot: ir.Slot, lead: int = 0, tail: int = 0) -> int:
    """Source frames the slot consumes: the area under its speed curve over its length plus the transition
    overlaps (at the curve's end speeds), minus freezes (a held frame uses no extra footage)."""
    first, last = slot.speed[0][1], sorted(slot.speed)[-1][1]
    return footage(slot.frames, slot.speed, slot.freeze) + round(lead * first) + round(tail * last)
