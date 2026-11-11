"""Synthetic reels with exact ground truth (docs/mvp-plan.md 5.1).

Frames are drawn with numpy/PIL and piped to ffmpeg, so every cut, caption box, transition window, flash and
zoom is known to the frame. A segment is a marker clip: a distinct solid colour (or a texture), the slot number
drawn large, and a bar whose x moves at BAR_SPEED px per *source* frame, so speed and freeze are measurable.
The same marker content is what validation A's marker pass feeds the renderer."""
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from app.ir import Box
from app.stages.markers import FPS, H, W, bar_x, colour, marker_clip, marker_frame  # noqa: F401  (re-exported)
from app.stages.markers import encode as _encode_frames
from app.stages.markers import font as _font


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
    type: str  # fade | dissolve | fade_black | fade_white | wipe_* | slide_* (b covers a) | push_* (both move)
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
    zooms: list[Zoom] = field(default_factory=list)  # more zooms, one per segment
    stills: list[int] = field(default_factory=list)
    speeds: dict = field(default_factory=dict)  # segment -> [(position 0..1, factor)]
    freezes: dict = field(default_factory=dict)  # segment -> [(start, end)] segment-relative frames that hold
    layouts: dict = field(default_factory=dict)  # segment -> "split_v" | "split_h" | "pip" | "blur_fill"
    overlay: tuple | None = None  # static (x, y, w, h) normalised rectangle on every frame, colour OVERLAY_RGB  # segments that are photos: nothing moves but the camera


@dataclass
class SynthTruth:
    n_frames: int
    cuts: list[int]
    segments: list[tuple[int, int]]
    captions: list[dict]  # {text, start, end, box: Box, anim}
    transitions: list[dict]  # {after, type, start, end}
    flashes: list[int]
    zoom: dict | None
    layouts: dict = field(default_factory=dict)  # segment -> {value, boxes: [Box]}
    overlay: Box | None = None


