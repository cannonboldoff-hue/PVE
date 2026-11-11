"""Frame layout per slot, from the slot's time-averaged colour picture (160 px wide):
letterbox / pillarbox: constant bands on two sides; blur fill: bands with almost no detail around a detailed
picture; split screen: one straight edge running the whole height (or width); picture in picture: a rectangle of
straight edges inside the frame; collage: several such rectangles. Boxes are normalised content regions."""
import cv2
import numpy as np

from .. import ir
from . import boundaries
from .frames import load

NAME, VERSION, DEPS = "layout", 11, ["cuts", "transitions", "overlays"]
EDGE = 6.0  # gradient of the blurred time-averaged colour picture (levels per px) that makes an edge pixel
TEXTURE_X = 2.5  # an edge must be this many times the slot's median gradient
BLUR = 9  # box blur (px at 160 wide) that averages texture away before edges are taken
LINE_MIN = 0.12  # a straight edge run must cover this share of the frame side
FULL = 0.93  # ... and this share to be a split line
BORDER = 0.12  # split lines this close to the frame edge are borders, not splits
GAP = 5  # px
STEP = 20.0  # mean colour step across a split line (levels), in every band
BANDS_NEEDED = 6  # strips that must show the step (a subject may cross the line in the others)
BANDS = 8  # the frame is cut into this many strips to check a split runs the whole length
BAND_DETAIL = 0.25  # band rows with less detail than this share of the picture's rows: fill, not content
BAND_MIN = 0.05  # bands thinner than this share of the height are ignored
FLAT = 3.0  # spatial std of a band row below which it is a constant bar (letterbox)
BAR_STEP = 25.0  # gray difference between a bar and the picture edge
INSET_MIN = 0.2  # an inset picture is at least this share of each side
INSET_STEP = 15.0  # mean colour difference between an inset and its surroundings
SPAN = 0.7  # a picture between bands has detail across this share of the frame


