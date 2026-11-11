"""M2 vertical slice on a synthetic reel: ingest -> cuts -> cut-only template -> same-shot pass."""
import pytest

from app import evidence, ir
from app.clients import ff
from app.evidence import cuts
from app.stages import analyze, roundtrip
from synth import SynthSpec, make_reel

CUTS = [27, 61, 90, 133, 170, 205]


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    d = tmp_path_factory.mktemp("reel")
    truth = make_reel(SynthSpec(n_frames=240, cuts=CUTS, textured=True), d / "reel.mp4")
    return d / "reel.mp4", truth


def test_cut_merge_rules():
    out = cuts.merge({"adaptive": [30, 60, 63], "content": [31, 3, 238]}, 240)
    assert [f for f, _ in out] == [31, 60]  # 30/31 merged; 63 within 6 of 60; 3 and 238 make shots too short
    assert out[0][1] == ["adaptive", "content"] and out[1][1] == ["adaptive"]


def test_cut_only_template_matches_truth_and_same_shot_pass(reel):
    path, truth = reel
    key, t, delta = analyze.run(path, provider=False)
    assert t.cuts() == truth.cuts
    assert [(s.start, s.end) for s in t.slots] == truth.segments
    assert t.n_frames == 240 and t.audio
    assert delta.coverage == 1.0
    assert delta.passed, [r.model_dump() for r in delta.rows]
    metrics = {r.metric for r in delta.rows}
    assert {"frame count", "per-frame SSIM min", "lag (samples @8 kHz)"} <= metrics
    assert ir.load(key, "delta", ir.Delta).passed
    # evidence is cached by fingerprint + track version
    assert [i.id for i in evidence.run_all(key).track("cuts")] == [i.id for i in ir.load(key, "evidence", ir.Evidence).track("cuts")]


def test_same_shot_pass_catches_a_short_slot(reel):
    path, _ = reel
    key, t, _ = analyze.run(path, provider=False)
    bad = t.model_copy(deep=True)
    bad.slots[2].end -= 1  # one frame short: slots no longer tile the reel
    ir.save(key, "template", bad)
    try:
        with pytest.raises(ValueError):
            roundtrip.same_shot_pass(key)
    finally:
        ir.save(key, "template", t)


def test_proxy_is_constant_30fps(reel):
    path, _ = reel
    src = analyze.ingest(path)
    assert ff.fps(analyze.proxy_path(src.key)) == 30 and src.n_frames == 240
