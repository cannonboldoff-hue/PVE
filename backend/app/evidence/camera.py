"""Camera path per slot: corners tracked with Lucas-Kanade, a similarity transform from the slot's first frame to
each frame fitted with RANSAC (text boxes masked out). The smoothed path is the move (zoom, pan, tilt); what is left
is shake. The same loop decides photo vs video (track "still"): with the camera path removed, a photo has nothing
left that moves."""
import math

import cv2
import numpy as np

from .. import ir
from .frames import load_mid

NAME, VERSION, DEPS = "camera", 3, ["cuts", "transitions", "text"]
MAX_CORNERS = 300
MIN_INLIERS = 25  # RANSAC inliers needed before a transform is believed
MIN_POINTS = 40  # fewer tracked points than this: detect new ones (anchored back to the first frame)
SMOOTH = 9  # frames in the moving average that separates the move from shake
ZOOM_MIN = 0.03  # |log scale change| over the slot that counts as a zoom
PAN_MIN = 0.04  # view-centre travel (share of the frame) that counts as a pan or tilt
SHAKE_MIN = 0.003  # residual std (share of frame width) that counts as handheld or shake
SHAKE_HZ = 3.0  # residual sign changes per second / 2 at or above this: shake, below: handheld
KEY_EVERY = 5  # keyframe spacing of the stored smooth path
STILL_DIFF = 40  # gray difference after removing the camera that counts as motion
STILL_BLOB = 20  # moving pixels (after a 3x3 opening) in a frame that make it "moving"
STILL_SHARE = 0.3  # share of checked frames that must move for the slot to be video


def _slots(cuts: list[int], n: int) -> list[tuple[int, int]]:
    b = [0, *cuts, n]
    return list(zip(b[:-1], b[1:]))


def _text_mask(texts: list[ir.Item], a: int, b: int, w: int, h: int) -> np.ndarray:
    m = np.full((h, w), 255, np.uint8)
    for t in texts:
        if t.start < b and t.end > a:
            bx = t.data["box"]
            x0, y0 = int((bx["x"] - 0.02) * w), int((bx["y"] - 0.02) * h)
            x1, y1 = int((bx["x"] + bx["w"] + 0.02) * w), int((bx["y"] + bx["h"] + 0.02) * h)
            m[max(0, y0):y1, max(0, x0):x1] = 0
    return m


def track(gray: np.ndarray, mask: np.ndarray) -> list[np.ndarray]:
    """2x3 similarity transforms mapping frame-0 coordinates to each frame's."""
    eye = np.array([[1.0, 0, 0], [0, 1.0, 0]])
    out = [eye]
    p0 = cv2.goodFeaturesToTrack(gray[0], MAX_CORNERS, 0.01, 6, mask=mask)
    if p0 is None:
        return [eye] * len(gray)
    origin, cur = p0.reshape(-1, 2), p0.reshape(-1, 2)
    A = eye
    for k in range(1, len(gray)):
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(gray[k - 1], gray[k], cur.reshape(-1, 1, 2).astype(np.float32), None,
                                              winSize=(21, 21), maxLevel=3)
        ok = st.ravel() == 1
        origin, cur = origin[ok], nxt.reshape(-1, 2)[ok]
        if len(cur) >= 6:
            M, inl = cv2.estimateAffinePartial2D(origin, cur, method=cv2.RANSAC, ransacReprojThreshold=1.5)
            if M is not None and inl is not None and inl.sum() >= MIN_INLIERS and inl.mean() >= 0.5:
                A = M  # too few agreeing points (plain footage: a moving bar, a caption) say nothing about the camera
        out.append(A)
        if len(cur) < MIN_POINTS:  # top up, anchoring the new points back to frame 0 through A
            fresh = cv2.goodFeaturesToTrack(gray[k], MAX_CORNERS, 0.01, 6, mask=mask)
            if fresh is not None:
                f = fresh.reshape(-1, 2)
                back = cv2.transform(f.reshape(-1, 1, 2), cv2.invertAffineTransform(A)).reshape(-1, 2)
                origin, cur = np.vstack([origin, back]), np.vstack([cur, f])
    return out


def view(A: np.ndarray, w: int, h: int) -> tuple[float, float, float, float]:
    """(scale, view centre x, y in frame-0 coordinates normalised 0..1, rotation degrees)."""
    s = math.hypot(A[0, 0], A[1, 0])
    rot = math.degrees(math.atan2(A[1, 0], A[0, 0]))
    c = cv2.transform(np.array([[[w / 2, h / 2]]]), cv2.invertAffineTransform(A))[0, 0]
    return s, c[0] / w, c[1] / h, rot


