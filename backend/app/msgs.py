"""Messages + SSE fan-out. publish() is thread-safe so render threads can report progress."""
import asyncio
from collections.abc import AsyncIterator

from . import db

_loop: asyncio.AbstractEventLoop | None = None
_subs: dict[str, set[asyncio.Queue]] = {}


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def _fanout(conv_id: str, ev: dict) -> None:
    for q in _subs.get(conv_id, ()):
        q.put_nowait(ev)


def publish(conv_id: str, ev: dict) -> None:
    if _loop:
        _loop.call_soon_threadsafe(_fanout, conv_id, ev)


async def stream(conv_id: str) -> AsyncIterator[dict]:
    q: asyncio.Queue = asyncio.Queue()
    _subs.setdefault(conv_id, set()).add(q)
    try:
        while True:
            yield await q.get()
    finally:
        _subs[conv_id].discard(q)


def post(conv_id: str, role: str, kind: str, content: str = "", card: dict | None = None) -> dict:
    mid = db.run("INSERT INTO messages(conv_id,role,kind,content,card,created) VALUES(?,?,?,?,?,?)",
                 (conv_id, role, kind, content, db.enc(card), db.now()))
    row = db.one("SELECT * FROM messages WHERE id=?", (mid,))
    publish(conv_id, {"type": "message", "message": row})
    return row


def text(conv_id: str, content: str, role: str = "assistant") -> dict:
    return post(conv_id, role, "text", content)


def card(conv_id: str, card_type: str, project_id: str) -> dict:
    return post(conv_id, "assistant", "card", card={"type": card_type, "project_id": project_id})


def changed(conv_id: str) -> None:
    publish(conv_id, {"type": "project"})
