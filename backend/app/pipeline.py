"""Pipeline runners: one coroutine per stage. The order of stages is code, never LLM choice."""
import asyncio
import json
import logging
import shutil
import time
from collections.abc import Coroutine
from pathlib import Path

from . import config, db, msgs, state
from .clients import openrouter
from .models import Brief, PatchList, Plan
from .stages import brief as brief_mod
from .stages import memory, music, orchestrator, preproduction, reference, verifier
from .stages import plan as plan_mod

log = logging.getLogger("pve")
TASKS: dict[str, asyncio.Task] = {}
BG: set[asyncio.Task] = set()  # per-asset ingest tasks; must not cancel a project's main task


def spawn(pid: str, coro: Coroutine, stage: str) -> None:
    """Run a stage as the project's single background task; failures become FAILED(stage, message)."""
    old = TASKS.pop(pid, None)
    if old and not old.done():
        old.cancel()

    async def wrapper():
        state.CURRENT.set(pid)
        t0, ok = time.monotonic(), False
        try:
            await coro
            ok = True
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("stage %s failed", stage)
            conv = state.get(pid)["conv_id"]
            try:
                state.fail(pid, stage, str(e))
            except state.StateError:
                pass
            msgs.text(conv, f"Something went wrong in {stage.lower().replace('_', ' ')}: {e}\n\nSay \"retry\" to try again.")
            msgs.changed(conv)
        finally:
            state.event(pid, "stage_time", {"stage": stage, "seconds": round(time.monotonic() - t0, 2), "ok": ok})

    TASKS[pid] = asyncio.create_task(wrapper())


def cancel(pid: str) -> None:
    t = TASKS.pop(pid, None)
    if t and not t.done():
        t.cancel()


def _ref(p: dict) -> dict:
    return (reference.lookup(p["reference_id"]) if p["reference_id"] else None) or {}


def work(pid: str) -> Path:
    d = config.PROJECTS / pid
    d.mkdir(exist_ok=True)
    return d


# ---------- 1-2. Reference Analyzer + Creative Brief ----------

async def run_analyze(pid: str, file: Path | None = None) -> None:
    p = state.get(pid)
    conv = p["conv_id"]
    msgs.text(conv, "Looking at the reference Reel…")
    try:
        key, analysis = await asyncio.to_thread(reference.analyze, p["ref_url"], work(pid) / "ref_tmp", file,
                                                lambda m: (msgs.text(conv, m), msgs.changed(conv)))
    except reference.DownloadFailed as e:
        db.update("projects", pid, error={"stage": "ANALYZING", "needs_file": True, "message": str(e)})
        msgs.text(conv, "I couldn't download that link (Instagram and others often block it). "
                        "Please upload a screen recording or the saved video file with the attach button.")
        msgs.card(conv, "reference_upload", pid)
        msgs.changed(conv)
        return
    brief_mod.save_template(key, analysis)
    if analysis.get("validation"):
        msgs.card(conv, "template", pid)  # what the round trip proved, what was downgraded, what needs a confirm
    await run_brief(pid, key, analysis)


async def run_brief(pid: str, key: str, analysis: dict) -> None:
    """Template is ready (just extracted, or picked from the saved ones): write the brief that will fill it."""
    p = state.get(pid)
    conv = p["conv_id"]
    brief = await brief_mod.make_brief(brief_mod.brief_input(key, analysis), p["goal"])
    # the reference's own song is the default soundtrack; "no music" in chat switches it off
    brief.music = "reference" if music.audio_path(key).exists() else ("none" if brief.music == "reference" else brief.music)
    db.update("projects", pid, reference_id=key, error=None, brief=brief.model_dump())
    state.transition(pid, "BRIEF")
    msgs.text(conv, f"The template has {len(analysis['shots'])} shots. Here is the brief for your version. "
                    "Tell me what to change, or confirm it.")
    msgs.card(conv, "brief", pid)
    msgs.changed(conv)


# ---------- 3. Shot Specs ----------

