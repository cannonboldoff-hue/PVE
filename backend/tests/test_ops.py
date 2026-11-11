"""M12: rate-limit backoff, per-project usage and stage time, gold-set regression guard."""
import json

import pytest

from app import config, db, state
from app.clients import openrouter
from app.stages import meaning


def test_rate_limited_calls_back_off_then_succeed(monkeypatch):
    monkeypatch.setattr(meaning, "BACKOFF", 0)
    calls = []

    class S(meaning.Session):
        def _ask(self, *a):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("429 Too Many Requests")
            return {"ok": True}

    assert S("k", "x.mp4", "gemini").ask("p", {}) == {"ok": True} and len(calls) == 3

    class Broken(meaning.Session):
        def _ask(self, *a):
            raise RuntimeError("400 bad schema")

    with pytest.raises(RuntimeError, match="400"):
        Broken("k", "x.mp4", "gemini").ask("p", {})  # not a rate limit: no retry


def test_usage_is_logged_against_the_running_project():
    token = state.CURRENT.set("p-ops")
    try:
        openrouter._log_usage("Brief", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": 0.001})
    finally:
        state.CURRENT.reset(token)
    ev = db.q("SELECT * FROM project_events WHERE project_id='p-ops' AND type='llm_usage'")
    assert ev and ev[-1]["data"]["total_tokens"] == 15 and ev[-1]["data"]["call"] == "Brief"


def test_gold_scores_do_not_regress():
    """Fails when a track's F1 on the gold set drops more than MARGIN below its recorded target."""
    MARGIN = 0.05
    targets = config.ROOT / "gold" / "targets.json"
    hist = config.ROOT / "gold" / "history.jsonl"
    if not targets.exists() or not hist.exists():
        pytest.skip("no gold baseline yet: add reels to gold/, run tools.score, then write gold/targets.json")
    want = json.loads(targets.read_text(encoding="utf-8"))
    last = json.loads(hist.read_text(encoding="utf-8").strip().splitlines()[-1])
    for reel, tracks in last["reels"].items():
        for track, m in tracks.items():
            if track in want:
                assert m["f1"] >= want[track] - MARGIN, (reel, track, m["f1"], want[track])
