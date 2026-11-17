"""Join frame-exact slot clips (concat demuxer, stream copy), then one final pass: burn the text layer and mux audio."""
import shutil
from pathlib import Path

from .. import config
from ..clients import ff
from ..models import Plan
from . import capabilities, overlay, textlayer, transition

FPS = config.FPS


def starts(plan: Plan) -> list[float]:
    """Start time of each shot in seconds, from exact frame counts."""
    out, f = [], 0
    for s in plan.shots:
        out.append(f / FPS)
        f += s.frames - s.tail  # the next clip starts where this one's outgoing window starts
    return out


def _audio_args(plan: Plan, n_frames: int) -> tuple[list[str], list[str]]:
    """(extra inputs, output args) for the soundtrack. Reference mode: the reference audio unchanged, no loop."""
    secs = f"{n_frames / FPS:.6f}"
    if plan.music_path:
        vol = 1.0 if plan.audio_mode == "reference" else plan.music_volume
        af = f"volume={vol},apad,atrim=0:{secs}" if vol != 1.0 else f"apad,atrim=0:{secs}"
        return ["-i", str(Path(plan.music_path).resolve())], ["-map", "1:a:0", "-af", af]
    # no soundtrack chosen: a silent track so players and checks see a normal file
    return ["-f", "lavfi", "-t", secs, "-i", "anullsrc=r=48000:cl=stereo"], ["-map", "1:a:0"]


FULL_FRAME = 0.05  # a layer clip within this of the frame's aspect is a full-frame cut-out, drawn at 0,0


def layer_overlay(base: str, idx: int, c: dict, label: str) -> str:
    """A supplied layer clip (alpha kept) over base from its start frame, moving from its first to its last key."""
    from ..clients import ff as ff_

    keys = sorted(c["keys"], key=lambda k: k["frame"])
    v = ff_.video_stream(ff_.probe(c["path"]))
    full = abs(int(v["width"]) / max(1, int(v["height"])) - config.W / config.H) < FULL_FRAME and \
        keys[0]["box"]["w"] > 0.5
    k0, k1 = keys[0], keys[-1]
    t0, t1 = k0["frame"] / FPS, max(k0["frame"] + 1, k1["frame"]) / FPS
    if full:
        size, x, y = f"{config.W}:{config.H}", "0", "0"
    else:
        b0, b1 = k0["box"], k1["box"]
        size = f"{max(2, round(b0['w'] * config.W / 2) * 2)}:{max(2, round(b0['h'] * config.H / 2) * 2)}"
        p = f"clip((t-{t0:.4f})/{t1 - t0:.4f},0,1)"
        x = f"{b0['x'] * config.W:.1f}+({(b1['x'] - b0['x']) * config.W:.1f})*{p}"
        y = f"{b0['y'] * config.H:.1f}+({(b1['y'] - b0['y']) * config.H:.1f})*{p}"
    return (f"[{idx}:v]format=yuva420p,scale={size},setpts=PTS-STARTPTS+{c['start'] / FPS:.4f}/TB[c{label}];"
            f"{base}[c{label}]overlay=x='{x}':y='{y}':eval=frame:eof_action=pass:"
            f"enable='between(n,{c['start']},{c['end'] - 1})'[{label}]")


