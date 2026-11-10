"""TwelveLabs wrapper. Sync SDK calls; callers wrap in asyncio.to_thread."""
import json
import time
from functools import lru_cache

from .. import config, db


@lru_cache
def _tl():
    from twelvelabs import TwelveLabs

    if not config.TWELVELABS_API_KEY:
        raise RuntimeError("TWELVELABS_API_KEY is not set (see .env.example)")
    return TwelveLabs(api_key=config.TWELVELABS_API_KEY)


def _wait(fn, done: set[str], bad: set[str], what: str, timeout: float = 1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = fn()
        if r.status in done:
            return r
        if r.status in bad:
            raise RuntimeError(f"TwelveLabs {what} {r.status}")
        time.sleep(4)
    raise RuntimeError(f"TwelveLabs {what} timed out")


def upload_asset(path: str) -> str:
    tl = _tl()
    with open(path, "rb") as f:
        a = tl.assets.create(method="direct", file=f)
    _wait(lambda: tl.assets.retrieve(a.id), {"ready"}, {"failed"}, "asset upload")
    return a.id


def delete_asset(asset_id: str) -> None:
    try:
        _tl().assets.delete(asset_id, force=True)
    except Exception:
        pass  # best effort; the local copy is what matters for privacy


def library_index() -> str:
    """Single Marengo index for the user's clips. Pegasus analysis runs on assets, not on an index."""
    iid = db.kv_get("tl_library_index")
    if iid:
        return iid
    from twelvelabs.indexes.types.indexes_create_request_models_item import IndexesCreateRequestModelsItem as M

    idx = _tl().indexes.create(index_name="pve-library", models=[M(model_name="marengo3.0", model_options=["visual", "audio"])])
    db.kv_set("tl_library_index", idx.id)
    return idx.id


def index_clip(path: str) -> tuple[str, str]:
    """Upload + index a clip. Returns (asset_id, indexed_asset_id)."""
    tl = _tl()
    aid = upload_asset(path)
    iid = library_index()
    ia = tl.indexes.indexed_assets.create(iid, asset_id=aid)
    _wait(lambda: tl.indexes.indexed_assets.retrieve(iid, ia.id), {"ready"}, {"failed"}, "indexing")
    return aid, ia.id


def search(query: str, limit: int = 10) -> list[dict]:
    """Ranked segments across the library: [{indexed_id, start, end, rank}]."""
    pager = _tl().search.query(index_id=library_index(), search_options=["visual", "audio"],
                               query_text=query[:500], page_limit=limit)
    hits = []
    for item in pager:
        for s in item.clips or [item]:
            hits.append({"indexed_id": getattr(s, "video_id", None) or item.video_id,
                         "start": float(s.start or 0), "end": float(s.end or 0), "rank": len(hits)})
        if len(hits) >= limit:
            break
    return hits


def analyze(asset_id: str, prompt: str, schema: dict, start: float | None = None, end: float | None = None) -> dict:
    from twelvelabs.types.sync_response_format import SyncResponseFormat
    from twelvelabs.types.video_context import VideoContext_AssetId

    kw = {"start_time": start, "end_time": end} if start is not None and end is not None else {}
    r = _tl().analyze(video=VideoContext_AssetId(asset_id=asset_id), prompt=prompt, temperature=0,
                      response_format=SyncResponseFormat(type="json_schema", json_schema=schema), **kw)
    return json.loads(r.data)
