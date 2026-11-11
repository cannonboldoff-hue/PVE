"""M11: validation as a loop. A broken template is repaired by typed patches, or reported."""
from app import ir
from app.stages import analyze, roundtrip
from synth import SynthSpec, make_reel


def test_broken_template_is_repaired(tmp_path):
    make_reel(SynthSpec(n_frames=120, cuts=[40, 80], textured=True), tmp_path / "r.mp4")
    key, t, delta = analyze.run(tmp_path / "r.mp4", provider=False)
    assert delta.passed
    bad = t.model_copy(deep=True)
    bad.slots[1].end -= 1  # one slot one frame short: the slots no longer tile the reel
    ir.save(key, "template", bad)
    fixed, d = roundtrip.validate(key, ir.load(key, "evidence", ir.Evidence), tracks=[], critic=False)
    assert d.passed and [(s.start, s.end) for s in fixed.slots] == [(0, 40), (40, 80), (80, 120)]
    assert ir.load(key, "template", ir.Template).slots[1].end == 80


def test_unrepairable_is_reported(tmp_path):
    make_reel(SynthSpec(n_frames=90, cuts=[45], textured=True), tmp_path / "r.mp4")
    key, t, _ = analyze.run(tmp_path / "r.mp4", provider=False)
    ev = ir.load(key, "evidence", ir.Evidence)
    ev.items.append(ir.Item(id="ghost_0", track="ghost", start=0, end=1, tool="t"))  # nothing in the template uses it
    _, d = roundtrip.validate(key, ev, tracks=[], critic=False)
    assert not d.passed and d.coverage < 1.0  # reported, not hidden
