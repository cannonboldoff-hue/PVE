"""M10: LLM decisions applied by code (timing untouchable), requirements, screening and all-slots assignment."""
import pytest

from app import config, ir
from app.clients import openrouter
from app.models import Match
from app.stages import extract, fusion, preproduction, requirements

SRC = ir.Source(key="dkey", fingerprint="fp-m10", n_frames=120, width=540, height=960, src_fps=30)
EV = ir.Evidence(items=[ir.Item(id="cuts_0", track="cuts", start=60, end=60, data={"frame": 60}, tool="t"),
                        ir.Item(id="effects_0", track="effects", start=10, end=12, data={"type": "flash"}, tool="t")])
RAMP = [(0.0, 1.0), (1 / 3, 3.0), (2 / 3, 0.5)]


def test_decisions_change_bindings_not_timing(monkeypatch):
    obs = fusion.fuse(SRC, EV)

    async def fake(messages, cls):
        assert cls is extract.Decisions and "slots" in messages[-1]["content"]
        return extract.Decisions(
            fields=[extract.FieldDecision(path="slots.0.subject", binding="swap", reason="content"),
                    extract.FieldDecision(path="slots.1.camera", binding="keep", reason="style"),
                    extract.FieldDecision(path="effects.0", binding="drop", reason="one-off joke"),
                    extract.FieldDecision(path="slots.0.start", binding="drop", reason="ignored: not a field")],
            slots=[extract.SlotIntent(slot="s01", role="hook", function="grab attention"),
                   extract.SlotIntent(slot="s02", role="punchline", function="the reveal")])

    monkeypatch.setattr(openrouter, "chat_json", fake)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test")
    t = extract.decide(obs)
    assert [(s.start, s.end) for s in t.slots] == [(0, 60), (60, 120)] and t.n_frames == 120
    assert (t.slots[0].role.value, t.slots[0].role.source, t.slots[0].function.value) == ("hook", "llm", "grab attention")
    assert t.slots[1].role.value == "other" and t.slots[1].role.raw == "punchline"  # out of vocabulary kept as raw
    assert t.slots[0].subject.binding == "swap" and t.slots[1].camera.binding == "keep"
    assert t.effects == [] and t.dropped == {"effects_0": "one-off joke"}


def test_requirements_for_a_ramped_slot():
    t = extract.build(fusion.fuse(SRC, EV))
    t.slots[1].speed = RAMP
    t.transitions[0].start, t.transitions[0].end = 55, 65  # a 10-frame window: lead of slot 2, tail of slot 1
    r = requirements.derive(t)
    assert r[1].footage_frames == 20 + 60 + 10 + 10  # area under the curve + 10 lead frames at 1x
    assert r[0].footage_frames == 60 + 10
    assert r[1].hard["min_seconds"] == round(100 / 30, 2) and r[1].camera_from_clip == "static"


def test_screen_and_assignment():
    req = ir.Requirement(media="video", footage_frames=90, camera_from_clip="static")
    assert preproduction.screen({"duration": 4.0, "filename": "a.mp4"}, req) == "ok"
    assert preproduction.screen({"duration": 2.0, "filename": "a.mp4"}, req) == "adaptable"  # 2 s of 3 s: slow down
    assert preproduction.screen({"duration": 1.0, "filename": "a.mp4"}, req) is None
    assert preproduction.screen({"duration": 5.0, "filename": "p.jpg"}, req) == "adaptable"  # photo + template motion
    moving = req.model_copy(update={"camera_from_clip": "other"})
    assert preproduction.screen({"duration": 5.0, "filename": "p.jpg"}, moving) is None

    def m(shot, asset):
        return Match(shot_id=shot, asset_id=asset, label="exact")

    # both slots prefer clip A; slot 1 also accepts B: they get different clips
    got = preproduction.assign({1: [(3.5, m(1, "A")), (2.9, m(1, "B"))], 2: [(3.4, m(2, "A"))]})
    assert (got[1].asset_id, got[2].asset_id) == ("B", "A")
    # nothing else fits slot 2: it reuses A rather than going missing
    got = preproduction.assign({1: [(3.5, m(1, "A"))], 2: [(3.4, m(2, "A"))], 3: []})
    assert got[1].asset_id == got[2].asset_id == "A" and got[3] is None


@pytest.mark.parametrize("frames", [60])
def test_footage_includes_overlaps(frames):
    s = ir.Slot(id="s", start=0, end=frames, speed=RAMP)
    assert requirements.footage_frames(s, lead=6, tail=4) == requirements.footage_frames(s) + 6 + 2
