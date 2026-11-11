"""Speed ramps and freezes per slot. Pace = median optical-flow magnitude over the moving pixels of each frame (the
camera move is part of the flow, so a pure camera move reads as steady pace). Change points where the pace shifts by
more than RAMP_RATIO for RAMP_MIN_FRAMES give a piecewise speed curve relative to the slot's median pace.
A slow subject and slow motion look alike: confidence stays low unless the change is abrupt. Freeze: frames that do
not change at all inside a slot that is not a photo. Reverse cannot be measured here (video AI)."""
import cv2
import numpy as np

from .. import ir
from . import boundaries
from .frames import load_mid

NAME, VERSION, DEPS = "speed", 4, ["cuts", "transitions", "camera", "text"]
MOVING_PX = 0.5  # flow (px at 320 wide) above which a pixel counts as moving
RAMP_RATIO = 1.6  # pace change (x or /) that makes a new speed piece
RAMP_MIN_FRAMES = 6  # ... sustained this long
FREEZE_DIFF = 8  # gray change (0..255) a pixel needs to count as changed (above encoder noise)
FREEZE_PX = 30  # fewer changed pixels than this (at 320 wide): the frame repeats the previous one
FREEZE_MIN = 3  # frames


def pace(gray: np.ndarray, keep: np.ndarray | None = None) -> np.ndarray:
    """Per frame (index k: from frame k-1 to k), median flow magnitude of moving pixels; 0 when nothing moves.
    keep: pixels that count (text boxes excluded: an animated caption is not the footage's speed)."""
    out = np.zeros(len(gray))
    for k in range(1, len(gray)):
        fl = cv2.calcOpticalFlowFarneback(gray[k - 1], gray[k], None, 0.5, 4, 21, 3, 5, 1.2, 0)
        mag = np.hypot(fl[..., 0], fl[..., 1])
        mv = mag[(mag > MOVING_PX) & (keep if keep is not None else True)]
        out[k] = float(np.median(mv)) if mv.size > 20 else 0.0
    return out


def freezes(gray: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) runs (slot-relative) where each frame repeats the previous one."""
    changed = (np.abs(np.diff(gray.astype(np.int16), axis=0)) > FREEZE_DIFF).sum(axis=(1, 2))
    still = np.r_[False, changed < FREEZE_PX]
    runs, k = [], 0
    while k < len(still):
        if still[k]:
            j = k
            while j + 1 < len(still) and still[j + 1]:
                j += 1
            if j - k + 1 >= FREEZE_MIN:
                runs.append((k - 1, j + 1))  # the held frame is the one before the first repeat
            k = j + 1
        k += 1
    return runs


def curve(p: np.ndarray, frozen: list[tuple[int, int]]) -> tuple[list[tuple[float, float]], float]:
    """(piecewise speed curve [(position, factor)], confidence) from a pace series; frozen frames are skipped."""
    n = len(p)
    ok = np.ones(n, bool)
    ok[0] = False
    for a, b in frozen:
        ok[max(0, a + 1):b] = False
    if ok.sum() < RAMP_MIN_FRAMES or np.median(p[ok]) <= 0:
        return [(0.0, 1.0)], 0.3
    sm = p.copy()
    for k in range(n):  # 5-frame mean, valid frames only: slow motion repeats frames, so pace alternates 0 / full
        w = [p[j] for j in range(max(0, k - 2), min(n, k + 3)) if ok[j]]
        sm[k] = np.mean(w) if w else 0.0
    starts, cur = [1], []
    k = 1
    while k < n:
        if not ok[k]:
            k += 1
            continue
        seg = [sm[j] for j in range(starts[-1], k) if ok[j]]
        base = np.mean(seg) if len(seg) >= 3 else None
        if base and base > 0 and sm[k] > 0 and abs(np.log(sm[k] / base)) > np.log(RAMP_RATIO):
            run = [j for j in range(k, min(n, k + RAMP_MIN_FRAMES)) if ok[j]]
            if len(run) >= RAMP_MIN_FRAMES - 1 and all(abs(np.log(max(sm[j], 1e-6) / base)) > np.log(RAMP_RATIO)
                                                         for j in run):
                starts.append(k)
                k += RAMP_MIN_FRAMES
                continue
        k += 1
    bounds = [*starts, n]
    paces = [float(np.mean([p[j] for j in range(a, b) if ok[j]] or [0])) for a, b in zip(bounds[:-1], bounds[1:])]
    ref = float(np.median(sm[ok]))
    pts = [(0.0 if i == 0 else a / n, round(v / ref, 3)) for i, (a, v) in enumerate(zip(bounds[:-1], paces))]
    if len(pts) == 1:  # one piece is the slot's own pace: 1x by definition
        return [(0.0, 1.0)], 0.5
    return pts, 0.7


def run(ctx) -> list[ir.Item]:
    gray = load_mid(ctx.key)
    n = len(gray)
    bs = boundaries(ctx.ev)
    edges = [0, *[f for f, _, _ in bs], n]
    photo = {i.start: i.data["value"] == "photo" for i in ctx.ev["camera"] if i.track == "still"}
    items = []
    for k, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        g = np.ascontiguousarray(gray[a:b])
        if len(g) < RAMP_MIN_FRAMES or photo.get(a, False):
            items.append(ir.Item(id=f"speed_{k}", track=NAME, start=a, end=b, conf=0.3, tool="farneback pace",
                                 data={"curve": [(0.0, 1.0)], "freeze": []}))
            continue
        from .camera import _text_mask

        keep = _text_mask(ctx.ev.get("text", []), a, b, g.shape[2], g.shape[1]) > 0
        frz = freezes(np.where(keep, g, 0))
        pts, conf = curve(pace(g, keep), frz)
        items.append(ir.Item(id=f"speed_{k}", track=NAME, start=a, end=b, conf=conf, tool="farneback pace",
                             data={"curve": pts, "freeze": frz}))
    return items
