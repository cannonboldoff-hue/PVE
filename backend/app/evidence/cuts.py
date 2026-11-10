"""Hard cuts: PySceneDetect AdaptiveDetector and ContentDetector on the 30 fps proxy, union of both."""
import scenedetect
from scenedetect import AdaptiveDetector, ContentDetector, detect

from .. import ir

NAME, VERSION, DEPS = "cuts", 1, []
MERGE_FRAMES = 2  # detections this close are one cut; higher merges real rapid cuts, lower double-counts soft ones
MIN_SHOT_FRAMES = 6  # shorter shots are dropped; lower keeps flash frames as shots, higher loses real quick cuts
ONE_DETECTOR_CONF = 0.6  # a cut only one detector saw


def _cuts(path, det) -> list[int]:
    return [s[0].frame_num for s in detect(str(path), det, show_progress=False)[1:]]


def merge(found: dict[str, list[int]], n_frames: int) -> list[tuple[int, list[str]]]:
    """Union of detector outputs, merged within MERGE_FRAMES, shots under MIN_SHOT_FRAMES dropped."""
    hits = sorted((f, name) for name, fs in found.items() for f in fs if 0 < f < n_frames)
    groups: list[list[tuple[int, str]]] = []
    for f, name in hits:
        if groups and f - groups[-1][-1][0] <= MERGE_FRAMES:
            groups[-1].append((f, name))
        else:
            groups.append([(f, name)])
    cuts = []
    for g in groups:
        frames = sorted(f for f, _ in g)
        cuts.append((frames[len(frames) // 2], sorted({n for _, n in g})))
    out, prev = [], 0
    for f, dets in cuts:
        if f - prev >= MIN_SHOT_FRAMES and n_frames - f >= MIN_SHOT_FRAMES:
            out.append((f, dets))
            prev = f
    return out


def run(ctx) -> list[ir.Item]:
    found = {
        "adaptive": _cuts(ctx.proxy, AdaptiveDetector(min_scene_len=MIN_SHOT_FRAMES)),
        "content": _cuts(ctx.proxy, ContentDetector(min_scene_len=MIN_SHOT_FRAMES)),
    }
    tool = f"pyscenedetect {scenedetect.__version__}"
    return [ir.Item(id=f"cuts_{k}", track=NAME, start=f, end=f, data={"frame": f, "detectors": dets},
                    conf=1.0 if len(dets) == 2 else ONE_DETECTOR_CONF, tool=tool)
            for k, (f, dets) in enumerate(merge(found, ctx.source.n_frames))]
