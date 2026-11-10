import json
import sqlite3
import threading
import time
import uuid

from .config import DATA

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, title TEXT, project_id TEXT, created REAL);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, conv_id TEXT, role TEXT, kind TEXT, content TEXT, card TEXT, created REAL);
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY, conv_id TEXT, state TEXT, error TEXT, goal TEXT, ref_url TEXT, reference_id TEXT,
  brief TEXT, brief_confirmed INTEGER DEFAULT 0, shots TEXT, matches TEXT, plan TEXT, approved INTEGER DEFAULT 0,
  music_asset TEXT, draft_n INTEGER DEFAULT 0, final_path TEXT, verifier TEXT, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS assets(
  id TEXT PRIMARY KEY, kind TEXT, filename TEXT, path TEXT, duration REAL, status TEXT, tl_asset_id TEXT,
  tl_indexed_id TEXT, error TEXT, created REAL);
CREATE TABLE IF NOT EXISTS reference_cache(key TEXT PRIMARY KEY, platform TEXT, fingerprint TEXT, analysis TEXT, created REAL);
CREATE TABLE IF NOT EXISTS templates(key TEXT PRIMARY KEY, title TEXT, shots TEXT, analysis_version INTEGER, created REAL);
CREATE TABLE IF NOT EXISTS graph_runs(
  project_id TEXT, node TEXT, hash TEXT, status TEXT, cached INTEGER DEFAULT 0, output_path TEXT, error TEXT,
  updated REAL, PRIMARY KEY(project_id, node));
CREATE TABLE IF NOT EXISTS drafts(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, n INTEGER, path TEXT, plan TEXT, verifier TEXT, created REAL);
CREATE TABLE IF NOT EXISTS project_events(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, type TEXT, data TEXT, created REAL);
CREATE TABLE IF NOT EXISTS preferences(key TEXT PRIMARY KEY, value TEXT, count INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS match_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, descriptor TEXT, asset_id TEXT, accepted INTEGER, created REAL);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
"""

JSON_COLS = {"error", "brief", "shots", "matches", "plan", "verifier", "analysis", "card", "data"}


def conn() -> sqlite3.Connection:
    c = getattr(_local, "c", None)
    if c is None:
        c = _local.c = sqlite3.connect(DATA / "pve.db", timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
    return c


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in JSON_COLS & d.keys():
        if isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except ValueError:
                pass
    return d


def q(sql: str, args: tuple = ()) -> list[dict]:
    return [_row(r) for r in conn().execute(sql, args).fetchall()]


def one(sql: str, args: tuple = ()) -> dict | None:
    r = q(sql, args)
    return r[0] if r else None


def run(sql: str, args: tuple = ()) -> int:
    c = conn()
    cur = c.execute(sql, args)
    c.commit()
    return cur.lastrowid


def enc(v):
    return v if v is None or isinstance(v, (str, int, float)) else json.dumps(v)


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> float:
    return time.time()


def update(table: str, id_: str, **cols) -> None:
    sets = ", ".join(f"{k}=?" for k in cols)
    run(f"UPDATE {table} SET {sets} WHERE id=?", (*[enc(v) for v in cols.values()], id_))


def kv_get(key: str) -> str | None:
    r = one("SELECT value FROM kv WHERE key=?", (key,))
    return r["value"] if r else None


def kv_set(key: str, value: str) -> None:
    run("INSERT OR REPLACE INTO kv(key,value) VALUES(?,?)", (key, value))


conn().executescript(SCHEMA)
