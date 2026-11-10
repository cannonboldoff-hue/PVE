"""Chat agent (OpenRouter). Talks and edits project state through tools; it never runs the pipeline itself
and has no approve tool, so only the Approve button can pass the gate."""
import json

from . import actions, db, msgs, state
from .clients import openrouter


def _tool(name: str, desc: str, props: dict | None = None, required: list[str] | None = None) -> dict:
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props or {}, "required": required or []}}}


TOOLS = [
    _tool("submit_reference", "Start the project from a Reel link the user pasted.",
          {"url": {"type": "string"}, "goal": {"type": "string", "description": "What the user wants their Reel to be about"}}, ["url"]),
    _tool("edit_brief", "Change brief fields. Keys: topic, keep, change, target_length, tone, caption_language, captions, media (photo, video or mixed), music (none, uploaded or reference = the reference Reel's own song).",
          {"changes": {"type": "object"}}, ["changes"]),
    _tool("confirm_brief", "The user is happy with the brief; write the shot list."),
    _tool("confirm_shots", "The user is happy with the shot list; search their clips."),
    _tool("edit_shot", "Edit one shot. Keys: start, end, purpose, subject, action, direction, camera, camera_motion, text, transition_out, background, fit (cover or blur_fit), animation (none, zoom_in, zoom_out), caption_animation (none, fade, pop, slide_up), overlay, caption_start and caption_end (seconds after the shot starts), caption_style (partial object: font Arial/Impact/Georgia/Comic Sans MS/Segoe Script/Times New Roman/Courier New/Verdana/Trebuchet MS, size 36-140, color #RRGGBB, outline_color, position top/center/bottom, bold, uppercase, emphasis_words, emphasis_color), grade (partial object: preset none/warm/cool/vintage/cinematic/noir, brightness -0.4..0.4, contrast 0.6..1.6, saturation 0..2), layout (single or collage), collage (partial object: tiles 2-6, background #RRGGBB, border, tilt 0-10).",
          {"shot_id": {"type": "integer"}, "changes": {"type": "object"}}, ["shot_id", "changes"]),
    _tool("skip_shot", "Drop a shot from the Reel (or restore it with skip=false).",
          {"shot_id": {"type": "integer"}, "skip": {"type": "boolean"}}, ["shot_id"]),
    _tool("swap_clip", "Use a different library clip for a shot.",
          {"shot_id": {"type": "integer"}, "asset_id": {"type": "string"}}, ["shot_id", "asset_id"]),
    _tool("request_revision", "Change a finished Reel, e.g. 'make the intro faster'.",
          {"instruction": {"type": "string"}}, ["instruction"]),
    _tool("retry_stage", "Retry the stage that failed."),
    _tool("upload_status", "List the user's uploaded clips and their indexing status."),
]

HANDLERS = {
    "submit_reference": lambda pid, a: actions.submit_reference(pid, a["url"], a.get("goal", "")),
    "edit_brief": lambda pid, a: actions.edit_brief(pid, a["changes"]),
    "confirm_brief": lambda pid, a: actions.confirm_brief(pid),
    "confirm_shots": lambda pid, a: actions.confirm_shots(pid),
    "edit_shot": lambda pid, a: actions.edit_shot(pid, a["shot_id"], a["changes"]),
    "skip_shot": lambda pid, a: actions.skip_shot(pid, a["shot_id"], a.get("skip", True)),
    "swap_clip": lambda pid, a: actions.swap_clip(pid, a["shot_id"], a["asset_id"]),
    "request_revision": lambda pid, a: actions.request_revision(pid, a["instruction"]),
    "retry_stage": lambda pid, a: actions.retry_stage(pid),
    "upload_status": lambda pid, a: actions.upload_status(pid),
}

SYSTEM = """You are the chat front of an AI Reel editor. The user pastes a Reel link, you help them make their own \
version from their own clips. Be brief and plain; the user is not a video expert.
Rules:
- You do not render or analyse anything yourself. Use tools to change project state; the pipeline does the work.
- Cards in the chat show the brief, shots, matches, approval and video. Do not repeat their content; say what to do next.
- You cannot approve. When everything is matched, tell the user to press Approve on the Approval card.
- If a tool returns an error, tell the user in plain words. Never say something will happen automatically unless a tool result says so.
- Once the Reel is finished (state FINAL), use request_revision for every change (captions, trims, speed, transitions, clips).
  edit_shot, skip_shot, swap_clip and edit_brief send the project back to the Approval card, so use them only before approval.
- Never invent clips, shot ids or asset ids; use only the project state below.

Project state:
{ctx}"""


def context(pid: str) -> str:
    p = state.get(pid)
    shots = [{"shot_id": s["shot_id"], "subject": s["subject"], "skipped": s.get("skipped", False)} for s in p["shots"] or []]
    return json.dumps({
        "state": p["state"], "error": p["error"], "goal": p["goal"], "brief": p["brief"], "shots": shots,
        "matches": [{k: m[k] for k in ("shot_id", "asset_id", "label")} for m in p["matches"] or []],
        "clips": [{"id": a["id"], "filename": a["filename"], "status": a["status"]} for a in db.q("SELECT * FROM assets WHERE kind='clip'")],
    })


def history(conv_id: str) -> list[dict]:
    rows = db.q("SELECT role,content FROM messages WHERE conv_id=? AND kind='text' ORDER BY id DESC LIMIT 30", (conv_id,))
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def reply(conv_id: str, pid: str) -> None:
    """One user turn: stream the answer, run tool calls, loop (max 5 rounds)."""
    msgs_ = [{"role": "system", "content": SYSTEM.format(ctx=context(pid))}, *history(conv_id)]
    for _ in range(5):
        text, calls = "", []
        mid = None
        async for ev in openrouter.chat_stream(msgs_, TOOLS):
            if "token" in ev:
                text += ev["token"]
                msgs.publish(conv_id, {"type": "token", "text": ev["token"]})
            else:
                calls = ev["tool_calls"]
        if text:
            mid = msgs.text(conv_id, text)["id"]
            msgs.publish(conv_id, {"type": "token_end", "message_id": mid})
        if not calls:
            return
        msgs_.append({"role": "assistant", "content": text or None, "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]})
        for c in calls:
            try:
                out = HANDLERS[c["name"]](pid, json.loads(c["arguments"] or "{}"))
            except actions.ActionError as e:
                out = f"Error: {e}"
            except Exception as e:
                out = f"Error: {type(e).__name__}: {e}"
            msgs_.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(out)})
        msgs_[0]["content"] = SYSTEM.format(ctx=context(pid))
