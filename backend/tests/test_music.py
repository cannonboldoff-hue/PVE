import numpy as np
import soundfile as sf

from app.clients import video
from app.models import Plan, PlanShot
from app.stages import editor, music, orchestrator
from helpers import ff


def click_track(path, bpm=120, secs=10, sr=22050):
    y = np.zeros(int(secs * sr), dtype="float32")
    for t in np.arange(0, secs, 60 / bpm):
        i = int(t * sr)
        n = int(0.12 * sr)  # a decaying 100 Hz thump, like a kick drum
        y[i:i + n] = np.exp(-np.arange(n) / (0.03 * sr)) * 0.9 * np.sin(2 * np.pi * 100 * np.arange(n) / sr)[:len(y[i:i + n])]
    sf.write(path, y, sr)


def shots(durs, transition="cut"):
    return Plan(shots=[PlanShot(shot_id=i, asset_id="a", path="x.mp4", src_in=0, src_out=d, transition=transition)
                       for i, d in enumerate(durs, 1)])


def test_detect_beats(tmp_path):
    p = tmp_path / "click.wav"
    click_track(p)
    beats, length = music.detect_beats(str(p))
    assert 9.5 < length < 10.5
    # 120 bpm = a beat every 0.5 s; allow a constant offset but not a wrong tempo
    gaps = np.diff(beats)
    assert abs(np.median(gaps) - 0.5) < 0.05


def test_cuts_land_on_beats_and_length_is_kept():
    plan = shots([1.8, 2.3, 1.9, 2.0])  # cuts at 1.8, 4.1, 6.0 on a 0.5 s grid
    music.snap_to_beats(plan, [i * 0.5 for i in range(40)], 20.0, {"a": 10.0})
    starts = np.cumsum([0, *[s.duration for s in plan.shots]])
    assert all(abs(c / 0.5 - round(c / 0.5)) < 1e-6 for c in starts[1:-1]), starts
    assert abs(starts[-1] - 8.0) < 1e-6


def test_far_cuts_stay_and_short_clips_slow_down():
    plan = shots([1.8, 2.0])
    music.snap_to_beats(plan, [i * 4.0 for i in range(5)], 20.0, {"a": 10.0})  # nearest beat 1.8 s away: no move
    assert abs(plan.shots[0].duration - 1.8) < 1e-6
    plan = shots([1.8, 2.0])
    music.snap_to_beats(plan, [i * 0.5 for i in range(40)], 20.0, {"a": 1.8})  # source can't grow: slows down instead
    assert plan.shots[0].src_out <= 1.8 and plan.shots[0].speed <= 1.0


def test_reference_song_replaces_clip_audio(tmp_path):
    clip = tmp_path / "c.mp4"
    ff("-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=4", "-f", "lavfi", "-i", "sine=frequency=880:duration=4",
       "-pix_fmt", "yuv420p", "-shortest", str(clip))
    song = tmp_path / "song.wav"
    click_track(song, secs=2)  # shorter than the reel: must loop
    plan = Plan(shots=[PlanShot(shot_id=1, asset_id="a", path=str(clip), src_in=0, src_out=3),
                       PlanShot(shot_id=2, asset_id="a", path=str(clip), src_in=0, src_out=3, transition="cut")],
                music_path=str(song), music_mode="replace", music_volume=0.8)
    final, dur, _ = orchestrator.run("pm", plan, tmp_path, lambda: None)
    assert video.info(final)["has_audio"] and abs(video.info(final)["duration"] - dur) < 0.5
    # clip audio was a loud 880 Hz tone; with the song replacing it, the tail (past the 2 s song) must still carry sound
    out = tmp_path / "tail.wav"
    ff("-ss", "4", "-i", str(final), "-t", "1.5", str(out))
    tail, _sr = sf.read(out)
    assert np.abs(tail).max() > 0.05  # looped song present, not silence
