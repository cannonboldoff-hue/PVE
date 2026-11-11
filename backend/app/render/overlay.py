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
from . import textlayer

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


GSAP = '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'


def _secs(f: int, fps: int = FPS) -> str:
    return f"{f / fps:.4f}"


def _text_html(k: int, e: dict, w: int, h: int) -> tuple[str, list[str]]:
    """One text event as a positioned div plus its GSAP tweens."""
    st, box = e["style"], e["keys"][0]["box"]
    words = e["text"]["value"]
    fs = textlayer.font_size(e["text"].get("raw") or words, st["size"], st["font"], st.get("bold", True), h)
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
    spans = a_in in ("word_highlight", "typewriter")
    pieces = (words.split(" ") if a_in == "word_highlight" else list(words)) if spans else [words]
    joiner = " " if a_in == "word_highlight" else ""
    inner = joiner.join(f'<span class="p{k}">{html.escape(p)}</span>' for p in pieces) if spans else html.escape(words)
    div = (f'<div id="t{k}" class="clip" data-start="{_secs(e["start"])}" data-duration="{_secs(e["end"] - e["start"])}" '
           f'style="position:absolute;{";".join(css)}">{inner}</div>')
    tw = []
    if a_in == "bounce":
        tw.append(f'tl.fromTo("{sel}",{{y:{0.12 * h:.0f}}},{{y:0,duration:{n_in:.3f},ease:"bounce.out"}},{t0:.4f});')
    elif a_in == "word_highlight":  # each word lights up in turn, grows a little, then settles back
        per = (t1 - t0) / max(1, len(pieces))
        tw.append(f'tl.to(".p{k}",{{color:"#FFD400",scale:1.12,duration:{min(per, 0.15):.3f},'
                  f'stagger:{{each:{per:.3f},yoyo:true,repeat:1}}}},{t0:.4f});')
    elif a_in == "typewriter":
        tw.append(f'tl.fromTo(".p{k}",{{opacity:0}},{{opacity:1,duration:0.001,stagger:{n_in / max(1, len(pieces)):.4f}}},{t0:.4f});')
    elif a_in == "fade":
        tw.append(f'tl.fromTo("{sel}",{{opacity:0}},{{opacity:1,duration:{n_in:.3f}}},{t0:.4f});')
    elif a_in == "pop":
        tw.append(f'tl.fromTo("{sel}",{{scale:0.5}},{{scale:1,duration:{n_in:.3f}}},{t0:.4f});')
    if a_out in ("fade", "bounce", "other"):
        tw.append(f'tl.to("{sel}",{{opacity:0,duration:{n_out:.3f}}},{t1 - n_out:.4f});')
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
        for a in assets:
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
        work = self._project(out.parent / f"{out.stem}_hf", whip_page(Path(a).name, Path(b).name, frames, kind),
                             [Path(a), Path(b)])
        return self._render(work, out, "mp4", frames)


ENGINES: list[OverlayEngine] = [HyperFrames()]  # Remotion second (not built yet, see docs/mvp-plan.md log)


def pick(feature: str) -> OverlayEngine | None:
    return next((e for e in ENGINES if e.supports(feature)), None)


def needs_engine(e: dict) -> bool:
    return e["anim_in"]["value"] in ENGINE_ANIMS or e["anim_out"]["value"] in ENGINE_ANIMS
