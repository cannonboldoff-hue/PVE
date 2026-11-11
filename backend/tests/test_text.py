"""M4: on-screen text detected (string, box, timing, animation), rebuilt with libass, measured back."""
import pytest

from app import ir
from app.render import textlayer
from app.stages import analyze, compare, roundtrip
from synth import Caption, SynthSpec, make_reel

# away from the marker digit (y 0.35..0.65) so each caption is read on its own
CAPS = [Caption("THREE TIPS", 6, 50, cy=0.2, anim="fade"),
        Caption("Big sale today", 58, 96, cy=0.75, anim="pop"),
        Caption("Swipe up now", 120, 170, cy=0.8, anim="slide_up"),
        Caption("No anim here", 180, 225, cy=0.15),
        Caption("Last one", 232, 280, cy=0.27, size=0.04, anim="fade")]


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    d = tmp_path_factory.mktemp("text")
    truth = make_reel(SynthSpec(n_frames=300, cuts=[100, 200], captions=CAPS), d / "reel.mp4")
    key, t, delta = analyze.run(d / "reel.mp4", provider=False)
    return key, t, truth


def _words(t):
    return [e for e in t.texts if not e.text.value.strip().isdigit()]  # the marker digit is on-screen text too


def test_detector_recovers_every_caption(reel):
    key, t, truth = reel
    found = _words(t)
    assert [e.text.value for e in found] == [c["text"] for c in truth.captions]
    for e, c in zip(found, truth.captions):
        assert abs(e.start - c["start"]) <= 2 and abs(e.end - c["end"]) <= 2, (e.id, e.start, e.end, c)
        assert compare.box_iou(e.keys[0].box, c["box"]) > 0.6, (e.id, e.keys[0].box, c["box"])
        if c["anim"] in ("fade", "pop", "slide_up"):
            assert e.anim_in.value == c["anim"], (e.id, e.anim_in.value, c["anim"])
        assert e.max_chars >= len(c["text"]) and e.text.binding == "swap"
    assert found[0].style.fill.upper() in ("#FFFFFF", "#FEFEFE", "#FDFDFD", "#FCFCFC", "#FBFBFB") or \
        int(found[0].style.fill[1:3], 16) > 200


def test_marker_pass_reproduces_every_caption(reel):
    key, t, truth = reel
    rows = roundtrip.marker_pass(key)
    for e in _words(t):
        mine = [r for r in rows if r.metric.startswith(e.id + " ")]
        assert mine, e.id
        bad = [r.model_dump() for r in mine if not r.ok and r.track == "text"]
        assert not bad, bad


def test_ass_timing_is_frame_exact():
    # frame f is at f/30 s; the event must start after frame f-1 and at or before frame f
    for f in (0, 1, 3, 10, 29, 30, 31, 299):
        h, m, s = textlayer.ts(f).split(":")
        t = int(h) * 3600 + int(m) * 60 + float(s)
        assert (f - 1) / 30 < t <= f / 30 + 1e-9, (f, t)
