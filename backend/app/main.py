import asyncio
import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import actions, agent, config, db, msgs, pipeline, state
from .clients import twelvelabs, video
from .models import Brief
from .stages import brief as brief_mod
from .stages import plan as plan_mod


@asynccontextmanager
async def lifespan(app: FastAPI):
    msgs.set_loop(asyncio.get_running_loop())
    pipeline.resume_all()
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(actions.ActionError)
async def _action_error(_, e: actions.ActionError):
    return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/health")
def health():
    return {"ok": True, "ffmpeg": bool(shutil.which("ffmpeg")), "openrouter_key": bool(config.OPENROUTER_API_KEY),
            "twelvelabs_key": bool(config.TWELVELABS_API_KEY)}


# ---------- conversations ----------

@app.get("/api/conversations")
def list_conversations():
    return db.q("SELECT c.*, p.state FROM conversations c JOIN projects p ON p.id=c.project_id ORDER BY c.created DESC")


@app.post("/api/conversations")
def new_conversation():
    cid, pid = db.new_id(), db.new_id()
    db.run("INSERT INTO conversations(id,title,project_id,created) VALUES(?,?,?,?)", (cid, "New Reel", pid, db.now()))
    db.run("INSERT INTO projects(id,conv_id,state,created,updated) VALUES(?,?,?,?,?)", (pid, cid, "NEW", db.now(), db.now()))
    msgs.text(cid, "Paste a link to a Reel you like and tell me what yours is about. I'll break it into shots, "
                   "match them to your own clips and tell you what to film for the rest. "
                   "You can drag clips into the chat any time.")
    return {"id": cid, "project_id": pid}


@app.delete("/api/conversations/{cid}")
async def delete_conversation(cid: str):
    c = db.one("SELECT * FROM conversations WHERE id=?", (cid,))
    if not c:
        raise HTTPException(404)
    pid = c["project_id"]
    pipeline.cancel(pid)
    for t in ("messages WHERE conv_id", "conversations WHERE id"):
        db.run(f"DELETE FROM {t}=?", (cid,))
    for t in ("projects WHERE id", "graph_runs WHERE project_id", "drafts WHERE project_id", "project_events WHERE project_id"):
        db.run(f"DELETE FROM {t}=?", (pid,))
    shutil.rmtree(config.PROJECTS / pid, ignore_errors=True)
    return {"ok": True}


@app.get("/api/conversations/{cid}/messages")
def get_messages(cid: str):
    return db.q("SELECT * FROM messages WHERE conv_id=? ORDER BY id", (cid,))


@app.get("/api/conversations/{cid}/events")
async def events(cid: str):
    async def gen():
        async for ev in msgs.stream(cid):
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


class Say(BaseModel):
    text: str


@app.post("/api/conversations/{cid}/messages", status_code=202)
async def say(cid: str, body: Say):
    c = db.one("SELECT * FROM conversations WHERE id=?", (cid,))
    if not c:
        raise HTTPException(404)
    msgs.text(cid, body.text, role="user")

    async def go():
        try:
            await agent.reply(cid, c["project_id"])
        except Exception as e:
            msgs.text(cid, f"I couldn't answer: {e}")

    t = asyncio.create_task(go())
    pipeline.BG.add(t)
    t.add_done_callback(pipeline.BG.discard)
    return {"ok": True}


# ---------- project state + card actions ----------

