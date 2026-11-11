"""Shot boundaries with their window and a coarse transition class.

Window: around each hard cut, and around each run of raised frame difference that is not a cut, the frames whose
difference to the previous frame stands out from the shots' own motion. A one-frame spike is a hard cut (window
start == end); a run is a gradual transition [s, e): frame s is the first that is no longer pure shot A, frame e
the first that is pure shot B.

Class, from A = frame s-1 and B = frame e: a brightness dip or peak (fade to black / white); every pixel a fixed mix
of A and B (fade); pixels already A or B, scattered (dissolve) or split by a straight edge (wipe); A still in place
while the rest matches neither (slide: B moves in over A); neither in place (push, whip, zoom, spin: optical flow)."""
import cv2
import numpy as np

from .. import ir
from .frames import load
from .text import read_frames

NAME, VERSION, DEPS = "transitions", 1, ["cuts"]
TRANS_WINDOW = 15  # frames examined each side of a boundary
MOTION_X = 3.0  # a frame difference this many times the shots' own motion is part of a boundary
MIN_JUMP = 0.02  # ... and at least this share of the A-B difference
GRADUAL_MIN = 3  # frames of raised difference that make a gradual boundary without a detected cut
SHOT_DIFF = 20.0  # mean gray difference between the frames around a run for it to be a shot change, not motion
DIFF_PX = 60  # per-pixel A/B difference (sum of RGB) that makes a pixel informative
NEAR = 0.25  # a pixel within this share of the A-B difference of A (or B) is "A" (or "B")
FADE_FIT = 0.15  # mean residual (share of A-B) of the best single mix ratio below which it is a fade
STILL_FLOW = 0.3  # mean flow (px at 160 wide) below which nothing moves
FLASH_MAX = 4  # frames: a brighter burst this short with the same shot on both sides is a flash
FLASH_JUMP = 30.0  # mean luma rise inside it
DIP = 0.6  # luma below this share of the darker end (or above the brighter end by the same) is a fade via black/white


def _diff(gray: np.ndarray) -> np.ndarray:
    d = np.zeros(len(gray))
    d[1:] = np.abs(np.diff(gray.astype(np.int16), axis=0)).mean(axis=(1, 2))
    return d


def _window(d: np.ndarray, gray: np.ndarray, c: int, n: int) -> tuple[int, int]:
    """[s, e) of raised difference around c."""
    lo, hi = max(1, c - TRANS_WINDOW), min(n - 1, c + TRANS_WINDOW)
    outside = np.r_[d[max(1, c - 2 * TRANS_WINDOW):lo], d[hi + 1:min(n, c + 2 * TRANS_WINDOW)]]
    base = float(np.median(outside)) if len(outside) else 0.0
    jump = float(np.abs(gray[max(0, lo - 1)].astype(np.int16) - gray[min(n - 1, hi)].astype(np.int16)).mean())
    thr = max(MOTION_X * base + 0.5, MIN_JUMP * jump)
    up = d > thr
    near = [f for f in range(max(lo, c - 2), min(hi, c + 2) + 1) if up[f]]
    if not near:
        return c, c
    f0 = min(near, key=lambda f: abs(f - c))
    s = e = f0
    while s - 1 >= lo and (up[s - 1] or (s - 2 >= lo and up[s - 2])):  # one quiet frame inside a run is allowed
        s -= 1 if up[s - 1] else 2
    while e + 1 <= hi and (up[e + 1] or (e + 2 <= hi and up[e + 2])):
        e += 1 if up[e + 1] else 2
    if s == e:  # one frame: hard cut at e
        return e, e
    return s, e


