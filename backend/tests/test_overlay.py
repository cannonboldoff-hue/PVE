"""M9: an overlay layer and an engine-drawn whip, through the engine interface (HyperFrames on this machine)."""
import numpy as np
import pytest

from app import evidence
from app.clients import ff
from app.models import Plan, PlanShot
from app.render import capabilities, overlay
from app.stages import analyze, orchestrator
from synth import H, W, marker_clip

pytestmark = pytest.mark.skipif(not capabilities.engine_available(), reason="no overlay engine installed")


def _text(eid, start, end, words, anim, y):
    box = {"x": 0.15, "y": y, "w": 0.7, "h": 0.05}
    return {"id": eid, "start": start, "end": end, "text": {"value": words, "raw": words},
            "keys": [{"frame": start, "box": box}], "anim_in": {"value": anim}, "anim_out": {"value": "none"},
            "anim_in_frames": 10, "anim_out_frames": 0,
            "style": {"size": 0.05, "font": "Arial", "fill": "#FFFFFF", "outline": "#000000", "bold": True}}


def test_layer_renders_exact_and_composites(tmp_path):
    texts = [_text("t1", 5, 40, "Bounce in", "bounce", 0.3), _text("t2", 20, 55, "one two three", "word_highlight", 0.6)]
    assert all(overlay.needs_engine(e) for e in texts) and overlay.pick("bounce").name == "hyperframes"
    spec = overlay.OverlaySpec(60, texts, [{"box": {"x": 0.1, "y": 0.8, "w": 0.3, "h": 0.05}, "start": 0, "end": 60,
                                            "image": None, "colour": "#00FF00"}])
    layer = overlay.pick("overlay").render(spec, tmp_path / "layer.webm")
    assert ff.count_frames(layer) == 60
    # composite through the product's assemble: text routed to the engine, exact length kept
    clip = marker_clip(1, 60, tmp_path / "m.mp4")
    plan = Plan(shots=[PlanShot(shot_id=1, asset_id="m", path=str(clip), src_in=0, src_out=2, frames=60)], n_frames=60,
                texts=texts, captions=True)
    final, _, _ = orchestrator.run("ov", plan, tmp_path, lambda: None)
    assert ff.count_frames(final) == 60
    frames = ff.decode(final, W, H)
    plain = ff.decode(clip, W, H)
    band = slice(int(0.3 * H), int(0.36 * H))
    assert np.abs(frames[30][band].astype(int) - plain[30][band].astype(int)).mean() > 5  # text is on the picture
    assert np.abs(frames[2][band].astype(int) - plain[2][band].astype(int)).mean() < 5  # not before it starts


def test_engine_whip_is_classified_as_whip(tmp_path):
    a, b = marker_clip(1, 45, tmp_path / "a.mp4", textured=True), marker_clip(6, 45, tmp_path / "b.mp4", textured=True)
    shots = [PlanShot(shot_id=1, asset_id="a", path=str(a), src_in=0, src_out=1.5, frames=36, tail=12),
             PlanShot(shot_id=2, asset_id="b", path=str(b), src_in=0, src_out=1.5, frames=36, lead=12)]
    render, loss = capabilities.transition("whip_left")
    assert render == "overlay:whip_left" and not loss
    plan = Plan(shots=shots, n_frames=60, transitions=[{"after": 0, "start": 24, "end": 36, "frames": 12,
                                                        "type": "whip_left", "render": render, "loss": loss}])
    final, _, _ = orchestrator.run("whip", plan, tmp_path, lambda: None)
    assert ff.count_frames(final) == 60
    src = analyze.ingest(final)
    found = [i for i in evidence.run_all(src.key, only=["transitions"]).track("transitions") if i.end > i.start]
    assert found and found[0].data["type"] == "whip_left", [(i.start, i.end, i.data) for i in found]
