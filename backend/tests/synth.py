"""Synthetic reels with exact ground truth (docs/mvp-plan.md 5.1).

Frames are drawn with numpy/PIL and piped to ffmpeg, so every cut, caption box, transition window, flash and
zoom is known to the frame. A segment is a marker clip: a distinct solid colour (or a texture), the slot number
drawn large, and a bar whose x moves at BAR_SPEED px per *source* frame, so speed and freeze are measurable.
The same marker content is what validation A's marker pass feeds the renderer."""
import colorsys
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.clients import ff  # noqa: F401  (puts ffmpeg on PATH)
from app.ir import Box

W, H, FPS = 540, 960, 30
BAR_SPEED = 6  # px per source frame at W=540
BAR_Y, BAR_H, BAR_W = 0.06, 0.03, 24
FONT = "C:/Windows/Fonts/arialbd.ttf"


@dataclass
class Caption:
    text: str
    start: int
    end: int
    cx: float = 0.5  # resting centre, normalised
    cy: float = 0.75
    size: float = 0.05  # glyph height as a fraction of H
    anim: str = "none"  # none | fade | pop | slide_up
    anim_frames: int = 8
    fill: tuple = (255, 255, 255)
    outline: tuple = (0, 0, 0)


@dataclass
class Trans:
    after: int  # boundary index: between segment `after` and `after + 1`
    type: str  # fade | dissolve | fade_black | fade_white | wipe_* | slide_*
    frames: int = 10


@dataclass
class Zoom:
    seg: int
    s0: float = 1.0
    s1: float = 1.3


@dataclass
class SynthSpec:
    n_frames: int
    cuts: list[int]  # first frame of each segment after the first
    captions: list[Caption] = field(default_factory=list)
    transitions: list[Trans] = field(default_factory=list)
    flash: int | None = None  # first flash frame
    flash_len: int = 2
    zoom: Zoom | None = None
    textured: bool = False
    audio: bool = True


@dataclass
class SynthTruth:
    n_frames: int
    cuts: list[int]
    segments: list[tuple[int, int]]
    captions: list[dict]  # {text, start, end, box: Box, anim}
    transitions: list[dict]  # {after, type, start, end}
    flashes: list[int]
    zoom: dict | None


def colour(i: int) -> tuple[int, int, int]:
    """Distinct, mid-bright colour per slot; successive slots are a golden-angle hue step apart."""
    r, g, b = colorsys.hsv_to_rgb((i * 0.381966) % 1.0, 0.75, 0.65)
    return int(r * 255), int(g * 255), int(b * 255)