def _zoom(img: np.ndarray, s: float) -> np.ndarray:
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _blend(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    return (a.astype(np.float32) * (1 - t) + b.astype(np.float32) * t).astype(np.uint8)


def transition_frame(a: np.ndarray, b: np.ndarray, kind: str, t: float) -> np.ndarray:
    """t in (0, 1): share of the way from a to b."""
    h, w = a.shape[:2]
    if kind == "fade":
        return _blend(a, b, t)
    if kind == "dissolve":  # each pixel switches from a to b at its own random moment (ffmpeg xfade dissolve)
        noise = np.random.default_rng(0).random((h, w))
        return np.where((noise < t)[..., None], b, a)
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
    if kind.startswith("slide_"):  # b moves in over a still a, travelling in the named direction
        d = kind[6:]
        if d in ("left", "right"):
            o = int(round(w * t))
            if d == "left":
                out[:, w - o:] = b[:, :o]
            else:
                out[:, :o] = b[:, w - o:]
        else:
            o = int(round(h * t))
            if d == "up":
                out[h - o:] = b[:o]
            else:
                out[:o] = b[h - o:]
        return out
    if kind.startswith("push_"):  # a and b move together in the named direction
        d = kind[5:]
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
    src = local
    if (seg in spec.speeds or seg in spec.freezes) and local >= 0:
        from app.render.shot import pieces, src_at

        a, b = _segments(spec)[seg]
        src = int(src_at(local, pieces(b - a, spec.speeds.get(seg), spec.freezes.get(seg))))
    img = marker_frame(seg + 1, 0 if seg in spec.stills else src, spec.textured, w, h)
    if seg in spec.layouts:
        img = _layout(img, spec.layouts[seg], seg, src, spec.textured)
    for z in [spec.zoom, *spec.zooms]:
        if z and z.seg == seg:
            s, e = _segments(spec)[seg]
            t = min(1.0, max(0.0, local / max(1, e - s - 1)))
            img = _zoom(img, z.s0 + (z.s1 - z.s0) * t)
    return img


PIP_BOX = (0.55, 0.08, 0.38, 0.3)  # inset rectangle for "pip"
OVERLAY_RGB = (250, 40, 160)


def layout_boxes(kind: str) -> list[tuple[float, float, float, float]]:
    """Content boxes of a layout, normalised: the truth the layout detector must find."""
    if kind == "split_v":
        return [(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)]
    if kind == "split_h":
        return [(0, 0, 1, 0.5), (0, 0.5, 1, 0.5)]
    if kind == "pip":
        return [(0, 0, 1, 1), PIP_BOX]
    if kind == "blur_fill":
        return [(0, (1 - 9 / 16 * W / H) / 2, 1, 9 / 16 * W / H)]  # a 16:9 picture centred on the 9:16 frame
    raise ValueError(kind)


def _px(box, w, h):
    x, y, bw, bh = box
    return int(round(x * w)), int(round(y * h)), int(round(bw * w)), int(round(bh * h))


def _layout(img: np.ndarray, kind: str, seg: int, local: int, textured: bool) -> np.ndarray:
    h, w = img.shape[:2]
    other = marker_frame(seg + 20, local, textured, w, h)  # unrelated footage with its own moving bar
    if kind in ("split_v", "split_h"):
        out = np.empty_like(img)
        for src, box in zip((img, other), layout_boxes(kind)):
            x, y, bw, bh = _px(box, w, h)
            out[y:y + bh, x:x + bw] = cv2.resize(src, (bw, bh), interpolation=cv2.INTER_AREA)
        return out
    if kind == "pip":
        x, y, bw, bh = _px(PIP_BOX, w, h)
        out = img.copy()
        out[y:y + bh, x:x + bw] = cv2.resize(other, (bw, bh), interpolation=cv2.INTER_AREA)
        return out
    if kind == "blur_fill":
        x, y, bw, bh = _px(layout_boxes(kind)[0], w, h)
        pic = cv2.resize(img, (bw, bh), interpolation=cv2.INTER_AREA)
        bg = cv2.GaussianBlur(cv2.resize(pic, (w, h)), (0, 0), 25)
        bg[y:y + bh, x:x + bw] = pic
        return bg
    raise ValueError(kind)


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
    if spec.overlay:
        x, y, bw, bh = _px(spec.overlay, *size)
        img = img.copy()
        img[y:y + bh, x:x + bw] = OVERLAY_RGB
    img = draw_captions(img, spec.captions, f)
    if spec.flash is not None and spec.flash <= f < spec.flash + spec.flash_len:
        img = _blend(img, np.full_like(img, 255), 0.85)
    return img


def make_reel(spec: SynthSpec, out: Path, size: tuple[int, int] = (W, H)) -> SynthTruth:
    out = Path(out)
    _encode_frames((frame(spec, f, size) for f in range(spec.n_frames)), spec.n_frames, out, size, spec.audio)
    wins = _windows(spec)
    flashes = list(range(spec.flash, spec.flash + spec.flash_len)) if spec.flash is not None else []
    return SynthTruth(
        n_frames=spec.n_frames, cuts=list(spec.cuts), segments=_segments(spec),
        captions=[{"text": c.text, "start": c.start, "end": c.end, "box": caption_box(c, *size), "anim": c.anim}
                  for c in spec.captions],
        transitions=[{"after": k, "type": t, "start": a, "end": b} for k, (a, b, t) in sorted(wins.items())],
        flashes=flashes,
        zoom={"seg": spec.zoom.seg, "s0": spec.zoom.s0, "s1": spec.zoom.s1} if spec.zoom else None,
        layouts={k: {"value": v, "boxes": [Box(x=b[0], y=b[1], w=b[2], h=b[3]) for b in layout_boxes(v)]}
                 for k, v in spec.layouts.items()},
        overlay=Box(x=spec.overlay[0], y=spec.overlay[1], w=spec.overlay[2], h=spec.overlay[3]) if spec.overlay else None,
    )
