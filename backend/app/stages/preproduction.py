"""Pre-Production: Personal Media Memory (indexed clips), Asset Matcher, Missing Assets."""
import asyncio
import math
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


MIN_SPEED = 0.5  # a clip down to half the needed length still fits by slowing it (same floor as plan.build)


def is_photo(asset: dict) -> bool:
    return Path(asset.get("filename") or "").suffix.lower() in video.IMAGE_EXTS


def screen(asset: dict, req) -> str | None:
    """Hard constraints from the slot's requirement: None (cannot fit), "ok", or "adaptable" (fits after a speed
    change within limits, or a photo used with the template's own motion)."""
    if req is None:
        return "ok"
    out = "ok"
    if req.media == "video" and is_photo(asset):
        if req.camera_from_clip != "static":  # the shot needs motion the template cannot add
            return None
        out = "adaptable"
    need = req.footage_frames / 30
    dur = asset.get("duration") or 0
    if not is_photo(asset) and dur < need:
        if dur < MIN_SPEED * need:
            return None
        out = "adaptable"
    return out


def _ranked_hits(shot: dict, s: ShotSpec, by_idx: dict) -> list[dict]:
    hits = [h for h in twelvelabs.search(query_for(s)) if h["indexed_id"] in by_idx]
    for h in hits:
        h["score"] = 1 / (1 + h["rank"]) + memory.boost(shot, by_idx[h["indexed_id"]]["id"])
    return sorted(hits, key=lambda h: -h["score"])


def candidates(shot: dict, assets: list[dict], req=None) -> list[tuple[float, Match]]:
    """Judged candidates for one shot, best first: (score, Match). Assets failing the hard screen never compete."""
    s = ShotSpec(**shot)
    fit = {a["id"]: screen(a, req) for a in assets}
    by_idx = {a["tl_indexed_id"]: a for a in assets if fit[a["id"]]}
    out = []
    for h in _ranked_hits(shot, s, by_idx)[:2]:  # judge the two best candidates with Pegasus on just that segment
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
        if label == "none":
            continue
        if fit[a["id"]] == "adaptable":
            label, j["reason"] = "adaptable", f"{j['reason']} (fits after a speed change or with the template's motion)"
        out.append((RANK.get(label, 1) + h["score"],
                    Match(shot_id=s.shot_id, asset_id=a["id"], start=start, end=end, label=label, reason=j["reason"])))
    return sorted(out, key=lambda c: -c[0])


def match_shot(shot: dict, assets: list[dict], req=None) -> Match:
    s = ShotSpec(**shot)
    if s.layout == "collage":
        by_idx = {a["tl_indexed_id"]: a for a in assets}
        return match_collage(s, shot, assets, _ranked_hits(shot, s, by_idx), by_idx)
    c = candidates(shot, assets, req)
    return c[0][1] if c else Match(shot_id=s.shot_id, reason="No clip in your library fits this shot")


