"""Marker clips: plain footage whose every measurable property is known (docs/mvp-plan.md 5.1).
A distinct solid colour (or texture) per slot, the slot number drawn large, and a bar whose x moves at BAR_SPEED px
per *source* frame, so speed and freeze are measurable. Used by the marker pass and by the synthetic test reels."""
import colorsys
import subprocess
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..clients import ff  # noqa: F401  (puts ffmpeg on PATH)

W, H, FPS = 540, 960, 30
BAR_SPEED = 6  # px per source frame at W=540
BAR_Y, BAR_H, BAR_W = 0.06, 0.03, 24
FONT = "C:/Windows/Fonts/arialbd.ttf"


def colour(i: int) -> tuple[int, int, int]:
    """Distinct, mid-bright colour per slot; successive slots are a golden-angle hue step apart."""
    r, g, b = colorsys.hsv_to_rgb((i * 0.381966) % 1.0, 0.75, 0.65)
    return int(r * 255), int(g * 255), int(b * 255)


@lru_cache(maxsize=64)
def font(px: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT, px)
    except OSError:
        return ImageFont.load_default(px)


@lru_cache(maxsize=32)
def _base(slot: int, textured: bool, w: int, h: int) -> np.ndarray:
    if textured:
        rng = np.random.default_rng(slot)
        n = rng.integers(0, 255, (h // 8, w // 8, 3), dtype=np.uint8)
        img = cv2.resize(n, (w, h), interpolation=cv2.INTER_NEAREST)
        img = (img.astype(np.float32) * 0.5 + np.array(colour(slot), np.float32) * 0.5).astype(np.uint8)
    else:
        img = np.full((h, w, 3), colour(slot), np.uint8)
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), str(slot), font=font(int(h * 0.3)), fill=(255, 255, 255), anchor="mm",
           stroke_width=max(2, h // 160), stroke_fill=(0, 0, 0))
    return np.asarray(im)


def marker_frame(slot: int, local: int, textured: bool = False, w: int = W, h: int = H) -> np.ndarray:
    """Frame `local` (source frame index) of slot `slot`'s marker clip."""
    img = _base(slot, textured, w, h).copy()
    bw = max(2, round(BAR_W * w / W))
    x = int(local * BAR_SPEED * w / W) % (w - bw)
    y0, y1 = int(BAR_Y * h), int((BAR_Y + BAR_H) * h)
    img[y0:y1, x:x + bw] = 255
    return img


def bar_x(img: np.ndarray) -> float | None:
    """Measured bar position in a frame (x of the bar's left edge in W=540 units)."""
    h, w = img.shape[:2]
    band = img[int(BAR_Y * h) + 1:int((BAR_Y + BAR_H) * h) - 1].min(axis=2).mean(axis=0)
    xs = np.nonzero(band > 235)[0]
    return float(xs[0]) * W / w if len(xs) else None


def encode(frames, n: int, out: Path, size: tuple[int, int], audio: bool = False, fps: int = FPS) -> Path:
    """Pipe RGB frames to libx264 (exactly n frames); optional pink-noise audio of the same length."""
    w, h = size
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if audio:
        args += ["-f", "lavfi", "-i", f"anoisesrc=color=pink:seed=11:sample_rate=48000:duration={n / fps}",
                 "-c:a", "aac", "-b:a", "192k"]
    args += ["-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p",
             "-g", "30", str(out)]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for img in frames:
            p.stdin.write(np.ascontiguousarray(img).tobytes())
    finally:
        p.stdin.close()
    err = p.stderr.read().decode(errors="replace")
    if p.wait():
        raise RuntimeError(f"encode failed: {err[-400:]}")
    return Path(out)


def marker_clip(slot_no: int, frames: int, out: Path, textured: bool = False, size: tuple[int, int] = (W, H),
                fps: int = FPS) -> Path:
    """A marker clip for one slot."""
    w, h = size
    return encode((marker_frame(slot_no, f, textured, w, h) for f in range(frames)), frames, Path(out), size, fps=fps)
