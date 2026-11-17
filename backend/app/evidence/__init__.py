"""Evidence tracks: measurements of the reference proxy. Each track module exposes NAME, VERSION, DEPS and
run(ctx) -> list[Item]. run_all runs them in dependency layers, independent tracks in parallel, and caches each
track's items by (fingerprint, track version)."""
import importlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .. import ir

TRACK_MODULES = ["cuts", "transitions", "text", "text_anim", "camera", "speed", "effects", "layout", "overlays", "colour", "tiles", "masks", "match_cuts"]  # grows per milestone
EVIDENCE_VERSION = 1


@dataclass
class Ctx:
    key: str
    source: ir.Source
    ev: dict[str, list[ir.Item]] = field(default_factory=dict)  # finished tracks, readable by dependants

    @property
    def proxy(self):
        from ..stages.analyze import proxy_path

        return proxy_path(self.key)


def boundaries(ev: dict) -> list[tuple[int, int, int]]:
    """(boundary frame, window start, window end) per shot change: the transitions track when it ran, else cuts."""
    if "transitions" in ev:
        return [(i.data["frame"], i.start, i.end) for i in sorted(ev["transitions"], key=lambda i: i.data["frame"])]
    return [(i.data["frame"],) * 3 for i in sorted(ev.get("cuts", []), key=lambda i: i.data["frame"])]


def tracks() -> dict:
    return {m.NAME: m for m in (importlib.import_module(f"{__name__}.{n}") for n in TRACK_MODULES)}


_lock = threading.Lock()


def _cached(key: str, fp: str, mod) -> list[ir.Item] | None:
    p = ir.ref_dir(key) / "evidence" / f"{mod.NAME}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("fp") != fp or d.get("v") != mod.VERSION:
        return None
    return [ir.Item.model_validate(i) for i in d["items"]]


def _store(key: str, fp: str, mod, items: list[ir.Item]) -> None:
    p = ir.ref_dir(key) / "evidence" / f"{mod.NAME}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({"fp": fp, "v": mod.VERSION, "items": [i.model_dump(mode="json") for i in items]}),
                 encoding="utf-8")


def run_all(key: str, only: list[str] | None = None) -> ir.Evidence:
    src = ir.load(key, "source", ir.Source)
    if src is None:
        raise FileNotFoundError(f"no ingested source for {key}")
    mods = tracks()
    want = set(only or mods)
    while (more := {d for name in want for d in mods[name].DEPS} - want):  # pull in dependencies, transitively
        want |= more
    ctx = Ctx(key, src)

    def one(mod) -> None:
        items = _cached(key, src.fingerprint, mod)
        if items is None:
            items = mod.run(ctx)
            _store(key, src.fingerprint, mod, items)
        with _lock:
            ctx.ev[mod.NAME] = items

    left = [mods[n] for n in mods if n in want]
    with ThreadPoolExecutor(4) as pool:
        while left:
            layer = [m for m in left if all(d in ctx.ev for d in m.DEPS)]
            if not layer:
                raise ValueError(f"evidence dependency cycle among {[m.NAME for m in left]}")
            list(pool.map(one, layer))
            left = [m for m in left if m.NAME not in ctx.ev]
    ev = ir.Evidence(items=[i for n in mods if n in ctx.ev for i in ctx.ev[n]])
    ir.save(key, "evidence", ev, v=EVIDENCE_VERSION, inputs=ir.digest({n: mods[n].VERSION for n in ctx.ev}))
    return ev
