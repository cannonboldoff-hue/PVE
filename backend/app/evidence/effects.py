"""Frame effects. Flash: a brightness jump above FLASH_DELTA lasting 1..FLASH_MAX frames that returns to the level
before it (frame-exact). RGB split: red and blue planes displaced against each other (phase correlation) in bursts.
Blur: a burst of low sharpness. Vignette: corners darker than the centre across a whole shot. Grain and glow are
shot looks the video AI names; they are not measured here."""
import cv2
import numpy as np

from .. import ir
from . import boundaries
from .frames import load

NAME, VERSION, DEPS = "effects", 2, ["cuts", "transitions", "text"]
FLASH_DELTA = 40.0  # mean luma jump (0..255) that makes a flash
FLASH_MAX = 4  # longest flash in frames; longer is a cut to a bright shot
SPLIT_PX = 1.0  # red/blue displacement (px at 160 wide) that counts as RGB split
BLUR_DROP = 0.35  # sharpness below this share of the shot's median is a blur burst
BURST_MIN = 2  # frames
BLUR_MIN = 20.0  # shots flatter than this (Laplacian variance) have no sharpness to lose
VIGNETTE = 0.8  # corner luma / mid-edge luma below this across a shot


def flashes(luma: np.ndarray, windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out, f, n = [], 1, len(luma)
    while f < n:
        if luma[f] - luma[f - 1] > FLASH_DELTA and not any(a <= f < b for a, b in windows):
            for L in range(1, FLASH_MAX + 1):
                if f + L < n and abs(luma[f + L] - luma[f - 1]) < FLASH_DELTA / 2:
                    out.append((f, f + L))
                    f += L
                    break
        f += 1
    return out


def _bursts(flag: np.ndarray) -> list[tuple[int, int]]:
    out, k = [], 0
    while k < len(flag):
        if flag[k]:
            j = k
            while j + 1 < len(flag) and flag[j + 1]:
                j += 1
            if j - k + 1 >= BURST_MIN:
                out.append((k, j + 1))
            k = j
        k += 1
    return out


def run(ctx) -> list[ir.Item]:
    gray, rgb = load(ctx.key)
    gray, rgb = np.asarray(gray), np.asarray(rgb)
    n = len(gray)
    luma = gray.reshape(n, -1).mean(1)
    bs = boundaries(ctx.ev)
    windows = [(s, e + 1) for _, s, e in bs if e > s]
    items: list[ir.Item] = []

    def add(kind, a, b, conf, **data):
        items.append(ir.Item(id=f"effects_{len(items)}", track=NAME, start=a, end=b, conf=conf, tool="pixel stats",
                             data={"type": kind, **data}))

    flash = flashes(luma, windows)
    for a, b in flash:
        add("flash", a, b, 0.9, strength=round(float(luma[a:b].max() - luma[a - 1]) / 255, 3))
    windows = windows + flash  # a flash also washes out sharpness: no blur burst there
    shift = np.zeros(n)
    sharp = np.zeros(n)
    h, w = gray.shape[1:]
    keep = np.ones((n, h, w), bool)  # a caption fading in or out changes sharpness; it is not a blur effect
    for t in ctx.ev.get("text", []):
        b = t.data["box"]
        keep[t.start:t.end, max(0, int(b["y"] * h) - 2):int((b["y"] + b["h"]) * h) + 3,
             max(0, int(b["x"] * w) - 2):int((b["x"] + b["w"]) * w) + 3] = False
    for f in range(n):
        r, bl = rgb[f, ..., 0].astype(np.float32), rgb[f, ..., 2].astype(np.float32)
        (dx, dy), _ = cv2.phaseCorrelate(r, bl)
        shift[f] = np.hypot(dx, dy)
        sharp[f] = cv2.Laplacian(gray[f], cv2.CV_64F)[keep[f]].var()
    edges = [0, *[f for f, _, _ in bs], n]
    for a, b in zip(edges[:-1], edges[1:]):
        for s, e in _bursts(shift[a:b] > SPLIT_PX):
            add("rgb_split", a + s, a + e, 0.6, px=round(float(shift[a + s:a + e].mean()), 2))
        med = np.median(sharp[a:b]) if b > a else 0
        for s, e in _bursts(sharp[a:b] < BLUR_DROP * med) if med > BLUR_MIN else []:
            if not any(x <= a + s < y for x, y in windows):
                add("blur", a + s, a + e, 0.5)
        h, w = gray.shape[1:]
        g = gray[a:b].astype(np.float32).mean(0)
        corners = np.mean([g[:h // 6, :w // 6].mean(), g[:h // 6, -w // 6:].mean(), g[-h // 6:, :w // 6].mean(),
                           g[-h // 6:, -w // 6:].mean()])
        # mid-edges, not the centre: a bright subject in the middle is not a vignette, a darkening towards corners is
        edges_ = np.mean([g[:h // 6, w // 3:2 * w // 3].mean(), g[-h // 6:, w // 3:2 * w // 3].mean(),
                          g[h // 3:2 * h // 3, :w // 6].mean(), g[h // 3:2 * h // 3, -w // 6:].mean()])
        if edges_ > 30 and corners / edges_ < VIGNETTE:
            add("vignette", a, b, 0.4, ratio=round(float(corners / edges_), 3))
    return items
