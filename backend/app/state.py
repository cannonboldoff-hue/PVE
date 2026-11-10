import json

from . import db

STATES = [
    "NEW", "ANALYZING", "BRIEF", "SHOT_SPECS", "PREPRODUCTION", "AWAITING_UPLOADS", "AWAITING_APPROVAL",
    "PLANNED", "PRODUCING", "VERIFYING", "REPAIRING", "FINAL", "FAILED",
]
# states from which approved production is already underway or done
POST_APPROVAL = {"PLANNED", "PRODUCING", "VERIFYING", "REPAIRING", "FINAL"}
# states whose work runs in a background task and is resumed on restart
RUNNING = {"ANALYZING", "PREPRODUCTION", "PLANNED", "PRODUCING", "VERIFYING", "REPAIRING"}

ALLOWED = {
    "NEW": {"ANALYZING"},
    "ANALYZING": {"BRIEF", "FAILED"},
    "BRIEF": {"SHOT_SPECS", "ANALYZING", "FAILED"},
    "SHOT_SPECS": {"PREPRODUCTION", "BRIEF", "FAILED"},
    "PREPRODUCTION": {"AWAITING_UPLOADS", "AWAITING_APPROVAL", "FAILED"},
    "AWAITING_UPLOADS": {"AWAITING_APPROVAL", "PREPRODUCTION", "BRIEF", "SHOT_SPECS", "FAILED"},
    "AWAITING_APPROVAL": {"PLANNED", "AWAITING_UPLOADS", "PREPRODUCTION", "BRIEF", "SHOT_SPECS"},
    "PLANNED": {"PRODUCING", "AWAITING_APPROVAL", "FAILED"},
    "PRODUCING": {"VERIFYING", "AWAITING_APPROVAL", "FAILED"},
    "VERIFYING": {"REPAIRING", "FINAL", "AWAITING_APPROVAL", "FAILED"},
    "REPAIRING": {"VERIFYING", "AWAITING_APPROVAL", "FAILED"},
    "FINAL": {"PRODUCING", "AWAITING_APPROVAL"},
    "FAILED": set(STATES),
}


class StateError(Exception):
    pass


def get(project_id: str) -> dict:
    p = db.one("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        raise StateError("unknown project")
    return p


def transition(project_id: str, new: str, error: dict | None = None) -> dict:
    p = get(project_id)
    old = p["state"]
    if new not in ALLOWED.get(old, set()):
        raise StateError(f"cannot go {old} -> {new}")
    # hard gate: nothing past approval without the user's Approve click
    if new in {"PLANNED", "PRODUCING"} and old != "FINAL" and not p["approved"]:
        raise StateError("production needs user approval")
    db.update("projects", project_id, state=new, error=error, updated=db.now())
    return get(project_id)


def fail(project_id: str, stage: str, message: str) -> None:
    transition(project_id, "FAILED", {"stage": stage, "message": message})


def event(project_id: str, type_: str, data: dict | None = None) -> None:
    db.run(
        "INSERT INTO project_events(project_id,type,data,created) VALUES(?,?,?,?)",
        (project_id, type_, json.dumps(data or {}), db.now()),
    )
