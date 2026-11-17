"""Overlay engines: animated layers and shader-style transitions that libass and ffmpeg filters cannot draw.

One interface, engines behind it. The template and plan never name an engine: capabilities.py marks a feature
"overlay:<name>" and pick() chooses the engine here. HyperFrames (HTML + GSAP, rendered by headless Chrome) is the
first engine; its transparent output is VP9 WebM with alpha (docs/mvp-plan.md section 8)."""
import html
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .. import config
from ..clients import ff
from . import capabilities, textlayer

FPS, W, H = config.FPS, config.W, config.H
ENGINE_ANIMS = {"bounce", "word_highlight", "other"}  # text animations routed here instead of libass
SHADER_TRANSITIONS = {"whip_left", "whip_right", "whip_up", "whip_down", "spin", "zoom_out", "glitch"}
CSS_PER_ASS = textlayer.K_FONT  # CSS font-size is an em like PIL's; libass sizes are K_FONT larger in ink


@dataclass
class OverlaySpec:
    n_frames: int
    texts: list[dict] = field(default_factory=list)  # ir.TextEvent dicts (absolute frames)
    overlays: list[dict] = field(default_factory=list)  # {box, start, end, colour | image}
    width: int = W
    height: int = H
    fps: int = FPS


class OverlayEngine(Protocol):
    name: str

    def supports(self, feature: str) -> bool: ...

    def render(self, layer: OverlaySpec, out: Path) -> Path: ...  # transparent video, exactly n_frames

    def transition(self, a: Path, b: Path, frames: int, kind: str, out: Path) -> Path: ...  # opaque, exactly frames


# vendored with the pinned hyperframes package, copied into each project: renders must not need the network
GSAP_FILE = config.ROOT / "overlay/hyperframes/node_modules/hyperframes/dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js"
GSAP = '<script src="gsap.min.js"></script>'


def _secs(f: int, fps: int = FPS) -> str:
    return f"{f / fps:.4f}"


PATH_MOVE = 0.06  # centre travel (share of the frame) or PATH_TURN degrees outside the in / out windows: a path
PATH_TURN = 5.0
PATH_SMOOTH = 0.35  # jitter around the smoothed path, as a share of its travel, above which it is OCR noise
PATH_MIN_KEYS = 6
PATH_STEP = 4  # keep every 4th sampled key (OCR samples every 2nd frame): a tween per ~8 frames


def _smooth_travel(v: list[float]) -> tuple[float, float]:
    """(travel of the 3-point moving average, std of what is left around it)."""
    sm = [sum(v[max(0, k - 1):k + 2]) / len(v[max(0, k - 1):k + 2]) for k in range(len(v))]
    res = [a - b for a, b in zip(v, sm)]
    mean = sum(res) / len(res)
    return max(sm) - min(sm), (sum((r - mean) ** 2 for r in res) / len(res)) ** 0.5


def path_keys(e: dict) -> list[dict]:
    """The measured box path while the text rests between its in and out animations, when it really moves
    (flying / drifting / turning text). Empty for text that holds still."""
    rest = e["keys"][0]
    a, b = e["start"] + e.get("anim_in_frames", 0), e["end"] - e.get("anim_out_frames", 0)
    ks = sorted((k for k in e["keys"][1:] if a <= k["frame"] < b), key=lambda k: k["frame"])
    if len(ks) < PATH_MIN_KEYS or sum(c.isalnum() for c in e["text"].get("raw") or e["text"]["value"]) < 3:
        return []  # a glyph or two: OCR boxes wander too much to call it a path
    real = False
    for v, need in (([k["box"]["x"] + k["box"]["w"] / 2 for k in ks], PATH_MOVE),
                    ([k["box"]["y"] + k["box"]["h"] / 2 for k in ks], PATH_MOVE),
                    ([float(k.get("rotation") or 0) for k in ks], PATH_TURN)):
        travel, jitter = _smooth_travel(v)
        real |= travel >= need and jitter <= PATH_SMOOTH * travel  # moves far, and smoothly
    if not real:
        return []
    return ks[::PATH_STEP] + ([ks[-1]] if (len(ks) - 1) % PATH_STEP else [])


