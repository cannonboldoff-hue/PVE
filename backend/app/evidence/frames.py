"""Decode the proxy once into small grayscale and colour stacks, memory-mapped under data/refs/<key>/frames/.
Every evidence track reads from these instead of decoding the video again (OCR, which needs pixels, is the exception)."""
import threading

import numpy as np

from .. import ir
from ..clients import ff

SMALL_W = 160  # wide enough for frame differences, flow and layout; small enough to hold a whole reel in RAM

_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def size(key: str) -> tuple[int, int]:
    src = ir.load(key, "source", ir.Source)
    h = int(round(SMALL_W * src.height / src.width / 2)) * 2
    return SMALL_W, h


def load(key: str) -> tuple[np.ndarray, np.ndarray]:
    """(gray (n, h, w) uint8, rgb (n, h, w, 3) uint8), read-only memory maps."""
    from ..stages.analyze import proxy_path

    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    d = ir.ref_dir(key) / "frames"
    g, c = d / "gray.npy", d / "rgb.npy"
    with lock:
        if not (g.exists() and c.exists()):
            d.mkdir(exist_ok=True)
            w, h = size(key)
            rgb = ff.decode(proxy_path(key), w, h)
            gray = (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114).round().astype(np.uint8)
            np.save(c, rgb)
            np.save(g, gray)
    return np.load(g, mmap_mode="r"), np.load(c, mmap_mode="r")


MID_W = 320  # gray stack for feature tracking: corners and sub-pixel flow need more than SMALL_W


def load_mid(key: str) -> np.ndarray:
    """Gray (n, h, w) uint8 at MID_W wide, memory-mapped."""
    from ..stages.analyze import proxy_path

    with _guard:
        lock = _locks.setdefault(key + ":mid", threading.Lock())
    p = ir.ref_dir(key) / "frames" / "gray_mid.npy"
    with lock:
        if not p.exists():
            p.parent.mkdir(exist_ok=True)
            src = ir.load(key, "source", ir.Source)
            h = int(round(MID_W * src.height / src.width / 2)) * 2
            np.save(p, ff.decode(proxy_path(key), MID_W, h, gray=True))
    return np.load(p, mmap_mode="r")
