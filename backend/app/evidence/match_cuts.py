"""Match cuts without a model: at a hard cut, the last frame before and the first frame after share their edges (the
subject or a shape stays in the same place and size) while the colours change (a new scene, outfit or location).
Edge overlap is the share of each frame's Canny edges that land near the other's, averaged both ways."""
import cv2
import numpy as np

from .. import ir
from . import boundaries
from .frames import load

NAME, VERSION, DEPS = "match_cuts", 1, ["cuts", "transitions"]
EDGE_MATCH = 0.45  # edge overlap at or above this: the shapes line up across the cut
COLOUR_CHANGE = 0.25  # hue/saturation histogram distance (Bhattacharyya) at or above this: a new scene
MIN_EDGES = 40  # fewer edge pixels than this (flat frame): nothing to match


def _edges(rgb: np.ndarray) -> np.ndarray:
    g = cv2.GaussianBlur(cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2GRAY), (3, 3), 0)
    return cv2.Canny(g, 50, 150) > 0


def edge_overlap(a: np.ndarray, b: np.ndarray) -> tuple[float, np.ndarray]:
    """(symmetric overlap 0..1, mask of the matched edges) for two RGB frames."""
    ea, eb = _edges(a), _edges(b)
    if ea.sum() < MIN_EDGES or eb.sum() < MIN_EDGES:
        return 0.0, np.zeros_like(ea)
    k = np.ones((5, 5), np.uint8)
    da, db = cv2.dilate(ea.astype(np.uint8), k) > 0, cv2.dilate(eb.astype(np.uint8), k) > 0
    both = (ea & db) | (eb & da)
    return float(((ea & db).sum() / ea.sum() + (eb & da).sum() / eb.sum()) / 2), both


def colour_change(a: np.ndarray, b: np.ndarray) -> float:
    def hist(x):
        hsv = cv2.cvtColor(np.ascontiguousarray(x), cv2.COLOR_RGB2HSV)
        hh = cv2.calcHist([hsv], [0, 1], None, [18, 8], [0, 180, 0, 256])
        return cv2.normalize(hh, hh).flatten()

    return float(cv2.compareHist(hist(a), hist(b), cv2.HISTCMP_BHATTACHARYYA))


def run(ctx) -> list[ir.Item]:
    _, rgb = load(ctx.key)
    rgb = np.asarray(rgb)
    n = len(rgb)
    items = []
    for f, s, e in boundaries(ctx.ev):
        if e > s or not 0 < f < n:  # gradual transitions are not match cuts
            continue
        ov, mask = edge_overlap(rgb[f - 1], rgb[f])
        cc = colour_change(rgb[f - 1], rgb[f])
        if ov < EDGE_MATCH or cc < COLOUR_CHANGE:
            continue
        ys, xs = np.nonzero(mask)
        h, w = mask.shape
        box = {"x": xs.min() / w, "y": ys.min() / h, "w": (xs.max() - xs.min() + 1) / w,
               "h": (ys.max() - ys.min() + 1) / h} if len(xs) else {"x": 0, "y": 0, "w": 1, "h": 1}
        items.append(ir.Item(id=f"match_cuts_{len(items)}", track=NAME, start=f, end=f, conf=0.5,
                             tool="canny edge overlap + hsv histogram",
                             data={"frame": f, "overlap": round(ov, 3), "colour_change": round(cc, 3), "box": box}))
    return items
