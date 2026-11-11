"""M6: boundary windows and classes measured, rebuilt from two prepped clips, measured back."""
import pytest

from app import evidence, ir
from app.clients import ff
from app.stages import analyze, extract, fusion, roundtrip
from synth import SynthSpec, Trans, make_reel

TRANS = [Trans(0, "fade", 10), Trans(1, "dissolve", 10), Trans(2, "slide_left", 12), Trans(3, "wipe_up", 10),
         Trans(4, "fade_black", 14)]


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    d = tmp_path_factory.mktemp("trans")
    truth = make_reel(SynthSpec(n_frames=360, cuts=[40, 90, 140, 190, 240, 300], textured=True, transitions=TRANS),
                      d / "reel.mp4")
    src = analyze.ingest(d / "reel.mp4")
    ev = evidence.run_all(src.key, only=["cuts", "transitions"])
    t = extract.build(fusion.fuse(src, ev))
    ir.save(src.key, "template", t)
    return src.key, t, truth


def test_windows_and_classes(reel):
    _, t, truth = reel
    assert t.cuts() == truth.cuts  # gradual boundaries become slot boundaries mid-window
    got = {tr.after_slot: tr for tr in t.transitions}
    for want in truth.transitions:
        tr = got[t.slots[want["after"]].id]
        assert tr.type.value == want["type"], (want, tr.type.value)
        assert abs(tr.start - want["start"]) <= 2 and abs(tr.end - want["end"]) <= 2, (want, tr.start, tr.end)
        assert tr.render.startswith("ffmpeg:") and not tr.loss
    assert got[t.slots[5].id].type.value == "cut" and got[t.slots[5].id].start == got[t.slots[5].id].end == 300


def test_rebuilt_reel_is_exact_and_marker_pass_finds_the_same_windows(reel):
    key, t, _ = reel
    rows = roundtrip.marker_pass(key, ["transitions"])
    assert ff.count_frames(ir.ref_dir(key) / "mk" / "render.mp4") == t.n_frames
    bad = [r.model_dump() for r in rows if not r.ok and "class" not in r.metric]
    assert not bad, bad
    classes = [r for r in rows if "class" in r.metric]
    assert sum(r.ok for r in classes) >= len(classes) - 1, [r.model_dump() for r in classes]
