"""M8: layout, picture in picture, blurred fill and a static overlay detected and rebuilt; colour moves toward
the target."""
import numpy as np
import pytest

from app import evidence, ir
from app.clients import ff
from app.evidence import colour
from app.render import shot
from app.stages import analyze, compare, extract, fusion, roundtrip
from synth import SynthSpec, make_reel

OVERLAY = (0.05, 0.86, 0.3, 0.06)


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    d = tmp_path_factory.mktemp("layout")
    truth = make_reel(SynthSpec(n_frames=200, cuts=[50, 100, 150], textured=True, overlay=OVERLAY,
                                layouts={0: "split_v", 1: "pip", 2: "blur_fill"}), d / "reel.mp4")
    src = analyze.ingest(d / "reel.mp4")
    ev = evidence.run_all(src.key, only=["cuts", "transitions", "layout", "overlays", "colour"])
    t = extract.build(fusion.fuse(src, ev))
    t.texts = []  # the markers' own digits are read as text; the text tests cover text
    ir.save(src.key, "template", t)
    return src.key, t, truth


def test_layouts_and_overlay_detected(reel):
    _, t, truth = reel
    for seg, want in truth.layouts.items():
        s = t.slots[seg]
        assert s.layout.value == want["value"], (seg, s.layout.value)
        for b in want["boxes"]:
            assert max(compare.box_iou(b, g) for g in s.layout_boxes) > 0.7, (seg, b, s.layout_boxes)
    assert t.slots[3].layout.value == "single"
    assert len(t.overlays) == 1 and compare.box_iou(t.overlays[0].keys[0].box, truth.overlay) > 0.7
    assert all(s.colour is not None for s in t.slots)


def test_marker_pass_rebuilds_layouts_and_overlay(reel):
    key, _, _ = reel
    rows = roundtrip.marker_pass(key, ["transitions", "layout", "overlays"])
    bad = [r.model_dump() for r in rows if not r.ok and r.track in ("layout", "overlays")]
    assert not bad, bad
    assert any(r.track == "overlays" for r in rows)


def test_colour_moves_toward_target(tmp_path):
    src = tmp_path / "s.mp4"
    ff.run(["-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=2", "-vf", "eq=brightness=-0.15:saturation=0.6",
            "-pix_fmt", "yuv420p", str(src)])
    target = {"l_mean": 150.0, "l_std": 60.0, "a_mean": 128.0, "a_std": 10.0, "b_mean": 150.0, "b_std": 15.0,
              "saturation": 0.6, "contrast": 0.7}
    before = colour.stats(shot.sample(str(src), 0, 1.5))
    out = tmp_path / "o.mp4"
    shot.prep({"path": str(src), "in": 0, "frames": 45, "colour": target}, out)
    after = colour.stats(ff.decode(out, 160, 284)[::5])
    for k in ("l_mean", "b_mean", "saturation"):
        assert abs(after[k] - target[k]) < abs(before[k] - target[k]), (k, before[k], after[k], target[k])
    assert ff.count_frames(out) == 45
    assert np.isfinite(list(after.values())).all()