async def run_shots(pid: str) -> None:
    p = state.get(pid)
    template = brief_mod.get_template(p["reference_id"], _ref(p))
    shots = await brief_mod.fill_shots(template, p["brief"], brief_mod.load_ir(p["reference_id"]))
    db.update("projects", pid, shots=[s.model_dump() for s in shots], matches=[])
    msgs.text(p["conv_id"], f"Shot list ready: {len(shots)} shots. Edit or drop any shot, then I'll look through your clips.")
    msgs.card(p["conv_id"], "shots", pid)
    msgs.changed(p["conv_id"])


# ---------- 4. Pre-Production ----------

async def run_preproduction(pid: str, only: set[int] | None = None, first: bool = True) -> None:
    p = state.get(pid)
    matches = await preproduction.match(p, only)
    db.update("projects", pid, matches=matches)
    if first:
        msgs.card(p["conv_id"], "matches", pid)
    settle(pid)


def settle(pid: str) -> None:
    """After matches change: AWAITING_UPLOADS while any shot is missing, else AWAITING_APPROVAL."""
    p = state.get(pid)
    if p["state"] not in {"PREPRODUCTION", "AWAITING_UPLOADS", "AWAITING_APPROVAL"}:
        msgs.changed(p["conv_id"])
        return
    missing = preproduction.pending_missing(p)
    target = "AWAITING_UPLOADS" if missing else "AWAITING_APPROVAL"
    if target != p["state"]:
        state.transition(pid, target)
        if missing:
            msgs.text(p["conv_id"], f"{len(missing)} shot(s) have no match in your clips. Film them using the card below, "
                                    "or skip them.")
            msgs.card(p["conv_id"], "film", pid)
        else:
            msgs.text(p["conv_id"], "Everything is matched. Review the summary and press Approve when you are happy.")
            msgs.card(p["conv_id"], "approval", pid)
    msgs.changed(p["conv_id"])


async def run_ingest(asset_id: str, pid: str, shot_id: int | None) -> None:
    from .models import Match

    await asyncio.to_thread(preproduction.ingest, asset_id)
    a = db.one("SELECT * FROM assets WHERE id=?", (asset_id,))
    p = state.get(pid)
    conv = p["conv_id"]
    if a["status"] == "failed":
        msgs.text(conv, f"I couldn't index {a['filename']}: {a['error']}")
    elif a["status"] == "too_short":
        msgs.text(conv, f"{a['filename']} is under {config.MIN_INDEX_SECONDS:.0f} s, so I can't search it, "
                        "but you can still assign it to a shot by hand.")
    else:
        msgs.text(conv, f"{a['filename']} is indexed and ready.")
    if a["status"] == "failed":
        msgs.changed(conv)
        return
    if shot_id is not None:  # clip filmed for one specific shot: match to that shot only
        shot = next((s for s in p["shots"] if s["shot_id"] == shot_id), None)
        if shot:
            end = round(min(a["duration"], shot["end"] - shot["start"]), 2)
            m = Match(shot_id=shot_id, asset_id=asset_id, start=0, end=end, label="exact", reason="Filmed for this shot")
            prev = next((x for x in p["matches"] if x["shot_id"] == shot_id), None)
            if shot.get("layout") == "collage" and prev and prev["asset_id"]:
                # a collage keeps what it has and gains this picture as another tile
                have = [prev["asset_id"], *prev.get("extra_assets", [])]
                if asset_id not in have and len(have) < shot["collage"]["tiles"]:
                    have.append(asset_id)
                m = Match(**{**prev, "extra_assets": have[1:], "label": "similar" if len(have) < 2 else "exact",
                             "reason": f"Collage of {len(have)} of your pictures"})
            matches = [x for x in p["matches"] if x["shot_id"] != shot_id] + [m.model_dump()]
            db.update("projects", pid, matches=sorted(matches, key=lambda x: x["shot_id"]))
            revert_if_approved(pid)
            settle(pid)
    elif p["state"] in {"AWAITING_UPLOADS", "AWAITING_APPROVAL"} and a["status"] == "ready":
        revert_if_approved(pid)
        spawn(pid, run_rematch(pid), "PREPRODUCTION")
    msgs.changed(conv)


