"""Pre-Production: Personal Media Memory (indexed clips), Asset Matcher, Missing Assets."""
import asyncio
from pathlib import Path

from .. import config, db
from ..clients import openrouter, twelvelabs, video
from ..models import Match, MissingList, ShotSpec
from . import memory

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {"match": {"type": "string", "enum": ["exact", "similar", "none"]}, "reason": {"type": "string"}},
    "required": ["match", "reason"],
}
RANK = {"exact": 2, "similar": 1, "none": 0}


def ingest(asset_id: str) -> None:
    """Probe and index one clip in TwelveLabs. Sets status ready / too_short / failed."""
    a = db.one("SELECT * FROM assets WHERE id=?", (asset_id,))
    try:
        if Path(a["path"]).suffix.lower() in video.IMAGE_EXTS:  # a photo becomes a short motion clip
            clip = Path(a["path"]).with_suffix(".mp4")
            video.image_to_clip(a["path"], clip)
            db.update("assets", asset_id, path=str(clip))
            a["path"] = str(clip)
        dur = video.info(a["path"])["duration"]
        if dur < config.MIN_INDEX_SECONDS:
            db.update("assets", asset_id, duration=dur, status="too_short")
            return
        db.update("assets", asset_id, duration=dur, status="indexing")
        tl_asset, tl_idx = twelvelabs.index_clip(a["path"])
        db.update("assets", asset_id, tl_asset_id=tl_asset, tl_indexed_id=tl_idx, status="ready")
    except Exception as e:
        db.update("assets", asset_id, status="failed", error=str(e)[:300])


def query_for(s: ShotSpec) -> str:
    return ". ".join(x for x in (s.subject, s.action, s.camera, s.camera_motion) if x)


def _fit(hit: dict, shot: ShotSpec, asset: dict) -> tuple[float, float]:
    """Segment from search -> in/out points that fill the shot slot where the clip allows."""
    start, end, dur = hit["start"], hit["end"], asset["duration"]
    if end - start < shot.duration:
        end = min(dur, start + shot.duration)
    if end - start < shot.duration:  # still short: pull the start back
        start = max(0.0, end - shot.duration)
    return round(start, 2), round(end, 2)


def match_collage(s: ShotSpec, shot: dict, assets: list[dict], hits: list[dict], by_idx: dict) -> Match:
    """A collage needs several pictures, not one best clip: the top search hits first, then the rest of the library.
    The tiles are not judged one by one (a collage is a set), so the label is 'similar'."""
    order: list[dict] = []
    for h in hits:
        a = by_idx[h["indexed_id"]]
        if a not in order:
            order.append(a)
    order += [a for a in sorted(assets, key=lambda a: a["created"]) if a not in order]
    n = min(s.collage.tiles, len(order))
    if n < 2:
        return Match(shot_id=s.shot_id, reason=f"A collage needs at least 2 pictures; your library has {len(order)}")
    main, extras = order[0], order[1:n]
    end = round(min(main["duration"], s.duration), 2)
    return Match(shot_id=s.shot_id, asset_id=main["id"], start=0, end=end, label="similar", extra_assets=[a["id"] for a in extras],
                 reason=f"Collage of {n} of your pictures (picked by relevance, not checked one by one)")


