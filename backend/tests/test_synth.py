import numpy as np

from app.clients import ff
from synth import H, W, Caption, SynthSpec, Trans, Zoom, bar_x, colour, make_reel, marker_clip


def _near(px, rgb, tol=20):
    return np.abs(px.astype(int) - np.array(rgb)).max() <= tol


def test_make_reel_frame_count_and_cuts(tmp_path):
    spec = SynthSpec(n_frames=120, cuts=[30, 55, 90], captions=[Caption("HELLO", 10, 40)], flash=70,
                     zoom=Zoom(seg=1))
    truth = make_reel(spec, tmp_path / "r.mp4")
    assert ff.count_frames(tmp_path / "r.mp4") == 120 == truth.n_frames
    assert truth.segments == [(0, 30), (30, 55), (55, 90), (90, 120)]
    frames = ff.decode(tmp_path / "r.mp4", W, H)
    probe = (int(H * 0.9), 20)  # a corner pixel away from number, bar and caption
    for i, c in enumerate(truth.cuts):
        assert _near(frames[c - 1][probe], colour(i + 1)), f"frame {c - 1}"
        assert _near(frames[c][probe], colour(i + 2)), f"frame {c}"
    assert frames[70].mean() > 200 and frames[69].mean() < 200 and frames[72].mean() < 200
    b = truth.captions[0]["box"]
    assert abs(b.x + b.w / 2 - 0.5) < 0.01 and abs(b.y + b.h / 2 - 0.75) < 0.02 and b.h > 0.03


def test_transition_window_and_bar(tmp_path):
    spec = SynthSpec(n_frames=60, cuts=[30], transitions=[Trans(after=0, type="fade", frames=10)])
    truth = make_reel(spec, tmp_path / "t.mp4")
    assert truth.transitions == [{"after": 0, "type": "fade", "start": 25, "end": 35}]
    frames = ff.decode(tmp_path / "t.mp4", W, H)
    p = (int(H * 0.9), 20)
    assert _near(frames[24][p], colour(1)) and _near(frames[35][p], colour(2))
    mid = frames[30][p].astype(int)
    assert not _near(frames[30][p], colour(1)) and not _near(frames[30][p], colour(2))
    assert mid.sum() > 0
    m = tmp_path / "m.mp4"
    marker_clip(3, 20, m)
    mf = ff.decode(m, W, H)
    xs = [bar_x(f) for f in mf]
    assert ff.count_frames(m) == 20
    assert np.allclose(np.diff(xs), 6, atol=1.5)
