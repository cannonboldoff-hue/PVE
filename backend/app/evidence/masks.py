"""Shape masks without a segmentation model: footage shown through a shape over a flat background. Per slot, the
pixels that never change and share one colour are the background; the bounding box of everything else is the shape's
box, and its fill share of that box hints the shape (about 0.79 for a circle or ellipse, near 1 for a rectangle).
track_box follows a box the video AI reported (a moving layer) by template matching."""
import cv2
import numpy as np

from .. import ir
from . import boundaries
from .frames import load

NAME, VERSION, DEPS = "masks", 1, ["cuts", "transitions", "text"]
STATIC_STD = 4.0  # temporal std (0..255) below which a pixel is static
FLAT = 18.0  # colour distance to the background median that still counts as background
MIN_BG = 0.2  # share of the frame that must be flat static background
MAX_BG = 0.9
TRACK_EVERY = 5  # frames between tracked keys
TRACK_MIN = 0.5  # normalised match score below which the layer is lost


def shape_region(rgb: np.ndarray, ignore: np.ndarray | None = None) -> dict | None:
    """rgb (n, h, w, 3) of one slot -> {box, bg, fill} when a flat static background frames the footage.
    ignore: pixels (captions) that are neither footage nor background."""
    if len(rgb) < 4:
        return None
    f = rgb.astype(np.float32)
    static = f.std(axis=0).max(axis=-1) < STATIC_STD
    if not static.any():
        return None
    mean = f.mean(axis=0)
    bg = np.median(mean[static], axis=0)
    flat = static & (np.linalg.norm(mean - bg, axis=-1) < FLAT)
    share = float(flat.mean())
    if ignore is not None:
        flat |= ignore
    if not MIN_BG <= share <= MAX_BG:
        return None
    ys, xs = np.nonzero(~flat)
    if not len(xs):
        return None
    h, w = flat.shape
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    inside = (~flat[y0:y1, x0:x1]).mean()
    return {"box": {"x": x0 / w, "y": y0 / h, "w": (x1 - x0) / w, "h": (y1 - y0) / h},
            "bg": "#{:02X}{:02X}{:02X}".format(*[int(v) for v in bg]), "fill": round(float(inside), 3),
            "background": round(share, 3)}


def track_box(rgb: np.ndarray, box: ir.Box) -> list[tuple[int, ir.Box]]:
    """Follow the patch inside box from frame 0 through rgb (n, h, w, 3); (relative frame, box) every TRACK_EVERY
    frames while the match holds."""
    n, h, w = rgb.shape[:3]
    x0, y0 = int(box.x * w), int(box.y * h)
    bw, bh = max(4, int(box.w * w)), max(4, int(box.h * h))
    gray = [cv2.cvtColor(np.ascontiguousarray(f), cv2.COLOR_RGB2GRAY) for f in rgb]
    patch = gray[0][y0:y0 + bh, x0:x0 + bw]
    if patch.shape[0] < 4 or patch.shape[1] < 4 or patch.std() < 2:
        return []
    out = [(0, box)]
    for k in range(TRACK_EVERY, n, TRACK_EVERY):
        r = cv2.matchTemplate(gray[k], patch, cv2.TM_CCOEFF_NORMED)
        _, score, _, (x, y) = cv2.minMaxLoc(r)
        if score < TRACK_MIN:
            break
        out.append((k, ir.Box(x=x / w, y=y / h, w=bw / w, h=bh / h)))
    return out


def run(ctx) -> list[ir.Item]:
    _, rgb = load(ctx.key)
    rgb = np.asarray(rgb)
    n = len(rgb)
    bs = boundaries(ctx.ev)
    edges = [0, *[f for f, _, _ in bs], n]
    items = []
    h, w = rgb.shape[1:3]
    for k, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        cap = np.zeros((h, w), bool)
        for t in ctx.ev.get("text", []):
            if t.start < b and t.end > a:
                bx = t.data["box"]
                cap[int(bx["y"] * h):int((bx["y"] + bx["h"]) * h) + 1, int(bx["x"] * w):int((bx["x"] + bx["w"]) * w) + 1] = True
        r = shape_region(rgb[a:b], cap)
        if r:
            items.append(ir.Item(id=f"masks_{len(items)}", track=NAME, start=a, end=b, conf=0.6,
                                 tool="static flat background", data={"value": "shape_mask", **r}))
    return items