@lru_cache(maxsize=64)
def _font(px: int) -> ImageFont.FreeTypeFont:
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
    d.text((w / 2, h / 2), str(slot), font=_font(int(h * 0.3)), fill=(255, 255, 255), anchor="mm",
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
    """Measured bar position in a frame (x of the bar's left edge in W=540 units), for speed/freeze tests."""
    h, w = img.shape[:2]
    band = img[int(BAR_Y * h) + 1:int((BAR_Y + BAR_H) * h) - 1].min(axis=2).mean(axis=0)
    xs = np.nonzero(band > 235)[0]
    return float(xs[0]) * W / w if len(xs) else None


def _zoom(img: np.ndarray, s: float) -> np.ndarray:
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _blend(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    return (a.astype(np.float32) * (1 - t) + b.astype(np.float32) * t).astype(np.uint8)


def transition_frame(a: np.ndarray, b: np.ndarray, kind: str, t: float) -> np.ndarray:
    """t in (0, 1): share of the way from a to b."""
    h, w = a.shape[:2]
    if kind in ("fade", "dissolve"):
        return _blend(a, b, t)
    if kind in ("fade_black", "fade_white"):
        c = np.zeros_like(a) if kind == "fade_black" else np.full_like(a, 255)
        return _blend(a, c, t * 2) if t < 0.5 else _blend(c, b, t * 2 - 1)
    out = a.copy()
    if kind.startswith("wipe_"):  # b revealed behind a boundary moving in the named direction
        d = kind[5:]
        if d == "left":
            x = int(round(w * (1 - t))); out[:, x:] = b[:, x:]
        elif d == "right":
            x = int(round(w * t)); out[:, :x] = b[:, :x]
        elif d == "up":
            y = int(round(h * (1 - t))); out[y:] = b[y:]
        else:
            y = int(round(h * t)); out[:y] = b[:y]
        return out
    if kind.startswith("slide_"):  # a and b move together in the named direction
        d = kind[6:]
        if d in ("left", "right"):
            o = int(round(w * t))
            if d == "left":
                out[:, :w - o] = a[:, o:]; out[:, w - o:] = b[:, :o]
            else:
                out[:, o:] = a[:, :w - o]; out[:, :o] = b[:, w - o:]
        else:
            o = int(round(h * t))
            if d == "up":
                out[:h - o] = a[o:]; out[h - o:] = b[:o]
            else:
                out[o:] = a[:h - o]; out[:o] = b[h - o:]
        return out
    raise ValueError(f"unknown transition {kind}")


def _caption_layer(c: Caption, f: int, h: int, w: int) -> tuple[Image.Image, tuple] | None:
    if not (c.start <= f < c.end):
        return None
    k_in, k_out = f - c.start, c.end - 1 - f
    p = min(1.0, min(k_in, k_out) / max(1, c.anim_frames)) if c.anim != "none" else 1.0
    alpha, scale, dy = 1.0, 1.0, 0.0
    if c.anim == "fade":
        alpha = p
    elif c.anim == "pop":
        scale = 0.5 + 0.5 * p
    elif c.anim == "slide_up":
        dy = 0.1 * (1 - p)
    px = max(6, int(round(c.size * h * scale / 0.72)))  # cap height ~0.72 of the font size for Arial
    return _font(px), (c.cx * w, (c.cy + dy) * h, alpha, px)


def draw_captions(img: np.ndarray, caps: list[Caption], f: int) -> np.ndarray:
    h, w = img.shape[:2]
    layers = [(c, _caption_layer(c, f, h, w)) for c in caps]
    layers = [(c, l) for c, l in layers if l]
    if not layers:
        return img
    base = Image.fromarray(img).convert("RGBA")
    for c, (font, (x, y, alpha, px)) in layers:
        ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
        a = int(round(255 * alpha))
        ImageDraw.Draw(ov).text((x, y), c.text, font=font, anchor="mm", fill=(*c.fill, a),
                                stroke_width=max(1, px // 14), stroke_fill=(*c.outline, a))
        base = Image.alpha_composite(base, ov)
    return np.asarray(base.convert("RGB"))


def caption_box(c: Caption, w: int = W, h: int = H) -> Box:
    font = _font(max(6, int(round(c.size * h / 0.72))))
    d = ImageDraw.Draw(Image.new("RGB", (w, h)))
    x0, y0, x1, y1 = d.textbbox((c.cx * w, c.cy * h), c.text, font=font, anchor="mm", stroke_width=max(1, font.size // 14))
    return Box(x=x0 / w, y=y0 / h, w=(x1 - x0) / w, h=(y1 - y0) / h)


def _segments(spec: SynthSpec) -> list[tuple[int, int]]:
    b = [0, *spec.cuts, spec.n_frames]
    return list(zip(b[:-1], b[1:]))


def _windows(spec: SynthSpec) -> dict[int, tuple[int, int, str]]:
    out = {}
    for t in spec.transitions:
        c = spec.cuts[t.after]
        a = c - t.frames // 2
        out[t.after] = (a, a + t.frames, t.type)
    return out


def _seg_frame(spec: SynthSpec, seg: int, local: int, size: tuple[int, int]) -> np.ndarray:
    w, h = size
    img = marker_frame(seg + 1, local, spec.textured, w, h)
    if spec.zoom and spec.zoom.seg == seg:
        s, e = _segments(spec)[seg]
        t = min(1.0, max(0.0, local / max(1, e - s - 1)))
        img = _zoom(img, spec.zoom.s0 + (spec.zoom.s1 - spec.zoom.s0) * t)
    return img


def frame(spec: SynthSpec, f: int, size: tuple[int, int] = (W, H)) -> np.ndarray:
    segs, wins = _segments(spec), _windows(spec)
    seg = next(i for i, (s, e) in enumerate(segs) if s <= f < e)
    img = None
    for k, (a, b, kind) in wins.items():
        if a <= f < b:
            sa, sb = segs[k][0], segs[k + 1][0]
            t = (f - a + 0.5) / (b - a)
            img = transition_frame(_seg_frame(spec, k, f - sa, size), _seg_frame(spec, k + 1, f - sb, size), kind, t)
    if img is None:
        img = _seg_frame(spec, seg, f - segs[seg][0], size)
    img = draw_captions(img, spec.captions, f)
    if spec.flash is not None and spec.flash <= f < spec.flash + spec.flash_len:
        img = _blend(img, np.full_like(img, 255), 0.85)
    return img


def _encode(frames, n: int, out: Path, size: tuple[int, int], audio: bool) -> None:
    w, h = size
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-"]
    if audio:
        args += ["-f", "lavfi", "-i", f"anoisesrc=color=pink:seed=11:sample_rate=48000:duration={n / FPS}",
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
        raise RuntimeError(f"synth encode failed: {err[-400:]}")


def make_reel(spec: SynthSpec, out: Path, size: tuple[int, int] = (W, H)) -> SynthTruth:
    out = Path(out)
    _encode((frame(spec, f, size) for f in range(spec.n_frames)), spec.n_frames, out, size, spec.audio)
    wins = _windows(spec)
    flashes = list(range(spec.flash, spec.flash + spec.flash_len)) if spec.flash is not None else []
    return SynthTruth(
        n_frames=spec.n_frames, cuts=list(spec.cuts), segments=_segments(spec),
        captions=[{"text": c.text, "start": c.start, "end": c.end, "box": caption_box(c, *size), "anim": c.anim}
                  for c in spec.captions],
        transitions=[{"after": k, "type": t, "start": a, "end": b} for k, (a, b, t) in sorted(wins.items())],
        flashes=flashes,
        zoom={"seg": spec.zoom.seg, "s0": spec.zoom.s0, "s1": spec.zoom.s1} if spec.zoom else None,
    )


def marker_clip(slot_no: int, frames: int, out: Path, textured: bool = False, size: tuple[int, int] = (W, H),
                fps: int = FPS) -> Path:
    """A marker clip for one slot: plain footage whose every measurable property is known."""
    out = Path(out)
    w, h = size
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-frames:v", str(frames), "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", str(out)]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for f in range(frames):
            p.stdin.write(marker_frame(slot_no, f, textured, w, h).tobytes())
    finally:
        p.stdin.close()
    if p.wait():
        raise RuntimeError(f"marker encode failed: {p.stderr.read().decode(errors='replace')[-400:]}")
    return out
