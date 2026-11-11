"""Orchestrator: schedules the graph. No creative decisions. Content-hash outputs = free cache."""
import os
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .. import config, db
from ..models import Plan
from ..render import assemble, shot, transition
from . import editor
from .graph import Node, compile_plan, order


def _mark(pid: str, node: Node, status: str, cached: bool = False, output: str = "", error: str = "") -> None:
    db.run("INSERT OR REPLACE INTO graph_runs(project_id,node,hash,status,cached,output_path,error,updated) VALUES(?,?,?,?,?,?,?,?)",
           (pid, node.id, node.hash, status, int(cached), output, error, db.now()))


def run(pid: str, plan: Plan, workdir: Path, on_progress: Callable[[], None]) -> tuple[Path, float, int]:
    """Returns (final mp4, duration, cache-hit count)."""
    cache = workdir / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    nodes = compile_plan(plan)
    db.run("DELETE FROM graph_runs WHERE project_id=?", (pid,))
    for n in nodes:
        _mark(pid, n, "pending")
    on_progress()

    outputs: dict[str, Path] = {}
    durations: dict[str, float] = {}
    hits = 0
    # nodes with the same hash share one output file (e.g. the same clip range used twice): build it once
    locks = {f"{n.kind}_{n.hash}": threading.Lock() for n in nodes}

    def execute(n: Node) -> tuple[Node, bool]:
        key = f"{n.kind}_{n.hash}"
        out = cache / f"{key}.mp4"
        with locks[key]:
            if out.exists():
                outputs[n.id] = out
                return n, True
            _mark(pid, n, "running")
            on_progress()
            for attempt in (0, 1):  # retry a failing node once
                try:
                    exact = plan.n_frames is not None
                    if n.kind == "prep":
                        (shot.prep if n.params.get("frames") is not None else editor.prep_clip)(n.params, out)
                    elif n.kind == "trans":
                        p = n.params
                        transition.render(outputs[n.deps[0]], p["a_frames"], outputs[n.deps[1]], p["frames"],
                                          p["xfade"], out)
                    else:
                        join = assemble.assemble if exact else editor.assemble
                        durations["total"] = join(plan, [outputs[d] for d in n.deps], workdir, out)
                    break
                except Exception as e:
                    out.unlink(missing_ok=True)
                    if attempt:
                        _mark(pid, n, "failed", error=str(e))
                        on_progress()
                        raise
            outputs[n.id] = out
            return n, False

    workers = max(1, (os.cpu_count() or 2) // 2)
    with ThreadPoolExecutor(workers) as pool:
        for layer in order(nodes):
            for n, cached in pool.map(execute, layer):
                hits += cached
                _mark(pid, n, "done", cached=cached, output=str(outputs[n.id]))
                on_progress()
    final = outputs["assemble"]
    if "total" not in durations:  # assemble was a cache hit
        from ..clients import video

        durations["total"] = plan.n_frames / config.FPS if plan.n_frames else video.info(final)["duration"]
    return final, durations["total"], hits
