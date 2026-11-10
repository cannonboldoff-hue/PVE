"""End-to-end through HTTP with OpenRouter / TwelveLabs / yt-dlp stubbed. Real ffmpeg renders, real cut detection
on a synthetic reference reel, frame-exact rendering pinned to the reference audio."""
import json
import shutil
import time

import pytest
from fastapi.testclient import TestClient

from app import db, ir
from app.clients import ff as ffc
from app.clients import openrouter, twelvelabs
from app.models import Brief, JudgeResult, Issue, MissingInstruction, MissingList, PatchList, PatchOp, ShotContent, ShotContentList
from app.stages import brief as brief_mod
from app.stages import music, reference
from helpers import ff
from synth import SynthSpec, make_reel

REEL_CUTS = [60, 120]  # 3 shots of 2 s at 30 fps


def shot(i, subject):
    return ShotContent(purpose=f"p{i}", subject=subject, action="act", text=f"Caption {i}")


class Script:
    judge_calls = 0

    async def chat_json(self, messages, cls):
        if cls is Brief:
            return Brief(topic="bakery", target_length=6)
        if cls is ShotContentList:
            return ShotContentList(shots=[shot(1, "bread"), shot(2, "unicorn"), shot(3, "cake")])
        if cls is MissingList:
            return MissingList(items=[MissingInstruction(shot_id=2, instruction="Film 5 seconds of a unicorn, vertical")])
        if cls is PatchList:
            return PatchList(ops=[PatchOp(shot_id=1, field="speed", value=1.0), PatchOp(shot_id=1, field="caption", value="Faster intro")])
        if cls is JudgeResult:
            Script.judge_calls += 1
            if Script.judge_calls == 1:  # first draft: deliberately flagged, with a fix
                return JudgeResult(verdict="REPAIR", summary="Caption 1 is too long.",
                                   issues=[Issue(shot_id=1, problem="caption", fixes=[PatchOp(shot_id=1, field="caption", value="Short")])])
            return JudgeResult(verdict="PASS", summary="ok")
        raise AssertionError(cls)

    async def chat_stream(self, messages, tools=None):
        if not any(m["role"] == "tool" for m in messages):
            yield {"tool_calls": [{"id": "1", "name": "submit_reference", "arguments": json.dumps(
                {"url": "https://youtube.com/shorts/abcdefghijk", "goal": "bakery"})}]}
        else:
            yield {"token": "On it."}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    s = Script()
    mp.setattr(openrouter, "chat_json", s.chat_json)
    mp.setattr(openrouter, "chat_stream", s.chat_stream)

    reel = tmp_path_factory.mktemp("ref") / "reel.mp4"
    make_reel(SynthSpec(n_frames=180, cuts=REEL_CUTS, textured=True), reel)

    def fake_download(url, dest):
        dest.mkdir(parents=True, exist_ok=True)
        return shutil.copy(reel, dest / "ref.mp4")

    mp.setattr(reference, "download", fake_download)
    mp.setattr(twelvelabs, "index_clip", lambda path: (f"ta-{path[-12:]}", f"ti-{path[-12:]}"))
    mp.setattr(twelvelabs, "search", lambda q, limit=10: [
        {"indexed_id": a["tl_indexed_id"], "start": 0.0, "end": 5.0, "rank": i}
        for i, a in enumerate(db.q("SELECT * FROM assets WHERE status='ready'"))])
    mp.setattr(twelvelabs, "upload_asset", lambda p: "tmp")
    mp.setattr(twelvelabs, "delete_asset", lambda a: None)

    def fake_tl_analyze(asset_id, prompt, schema, start=None, end=None):
        if "role" in schema["properties"]:  # typed per-slot meaning, one call per measured slot window
            assert start is not None and end is not None
            ans = lambda v: {"value": v, "note": f"note {v}", "confidence": 0.9}  # noqa: E731
            return {"media": ans("video"), "role": ans("hook" if start == 0 else "detail"),
                    "function": ans(f"shot at {start:.1f}"), "subject": ans("s"), "action": ans("a"),
                    "shot_size": ans("close"), "angle": ans("eye level"), "layout": ans("single"),
                    "camera": ans("static"), "style": {"color_look": "warm"}}
        if "hook" in schema["properties"]:
            return {"hook": "h", "arc": "a", "payoff": "p", "cta": "c", "overall_style": "fast cuts"}
        if "match" in schema["properties"]:
            return {"match": "none" if "unicorn" in prompt else "exact", "reason": "stub"}
        return {"subject_in_frame": True, "captions_readable": True, "pacing_close_to_reference": True, "notes": ""}

    mp.setattr(twelvelabs, "analyze", fake_tl_analyze)
    from app.main import app

    with TestClient(app) as c:
        yield c
    mp.undo()


