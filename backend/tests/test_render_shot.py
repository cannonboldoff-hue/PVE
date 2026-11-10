import numpy as np
import pytest

from app.clients import ff
from app.render import shot
from synth import H, W, bar_x, marker_clip


@pytest.mark.parametrize("fps", [24, 25, 30, 60])
def test_prep_frame_count_is_exact(tmp_path, fps):
    src = tmp_path / f"s{fps}.mp4"
    ff.run(["-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate={fps}:duration=4", "-pix_fmt", "yuv420p", str(src)])
    for fit in ("cover", "blur_fit"):
        out = tmp_path / f"o{fps}{fit}.mp4"
        shot.prep({"path": str(src), "in": 1.3, "frames": 47, "fit": fit}, out)
        assert ff.count_frames(out) == 47
        v = ff.video_stream(ff.probe(out))
        assert (v["width"], v["height"], v["r_frame_rate"]) == (1080, 1920, "30/1")


def test_prep_selects_the_exact_source_frame(tmp_path):
    src = marker_clip(1, 120, tmp_path / "m.mp4")  # bar moves 6 px per frame: bar x tells the source frame
    for start in (0, 7, 45, 61):
        out = tmp_path / f"p{start}.mp4"
        shot.prep({"path": str(src), "in": start / 30, "frames": 10}, out)
        got = [bar_x(f) for f in ff.decode(out, W, H)]
        want = [bar_x(f) for f in ff.decode(src, W, H)[start:start + 10]]
        assert np.allclose(got, want, atol=3), (start, got, want)


def test_short_source_slows_then_holds(tmp_path):
    src = marker_clip(2, 20, tmp_path / "m.mp4")
    out = tmp_path / "o.mp4"
    shot.prep({"path": str(src), "in": 0, "frames": 60, "speed": 0.5}, out)
    xs = [bar_x(f) for f in ff.decode(out, W, H)]
    assert ff.count_frames(out) == 60
    assert xs[-1] == xs[-10]  # held
    assert 2.5 <= np.mean(np.diff(xs[:30])) <= 3.5  # half speed, no interpolation: each frame twice, 3 px on average
