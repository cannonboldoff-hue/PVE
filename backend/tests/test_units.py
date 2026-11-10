import pytest
from pydantic import ValidationError

from app import agent, db, state
from app.models import Brief, PatchOp, Plan, PlanShot, ShotSpec
from app.stages import brief as brief_mod
from app.stages import plan as plan_mod
from app.stages import reference


def test_schemas_reject_bad_input():
    with pytest.raises(ValidationError):
        Brief(topic="x", target_length=0)
    with pytest.raises(ValidationError):
        ShotSpec(shot_id=1, start=0, end=2, purpose="p", subject="s", action="a", transition_out="spin")
    assert Brief(topic="x", target_length=15).music == "none"


@pytest.mark.parametrize("url,key", [
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share", "youtube:dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "youtube:dQw4w9WgXcQ"),
    ("https://www.instagram.com/reel/C1abc_DEF-9/?igsh=zzz", "instagram:C1abc_DEF-9"),
    ("https://www.tiktok.com/@u/video/7123456789", "tiktok:7123456789"),
])
def test_url_normaliser(url, key):
    assert reference.cache_key(url) == key


def test_snap_to_scene_cuts():
    shots = [{"start": 0, "end": 2.1}, {"start": 2.1, "end": 5.0}, {"start": 5.0, "end": 8}]
    out = reference.snap(shots, [2.4, 5.1], 8.0)
    assert [(s["start"], s["end"]) for s in out] == [(0, 2.4), (2.4, 5.1), (5.1, 8.0)]


def test_retime_contiguous():
    shots = [ShotSpec(shot_id=9, start=5, end=7, purpose="", subject="", action=""),
             ShotSpec(shot_id=3, start=0, end=1.5, purpose="", subject="", action="")]
    out = brief_mod.retime(shots)
    assert [(s.shot_id, s.start, s.end) for s in out] == [(1, 0, 2), (2, 2, 3.5)]


def _plan():
    return Plan(shots=[PlanShot(shot_id=i, asset_id="a", path="x.mp4", src_in=0, src_out=3, caption="c") for i in (1, 2)])


TPL_ANALYSIS = {"shots": [
    {"start": 0, "end": 2, "description": "d1", "subject": "s1", "action": "a1", "transition_out": "Fade",
     "background": "inset over blurred backdrop", "frame_motion": "zoom in", "caption_animation": "pop"},
    {"start": 2, "end": 5, "description": "d2", "subject": "s2", "action": "a2", "transition_out": "spin"}]}


def test_extract_template_deterministic_structure():
    a, b = brief_mod.extract_template(TPL_ANALYSIS), brief_mod.extract_template(TPL_ANALYSIS)
    assert a == b
    assert (a[0].transition_out, a[0].fit, a[0].animation, a[0].caption_animation) == ("fade", "blur_fit", "zoom_in", "pop")
    assert (a[1].transition_out, a[1].fit, a[1].animation) == ("cut", "cover", "none")  # unknown transition -> cut
    assert [s.duration for s in a] == [2, 3]


@pytest.mark.asyncio
async def test_fill_shots_keeps_structure(monkeypatch):
    from app.clients import openrouter
    from app.models import ShotContent, ShotContentList

    async def fake(messages, cls):
        return ShotContentList(shots=[ShotContent(purpose="P", subject="bread", action="slice", text="Hi")] * 2)

    monkeypatch.setattr(openrouter, "chat_json", fake)
    tpl = brief_mod.extract_template(TPL_ANALYSIS)
    out = await brief_mod.fill_shots(tpl, {"topic": "bakery"})
    assert [s.subject for s in out] == ["bread", "bread"]
    for t, o in zip(tpl, out):
        assert o.model_dump(exclude={"purpose", "subject", "action", "direction", "asset_type", "text"}) == \
               t.model_dump(exclude={"purpose", "subject", "action", "direction", "asset_type", "text"})


def test_patch_applier():
    plan = _plan()
    notes = plan_mod.apply_patches(plan, [
        PatchOp(shot_id=1, field="speed", value=2), PatchOp(shot_id=1, field="caption", value="new"),
        PatchOp(shot_id=2, field="in", value=5),  # past out: rejected
        PatchOp(shot_id=2, field="transition", value="spin"),  # not allowed: rejected
        PatchOp(shot_id=7, field="drop"),  # unknown shot: rejected
        PatchOp(shot_id=2, field="drop"),
    ], lambda _id: None)
    assert plan.shots[0].speed == 2 and plan.shots[0].duration == 1.5 and plan.shots[0].caption == "new"
    assert [s.shot_id for s in plan.shots] == [1]
    assert len(notes) == 3


def test_cannot_produce_without_approval():
    pid = db.new_id()
    db.run("INSERT INTO projects(id,conv_id,state,approved,created,updated) VALUES(?,?,?,?,?,?)", (pid, "c", "AWAITING_APPROVAL", 0, 0, 0))
    with pytest.raises(state.StateError):
        state.transition(pid, "PLANNED")
    db.update("projects", pid, state="PLANNED")
    with pytest.raises(state.StateError):
        state.transition(pid, "PRODUCING")  # approved flag still 0
    db.update("projects", pid, approved=1)
    assert state.transition(pid, "PRODUCING")["state"] == "PRODUCING"


def test_agent_has_no_approve_tool():
    names = {t["function"]["name"] for t in agent.TOOLS}
    assert not any("approv" in n for n in names | set(agent.HANDLERS))