def match_shot(shot: dict, assets: list[dict]) -> Match:
    s = ShotSpec(**shot)
    by_idx = {a["tl_indexed_id"]: a for a in assets}
    hits = [h for h in twelvelabs.search(query_for(s)) if h["indexed_id"] in by_idx]
    for h in hits:
        h["score"] = 1 / (1 + h["rank"]) + memory.boost(shot, by_idx[h["indexed_id"]]["id"])
    hits.sort(key=lambda h: -h["score"])
    if s.layout == "collage":
        return match_collage(s, shot, assets, hits, by_idx)
    best: tuple[int, float, Match] | None = None
    for h in hits[:2]:  # judge the two best candidates with Pegasus on just that segment
        a = by_idx[h["indexed_id"]]
        start, end = _fit(h, s, a)
        prompt = (f"Does this video segment show: {query_for(s)}? Answer exact if it clearly shows the subject and "
                  "action, similar if related but the subject, action or setting differs, none otherwise. "
                  "Give a one-line reason.")
        j_end = min(a["duration"], max(h["end"], h["start"] + 1))  # TwelveLabs rejects end_time past the clip
        j = twelvelabs.analyze(a["tl_asset_id"], prompt, JUDGE_SCHEMA, min(h["start"], max(0.0, j_end - 1)), j_end)
        label = j["match"]
        if label == "exact" and end - start < 0.6 * s.duration:
            label, j["reason"] = "similar", f"{j['reason']} (clip segment is shorter than the slot)"
        if label != "none":
            m = Match(shot_id=s.shot_id, asset_id=a["id"], start=start, end=end, label=label, reason=j["reason"])
            if not best or (RANK[label], h["score"]) > best[:2]:
                best = (RANK[label], h["score"], m)
    return best[2] if best else Match(shot_id=s.shot_id, reason="No clip in your library fits this shot")


async def match(project: dict, only: set[int] | None = None) -> list[dict]:
    """Match shots without a usable match (or those in `only`). Returns the full matches list."""
    existing = {m["shot_id"]: m for m in (project["matches"] or [])}
    assets = db.q("SELECT * FROM assets WHERE kind='clip' AND status='ready'")
    targets = [s for s in project["shots"] if not s.get("skipped")
               and (s["shot_id"] in (only or ()) or existing.get(s["shot_id"], {}).get("label", "missing") == "missing")]
    sem = asyncio.Semaphore(4)

    async def one(s: dict) -> Match:
        if not assets:
            return Match(shot_id=s["shot_id"], reason="Your library has no usable clips yet")
        async with sem:
            return await asyncio.to_thread(match_shot, s, assets)

    for m in await asyncio.gather(*(one(s) for s in targets)):
        existing[m.shot_id] = m.model_dump()
    out = [existing[s["shot_id"]] for s in project["shots"] if s["shot_id"] in existing]
    return await write_instructions(project["shots"], out)


async def write_instructions(shots: list[dict], matches: list[dict]) -> list[dict]:
    """One plain filming instruction per missing shot (at least 5 s so the clip can be indexed and trimmed)."""
    skipped = {s["shot_id"] for s in shots if s.get("skipped")}
    need = [m for m in matches if m["label"] == "missing" and not m.get("instruction") and m["shot_id"] not in skipped]
    if not need:
        return matches
    by_id = {s["shot_id"]: s for s in shots}
    desc = [{"shot_id": m["shot_id"], "subject": by_id[m["shot_id"]]["subject"], "action": by_id[m["shot_id"]]["action"],
             "asset_type": by_id[m["shot_id"]]["asset_type"], "direction": by_id[m["shot_id"]]["direction"], "camera": by_id[m["shot_id"]]["camera"],
             "camera_motion": by_id[m["shot_id"]]["camera_motion"], "layout": by_id[m["shot_id"]]["layout"],
             "collage_tiles": by_id[m["shot_id"]]["collage"]["tiles"]} for m in need]
    msg = ("For each shot, write one plain instruction for a non-expert holding a phone. If asset_type is 'photo', "
           "ask for one vertical photo and say what it should show (for a shot with layout 'collage', ask for the "
           "number of photos in collage_tiles). Otherwise ask for a clip, e.g. "
           "'Film 5 seconds, vertical, walk straight toward the camera'; always at least 5 seconds. "
           f"Reply as JSON items[{{shot_id, instruction}}].\n{desc}")
    out = await openrouter.chat_json([{"role": "user", "content": msg}], MissingList)
    ins = {i.shot_id: i.instruction for i in out.items}
    for m in matches:
        if m["shot_id"] in ins:
            m["instruction"] = ins[m["shot_id"]]
    return matches


def pending_missing(project: dict) -> list[int]:
    skipped = {s["shot_id"] for s in project["shots"] if s.get("skipped")}
    return [m["shot_id"] for m in project["matches"] if m["label"] == "missing" and m["shot_id"] not in skipped]
