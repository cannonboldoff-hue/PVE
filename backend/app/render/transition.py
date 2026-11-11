"""Transition segment between two prepped clips: the last `frames` of a and the first `frames` of b, exactly
`frames` frames out."""
from pathlib import Path

from .. import config
from ..clients import ff
from .shot import CRF

FPS = config.FPS
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(CRF), "-pix_fmt", "yuv420p", "-video_track_timescale",
       "15360", "-an"]  # same settings as render/shot.py so the concat demuxer can stream-copy


def render(a: Path, a_frames: int, b: Path, frames: int, xfade: str, out: Path) -> None:
    """a_frames: length of clip a (its tail is the last `frames`); xfade: an ffmpeg xfade transition name, or
    "overlay:<kind>" for a transition the overlay engine draws from the two overlap clips."""
    if xfade.startswith("overlay:"):
        from . import overlay

        kind = xfade.split(":", 1)[1]
        tail, head = Path(out).with_suffix(".a.mp4"), Path(out).with_suffix(".b.mp4")
        cut(Path(a), a_frames - frames, a_frames, tail)
        cut(Path(b), 0, frames, head)
        try:
            overlay.pick(kind).transition(tail, head, frames, kind, Path(out))
        finally:
            tail.unlink(missing_ok=True), head.unlink(missing_ok=True)
        return
    graph = (f"[0:v]trim=start_frame={a_frames - frames},setpts=PTS-STARTPTS[a];"
             f"[1:v]trim=end_frame={frames},setpts=PTS-STARTPTS[b];"
             f"[a][b]xfade=transition={xfade}:duration={frames / FPS:.6f}:offset=0,"
             f"tpad=stop_mode=clone:stop={frames}[v]")
    ff.run(["-i", str(a), "-i", str(b), "-filter_complex", graph, "-map", "[v]", "-frames:v", str(frames), "-r", str(FPS),
            *ENC, str(out)])


def cut(src: Path, start: int, end: int, out: Path) -> None:
    """Frames [start, end) of a prepped clip (the body between its transitions)."""
    ff.run(["-i", str(src), "-vf", f"trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS",
            "-frames:v", str(end - start), "-r", str(FPS), *ENC, str(out)])