def _summary(p: dict) -> dict | None:
    if not p["shots"] or p["matches"] is None:
        return None
    assets = {a["id"]: a for a in db.q("SELECT * FROM assets")}
    brief = Brief(**p["brief"])
    plan = plan_mod.build(p["shots"], p["matches"], assets, None, brief.captions, brief_mod.load_ir(p["reference_id"]))
    by = {m["shot_id"]: m for m in p["matches"]}
    rows = [{"shot_id": s["shot_id"], "purpose": s["purpose"], "skipped": s.get("skipped", False),
             "clip": assets.get((by.get(s["shot_id"]) or {}).get("asset_id"), {}).get("filename"),
             "tiles": len((by.get(s["shot_id"]) or {}).get("extra_assets", [])),
             "label": (by.get(s["shot_id"]) or {}).get("label", "missing"),
             "reason": (by.get(s["shot_id"]) or {}).get("reason", "")} for s in p["shots"]]
    return {"rows": rows, "duration": round(plan_mod.total_duration(plan), 1), "music": brief.music, "captions": brief.captions}


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = actions._p(pid)
    p["progress"] = db.q("SELECT node,status,cached FROM graph_runs WHERE project_id=? ORDER BY rowid", (pid,))
    p["assets"] = db.q("SELECT id,filename,kind,status,duration,error FROM assets ORDER BY created")
    p["summary"] = _summary(p)
    p["template_report"] = _template_report(p)
    return p


def _template_report(p: dict) -> dict | None:
    """What validation A proved, what the renderer could not reproduce, and what needs a confirm."""
    row = db.one("SELECT template, delta FROM templates WHERE key=?", (p["reference_id"],)) if p["reference_id"] else None
    if not row or not row.get("template"):
        return None
    t = row["template"]

    def get(path):
        obj = t
        for part in path.split("."):
            obj = obj[int(part)] if part.isdigit() else obj[part]
        return obj

    from .render import overlay

    losses = [x["loss"] for x in t["transitions"] + t["effects"] + t.get("layers", []) if x.get("loss")]
    for e in t.get("texts", []):  # what the text renderer (libass or the overlay engine) cannot draw
        try:
            losses += [f"text {e['id']}: {x}" for x in overlay.text_losses(e)]
        except (KeyError, TypeError):
            continue
    confirm = []
    for path in t.get("low_conf", []):
        try:
            f = get(path)
            confirm.append({"path": path, "value": f["value"], "note": f.get("raw"), "conf": f.get("conf")})
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    shot_list = [x for s in t.get("slots", []) for x in ((s.get("requirement") or {}).get("instructions") or [])]
    return {"delta": row.get("delta"), "losses": sorted(set(losses)), "confirm": confirm,
            "omissions": t.get("narrative", {}).get("omissions", []), "shot_list": shot_list}


class Changes(BaseModel):
    changes: dict


class ShotChanges(BaseModel):
    shot_id: int
    changes: dict


class ShotRef(BaseModel):
    shot_id: int
    skip: bool = True


class Swap(BaseModel):
    shot_id: int
    asset_id: str


class Revision(BaseModel):
    instruction: str


def _ok(msg) -> dict:
    return {"ok": True, "message": msg}


@app.get("/api/templates")
async def templates():
    return [{"key": t["key"], "title": t["title"], "shots": len(t["shots"]),
             "seconds": round(sum(s["end"] - s["start"] for s in t["shots"]), 1)}
            for t in db.q("SELECT key,title,shots FROM templates ORDER BY created DESC")]


class TemplateKey(BaseModel):
    key: str


@app.post("/api/projects/{pid}/use-template")
async def use_template(pid: str, b: TemplateKey): return _ok(actions.use_template(pid, b.key))


@app.post("/api/projects/{pid}/edit-brief")
async def edit_brief(pid: str, b: Changes): return _ok(actions.edit_brief(pid, b.changes))


@app.post("/api/projects/{pid}/confirm-brief")
async def confirm_brief(pid: str): return _ok(actions.confirm_brief(pid))


@app.post("/api/projects/{pid}/confirm-shots")
async def confirm_shots(pid: str): return _ok(actions.confirm_shots(pid))


class FieldConfirm(BaseModel):
    path: str
    value: str | None = None


@app.post("/api/projects/{pid}/confirm-template-field")
async def confirm_template_field(pid: str, b: FieldConfirm): return _ok(actions.confirm_template_field(pid, b.path, b.value))


@app.post("/api/projects/{pid}/edit-shot")
async def edit_shot(pid: str, b: ShotChanges): return _ok(actions.edit_shot(pid, b.shot_id, b.changes))


