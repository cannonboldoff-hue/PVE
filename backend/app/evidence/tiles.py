"""Per-box motion in multi-box layouts (split screen, picture in picture, collage). Each box is its own shot: the
whole-frame camera and speed tracks mix them, so here each box region is measured on its own with the same tools
(camera path + shake windows + zoom punches, pace curve + freezes). A box that shows no cut at the slot's start
while the frame as a whole does keeps playing the previous slot's clip ("continues")."""
import numpy as np

from .. import ir
from . import camera, speed
from .frames import load_mid

NAME, VERSION, DEPS = "tiles", 1, ["cuts", "transitions", "text", "layout", "camera"]
MULTI = ("split_h", "split_v", "pip", "collage")
CONT_DIFF = 14  # mean gray change (0..255) across the boundary below which a box did not cut


def _crop(g: np.ndarray, box: dict) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    h, w = g.shape[-2:]
    x0, y0 = int(box["x"] * w), int(box["y"] * h)
    x1, y1 = max(x0 + 8, int((box["x"] + box["w"]) * w)), max(y0 + 8, int((box["y"] + box["h"]) * h))
    return np.ascontiguousarray(g[..., y0:y1, x0:x1]), (x0, y0, x1, y1)


def continues(gray: np.ndarray, a: int, box: dict) -> bool:
    """Box region barely changes from the frame before the slot to its first frame."""
    if a <= 0 or a >= len(gray):
        return False
    before, _ = _crop(gray[a - 1], box)
    after, _ = _crop(gray[a], box)
    return float(np.abs(before.astype(np.int16) - after.astype(np.int16)).mean()) < CONT_DIFF


def measure(g: np.ndarray, mask: np.ndarray) -> dict:
    """Camera and speed of one box's frames (n, h, w)."""
    n, h, w = g.shape
    eye = np.array([[1.0, 0, 0], [0, 1.0, 0]])
    As = camera.track(g, mask) if n > 2 else [eye] * n
    path = np.array([camera.view(A, w, h) for A in As])
    move, info = camera.classify(path) if n > 2 else ("static", {})
    hits = camera.punches(path)
    out = {"camera": move, "path": camera.keyframes(path, hits), "shake_windows": camera.shake_windows(path),
           "punches": hits, "shake": info.get("shake", {})}
    if n >= speed.RAMP_MIN_FRAMES:
        keep = mask > 0
        frz = speed.freezes(np.where(keep, g, 0))
        out["curve"], _ = speed.curve(speed.pace(g, keep), frz)
        out["freeze"] = frz
    return out


def run(ctx) -> list[ir.Item]:
    gray = load_mid(ctx.key)
    n, h, w = gray.shape
    items = []
    for lay in ctx.ev.get("layout", []):
        boxes = lay.data.get("boxes") or []
        if lay.data.get("value") not in MULTI or len(boxes) < 2:
            continue
        a, b = max(0, lay.start), min(n, lay.end)
        if b - a < 3:
            continue
        full_mask = camera._text_mask(ctx.ev.get("text", []), a, b, w, h)
        tiles = []
        for k, box in enumerate(boxes):
            g, (x0, y0, x1, y1) = _crop(gray[a:b], box)
            t = measure(g, np.ascontiguousarray(full_mask[y0:y1, x0:x1]))
            tiles.append({"box": k, **t, "continues": continues(gray, a, box)})
        items.append(ir.Item(id=f"tiles_{len(items)}", track=NAME, start=a, end=b, conf=0.6,
                             tool="opencv lk + ransac similarity, farneback pace (per box)",
                             data={"value": lay.data["value"], "tiles": tiles}))
    return items
