import subprocess
from pathlib import Path

import pytest

from app.clients import video
from app.models import Plan, PlanShot
from app.stages import editor, orchestrator
from app.stages.graph import compile_plan, order
from helpers import ff


def make_clip(path: Path, size: str, fps: int, audio: bool, secs: float = 4) -> str:
    args = ["-f", "lavfi", "-i", f"testsrc2=size={size}:rate={fps}:duration={secs}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}"]
    ff(*args, "-pix_fmt", "yuv420p", str(path))
    return str(path)


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("clips")
    return [make_clip(d / "a.mp4", "1280x720", 24, True), make_clip(d / "b.mp4", "640x480", 30, False),
            make_clip(d / "c.mp4", "1080x1920", 60, True)]


def plan_for(clips, music=None):
    shots = [
        PlanShot(shot_id=1, asset_id="a", path=clips[0], src_in=0, src_out=3, caption="Hello world", cap_end=2.5, transition="fade"),
        PlanShot(shot_id=2, asset_id="b", path=clips[1], src_in=0.5, src_out=3.5, speed=0.75, caption="Mixed fps, no audio", cap_end=3.5, transition="cut"),
        PlanShot(shot_id=3, asset_id="c", path=clips[2], src_in=0, src_out=2, caption="", transition="cut"),
    ]
    return Plan(shots=shots, music_path=music)


def test_prep_normalises_mixed_inputs(clips, tmp_path):
    plan = plan_for(clips)
    infos = []
    for n in compile_plan(plan)[:3]:
        out = tmp_path / f"{n.id.replace('[', '_').replace(']', '')}.mp4"
        editor.prep_clip(n.params, out)
        i = video.info(out)
        infos.append((i["width"], i["height"], i["has_audio"]))
    assert infos == [(1080, 1920, True)] * 3, infos  # 24/30/60 fps, 16:9 / 4:3 / 9:16, with and without audio


def test_full_render_and_cache(clips, tmp_path):
    plan = plan_for(clips)
    final, dur, hits = orchestrator.run("p1", plan, tmp_path, lambda: None)
    assert hits == 0
    checks = video.tech_checks(final, dur)
    assert checks["resolution"]["ok"] and checks["duration"]["ok"], checks
    assert video.info(final)["has_audio"]
    # change only shot 2: shot 1 and 3 prep are cache hits, assemble re-runs
    plan.shots[1].src_in = 0.0
    _, _, hits2 = orchestrator.run("p1", plan, tmp_path, lambda: None)
    assert hits2 == 2


def test_music_ducking_render(clips, tmp_path):
    music = tmp_path / "m.mp3"
    ff("-f", "lavfi", "-i", "sine=frequency=220:duration=3", str(music))
    final, dur, _ = orchestrator.run("p2", plan_for(clips, str(music)), tmp_path, lambda: None)
    assert video.tech_checks(final, dur)["audio"]["ok"]


def test_graph_order(clips):
    layers = order(compile_plan(plan_for(clips)))
    assert [len(l) for l in layers] == [3, 1] and layers[1][0].id == "assemble"