def assemble(plan: Plan, clips: list[Path], workdir: Path, out: Path) -> float:
    """Returns the planned length in seconds (n_frames / FPS)."""
    from ..stages import editor

    k = len(plan.shots)
    clips, trans = list(clips[:k]), list(clips[k:])  # graph order: prep nodes, then transition segments
    n = sum(s.frames for s in plan.shots) - sum(t["frames"] for t in plan.transitions)
    if plan.n_frames is not None and n != plan.n_frames:
        raise ValueError(f"slot frames add up to {n}, plan says {plan.n_frames}")
    tmp = Path(workdir) / "assemble_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        after = {t["after"]: seg for t, seg in zip(plan.transitions, trans)}
        parts = []
        for i, (s, c) in enumerate(zip(plan.shots, clips)):
            if s.lead or s.tail:  # only the body: the overlaps live in the transition segments
                if s.frames - s.lead - s.tail > 0:
                    body = tmp / f"body{i:03d}.mp4"
                    transition.cut(Path(c), s.lead, s.frames - s.tail, body)
                    parts.append(body)
            else:
                parts.append(c)
            if i in after:
                parts.append(after[i])
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{Path(p).resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
        body = tmp / "body.mp4"
        ff.run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(body)])
        ins, aargs = _audio_args(plan, n)
        vargs = ["-c:v", "copy"]
        doc, layer = None, None
        engine_texts = [e for e in plan.texts if overlay.needs_engine(e)]
        images = [o for o in plan.overlays if o.get("image")]
        if engine_texts or images:  # what libass and drawbox cannot draw: one transparent layer from the engine
            layer = overlay.pick("overlay").render(overlay.OverlaySpec(n, engine_texts, images), tmp / "layer.webm")
        lib_texts = [e for e in plan.texts if not overlay.needs_engine(e)]
        if lib_texts:
            doc, _losses = textlayer.ass(lib_texts)  # losses reach the user on the template card (main._template_report)
        elif plan.captions and any(s.caption.strip() for s in plan.shots):
            doc = editor._ass(plan, starts(plan))
        vf = [f for f in (capabilities.effect_filter(e) for e in plan.effects) if f]
        for o in plan.overlays:  # shortcut: solid boxes only; user images and animated layers arrive with M9
            if o.get("colour"):
                b = o["box"]
                vf.append(f"drawbox=x={round(b['x'] * config.W)}:y={round(b['y'] * config.H)}:w={round(b['w'] * config.W)}:"
                          f"h={round(b['h'] * config.H)}:color={o['colour'].replace('#', '0x')}:t=fill:"
                          f"enable='between(n,{o['start']},{o['end'] - 1})'")
        if doc:
            (tmp / "captions.ass").write_text(doc, encoding="utf-8")
            vf.append("subtitles=captions.ass")
        enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p"]
        if layer or plan.layer_clips:  # one graph: engine layer, layer clips under / over the text
            graph, cur, nxt = [], "0:v", 2
            if layer:  # composite under the libass text and effects; input 2 after the soundtrack
                ins += ["-c:v", "libvpx-vp9", "-i", str(layer.resolve())]
                graph.append("[0:v][2:v]overlay=0:0:eof_action=pass[b0]")
                cur, nxt = "b0", 3
            below = [c for c in plan.layer_clips if not c.get("above_text")]
            above = [c for c in plan.layer_clips if c.get("above_text")]
            for k, c in enumerate(below + above):
                ins += [*(["-c:v", "libvpx-vp9"] if Path(c["path"]).suffix.lower() == ".webm" else []),
                        "-i", str(Path(c["path"]).resolve())]
            for k, c in enumerate(below):
                graph.append(layer_overlay(f"[{cur}]", nxt + k, c, f"lb{k}"))
                cur = f"lb{k}"
            graph.append(f"[{cur}]{','.join(vf) or 'null'}[mid]")
            cur = "mid"
            for k, c in enumerate(above):
                graph.append(layer_overlay(f"[{cur}]", nxt + len(below) + k, c, f"la{k}"))
                cur = f"la{k}"
            graph.append(f"[{cur}]null[vout]")
            vargs = ["-filter_complex", ";".join(graph), *enc]
        elif vf:
            vargs = ["-vf", ",".join(vf), *enc]
        # cwd=tmp so the subtitles filter sees a bare file name (no C:\ escaping)
        vmap = ["-map", "[vout]"] if layer or plan.layer_clips else ["-map", "0:v:0"]
        ff.run(["-i", str(body.resolve()), *ins, *vmap, *aargs, *vargs, "-frames:v", str(n),
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", str((tmp / "final.mp4").resolve())], cwd=tmp)
        shutil.copy2(tmp / "final.mp4", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n / FPS
