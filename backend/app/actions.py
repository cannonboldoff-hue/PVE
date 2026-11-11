"""Every project mutation lives here. HTTP card buttons and chat-agent tools both call these.
`approve` is deliberately NOT exposed as an agent tool: only the Approve button's HTTP call reaches it."""
from pydantic import ValidationError

from . import db, msgs, pipeline, state
from .models import ShotSpec
from .stages import brief as brief_mod
from .stages import memory, preproduction, reference
from .stages import plan as plan_mod

SEARCH_FIELDS = {"subject", "action", "camera", "camera_motion", "direction"}
SEARCH_FIELDS |= {"layout", "collage"}  # a different layout needs different pictures
NESTED = ("caption_style", "grade", "collage")  # partial dicts merge into the existing values
EDITABLE_SHOT = {"start", "end", "purpose", "text", "transition_out", "background", "fit", "animation", "caption_animation",
                 "overlay", "caption_start", "caption_end", *NESTED, "layout", *SEARCH_FIELDS}


class ActionError(Exception):
    pass


def _p(pid: str) -> dict:
    try:
        return state.get(pid)
    except state.StateError as e:
        raise ActionError(str(e)) from e


def submit_reference(pid: str, url: str, goal: str = "") -> str:
    p = _p(pid)
    if p["state"] not in {"NEW", "BRIEF", "ANALYZING", "FAILED"}:
        raise ActionError("This project already has a reference. Start a new chat for a different Reel.")
    db.update("projects", pid, ref_url=url, goal=goal or p["goal"] or "", error=None, brief=None, brief_confirmed=0,
              shots=None, matches=None)
    db.run("UPDATE conversations SET title=? WHERE id=?", ((goal or url)[:40], p["conv_id"]))
    if p["state"] != "ANALYZING":
        state.transition(pid, "ANALYZING")
    pipeline.spawn(pid, pipeline.run_analyze(pid), "ANALYZING")
    return "Analysing the reference now."


def use_template(pid: str, key: str, goal: str = "") -> str:
    """Start from a saved template: skips reference analysis and goes straight to the brief."""
    p = _p(pid)
    if p["state"] not in {"NEW", "BRIEF", "FAILED"}:
        raise ActionError("This project already has a reference. Start a new chat for a different Reel.")
    analysis = reference.lookup(key)
    if not analysis or not db.one("SELECT 1 FROM templates WHERE key=?", (key,)):
        raise ActionError("Unknown template.")
    db.update("projects", pid, ref_url=None, goal=goal or p["goal"] or "", error=None, brief=None, brief_confirmed=0,
              shots=None, matches=None)
    if p["state"] != "ANALYZING":
        state.transition(pid, "ANALYZING")
    pipeline.spawn(pid, pipeline.run_brief(pid, key, analysis), "ANALYZING")
    return "Using the saved template."


def edit_brief(pid: str, changes: dict) -> str:
    p = _p(pid)
    if not p["brief"]:
        raise ActionError("There is no brief yet.")
    try:
        b = brief_mod.merge_brief(p["brief"], changes)
    except ValidationError as e:
        raise ActionError(f"Invalid brief change: {e.errors()[0]['msg']}") from e
    db.update("projects", pid, brief=b.model_dump())
    state.event(pid, "brief_edit", changes)
    pipeline.revert_if_approved(pid)
    msgs.changed(p["conv_id"])
    return "Brief updated." + ("" if p["state"] == "BRIEF" else " The shot list is unchanged until the brief is confirmed again.")


def confirm_brief(pid: str) -> str:
    p = _p(pid)
    if not p["brief"]:
        raise ActionError("There is no brief yet.")
    pipeline.revert_if_approved(pid)
    memory.learn_brief(p["brief"])
    state.event(pid, "brief_confirmed", p["brief"])
    db.update("projects", pid, brief_confirmed=1, shots=[], matches=[], approved=0)
    try:
        state.transition(pid, "SHOT_SPECS")
    except state.StateError as e:
        raise ActionError(str(e)) from e
    pipeline.spawn(pid, pipeline.run_shots(pid), "SHOT_SPECS")
    msgs.changed(p["conv_id"])
    return "Brief confirmed. Writing the shot list."