async def run_rematch(pid: str, only: set[int] | None = None) -> None:
    await run_preproduction(pid, only, first=False)


def ingest(asset_id: str, pid: str, shot_id: int | None = None) -> None:
    t = asyncio.create_task(run_ingest(asset_id, pid, shot_id))
    BG.add(t)
    t.add_done_callback(BG.discard)


def revert_if_approved(pid: str) -> None:
    """Hard gate: any change after approval drops the project back to the Approval card."""
    p = state.get(pid)
    if p["state"] in state.POST_APPROVAL:
        cancel(pid)
        db.update("projects", pid, approved=0)
        state.transition(pid, "AWAITING_APPROVAL")
        state.event(pid, "approval_revoked", {"from": p["state"]})
        msgs.text(p["conv_id"], "You changed something after approving, so I need your approval again.")
        msgs.card(p["conv_id"], "approval", pid)


# ---------- 6-10. Plan, Graph, Orchestrator, Draft, Verifier, Final ----------

async def run_production(pid: str, rebuild: bool = True) -> None:
    p = state.get(pid)
    conv = p["conv_id"]
    assets = {a["id"]: a for a in db.q("SELECT * FROM assets")}
    if rebuild:
        brief = Brief(**p["brief"])
        track, mode = music.music_for(p["brief"], p, assets)
        template = brief_mod.load_ir(p["reference_id"])
        plan = plan_mod.build(p["shots"], p["matches"], assets, track, brief.captions, template)
        if not plan.shots:
            raise RuntimeError("no shots with a clip to render")
        plan.music_mode = mode
        if mode == "replace":
            plan.music_volume = music.REFERENCE_VOLUME
            if template:  # timing is pinned to the reference audio: play it unchanged
                plan.audio_mode, plan.music_volume = "reference", 1.0
        db.update("projects", pid, plan=plan.model_dump())
        if state.get(pid)["state"] != "PRODUCING":  # already PRODUCING when retried after a failure
            state.transition(pid, "PRODUCING")
    else:
        plan = Plan(**p["plan"])
    msgs.card(conv, "progress", pid)
    ref = _ref(p)
    rounds = 0
    while True:
        n = state.get(pid)["draft_n"] + 1
        db.update("projects", pid, draft_n=n)
        ddir = work(pid) / f"draft_v{n}"
        ddir.mkdir(exist_ok=True)
        final, dur, hits = await asyncio.to_thread(orchestrator.run, pid, plan, work(pid), lambda: msgs.changed(conv))
        shutil.copy(final, ddir / "draft.mp4")
        (ddir / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        if state.get(pid)["state"] != "VERIFYING":  # already VERIFYING when resumed after a restart
            state.transition(pid, "VERIFYING")
        msgs.text(conv, f"Draft v{n} is rendered ({hits} step(s) reused from cache). Checking it now…")
        msgs.card(conv, "video", pid)
        judge, tech, content = await verifier.verify(plan, ddir / "draft.mp4", dur, p["brief"], ref,
                                                     brief_mod.load_ir(p["reference_id"]) if plan.n_frames else None)
        report = {**judge.model_dump(), "tech": tech, "content": content, "round": rounds, "draft": n}
        db.run("INSERT INTO drafts(project_id,n,path,plan,verifier,created) VALUES(?,?,?,?,?,?)",
               (pid, n, str(ddir / "draft.mp4"), plan.model_dump_json(), json.dumps(report), db.now()))
        db.update("projects", pid, verifier=report, final_path=str(ddir / "draft.mp4"), plan=plan.model_dump())
        if judge.verdict == "PASS":
            return finish(pid, report, unresolved=False)
        ops = [f for i in judge.issues for f in i.fixes]
        if rounds >= config.MAX_REPAIR_ROUNDS:
            return finish(pid, report, unresolved=True)
        notes = plan_mod.apply_patches(plan, ops, assets.get)
        if not ops or len(notes) == len(ops):  # no fix could be applied
            return finish(pid, report, unresolved=True)
        rounds += 1
        state.transition(pid, "REPAIRING")
        db.update("projects", pid, plan=plan.model_dump())
        msgs.text(conv, f"Repair round {rounds} of {config.MAX_REPAIR_ROUNDS}: {judge.summary}")


def finish(pid: str, report: dict, unresolved: bool) -> None:
    p = state.get(pid)
    conv = p["conv_id"]
    state.transition(pid, "FINAL")
    state.event(pid, "final", {"draft": report["draft"], "unresolved": unresolved})
    if unresolved:
        issues = "\n".join(f"- {i['problem']}" for i in report["issues"]) or f"- {report['summary']}"
        msgs.text(conv, f"Here is your Reel. I could not fix everything automatically, so please judge it yourself:\n{issues}")
    else:
        msgs.text(conv, "Your Reel is done and passed my checks. Download it below, or ask me for changes "
                        "(for example \"make the intro faster\").")
    msgs.card(conv, "final", pid)
    msgs.card(conv, "verifier", pid)
    msgs.changed(conv)


async def run_revision(pid: str, instruction: str) -> None:
    p = state.get(pid)
    conv = p["conv_id"]
    plan = Plan(**p["plan"])
    msg = (f"Plan:\n{plan.model_dump_json()}\n\nUser request: {instruction}\n\nTranslate it into patch ops "
           "{shot_id, field, value}. Fields: in, out (seconds in the source clip), speed (0.5-2), caption, "
           "cap_start, cap_end (seconds inside the shot), transition, fit (cover or blur_fit), animation (none, zoom_in, "
           "zoom_out), caption_animation (none, fade, pop, slide_up), caption_color (#RRGGBB), caption_size (36-140), caption_position (top, center, bottom), clip (asset id), drop. "
           "Reply as JSON ops[]. Return an empty list if it cannot be expressed.")
    ops = (await openrouter.chat_json([{"role": "user", "content": msg}], PatchList)).ops
    assets = {a["id"]: a for a in db.q("SELECT * FROM assets")}
    notes = plan_mod.apply_patches(plan, ops, assets.get)
    if not ops or len(notes) == len(ops):
        msgs.text(conv, "I couldn't turn that into an edit I can render. " + " ".join(notes))
        return
    state.event(pid, "revision", {"instruction": instruction, "ops": [o.model_dump() for o in ops]})
    db.update("projects", pid, plan=plan.model_dump())
    state.transition(pid, "PRODUCING")
    msgs.text(conv, "On it. Re-rendering only what changed.")
    await run_production(pid, rebuild=False)


# ---------- retry / resume ----------

STAGE_RUN = {"ANALYZING": lambda pid: run_analyze(pid), "SHOT_SPECS": lambda pid: run_shots(pid),
             "PREPRODUCTION": lambda pid: run_preproduction(pid), "PRODUCING": lambda pid: run_production(pid, rebuild=not state.get(pid)["plan"])}


def resume_all() -> None:
    """On restart, unfinished projects continue from their last persisted state."""
    for p in db.q("SELECT id,state,shots,plan FROM projects"):
        s, pid = p["state"], p["id"]
        if s == "ANALYZING":
            spawn(pid, run_analyze(pid), s)
        elif s == "SHOT_SPECS" and not p["shots"]:
            spawn(pid, run_shots(pid), s)
        elif s == "PREPRODUCTION":
            spawn(pid, run_preproduction(pid), s)
        elif s == "PLANNED":
            spawn(pid, run_production(pid), "PRODUCING")
        elif s in {"PRODUCING", "VERIFYING", "REPAIRING"} and p["plan"]:
            spawn(pid, run_production(pid, rebuild=False), "PRODUCING")
