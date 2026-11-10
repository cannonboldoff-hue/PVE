"""Project Memory: preferences (with confidence counts) and match feedback. Structure and choices only;
no user media and no reference video are stored here."""
import json

from .. import db

PREF_KEYS = ("target_length", "tone", "caption_language", "captions", "music")


def prefs() -> dict:
    return {r["key"]: json.loads(r["value"]) for r in db.q("SELECT key,value FROM preferences")}


def learn_brief(brief: dict) -> None:
    """Called when a brief is confirmed. Same value again raises confidence; a new value replaces it."""
    for k in PREF_KEYS:
        if k not in brief:
            continue
        v = json.dumps(brief[k])
        row = db.one("SELECT value,count FROM preferences WHERE key=?", (k,))
        count = row["count"] + 1 if row and row["value"] == v else 1
        db.run("INSERT OR REPLACE INTO preferences(key,value,count) VALUES(?,?,?)", (k, v, count))


def descriptor(shot: dict) -> str:
    return f"{shot['subject']} | {shot['action']}".lower().strip()


def feedback(shot: dict, asset_id: str, accepted: bool) -> None:
    db.run("INSERT INTO match_feedback(descriptor,asset_id,accepted,created) VALUES(?,?,?,?)",
           (descriptor(shot), asset_id, int(accepted), db.now()))


def boost(shot: dict, asset_id: str) -> float:
    """Ranking nudge from past accepted (+) and rejected (-) matches of the same shot descriptor and clip."""
    rows = db.q("SELECT accepted FROM match_feedback WHERE descriptor=? AND asset_id=?", (descriptor(shot), asset_id))
    return max(-0.5, min(0.5, sum(0.2 if r["accepted"] else -0.3 for r in rows)))