def confirm_shots(pid: str) -> str:
    p = _p(pid)
    if p["state"] != "SHOT_SPECS" or not p["shots"]:
        raise ActionError("The shot list isn't ready to confirm.")
    state.transition(pid, "PREPRODUCTION")
    pipeline.spawn(pid, pipeline.run_preproduction(pid), "PREPRODUCTION")
    msgs.text(p["conv_id"], "Searching your clips for each shot…")
    msgs.changed(p["conv_id"])
    return "Looking through the clip library."


def edit_shot(pid: str, shot_id: int, changes: dict) -> str:
    p = _p(pid)
    bad = set(changes) - EDITABLE_SHOT
    if bad:
        raise ActionError(f"Cannot edit {sorted(bad)}")
    shots = p["shots"] or []
    old = next((s for s in shots if s["shot_id"] == shot_id), None)
    if not old:
        raise ActionError(f"No shot {shot_id}")
    changes = {**changes, **{k: {**old.get(k, {}), **changes[k]} for k in NESTED if isinstance(changes.get(k), dict)}}
    try:
        new = ShotSpec(**{**old, **changes}).model_dump()
    except ValidationError as e:
        raise ActionError(f"Invalid shot change: {e.errors()[0]['msg']}") from e
    db.update("projects", pid, shots=[new if s["shot_id"] == shot_id else s for s in shots])
    state.event(pid, "shot_edit", {"shot_id": shot_id, **changes})
    if p["state"] != "SHOT_SPECS":
        pipeline.revert_if_approved(pid)
        if SEARCH_FIELDS & set(changes):  # the shot's content changed: its old match no longer applies
            ms = [m for m in p["matches"] if m["shot_id"] != shot_id]
            db.update("projects", pid, matches=ms)
            pipeline.spawn(pid, pipeline.run_rematch(pid, {shot_id}), "PREPRODUCTION")
    msgs.changed(p["conv_id"])
    return f"Shot {shot_id} updated."


def skip_shot(pid: str, shot_id: int, skip: bool = True) -> str:
    p = _p(pid)
    shots = p["shots"] or []
    if not any(s["shot_id"] == shot_id for s in shots):
        raise ActionError(f"No shot {shot_id}")
    db.update("projects", pid, shots=[{**s, "skipped": skip} if s["shot_id"] == shot_id else s for s in shots])
    state.event(pid, "shot_skip", {"shot_id": shot_id, "skipped": skip})
    if p["state"] != "SHOT_SPECS":
        pipeline.revert_if_approved(pid)
        pipeline.settle(pid)
    msgs.changed(p["conv_id"])
    return f"Shot {shot_id} {'skipped' if skip else 'restored'}."


def skip_missing(pid: str) -> str:
    p = _p(pid)
    for sid in preproduction.pending_missing(p):
        skip_shot(pid, sid)
    return "Skipped the shots without a clip."


def swap_clip(pid: str, shot_id: int, asset_id: str) -> str:
    p = _p(pid)
    shot = next((s for s in p["shots"] or [] if s["shot_id"] == shot_id), None)
    a = db.one("SELECT * FROM assets WHERE id=? AND kind='clip'", (asset_id,))
    if not shot or not a or a["status"] not in {"ready", "too_short"}:
        raise ActionError("Unknown shot or clip, or the clip isn't usable.")
    for m in p["matches"] or []:
        if m["shot_id"] == shot_id and m["asset_id"] and m["asset_id"] != asset_id:
            memory.feedback(shot, m["asset_id"], False)
    memory.feedback(shot, asset_id, True)
    end = round(min(a["duration"] or 0, shot["end"] - shot["start"]), 2) or 1.0
    prev = next((m for m in p["matches"] or [] if m["shot_id"] == shot_id), {})
    # swapping the main tile of a collage keeps its other tiles (minus the new main, if it was one of them)
    extras = [x for x in prev.get("extra_assets", []) if x != asset_id]
    new = {"shot_id": shot_id, "asset_id": asset_id, "start": 0, "end": end, "label": "exact", "extra_assets": extras,
           "reason": "Chosen by you", "instruction": ""}
    ms = [m for m in p["matches"] or [] if m["shot_id"] != shot_id] + [new]
    db.update("projects", pid, matches=sorted(ms, key=lambda m: m["shot_id"]))
    state.event(pid, "clip_swap", {"shot_id": shot_id, "asset_id": asset_id})
    pipeline.revert_if_approved(pid)
    pipeline.settle(pid)
    return f"Shot {shot_id} now uses {a['filename']}."