def _path_tweens(sel: str, e: dict, w: int, h: int) -> list[str]:
    rest = e["keys"][0]["box"]
    cx0, cy0 = rest["x"] + rest["w"] / 2, rest["y"] + rest["h"] / 2
    out, prev = [], None
    for k in path_keys(e):
        b = k["box"]
        x, y = (b["x"] + b["w"] / 2 - cx0) * w, (b["y"] + b["h"] / 2 - cy0) * h
        sc = b["h"] / max(1e-6, rest["h"])
        props = f'x:{x:.1f},y:{y:.1f},scale:{sc:.3f},rotation:{float(k.get("rotation") or 0):.1f}'
        if prev is None:
            out.append(f'tl.set("{sel}",{{{props}}},{k["frame"] / FPS:.4f});')
        else:
            out.append(f'tl.to("{sel}",{{{props},duration:{(k["frame"] - prev) / FPS:.4f},ease:"none"}},'
                       f'{prev / FPS:.4f});')
        prev = k["frame"]
    return out


SLIDES = {"slide_up": ("y", 1), "slide_down": ("y", -1), "slide_left": ("x", 1), "slide_right": ("x", -1)}


def text_losses(e: dict) -> list[str]:
    """What the renderer that draws this event cannot reproduce."""
    if not needs_engine(e):
        return textlayer.event_tags(e, FPS)[2]
    out = []
    if e["anim_in"]["value"] == "other":
        out.append("unknown text animation in: shown as a fade")
    return out


