"""Production Graph: Plan -> DAG of content-hashed nodes (prep_clip[shot] -> assemble)."""
import hashlib
import json
import os
from dataclasses import dataclass, field

from ..models import Plan


@dataclass
class Node:
    id: str
    kind: str  # "prep" | "assemble"
    params: dict
    deps: list[str] = field(default_factory=list)
    hash: str = ""


def _h(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _file_id(path: str | None) -> list:
    if not path:
        return []
    st = os.stat(path)
    return [path, st.st_size, int(st.st_mtime)]


def compile_plan(plan: Plan) -> list[Node]:
    nodes: list[Node] = []
    for s in plan.shots:
        p = {"src": _file_id(s.path), "in": s.src_in, "out": s.src_out, "speed": s.speed, "fit": s.fit, "animation": s.animation,
             "grade": s.grade.model_dump(), "collage": s.collage.model_dump() if s.collage else None,
             "tiles": [_file_id(t) for t in s.tiles]}
        n = Node(f"prep_clip[{s.shot_id}]", "prep", {**p, "path": s.path, "tile_paths": s.tiles})
        n.hash = _h(p)
        nodes.append(n)
    preps = list(nodes)
    ap = {
        "preps": [n.hash for n in preps],
        "transitions": [s.transition for s in plan.shots[:-1]],
        "captions": [[s.caption, s.cap_start, s.cap_end, s.caption_animation, s.caption_style.model_dump()] for s in plan.shots] if plan.captions else [],
        "music": [_file_id(plan.music_path), plan.music_volume, plan.music_mode],
    }
    a = Node("assemble", "assemble", {**ap, "music_path": plan.music_path}, [n.id for n in preps])
    a.hash = _h(ap)
    nodes.append(a)
    return nodes


def order(nodes: list[Node]) -> list[list[Node]]:
    """Topological layers; nodes in one layer are independent."""
    done: set[str] = set()
    left = list(nodes)
    layers = []
    while left:
        layer = [n for n in left if all(d in done for d in n.deps)]
        if not layer:
            raise ValueError("cycle in production graph")
        layers.append(layer)
        done |= {n.id for n in layer}
        left = [n for n in left if n.id not in done]
    return layers
