"""Join frame-exact slot clips (concat demuxer, stream copy), then one final pass: burn the text layer and mux audio."""
import shutil
from pathlib import Path

from .. import config
from ..clients import ff
from ..models import Plan

FPS = config.FPS


def starts(plan: Plan) -> list[float]:
    """Start time of each shot in seconds, from exact frame counts."""
    out, f = [], 0
    for s in plan.shots:
        out.append(f / FPS)
        f += s.frames
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

    n = sum(s.frames for s in plan.shots)
    if plan.n_frames is not None and n != plan.n_frames:
        raise ValueError(f"slot frames add up to {n}, plan says {plan.n_frames}")
    tmp = Path(workdir) / "assemble_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{Path(c).resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
        body = tmp / "body.mp4"
        ff.run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(body)])
        ins, aargs = _audio_args(plan, n)
        vargs = ["-c:v", "copy"]
        if plan.captions and any(s.caption.strip() for s in plan.shots):
            (tmp / "captions.ass").write_text(editor._ass(plan, starts(plan)), encoding="utf-8")
            vargs = ["-vf", "subtitles=captions.ass", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                     "-pix_fmt", "yuv420p"]
        # cwd=tmp so the subtitles filter sees a bare file name (no C:\ escaping)
        ff.run(["-i", str(body.resolve()), *ins, "-map", "0:v:0", *aargs, *vargs, "-frames:v", str(n),
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", str((tmp / "final.mp4").resolve())], cwd=tmp)
        shutil.copy2(tmp / "final.mp4", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n / FPS