def approve(pid: str) -> str:
    """Hard gate. Only reachable from the Approval card's button (HTTP), never from the chat agent."""
    p = _p(pid)
    if p["state"] != "AWAITING_APPROVAL":
        raise ActionError("There is nothing waiting for approval.")
    assets = {a["id"]: a for a in db.q("SELECT * FROM assets")}
    plan = plan_mod.build(p["shots"], p["matches"], assets, None, True)
    if not plan.shots:
        raise ActionError("No shot has a clip yet.")
    shots = {s["shot_id"]: s for s in p["shots"]}
    for m in p["matches"]:
        if m["asset_id"] and m["shot_id"] in shots:
            memory.feedback(shots[m["shot_id"]], m["asset_id"], True)
    db.update("projects", pid, approved=1)
    state.event(pid, "approved", {"shots": len(plan.shots)})
    state.transition(pid, "PLANNED")
    pipeline.spawn(pid, pipeline.run_production(pid), "PRODUCING")
    msgs.text(p["conv_id"], "Approved. Building your Reel now.")
    msgs.changed(p["conv_id"])
    return "Approved."


def request_revision(pid: str, instruction: str) -> str:
    p = _p(pid)
    if p["state"] != "FINAL":
        raise ActionError("Revisions are possible once the Reel is finished.")
    pipeline.spawn(pid, pipeline.run_revision(pid, instruction), "PRODUCING")
    return "Working on that change."


def retry_stage(pid: str) -> str:
    p = _p(pid)
    if p["state"] != "FAILED":
        raise ActionError("Nothing has failed.")
    stage = p["error"]["stage"]
    state.transition(pid, stage)
    pipeline.spawn(pid, pipeline.STAGE_RUN[stage](pid), stage)
    msgs.changed(p["conv_id"])
    return f"Retrying {stage.lower().replace('_', ' ')}."


def upload_status(pid: str) -> list[dict]:
    _p(pid)
    return [{"id": a["id"], "filename": a["filename"], "kind": a["kind"], "status": a["status"],
             "duration": a["duration"], "error": a["error"]} for a in db.q("SELECT * FROM assets ORDER BY created")]


def _field(t, path: str):
    obj = t
    for part in path.split("."):
        obj = obj[int(part)] if part.isdigit() else getattr(obj, part)
    return obj


def confirm_template_field(pid: str, path: str, value=None) -> str:
    """The user confirms (value None) or corrects a low-confidence template field: it becomes source "user",
    confidence 1 and leaves the confirm list. Only labelled values (F fields) can be set, never timing."""
    from . import ir

    p = _p(pid)
    t = brief_mod.load_ir(p["reference_id"])
    if t is None:
        raise ActionError("This project has no measured template.")
    try:
        f = _field(t, path)
        parent, last = _field(t, path.rsplit(".", 1)[0]), path.rsplit(".", 1)[1]
    except (AttributeError, IndexError, ValueError) as e:
        raise ActionError(f"Unknown template field {path}") from e
    if not isinstance(f, ir.F):
        raise ActionError(f"{path} is not a labelled field")
    try:
        new = f.__class__(**{**f.model_dump(), "value": f.value if value is None else value, "source": "user",
                             "conf": 1.0})
    except ValidationError as e:
        raise ActionError(f"Not a valid value for {path}: {e.errors()[0]['msg']}") from e
    setattr(parent, last, new)
    t.low_conf = [x for x in t.low_conf if x != path]
    db.run("UPDATE templates SET template=? WHERE key=?", (t.model_dump_json(), p["reference_id"]))
    ir.save(t.key, "template", t)
    return f"Saved {path} = {new.value}."