def _smooth(x: np.ndarray) -> np.ndarray:
    if len(x) < 3:
        return x.copy()
    k = min(SMOOTH, len(x) // 2 * 2 - 1)
    pad = np.pad(x, k // 2, mode="edge")
    return np.convolve(pad, np.ones(k) / k, mode="valid")


def classify(path: np.ndarray, fps: int = ir.FPS) -> tuple[str, dict]:
    """path: (n, 4) of scale, cx, cy, rot. Returns (CameraMove, details)."""
    sm = np.stack([_smooth(path[:, i]) for i in range(4)], 1)
    res = path[:, 1:3] - sm[:, 1:3]
    amp = float(res.std(axis=0).max()) if len(path) > 2 else 0.0
    flips = np.abs(np.diff(np.sign(res[:, 0] - res[:, 0].mean()))).sum() / 2 if len(path) > 2 else 0
    hz = float(flips / 2 / max(1e-6, len(path) / fps))
    ds = math.log(sm[-1, 0] / sm[0, 0])
    dx, dy = sm[-1, 1] - sm[0, 1], sm[-1, 2] - sm[0, 2]
    info = {"scale_end": float(sm[-1, 0] / sm[0, 0]), "dx": float(dx), "dy": float(dy),
            "shake": {"amp": round(amp, 5), "hz": round(hz, 2)}}
    if abs(ds) > ZOOM_MIN:
        return ("zoom_in" if ds > 0 else "zoom_out"), info
    if max(abs(dx), abs(dy)) > PAN_MIN:
        if abs(dx) >= abs(dy):
            return ("pan_right" if dx > 0 else "pan_left"), info
        return ("tilt_down" if dy > 0 else "tilt_up"), info
    if amp > SHAKE_MIN:
        return ("shake" if hz >= SHAKE_HZ else "handheld"), info
    return "static", info


def still(gray: np.ndarray, As: list[np.ndarray], mask: np.ndarray) -> tuple[bool, float]:
    """(is a photo, share of checked frames with motion left after removing the camera)."""
    h, w = gray.shape[1:]
    kern = np.ones((3, 3), np.uint8)
    moving, checked = 0, 0
    for k in range(2, len(gray), 3):
        inv = cv2.invertAffineTransform(As[k])
        back = cv2.warpAffine(gray[k], inv, (w, h), flags=cv2.INTER_LINEAR)
        valid = cv2.warpAffine(np.full((h, w), 255, np.uint8), inv, (w, h)) == 255
        valid &= cv2.erode((mask > 0).astype(np.uint8), kern, iterations=2) > 0
        d = (np.abs(back.astype(np.int16) - gray[0].astype(np.int16)) > STILL_DIFF) & valid
        d = cv2.morphologyEx(d.astype(np.uint8), cv2.MORPH_OPEN, kern)
        moving += int(d.sum() > STILL_BLOB)
        checked += 1
    share = moving / checked if checked else 1.0
    return share < STILL_SHARE, share


def run(ctx) -> list[ir.Item]:
    gray = load_mid(ctx.key)
    n, h, w = gray.shape
    from . import boundaries

    bs = boundaries(ctx.ev)
    items = []
    for k, (a, b) in enumerate(_slots([f for f, _, _ in bs], n)):
        # the body only: frames inside a transition window belong to two shots at once
        a = max(a, bs[k - 1][2]) if k else a
        b = min(b, bs[k][1]) if k < len(bs) and bs[k][1] > a + 2 else b
        g = np.ascontiguousarray(gray[a:b])
        mask = _text_mask(ctx.ev["text"], a, b, w, h)
        As = track(g, mask) if len(g) > 2 else [np.array([[1.0, 0, 0], [0, 1.0, 0]])] * len(g)
        path = np.array([view(A, w, h) for A in As])
        move, info = classify(path) if len(g) > 2 else ("static", {})
        sm = np.stack([_smooth(path[:, i]) for i in range(4)], 1)
        keys = [[f, *map(float, sm[f])] for f in sorted({*range(0, len(g), KEY_EVERY), len(g) - 1})]
        items.append(ir.Item(id=f"camera_{k}", track=NAME, start=a, end=b, conf=0.8 if move != "static" else 0.9,
                             tool="opencv lk + ransac similarity", data={"value": move, "path": keys, **info}))
        photo, share = still(g, As, mask) if len(g) > 3 else (False, 1.0)
        items.append(ir.Item(id=f"still_{k}", track="still", start=a, end=b, conf=0.6 if photo else 0.8,
                             tool="camera-compensated difference",
                             data={"value": "photo" if photo else "video", "moving_share": round(share, 3)}))
    return items
