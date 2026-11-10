"""Soundtrack: the reference Reel's audio (kept as audio only), beat detection, and cut-to-beat snapping."""
import json
from pathlib import Path

from .. import config
from ..clients import video
from ..models import Plan
from . import editor
from . import plan as plan_mod

REFERENCE_VOLUME = 0.7  # songs are mastered near 0 dBFS; the verifier flags true peaks above -0.1 dBTP
TOLERANCE = 0.4  # a cut only moves to a beat this close; otherwise it stays where it is
MIN_SHOT = 0.6


def audio_path(key: str) -> Path:
    return config.REF_AUDIO / (key.replace(":", "_") + ".wav")


def extract(src: Path, key: str) -> Path | None:
    """Pull the audio track out of the reference video before the video is deleted. None if it has no audio."""
    dest = audio_path(key)
    try:
        video.client().extract_audio(str(src), output=str(dest), format="wav", overwrite=True)
    except Exception:
        dest.unlink(missing_ok=True)
        return None
    return dest if dest.exists() else None


def music_for(brief: dict, project: dict, assets: dict[str, dict]) -> tuple[str | None, str]:
    """(music file, mode). 'replace' = the song becomes the soundtrack; 'duck' = it sits under the clip audio."""
    if brief["music"] == "reference" and project["reference_id"]:
        p = audio_path(project["reference_id"])
        if p.exists():
            return str(p), "replace"
    if brief["music"] == "uploaded" and project["music_asset"] in assets:
        return assets[project["music_asset"]]["path"], "duck"
    return None, "duck"


def detect_beats(path: str) -> tuple[list[float], float]:
    """(beat times in seconds, track length). Cached next to the audio file."""
    cache = Path(path + ".beats.json")
    if cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
        return d["beats"], d["length"]
    import librosa

    y, sr = librosa.load(path, sr=22050)
    _, frames = librosa.beat.beat_track(y=y, sr=sr)
    beats = [float(t) for t in librosa.frames_to_time(frames, sr=sr)]
    length = len(y) / sr
    cache.write_text(json.dumps({"beats": beats, "length": length}), encoding="utf-8")
    return beats, length


def snap_to_beats(plan: Plan, beats: list[float], length: float, asset_len: dict[str, float]) -> None:
    """Move interior cuts onto the nearest beat (within TOLERANCE) by re-timing the shots on either side.
    Total length is kept; the last shot absorbs the drift. The music starts at 0 and loops, so the beat grid repeats."""
    n = len(plan.shots)
    if n < 2 or not beats:
        return
    durs = [s.duration for s in plan.shots]
    td, starts, total = editor.timeline(plan, durs)
    grid = list(beats)
    if length > 0:
        k = 1
        while grid[-1] < total + length:
            grid += [b + k * length for b in beats]
            k += 1
    t = [0.0 if s.transition == "cut" else td for s in plan.shots[:-1]]
    # a boundary is the centre of its transition (the cut itself for hard cuts)
    snapped, prev = [], 0.0
    for i in range(n - 1):
        x = starts[i + 1] + t[i] / 2
        near = min(grid, key=lambda g: abs(g - x))
        y = near if abs(near - x) <= TOLERANCE else x
        y = max(y, prev + MIN_SHOT)
        snapped.append(y)
        prev = y
    if total - prev < MIN_SHOT:
        return  # snapping would squeeze the last shot; leave the plan as is
    bounds = [0.0, *snapped, total]
    tt = [0.0, *t, 0.0]
    for i, s in enumerate(plan.shots):
        d = (bounds[i + 1] - bounds[i]) + tt[i] / 2 + tt[i + 1] / 2
        _retime(s, d, asset_len.get(s.asset_id, float("inf")))


def _retime(s, d: float, source_len: float) -> None:
    """Make the shot last d seconds: take more or less source at the same speed; if the clip runs out, slow it down."""
    want_out = s.src_in + d * s.speed
    if want_out <= source_len:
        s.src_out = want_out
    else:
        s.src_out = source_len
        s.speed = min(2.0, max(0.5, (source_len - s.src_in) / d))
    plan_mod._fit_caption(s)


def sync_plan(plan: Plan, assets: dict[str, dict]) -> None:
    if plan.music_path:
        beats, length = detect_beats(plan.music_path)
        snap_to_beats(plan, beats, length, {k: a["duration"] or float("inf") for k, a in assets.items()})