@app.post("/api/projects/{pid}/skip-shot")
async def skip_shot(pid: str, b: ShotRef): return _ok(actions.skip_shot(pid, b.shot_id, b.skip))


@app.post("/api/projects/{pid}/skip-missing")
async def skip_missing(pid: str): return _ok(actions.skip_missing(pid))


@app.post("/api/projects/{pid}/swap-clip")
async def swap_clip(pid: str, b: Swap): return _ok(actions.swap_clip(pid, b.shot_id, b.asset_id))


@app.post("/api/projects/{pid}/approve")
async def approve(pid: str): return _ok(actions.approve(pid))


@app.post("/api/projects/{pid}/revise")
async def revise(pid: str, b: Revision): return _ok(actions.request_revision(pid, b.instruction))


@app.post("/api/projects/{pid}/retry")
async def retry(pid: str): return _ok(actions.retry_stage(pid))


# ---------- uploads ----------

async def _save(file: UploadFile, folder: Path) -> tuple[str, Path]:
    aid = db.new_id()
    dest = folder / f"{aid}_{Path(file.filename or 'upload').name}"
    with open(dest, "wb") as f:
        while chunk := await file.read(1 << 20):
            f.write(chunk)
    return aid, dest


@app.post("/api/assets")
async def upload_asset(file: UploadFile = File(...), project_id: str = Form(...), kind: str = Form("clip"),
                       shot_id: int | None = Form(None)):
    p = actions._p(project_id)
    if kind not in {"clip", "music"}:
        raise HTTPException(400, "kind must be clip or music")
    aid, path = await _save(file, config.ASSETS)
    row = dict(id=aid, kind=kind, filename=file.filename, path=str(path), status="indexing", created=db.now())
    if kind == "music":
        row["status"] = "ready"
    db.run("INSERT INTO assets(id,kind,filename,path,status,created) VALUES(:id,:kind,:filename,:path,:status,:created)", row)
    if kind == "music":
        db.update("projects", project_id, music_asset=aid)
        if p["brief"]:
            actions.edit_brief(project_id, {"music": "uploaded"})
        msgs.text(p["conv_id"], f"Using {file.filename} as the soundtrack.")
    else:
        pipeline.ingest(aid, project_id, shot_id)
    msgs.changed(p["conv_id"])
    return {"id": aid}


@app.post("/api/projects/{pid}/reference-file")
async def reference_file(pid: str, file: UploadFile = File(...)):
    p = actions._p(pid)
    if p["state"] != "ANALYZING":
        raise HTTPException(400, "No reference is waiting for a file")
    tmp = config.PROJECTS / pid / "ref_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    _, path = await _save(file, tmp)
    db.update("projects", pid, error=None)
    pipeline.spawn(pid, pipeline.run_analyze(pid, path), "ANALYZING")
    return _ok("Analysing your file.")


@app.delete("/api/assets/{aid}")
async def delete_asset(aid: str):
    a = db.one("SELECT * FROM assets WHERE id=?", (aid,))
    if not a:
        raise HTTPException(404)
    if a["tl_asset_id"]:
        twelvelabs.delete_asset(a["tl_asset_id"])
    for p in db.q("SELECT id,matches FROM projects WHERE matches IS NOT NULL"):
        ms = [{**m, "asset_id": None, "label": "missing", "reason": "Clip was deleted"} if m.get("asset_id") == aid else m
              for m in p["matches"]]
        if ms != p["matches"]:
            db.update("projects", p["id"], matches=ms)
            pipeline.revert_if_approved(p["id"])
            pipeline.settle(p["id"])
    db.run("DELETE FROM assets WHERE id=?", (aid,))
    Path(a["path"]).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/projects/{pid}/video")
def video(pid: str, n: int | None = None, download: bool = False):
    p = actions._p(pid)
    path = p["final_path"]
    if n:
        d = db.one("SELECT path FROM drafts WHERE project_id=? AND n=?", (pid, n))
        path = d and d["path"]
    if not path:
        raise HTTPException(404)
    return FileResponse(path, media_type="video/mp4", filename="reel.mp4" if download else None)


_dist = config.ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