def _text_html(k: int, e: dict, w: int, h: int) -> tuple[str, list[str]]:
    """One text event as a positioned div plus its GSAP tweens."""
    st, box = e["style"], e["keys"][0]["box"]
    fs, words = textlayer.fit(e, w, h)
    css = [f"left:{(box['x'] + box['w'] / 2) * w:.1f}px", f"top:{(box['y'] + box['h'] / 2) * h:.1f}px",
           "transform:translate(-50%,-50%)", f"font-family:'{st['font']}'", f"font-size:{fs * CSS_PER_ASS:.1f}px",
           f"font-weight:{700 if st.get('bold', True) else 400}", f"color:{st['fill']}", "white-space:pre",
           "text-align:center", "line-height:1.1"]
    if st.get("outline"):
        css.append(f"-webkit-text-stroke:{max(1.0, fs * textlayer.OUTLINE_PER_FS):.1f}px {st['outline']};paint-order:stroke fill")
    if st.get("box"):
        css.append(f"background:{st['box']};padding:0.1em 0.3em")
    sel, t0, t1 = f"#t{k}", e["start"] / FPS, e["end"] / FPS
    n_in, n_out = e.get("anim_in_frames", 0) / FPS or 0.3, e.get("anim_out_frames", 0) / FPS or 0.3
    a_in, a_out = e["anim_in"]["value"], e["anim_out"]["value"]
    word_split = words.split()  # numbered across lines, like the detector's word indices
    starts = textlayer.word_starts(e, len(word_split))
    by_word = a_in == "word_highlight" or (a_in == "typewriter" and starts)
    spans = by_word or a_in == "typewriter"
    pieces = (word_split if by_word else list(words)) if spans else [words]
    # inline-block so a word can scale; the div's white-space:pre keeps the line breaks of the fitted text
    span = f'<span class="p{k}" style="display:inline-block;white-space:pre">{{}}</span>'
    keys = textlayer.key_words(e, len(word_split)) if not spans else set()
    if keys:  # key words in their own colour the whole time
        hi0 = e.get("highlight") or textlayer.HIGHLIGHT
        inner = textlayer.join_words(words, lambda i, p: f'<span style="color:{hi0}">{html.escape(p)}</span>'
                                     if i in keys else html.escape(p))
    elif by_word:
        inner = textlayer.join_words(words, lambda i, p: span.format(html.escape(p)))
    else:
        inner = "".join(span.format(html.escape(p)) for p in pieces) if spans else html.escape(words)
    div = (f'<div id="t{k}" class="clip" data-start="{_secs(e["start"])}" data-duration="{_secs(e["end"] - e["start"])}" '
           f'style="position:absolute;{";".join(css)}">{inner}</div>')
    tw = []
    pose = {}
    if abs(textlayer.rotation(e)) >= 0.5:
        pose["rotation"] = f"{textlayer.rotation(e):.1f}"
    persp = e.get("perspective") or {}
    if persp.get("rx") or persp.get("ry"):  # 3D tilt, from the video AI only
        pose |= {"rotationX": f"{float(persp.get('rx') or 0):.1f}", "rotationY": f"{float(persp.get('ry') or 0):.1f}",
                 "transformPerspective": "800"}
    if pose:
        tw.append(f'tl.set("{sel}",{{{",".join(f"{a}:{v}" for a, v in pose.items())}}},0);')
    line_h = box["h"] / max(1, words.count("\n") + 1)
    hi = e.get("highlight") or textlayer.HIGHLIGHT
    if a_in == "bounce":
        # back.out overshoots past the rest and settles: what text_anim reads as a bounce (bounce.out never crosses)
        tw.append(f'tl.fromTo("{sel}",{{y:{0.12 * h:.0f}}},{{y:0,duration:{n_in:.3f},ease:"back.out(2.5)"}},{t0:.4f});')
    elif a_in == "word_highlight" and starts:  # each word lights up at its measured frame, grows, settles back
        for i, s in enumerate(starts):
            tw.append(f'tl.to("#t{k} .p{k}:nth-child({i + 1})",{{color:"{hi}",scale:1.12,duration:0.12,yoyo:true,'
                      f'repeat:1}},{s / FPS:.4f});')
    elif a_in == "word_highlight":  # no measured timing: words in turn over the event
        per = (t1 - t0) / max(1, len(pieces))
        tw.append(f'tl.to(".p{k}",{{color:"{hi}",scale:1.12,duration:{min(per, 0.15):.3f},'
                  f'stagger:{{each:{per:.3f},yoyo:true,repeat:1}}}},{t0:.4f});')
    elif a_in == "typewriter" and starts:  # whole words pop in at their measured frames
        tw.append(f'tl.set(".p{k}",{{opacity:0}},{t0:.4f});')
        tw += [f'tl.fromTo("#t{k} .p{k}:nth-child({i + 1})",{{opacity:0,scale:0.6}},{{opacity:1,scale:1,'
               f'duration:0.08}},{s / FPS:.4f});' for i, s in enumerate(starts)]
    elif a_in == "typewriter":
        tw.append(f'tl.fromTo(".p{k}",{{opacity:0}},{{opacity:1,duration:0.001,stagger:{n_in / max(1, len(pieces)):.4f}}},{t0:.4f});')
    elif a_in in ("fade", "other"):  # other: nearest is a fade (text_losses records it)
        tw.append(f'tl.fromTo("{sel}",{{opacity:0}},{{opacity:1,duration:{n_in:.3f}}},{t0:.4f});')
    elif a_in == "pop":
        tw.append(f'tl.fromTo("{sel}",{{scale:0.5}},{{scale:1,duration:{n_in:.3f}}},{t0:.4f});')
    elif a_in in SLIDES:
        axis, sign = SLIDES[a_in]
        d = sign * textlayer.SLIDE_BOXES * line_h * h
        tw.append(f'tl.fromTo("{sel}",{{{axis}:{d:.1f}}},{{{axis}:0,duration:{n_in:.3f},ease:"power2.out"}},{t0:.4f});')
    tw += _path_tweens(sel, e, w, h)
    if a_out in ("fade", "bounce", "other"):
        tw.append(f'tl.to("{sel}",{{opacity:0,duration:{n_out:.3f}}},{t1 - n_out:.4f});')
    elif a_out == "pop":
        tw.append(f'tl.to("{sel}",{{scale:0.5,opacity:0,duration:{n_out:.3f}}},{t1 - n_out:.4f});')
    elif a_out in SLIDES:
        axis, sign = SLIDES[a_out]
        d = -sign * textlayer.SLIDE_BOXES * line_h * h
        tw.append(f'tl.to("{sel}",{{{axis}:"+={d:.1f}",duration:{n_out:.3f},ease:"power2.in"}},{t1 - n_out:.4f});')
    return div, tw


def composition(spec: OverlaySpec) -> str:
    w, h = spec.width, spec.height
    body, tweens = [], []
    for k, e in enumerate(spec.texts):
        div, tw = _text_html(k, e, w, h)
        body.append(div)
        tweens += tw
    for k, o in enumerate(spec.overlays):
        b = o["box"]
        fill = f'<img src="{html.escape(Path(o["image"]).name)}" style="width:100%;height:100%;object-fit:contain">' \
            if o.get("image") else ""
        bg = "" if o.get("image") else f"background:{o.get('colour', '#FF00FF')};"
        body.append(f'<div class="clip" data-start="{_secs(o["start"])}" data-duration="{_secs(o["end"] - o["start"])}" '
                    f'style="position:absolute;left:{b["x"] * w:.1f}px;top:{b["y"] * h:.1f}px;width:{b["w"] * w:.1f}px;'
                    f'height:{b["h"] * h:.1f}px;{bg}">{fill}</div>')
    return _page(w, h, spec.n_frames, "\n".join(body), "\n".join(tweens), transparent=True)