def wait(c, pid, want, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        p = c.get(f"/api/projects/{pid}").json()
        if p["state"] in want:
            return p
        assert p["state"] != "FAILED", p["error"]
        time.sleep(0.5)
    raise AssertionError(f"timeout waiting for {want}, at {p['state']}")


def upload(c, pid, tmp_path, name, shot_id=None):
    f = tmp_path / name
    ff("-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=6", "-f", "lavfi", "-i", "sine=duration=6",
       "-pix_fmt", "yuv420p", "-shortest", str(f))
    data = {"project_id": pid, "kind": "clip", **({"shot_id": str(shot_id)} if shot_id else {})}
    r = c.post("/api/assets", data=data, files={"file": (name, f.read_bytes(), "video/mp4")})
    assert r.status_code == 200, r.text


def wait_assets(c, pid, n):
    for _ in range(100):
        a = c.get(f"/api/projects/{pid}").json()["assets"]
        if sum(x["status"] == "ready" for x in a) >= n:
            return
        time.sleep(0.3)
    raise AssertionError("assets not ready")


def test_full_flow(client, tmp_path):
    c = client
    conv = c.post("/api/conversations").json()
    pid, cid = conv["project_id"], conv["id"]

    # chat -> agent tool call -> reference analysis -> brief
    assert c.post(f"/api/conversations/{cid}/messages", json={"text": "https://youtube.com/shorts/abcdefghijk make it about my bakery"}).status_code == 202
    wait(c, pid, {"BRIEF"})
    t = brief_mod.load_ir("youtube:abcdefghijk")
    assert t.cuts() == REEL_CUTS and t.n_frames == 180  # measured, not from the model
    delta = ir.Delta.model_validate(db.one("SELECT delta FROM templates WHERE key=?", ("youtube:abcdefghijk",))["delta"])
    assert delta.passed

    # clips first, then confirm brief -> shot list
    upload(c, pid, tmp_path, "a.mp4")
    upload(c, pid, tmp_path, "b.mp4")
    wait_assets(c, pid, 2)
    assert c.post(f"/api/projects/{pid}/confirm-brief").status_code == 200
    p = wait(c, pid, {"SHOT_SPECS"})
    for _ in range(60):
        p = c.get(f"/api/projects/{pid}").json()
        if p["shots"]:
            break
        time.sleep(0.3)
    assert len(p["shots"]) == 3

    # matching: shot 2 (unicorn) has no match -> awaiting uploads with a filming instruction
    assert c.post(f"/api/projects/{pid}/confirm-shots").status_code == 200
    p = wait(c, pid, {"AWAITING_UPLOADS"})
    labels = {m["shot_id"]: m["label"] for m in p["matches"]}
    assert labels == {1: "exact", 2: "missing", 3: "exact"}
    assert "unicorn" in next(m for m in p["matches"] if m["shot_id"] == 2)["instruction"]

    # approving before everything is matched must fail; production stays locked
    assert c.post(f"/api/projects/{pid}/approve").status_code == 400

    # per-shot upload fills the gap -> approval gate
    upload(c, pid, tmp_path, "unicorn.mp4", shot_id=2)
    p = wait(c, pid, {"AWAITING_APPROVAL"})
    assert p["summary"]["duration"] == 6.0 and all(r["label"] != "missing" for r in p["summary"]["rows"])

    # editing a shot's text before approval is fine and keeps the gate; now approve
    assert c.post(f"/api/projects/{pid}/approve").status_code == 200
    p = wait(c, pid, {"FINAL"})
    assert p["approved"] == 1 and p["draft_n"] == 2  # draft 1 flagged REPAIR, repaired, draft 2 PASS
    assert p["verifier"]["verdict"] == "PASS"
    assert c.get(f"/api/projects/{pid}/video").status_code == 200
    # the render has the reference's length and the reference audio, sample-aligned
    assert ffc.count_frames(p["final_path"]) == 180
    assert ffc.audio_lag(p["final_path"], music.audio_path("youtube:abcdefghijk")) == 0
    assert p["plan"]["audio_mode"] == "reference" and [s["frames"] for s in p["plan"]["shots"]] == [60, 60, 60]
    assert len(db.q("SELECT * FROM drafts WHERE project_id=?", (pid,))) == 2

    # revision re-runs only changed nodes
    assert c.post(f"/api/projects/{pid}/revise", json={"instruction": "make the intro faster"}).status_code == 200
    for _ in range(300):
        p = c.get(f"/api/projects/{pid}").json()
        if p["state"] == "FINAL" and p["draft_n"] == 3:
            break
        assert p["state"] != "FAILED", p["error"]
        time.sleep(0.5)
    assert p["draft_n"] == 3
    runs = db.q("SELECT cached FROM graph_runs WHERE project_id=? AND node LIKE 'prep_clip%'", (pid,))
    assert sum(r["cached"] for r in runs) >= 2  # shots 2 and 3 untouched

    # editing after approval reverts to the approval gate
    assert c.post(f"/api/projects/{pid}/edit-shot", json={"shot_id": 1, "changes": {"text": "New text"}}).status_code == 200
    p = c.get(f"/api/projects/{pid}").json()
    assert p["state"] == "AWAITING_APPROVAL" and p["approved"] == 0
