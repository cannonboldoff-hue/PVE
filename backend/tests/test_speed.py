"""M7: speed ramp, freeze and flash measured, rebuilt, measured back; footage arithmetic."""
import pytest

from app import evidence, ir
from app.clients import ff
from app.render import shot
from app.stages import analyze, extract, fusion, requirements, roundtrip
from synth import SynthSpec, bar_x, make_reel, marker_clip, H, W

RAMP = [(0.0, 1.0), (1 / 3, 3.0), (2 / 3, 0.5)]


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    d = tmp_path_factory.mktemp("speed")
    make_reel(SynthSpec(n_frames=180, cuts=[60, 120], textured=True, flash=30, speeds={1: RAMP},
                        freezes={2: [(20, 30)]}), d / "reel.mp4")
    src = analyze.ingest(d / "reel.mp4")
    ev = evidence.run_all(src.key, only=["cuts", "transitions", "camera", "speed", "effects"])
    t = extract.build(fusion.fuse(src, ev))
    ir.save(src.key, "template", t)
    return src.key, t


def test_ramp_freeze_flash_measured(reel):
    _, t = reel
    assert t.cuts() == [60, 120]  # the flash is not a cut
    (p0, f0), (p1, f1), (p2, f2) = t.slots[1].speed
    assert abs(p1 * 60 - 20) <= 3 and abs(p2 * 60 - 40) <= 3
    for got, want in ((f0, 1.0), (f1, 3.0), (f2, 0.5)):
        assert abs(got - want) / want <= 0.25, t.slots[1].speed
    assert t.slots[2].freeze and all(abs(x - y) <= 2 for x, y in zip(t.slots[2].freeze[0], (20, 30)))
    flash = [e for e in t.effects if e.type.value == "flash"]
    assert [(e.start, e.end) for e in flash] == [(30, 32)]


def test_footage_arithmetic():
    s = ir.Slot(id="s", start=0, end=60, speed=RAMP)
    assert requirements.footage_frames(s) == 20 * 1 + 20 * 3 + 20 * 0.5  # 90
    s.freeze = [(20, 30)]  # a freeze over part of the 3x piece uses none of its footage
    assert requirements.footage_frames(s) == 20 + 10 * 3 + 20 * 0.5 + 3  # held frame advances by one 3x step after
    assert requirements.footage_frames(s, lead=6, tail=4) == requirements.footage_frames(s) + 6 + 2


def test_rendered_ramp_and_freeze_are_exact(tmp_path):
    clip = marker_clip(4, 120, tmp_path / "m.mp4")
    out = tmp_path / "r.mp4"
    shot.prep({"path": str(clip), "in": 0, "frames": 60, "speed_curve": RAMP, "freeze": [(45, 50)]}, out)
    assert ff.count_frames(out) == 60
    xs = [bar_x(f) for f in ff.decode(out, W, H)]
    want = [shot.src_at(o, shot.pieces(60, RAMP, [(45, 50)])) for o in range(60)]
    assert all(abs(x - (int(w) * 6) % 516) <= 6 or abs(x - (int(w) * 6) % 516) >= 510 for x, w in zip(xs, want)), \
        list(zip(xs, want))


def test_marker_pass_reproduces_speed_and_flash(reel):
    key, _ = reel
    rows = roundtrip.marker_pass(key, ["transitions", "speed", "effects"])
    bad = [r.model_dump() for r in rows if not r.ok and r.track in ("speed", "effects")]
    assert not bad, bad
    assert any(r.track == "speed" for r in rows) and any(r.track == "effects" for r in rows)
