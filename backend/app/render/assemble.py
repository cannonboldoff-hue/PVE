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
            doc, _losses = textlayer.ass(lib_texts)
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
        if layer:  # composite under the libass text and effects; input 2 after the soundtrack
            ins += ["-c:v", "libvpx-vp9", "-i", str(layer.resolve())]
            chain = ",".join(vf) or "null"
            vargs = ["-filter_complex", f"[0:v][2:v]overlay=0:0:eof_action=pass,{chain}[vout]", "-c:v", "libx264",
                     "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p"]
        elif vf:
            vargs = ["-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p"]
        # cwd=tmp so the subtitles filter sees a bare file name (no C:\ escaping)
        vmap = ["-map", "[vout]"] if layer else ["-map", "0:v:0"]
        ff.run(["-i", str(body.resolve()), *ins, *vmap, *aargs, *vargs, "-frames:v", str(n),
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", str((tmp / "final.mp4").resolve())], cwd=tmp)
        shutil.copy2(tmp / "final.mp4", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n / FPS
