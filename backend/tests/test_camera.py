"""M5: camera path measured, rebuilt on new footage, measured back; photo vs video."""
import numpy as np
import pytest

from app import evidence, ir
from app.clients import ff
from app.evidence import camera
from app.render import shot
from app.stages import analyze, fusion
from synth import SynthSpec, Zoom, make_reel, marker_clip


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    d = tmp_path_factory.mktemp("cam")
    spec = SynthSpec(n_frames=180, cuts=[60, 120], textured=True, zooms=[Zoom(1, 1.0, 1.3), Zoom(2, 1.0, 1.2)],
                     stills=[2])
    make_reel(spec, d / "reel.mp4")
    src = analyze.ingest(d / "reel.mp4")
    cuts = evidence.run_all(src.key, only=["cuts"])
    ctx = evidence.Ctx(src.key, src, {"cuts": cuts.items, "text": []})
    items = camera.run(ctx)
    return d, src, ir.Evidence(items=[*cuts.items, *items])


def _end_scale(items, k):
    return next(i for i in items if i.id == f"camera_{k}").data["scale_end"]


def test_zoom_is_measured_and_photo_is_found(measured):
    _, _, ev = measured
    cam = {i.id: i.data for i in ev.items if i.track == "camera"}
    still = {i.id: i.data["value"] for i in ev.items if i.track == "still"}
    assert cam["camera_0"]["value"] == "static" and still["still_0"] == "video"
    assert cam["camera_1"]["value"] == "zoom_in" and abs(cam["camera_1"]["scale_end"] - 1.3) / 1.3 < 0.05
    assert still["still_1"] == "video"  # the bar moves: zoomed footage, not a photo
    assert cam["camera_2"]["value"] == "zoom_in" and still["still_2"] == "photo"


def test_rendered_zoom_is_measured_back_without_stepping(measured, tmp_path):
    d, src, ev = measured
    obs = fusion.fuse(src, ev)
    slot = obs.slots[1]
    assert slot.camera.value == "zoom_in" and slot.camera_path and obs.slots[2].media.value == "photo"
    clip = marker_clip(5, 60, tmp_path / "m.mp4", textured=True)
    out = tmp_path / "r.mp4"
    shot.prep({"path": str(clip), "in": 0, "frames": slot.frames,
               "camera_path": [k.model_dump(mode="json") for k in slot.camera_path]}, out)
    assert ff.count_frames(out) == slot.frames
    gray = ff.decode(out, 320, 568, gray=True)
    As = camera.track(gray, np.full(gray.shape[1:], 255, np.uint8))
    path = np.array([camera.view(A, 320, 568) for A in As])
    assert abs(path[-1, 0] - 1.3) / 1.3 < 0.05, path[-1]
    steps = np.diff(path[:, 0])
    assert (steps > -0.002).all()  # monotone zoom: no backward jumps
    assert steps.std() < 0.004, steps.std()  # no stepping: increments stay even