def assign(cands: dict) -> dict:
    """All slots at once: each clip goes to one slot when that leaves every slot a fit; a slot left over takes its
    best candidate even if another slot uses the same clip (better a repeat than a gap)."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    sids = [k for k, c in cands.items() if c]
    aids = sorted({m.asset_id for k in sids for _, m in cands[k]})
    out = {}
    if sids and aids:
        score = np.zeros((len(sids), len(aids)))
        best = {}
        for i, k in enumerate(sids):
            for sc, m in cands[k]:
                j = aids.index(m.asset_id)
                if sc > score[i, j]:
                    score[i, j], best[(i, j)] = sc, m
        for i, j in zip(*linear_sum_assignment(-score)):
            if score[i, j] > 0:
                out[sids[i]] = best[(i, j)]
    for k, c in cands.items():
        if k not in out:
            out[k] = c[0][1] if c else None
    return out


async def match(project: dict, only: set[int] | None = None) -> list[dict]:
    """Match shots without a usable match (or those in `only`). Returns the full matches list."""
    existing = {m["shot_id"]: m for m in (project["matches"] or [])}
    assets = db.q("SELECT * FROM assets WHERE kind='clip' AND status='ready'")
    targets = [s for s in project["shots"] if not s.get("skipped")
               and (s["shot_id"] in (only or ()) or existing.get(s["shot_id"], {}).get("label", "missing") == "missing")]
    sem = asyncio.Semaphore(4)
    reqs = requirements_for(project)

    async def one(s: dict):
        async with sem:
            if ShotSpec(**s).layout == "collage":
                return s["shot_id"], await asyncio.to_thread(match_shot, s, assets, reqs.get(s["shot_id"]))
            return s["shot_id"], await asyncio.to_thread(candidates, s, assets, reqs.get(s["shot_id"]))

    if not assets:
        for s in targets:
            existing[s["shot_id"]] = Match(shot_id=s["shot_id"], reason="Your library has no usable clips yet").model_dump()
    else:
        done = dict(await asyncio.gather(*(one(s) for s in targets)))
        singles = {k: v for k, v in done.items() if isinstance(v, list)}
        chosen = {**{k: v for k, v in done.items() if isinstance(v, Match)}, **assign(singles)}
        for k, m in chosen.items():
            existing[k] = (m or Match(shot_id=k, reason="No clip in your library fits this shot")).model_dump()
    out = [existing[s["shot_id"]] for s in project["shots"] if s["shot_id"] in existing]
    return await write_instructions(project["shots"], out, project)


async def write_instructions(shots: list[dict], matches: list[dict], project: dict | None = None) -> list[dict]:
    """One plain filming instruction per missing shot (at least 5 s so the clip can be indexed and trimmed)."""
    skipped = {s["shot_id"] for s in shots if s.get("skipped")}
    need = [m for m in matches if m["label"] == "missing" and not m.get("instruction") and m["shot_id"] not in skipped]
    if not need:
        return matches
    by_id = {s["shot_id"]: s for s in shots}
    reqs = requirements_for(project) if project else {}
    desc = [{"shot_id": m["shot_id"], "subject": by_id[m["shot_id"]]["subject"], "action": by_id[m["shot_id"]]["action"],
             **({"min_seconds": math.ceil(reqs[m["shot_id"]].footage_frames / 30),
                 "framing": reqs[m["shot_id"]].shot_size, "orientation": reqs[m["shot_id"]].orientation}
                if m["shot_id"] in reqs else {}),
             "asset_type": by_id[m["shot_id"]]["asset_type"], "direction": by_id[m["shot_id"]]["direction"], "camera": by_id[m["shot_id"]]["camera"],
             "camera_motion": by_id[m["shot_id"]]["camera_motion"], "layout": by_id[m["shot_id"]]["layout"],
             "collage_tiles": by_id[m["shot_id"]]["collage"]["tiles"]} for m in need]
    msg = ("For each shot, write one plain instruction for a non-expert holding a phone. If asset_type is 'photo', "
           "ask for one vertical photo and say what it should show (for a shot with layout 'collage', ask for the "
           "number of photos in collage_tiles). Otherwise ask for a clip, e.g. "
           "'Film 5 seconds, vertical, walk straight toward the camera'; always at least 5 seconds, and at least "
           "min_seconds when given (rounded up). Use framing (close, medium, wide...) and orientation when given. "
           f"Reply as JSON items[{{shot_id, instruction}}].\n{desc}")
    out = await openrouter.chat_json([{"role": "user", "content": msg}], MissingList)
    ins = {i.shot_id: i.instruction for i in out.items}
    for m in matches:
        if m["shot_id"] in ins:
            m["instruction"] = ins[m["shot_id"]]
    return matches


def requirements_for(project: dict) -> dict:
    """shot_id -> ir.Requirement for IR templates (empty for legacy ones)."""
    from .brief import load_ir

    t = load_ir(project.get("reference_id"))
    return {k + 1: s.requirement for k, s in enumerate(t.slots) if s.requirement} if t else {}


def pending_missing(project: dict) -> list[int]:
    skipped = {s["shot_id"] for s in project["shots"] if s.get("skipped")}
    return [m["shot_id"] for m in project["matches"] if m["label"] == "missing" and m["shot_id"] not in skipped]