def _runs(mask_1d: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    """Runs of True at least min_len long; gaps up to GAP long inside a run are bridged (texture breaks edges)."""
    mask_1d = mask_1d.copy()
    idx = np.nonzero(mask_1d)[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= GAP:
            mask_1d[a:b] = True
    out, k, n = [], 0, len(mask_1d)
    while k < n:
        if mask_1d[k]:
            j = k
            while j + 1 < n and mask_1d[j + 1]:
                j += 1
            if j - k + 1 >= min_len:
                out.append((k, j + 1))
            k = j
        k += 1
    return out


def lines(mean: np.ndarray, ignore: np.ndarray | None = None) -> tuple[list, list]:
    """Straight persistent edges between regions: vertical (x, y0, y1) and horizontal (y, x0, x1) runs, in pixels.
    mean: time-averaged colour picture. A box blur averages texture away first (two textures side by side differ in
    colour, not in gray detail); the gradient is the largest over the colour channels."""
    h, w = mean.shape[:2]
    m = cv2.blur(mean, (BLUR, BLUR))
    gx = (np.abs(cv2.Sobel(m, cv2.CV_32F, 1, 0, ksize=3)) / 4).reshape(h, w, -1).max(axis=2)
    gy = (np.abs(cv2.Sobel(m, cv2.CV_32F, 0, 1, ksize=3)) / 4).reshape(h, w, -1).max(axis=2)
    if ignore is not None:  # overlays sit on every shot: their outline is not the shot's layout
        gx[ignore], gy[ignore] = 0, 0
    thr = max(EDGE, TEXTURE_X * float(np.median(np.r_[gx.ravel(), gy.ravel()])))  # textured footage: higher bar
    vx = [(x, a, b) for x in range(1, w - 1) for a, b in _runs(gx[:, x] > thr, int(LINE_MIN * h))]
    hy = [(y, a, b) for y in range(1, h - 1) for a, b in _runs(gy[y, :] > thr, int(LINE_MIN * w))]
    lines.masks = (gx > thr, gy > thr)  # for rectangles(): side coverage is checked on the edge maps
    return _dedup(vx), _dedup(hy)


def _dedup(runs: list) -> list:
    """An edge is 2-3 px wide after Sobel: keep the longest run of each neighbouring group."""
    out: list = []
    for r in sorted(runs, key=lambda r: -(r[2] - r[1])):
        if not any(abs(r[0] - o[0]) <= 3 and min(r[2], o[2]) - max(r[1], o[1]) > 0.5 * (r[2] - r[1]) for o in out):
            out.append(r)
    return out


def split_line(colour: np.ndarray, axis: int) -> int | None:
    """Position of a straight line across the whole frame with a different mean colour on each side, checked in
    BANDS strips along it so a local edge does not count. axis=1: vertical line (columns), 0: horizontal."""
    c = colour if axis == 1 else colour.transpose(1, 0, 2)
    h, w = c.shape[:2]
    lo, hi = int(BORDER * w), int((1 - BORDER) * w)
    best = None
    for x in range(lo, hi):
        steps = []
        for band in np.array_split(c, BANDS, axis=0):
            left, right = band[:, max(0, x - 10):x - 1].mean(axis=(0, 1)), band[:, x + 2:x + 11].mean(axis=(0, 1))
            steps.append(np.abs(left - right).max())
        q = float(np.sort(steps)[BANDS - BANDS_NEEDED])  # the step holds in BANDS_NEEDED of the strips
        if q > STEP and (best is None or q > best[1]):
            best = (x, q)
    return best[0] if best else None


def rectangles(vx: list, hy: list, w: int, h: int, cover: float = 0.6) -> list[tuple[int, int, int, int]]:
    """(x0, y0, x1, y1) rectangles whose four sides are edges along at least `cover` of their length. Candidate
    sides come from the straight runs; texture and content crossing the border break runs, so runs need not end
    at the corners."""
    ex, ey = lines.masks
    exd = ex | np.roll(ex, 1, 1) | np.roll(ex, -1, 1)  # one pixel of slack across the edge
    eyd = ey | np.roll(ey, 1, 0) | np.roll(ey, -1, 0)
    xs = sorted({x for x, _, _ in vx})
    ys = sorted({y for y, _, _ in hy})
    out = []
    for i, x0 in enumerate(xs):
        for x1 in xs[i + 1:]:
            if x1 - x0 < LINE_MIN * w:
                continue
            for j, y0 in enumerate(ys):
                for y1 in ys[j + 1:]:
                    if y1 - y0 < LINE_MIN * h or (x1 - x0 > 0.95 * w and y1 - y0 > 0.95 * h):
                        continue
                    sides = (exd[y0:y1, x0].mean(), exd[y0:y1, x1].mean(), eyd[y0, x0:x1].mean(), eyd[y1, x0:x1].mean())
                    if min(sides) >= cover:
                        out.append((min(sides), (x0, y0, x1 + 1, y1)))
    keep: list = []
    for _, r in sorted(out, reverse=True):  # best covered first; drop near-duplicates and boxes inside a kept one
        if not any(r[0] >= k[0] - 4 and r[1] >= k[1] - 4 and r[2] <= k[2] + 4 and r[3] <= k[3] + 4 or
                   k[0] >= r[0] - 4 and k[1] >= r[1] - 4 and k[2] <= r[2] + 4 and k[3] <= r[3] + 4 for k in keep):
            keep.append(r)
    return keep


def _inset_like(colour: np.ndarray, r: tuple[int, int, int, int]) -> bool:
    """Big enough and a different picture from what surrounds it (not the strokes of a glyph or a logo)."""
    h, w = colour.shape[:2]
    x0, y0, x1, y1 = r
    if (x1 - x0) < INSET_MIN * w or (y1 - y0) < INSET_MIN * h:
        return False
    m = 6
    ring = np.ones((h, w), bool)
    ring[:max(0, y0 - m)] = ring[y1 + m:] = False
    ring[:, :max(0, x0 - m)] = ring[:, x1 + m:] = False
    ring[y0:y1, x0:x1] = False
    if not ring.any():
        return True
    return float(np.abs(colour[y0:y1, x0:x1].mean(axis=(0, 1)) - colour[ring].mean(axis=0)).max()) > INSET_STEP


def _box(x0, y0, x1, y1, w, h) -> dict:
    return ir.Box(x=x0 / w, y=y0 / h, w=(x1 - x0) / w, h=(y1 - y0) / h).model_dump()


def classify(frames: np.ndarray, ignore: np.ndarray | None = None) -> tuple[str, list[dict], float]:
    """(Layout, content boxes, confidence) for one slot's RGB frames (n, h, w, 3)."""
    n, h, w = frames.shape[:3]
    colour = frames.astype(np.float32).mean(0)
    mean = colour.mean(axis=2) if colour.ndim == 3 else colour
    full = [_box(0, 0, w, h, w, h)]
    # bands: rows (then columns) with little detail around a detailed middle
    lap = np.abs(cv2.Laplacian(mean, cv2.CV_32F))
    for axis, size in ((1, h), (0, w)):
        detail = lap.mean(axis=axis)
        flat = mean.std(axis=axis)
        ref = np.percentile(detail, 90)
        content = detail > BAND_DETAIL * ref
        idx = np.nonzero(content)[0]
        if len(idx) == 0:
            continue
        a, b = idx[0], idx[-1] + 1
        if a / size < BAND_MIN or (size - b) / size < BAND_MIN:
            continue
        bands = np.r_[flat[:a], flat[b:]]
        across = lap[a:b].mean(axis=0) if axis == 1 else lap[:, a:b].mean(axis=1)
        if (across > BAND_DETAIL * ref).mean() < SPAN:
            continue  # detail only in the middle (a subject on plain footage), not a picture filling a band
        bar = np.r_[(mean[:a] if axis == 1 else mean[:, :a]).ravel(), (mean[b:] if axis == 1 else mean[:, b:]).ravel()]
        edge = (mean[a:a + 3] if axis == 1 else mean[:, a:a + 3]).mean()
        barlike = bar.mean() < 25 or bar.mean() > 230 or abs(bar.mean() - edge) > BAR_STEP
        # a heavy blur is nearly flat too: a bar is also black / white or clearly unlike the picture's edge
        kind = "letterbox" if np.median(bands) < FLAT and barlike else "blur_fill"
        box = _box(0, a, w, b, w, h) if axis == 1 else _box(a, 0, b, h, w, h)
        return kind, [box], 0.8
    sv, sh = split_line(colour, 1), split_line(colour, 0)
    if sv is not None and sh is None:
        return "split_v", [_box(0, 0, sv, h, w, h), _box(sv, 0, w, h, w, h)], 0.8
    if sh is not None and sv is None:
        return "split_h", [_box(0, 0, w, sh, w, h), _box(0, sh, w, h, w, h)], 0.8
    vx, hy = lines(colour, ignore)
    splits_v, splits_h = ([sv] if sv is not None else []), ([sh] if sh is not None else [])
    rects = [r for r in rectangles(vx, hy, w, h) if _inset_like(colour, r)]
    if len(rects) >= 2 or (splits_v and splits_h):
        boxes = [_box(*r, w, h) for r in rects] or full
        return "collage", boxes, 0.6
    if len(rects) == 1:
        return "pip", [full[0], _box(*rects[0], w, h)], 0.7
    return "single", full, 0.6


def run(ctx) -> list[ir.Item]:
    _, rgb = load(ctx.key)
    n = len(rgb)
    bs = boundaries(ctx.ev)
    edges = [0, *[f for f, _, _ in bs], n]
    h, w = rgb.shape[1:3]
    ignore = np.zeros((h, w), bool)
    for o in ctx.ev.get("overlays", []):
        bx = o.data["box"]
        ignore[max(0, int(bx["y"] * h) - 3):int((bx["y"] + bx["h"]) * h) + 4,
               max(0, int(bx["x"] * w) - 3):int((bx["x"] + bx["w"]) * w) + 4] = True
    items = []
    for k, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        a2 = max(a, bs[k - 1][2]) if k else a  # body only: transition windows mix two layouts
        b2 = min(b, bs[k][1]) if k < len(bs) and bs[k][1] > a2 + 2 else b
        value, boxes, conf = classify(np.asarray(rgb[a2:b2]), ignore)
        items.append(ir.Item(id=f"layout_{k}", track=NAME, start=a, end=b, conf=conf, tool="persistent edges",
                             data={"value": value, "boxes": boxes}))
    return items