def _mids(s: int, e: int) -> list[int]:
    return [s + (e - s) * q // 4 for q in (1, 2, 3)]


def classify(rgb, gray: np.ndarray, s: int, e: int) -> tuple[str, float, dict]:
    """(TransitionType, conf, signals) for window [s, e). rgb: frame index -> full-resolution frame (a dissolve
    switches single pixels; a downscaled frame averages them into a fade)."""
    if e <= s:
        return "cut", 1.0, {}
    A, B = rgb[s - 1].astype(np.int16), rgb[e].astype(np.int16)
    mids = _mids(s, e)
    luma = [float(gray[f].mean()) for f in range(s - 1, e + 1)]
    la, lb = luma[0], luma[-1]
    sig = {"luma_min": round(min(luma), 2), "luma_max": round(max(luma), 2), "luma_a": la, "luma_b": lb}
    if min(luma[1:-1] or [la]) < DIP * min(la, lb) and min(luma) < 60:
        return "fade_black", 0.8, sig
    if max(luma[1:-1] or [la]) > max(la, lb) + (1 - DIP) * (255 - max(la, lb)) and max(luma) > 200:
        return "fade_white", 0.8, sig
    dab = np.abs(A - B).sum(-1)
    P = dab > DIFF_PX
    if P.sum() < 50:
        return "fade", 0.4, sig
    fits, closeA, closeB, coher = [], [], [], []
    for f in mids:
        F = rgb[f].astype(np.int16)
        num = ((F - B) * (A - B)).sum(-1)[P]
        den = ((A - B) ** 2).sum(-1)[P]
        alpha = float(num.sum() / max(1, den.sum()))
        resid = np.abs(F - (alpha * A + (1 - alpha) * B)).sum(-1)[P] / dab[P]
        fits.append(float(resid.mean()))
        dA, dB = np.abs(F - A).sum(-1), np.abs(F - B).sum(-1)
        isA, isB = (dA < NEAR * dab) & P, (dB < NEAR * dab) & P
        closeA.append(isA.sum() / P.sum())
        closeB.append(isB.sum() / P.sum())
        if isB.sum() > 20:  # coherent B region: neighbours of B pixels are B too
            nb = np.zeros_like(isB)
            nb[1:] |= isB[:-1]; nb[:-1] |= isB[1:]; nb[:, 1:] |= isB[:, :-1]; nb[:, :-1] |= isB[:, 1:]
            inner = isB[1:-1, 1:-1] & isB[:-2, 1:-1] & isB[2:, 1:-1] & isB[1:-1, :-2] & isB[1:-1, 2:]
            coher.append(inner.sum() / max(1, isB.sum()))
    sig |= {"fade_fit": round(float(np.median(fits)), 3), "close_a": round(float(np.median(closeA)), 3),
            "close_b": round(float(np.median(closeB)), 3), "coherence": round(float(np.median(coher or [0])), 3)}
    if sig["fade_fit"] < FADE_FIT and sig["close_a"] + sig["close_b"] < 0.5:
        return "fade", 0.8, sig
    m = mids[1]
    F = rgb[m].astype(np.int16)
    isA = (np.abs(F - A).sum(-1) < NEAR * dab) & P
    isB = (np.abs(F - B).sum(-1) < NEAR * dab) & P
    if sig["close_a"] + sig["close_b"] > 0.7:
        if sig["coherence"] < 0.5:
            return "dissolve", 0.8, sig
        return "wipe_" + _side(isB, P, entering=True), 0.8, sig
    if sig["close_a"] > 0.25:  # A held still on one side: B moves in over it from the other
        return "slide_" + _side(isA, P, entering=False), 0.7, sig
    return _flow_class(gray, s, e, sig)


def _side(mask: np.ndarray, P: np.ndarray, entering: bool) -> str:
    """Direction of travel of the boundary. entering=True: mask is the arriving shot; False: the leaving shot."""
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    cx, cy = xs.mean() / w - 0.5, ys.mean() / h - 0.5
    if not entering:
        cx, cy = -cx, -cy  # the leaving shot sits opposite the arriving one
    if abs(cx) >= abs(cy):
        return "left" if cx > 0 else "right"  # arriving on the right: the edge travels left
    return "up" if cy > 0 else "down"


def _flow_class(gray: np.ndarray, s: int, e: int, sig: dict) -> tuple[str, float, dict]:
    fx, fy, div, curl, blur = [], [], [], [], []
    h, w = gray.shape[1:]
    yy, xx = np.mgrid[0:h, 0:w]
    rx, ry = xx - w / 2, yy - h / 2
    for f in range(max(s, 1), min(e + 1, len(gray))):
        fl = cv2.calcOpticalFlowFarneback(gray[f - 1], gray[f], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        fx.append(fl[..., 0].mean()); fy.append(fl[..., 1].mean())
        div.append(float((fl[..., 0] * rx + fl[..., 1] * ry).mean() / (w * h / 8)))
        curl.append(float((fl[..., 1] * rx - fl[..., 0] * ry).mean() / (w * h / 8)))
        blur.append(cv2.Laplacian(gray[f], cv2.CV_64F).var())
    mx, my = float(np.mean(fx)), float(np.mean(fy))
    dv, cu = float(np.mean(div)), float(np.mean(curl))
    sharp = min(cv2.Laplacian(gray[s - 1], cv2.CV_64F).var(), cv2.Laplacian(gray[min(e, len(gray) - 1)], cv2.CV_64F).var())
    blurred = bool(min(blur) < 0.5 * sharp)
    sig |= {"flow": [round(mx, 2), round(my, 2)], "div": round(dv, 3), "curl": round(cu, 3), "blurred": blurred}
    if np.hypot(mx, my) < STILL_FLOW and abs(dv) < 0.05 and abs(cu) < 0.05 and sig.get("coherence", 1) < 0.3:
        return "dissolve", 0.6, sig  # nothing moves, no single mix fits, the new shot shows through in specks
    if abs(cu) > max(abs(dv), 0.2) and abs(cu) > 0.1:
        return "spin", 0.5, sig
    if abs(dv) > 0.1 and abs(dv) > abs(cu):
        return ("zoom_in" if dv > 0 else "zoom_out"), 0.5, sig
    direction = ("left" if mx < 0 else "right") if abs(mx) >= abs(my) else ("up" if my < 0 else "down")
    return (f"whip_{direction}" if blurred else f"push_{direction}"), 0.5, sig


def _gradual(d: np.ndarray, gray: np.ndarray) -> list[int]:
    """Centres of runs of raised difference that join two different-looking stretches (fades the cut detectors miss)."""
    thr = MOTION_X * float(np.median(d[1:])) + 0.5 if len(d) > 1 else 1e9
    up = d > thr
    out, f, n = [], 1, len(d)
    while f < n:
        if up[f]:
            g = f
            while g + 1 < n and up[g + 1]:
                g += 1
            if g - f + 1 >= GRADUAL_MIN and \
                    np.abs(gray[f - 1].astype(np.int16) - gray[min(n - 1, g + 1)].astype(np.int16)).mean() > SHOT_DIFF:
                out.append((f + g + 1) // 2)
            f = g + 1
        f += 1
    return out


def _is_flash(gray: np.ndarray, c: int) -> bool:
    n = len(gray)
    for f in range(max(1, c - FLASH_MAX), c + 1):  # flash starts at f, the cut detector may fire at f or after it
        for L in range(1, FLASH_MAX + 1):
            if f + L >= n:
                break
            before, after = gray[f - 1].astype(np.int16), gray[f + L].astype(np.int16)
            inside = gray[f:f + L].astype(np.int16)
            if np.abs(before - after).mean() < SHOT_DIFF / 4 and                     (inside.mean(axis=(1, 2)) - before.mean() > FLASH_JUMP).all():
                return True
    return False


def run(ctx) -> list[ir.Item]:
    gray = np.asarray(load(ctx.key)[0])
    n = len(gray)
    d = _diff(gray)
    cands = [(i.data["frame"], i.id) for i in ctx.ev["cuts"]] + [(c, None) for c in _gradual(d, gray)]
    seen: list[tuple[int, int, list[str]]] = []
    for c, cid in sorted(cands, key=lambda x: (x[0], x[1] is None)):
        if _is_flash(gray, c):  # the same shot on both sides of a few bright frames: an effect, not a boundary
            continue
        s, e = _window(d, gray, c, n)
        hit = next((x for x in seen if (x[0] <= c <= max(x[1], x[0])) or abs(c - x[0]) <= 2 or (x[0] <= s < x[1]) or
                    (s <= x[0] < e)), None)
        if hit:
            if cid:
                hit[2].append(cid)
            continue
        seen.append((s, e, [cid] if cid else []))
    want = {f for s, e, _ in seen if e > s for f in (s - 1, e, *_mids(s, e))}
    rgb = read_frames(ctx.proxy, {f for f in want if 0 <= f < n}, (ctx.source.width, ctx.source.height))
    items = []
    for k, (s, e, cids) in enumerate(sorted(seen)):
        kind, conf, sig = classify(rgb, gray, s, e)
        frame = s if e == s else s + (e - s) // 2  # the slot boundary sits in the middle of a gradual window
        items.append(ir.Item(id=f"transitions_{k}", track=NAME, start=s, end=e, conf=conf, tool="frame difference + "
                             "pixel mix + farneback", data={"type": kind, "frame": frame, "cuts": cids, "signals": sig}))
    return items
