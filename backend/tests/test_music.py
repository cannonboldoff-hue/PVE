import numpy as np

from app.clients import ff, video
from app.models import Plan, PlanShot
from app.stages import orchestrator
from helpers import ff as run_ff


def test_reference_song_replaces_clip_audio(tmp_path):
    """Legacy (seconds-based) plans: the song loops under the reel and the clip audio is dropped."""
    clip = tmp_path / "c.mp4"
    run_ff("-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=4", "-f", "lavfi", "-i", "sine=frequency=880:duration=4",
           "-pix_fmt", "yuv420p", "-shortest", str(clip))
    song = tmp_path / "song.wav"
    run_ff("-f", "lavfi", "-i", "sine=frequency=100:duration=2", str(song))  # shorter than the reel: must loop
    plan = Plan(shots=[PlanShot(shot_id=1, asset_id="a", path=str(clip), src_in=0, src_out=3),
                       PlanShot(shot_id=2, asset_id="a", path=str(clip), src_in=0, src_out=3, transition="cut")],
                music_path=str(song), music_mode="replace", music_volume=0.8)
    final, dur, _ = orchestrator.run("pm", plan, tmp_path, lambda: None)
    assert video.info(final)["has_audio"] and abs(video.info(final)["duration"] - dur) < 0.5
    # clip audio was a loud 880 Hz tone; with the song replacing it, the tail (past the 2 s song) must still carry sound
    out = tmp_path / "tail.wav"
    run_ff("-ss", "4", "-i", str(final), "-t", "1.5", str(out))
    tail = ff.audio_samples(out)
    assert np.abs(tail).max() > 0.05  # looped song present, not silence