def _page(w: int, h: int, n: int, body: str, tweens: str, transparent: bool) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width={w}, height={h}" />{GSAP}
<style>*{{margin:0;padding:0;box-sizing:border-box}} html,body{{width:{w}px;height:{h}px;overflow:hidden;
background:{'transparent' if transparent else '#000'}}} #root{{position:relative;width:100%;height:100%}}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{_secs(n)}" data-width="{w}" data-height="{h}">
{body}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{tweens}
tl.set({{}}, {{}}, {n / FPS:.4f});
window.__timelines["main"] = tl;
tl.seek(0);
</script></body></html>"""


def whip_page(a: str, b: str, frames: int, kind: str, w: int = W, h: int = H) -> str:
    """Two clips, the outgoing one thrown out and the incoming one thrown in, blurred along the motion."""
    d = kind.split("_", 1)[1] if "_" in kind else "left"
    axis, sign = ("x", -1 if d == "left" else 1) if d in ("left", "right") else ("y", -1 if d == "up" else 1)
    span = w if axis == "x" else h
    dur = frames / FPS
    vids = (f'<video id="va" class="clip" src="{a}" muted data-start="0" data-duration="{_secs(frames)}" '
            f'style="position:absolute;left:0;top:0;width:{w}px;height:{h}px"></video>'
            f'<video id="vb" class="clip" src="{b}" muted data-start="0" data-duration="{_secs(frames)}" '
            f'style="position:absolute;left:0;top:0;width:{w}px;height:{h}px"></video>')
    tweens = (f'tl.fromTo("#va",{{{axis}:0,filter:"blur(0px)"}},{{{axis}:{sign * span},filter:"blur(28px)",'
              f'duration:{dur:.4f},ease:"power2.in"}},0);'
              f'tl.fromTo("#vb",{{{axis}:{-sign * span},filter:"blur(28px)"}},{{{axis}:0,filter:"blur(0px)",'
              f'duration:{dur:.4f},ease:"power2.out"}},0);')
    return _page(w, h, frames, vids, tweens, transparent=False)


def _two_clips(a: str, b: str, frames: int, w: int, h: int) -> str:
    style = f"position:absolute;left:0;top:0;width:{w}px;height:{h}px;object-fit:cover"
    return (f'<video id="va" class="clip" src="{a}" muted data-start="0" data-duration="{_secs(frames)}" style="{style}"></video>'
            f'<video id="vb" class="clip" src="{b}" muted data-start="0" data-duration="{_secs(frames)}" style="{style}"></video>')


def spin_page(a: str, b: str, frames: int, kind: str = "spin", w: int = W, h: int = H) -> str:
    """Outgoing clip spins away and shrinks, incoming spins in from the other side, both blurred mid-turn."""
    d, half = frames / FPS, frames / FPS / 2
    tweens = (f'tl.set("#vb",{{opacity:0}},0);'
              f'tl.to("#va",{{rotation:180,scale:0.4,filter:"blur(18px)",duration:{half:.4f},ease:"power2.in"}},0);'
              f'tl.set("#va",{{opacity:0}},{half:.4f});'
              f'tl.fromTo("#vb",{{rotation:-180,scale:0.4,opacity:1,filter:"blur(18px)"}},{{rotation:0,scale:1,'
              f'filter:"blur(0px)",duration:{d - half:.4f},ease:"power2.out"}},{half:.4f});')
    return _page(w, h, frames, _two_clips(a, b, frames, w, h), tweens, transparent=False)


def zoom_out_page(a: str, b: str, frames: int, kind: str = "zoom_out", w: int = W, h: int = H) -> str:
    """Outgoing clip pulls back to nothing while the incoming one settles from a close crop."""
    d = frames / FPS
    tweens = (f'tl.fromTo("#vb",{{scale:1.8,opacity:0}},{{scale:1,opacity:1,duration:{d:.4f},ease:"power2.out"}},0);'
              f'tl.to("#va",{{scale:0.3,opacity:0,filter:"blur(10px)",duration:{d:.4f},ease:"power2.in"}},0);')
    return _page(w, h, frames, _two_clips(a, b, frames, w, h), tweens, transparent=False)


GLITCH_STEPS = [(-0.06, 0.0), (0.04, 0.02), (-0.02, -0.03), (0.07, 0.01), (-0.05, 0.02), (0.03, -0.01)]


def glitch_page(a: str, b: str, frames: int, kind: str = "glitch", w: int = W, h: int = H) -> str:
    """Hard jumps with sideways offsets and a colour split; the incoming clip takes over half way. Deterministic."""
    d = frames / FPS
    n = max(2, min(len(GLITCH_STEPS), frames // 2))
    tw = ['tl.set("#vb",{opacity:0},0);']
    for i in range(n):
        t = d * i / n
        dx, dy = GLITCH_STEPS[i]
        tgt = "#va" if i < n / 2 else "#vb"
        if i == n // 2:
            tw.append(f'tl.set("#va",{{opacity:0}},{t:.4f});tl.set("#vb",{{opacity:1}},{t:.4f});')
        tw.append(f'tl.set("{tgt}",{{x:{dx * w:.0f},y:{dy * h:.0f},filter:"saturate(2.5) hue-rotate({60 * (i % 3)}deg) '
                  f'drop-shadow({8 * (1 if i % 2 else -1)}px 0 0 #ff0040)"}},{t:.4f});')
    tw.append(f'tl.set("#vb",{{x:0,y:0,filter:"none"}},{d * (n - 0.5) / n:.4f});')
    return _page(w, h, frames, _two_clips(a, b, frames, w, h), "".join(tw), transparent=False)


TRANSITION_PAGES = {"spin": spin_page, "zoom_out": zoom_out_page, "glitch": glitch_page}


class HyperFrames:
    name = "hyperframes"

    def supports(self, feature: str) -> bool:
        return feature in ENGINE_ANIMS or feature in SHADER_TRANSITIONS or feature in ("overlay", "sticker", "frame")

    def _project(self, work: Path, page: str, assets: list[Path] = ()) -> Path:
        from ..clients import video

        shutil.rmtree(work, ignore_errors=True)
        work.parent.mkdir(parents=True, exist_ok=True)
        video.client().hyperframes_init(work.name, output_dir=str(work.parent), template="blank", resolution="portrait",
                                        overwrite=True)
        for a in (GSAP_FILE, *assets):
            shutil.copy2(a, work / Path(a).name)
        (work / "index.html").write_text(page, encoding="utf-8")
        return work

    def _render(self, work: Path, out: Path, fmt: str, frames: int) -> Path:
        from ..clients import video

        raw = out.with_suffix(f".raw.{fmt}")
        video.client().hyperframes_render(str(work), output=str(raw), fps=FPS, format=fmt, overwrite=True)
        # exact length, whatever the browser capture rounded to; alpha kept (VP9 decoder that reads it)
        dec = ["-c:v", "libvpx-vp9"] if fmt == "webm" else []
        enc = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30"] if fmt == "webm" else \
            ["-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", "-video_track_timescale", "15360"]
        ff.run([*dec, "-i", str(raw), "-vf", f"fps={FPS},tpad=stop_mode=clone:stop={frames}", "-frames:v", str(frames),
                "-an", *enc, str(out)])
        raw.unlink(missing_ok=True)
        return out

    def render(self, layer: OverlaySpec, out: Path) -> Path:
        out = Path(out)
        assets = [Path(o["image"]) for o in layer.overlays if o.get("image")]
        work = self._project(out.parent / f"{out.stem}_hf", composition(layer), assets)
        return self._render(work, out, "webm", layer.n_frames)

    def transition(self, a: Path, b: Path, frames: int, kind: str, out: Path) -> Path:
        out = Path(out)
        page = TRANSITION_PAGES.get(kind, whip_page)
        work = self._project(out.parent / f"{out.stem}_hf", page(Path(a).name, Path(b).name, frames, kind),
                             [Path(a), Path(b)])
        return self._render(work, out, "mp4", frames)


ENGINES: list[OverlayEngine] = [HyperFrames()]  # Remotion second (not built yet, see docs/mvp-plan.md log)


def pick(feature: str) -> OverlayEngine | None:
    return next((e for e in ENGINES if e.supports(feature)), None)


def needs_engine(e: dict) -> bool:
    """libass draws one move and a static rotation; paths, 3D tilt and the engine animations need the engine."""
    if not capabilities.engine_available():
        return False
    persp = e.get("perspective") or {}
    return (e["anim_in"]["value"] in ENGINE_ANIMS or e["anim_out"]["value"] in ENGINE_ANIMS
            or bool(persp.get("rx") or persp.get("ry")) or bool(path_keys(e)))
