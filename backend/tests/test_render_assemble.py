from app.clients import ff, video
from app.models import Plan, PlanShot
from app.stages import orchestrator
from app.stages.graph import compile_plan


def _src(tmp, name, fps, size="1280x720"):
    p = tmp / name
    ff.run(["-f", "lavfi", "-i", f"testsrc2=size={size}:rate={fps}:duration=3", "-f", "lavfi", "-i", "sine=880:d=3",
            "-pix_fmt", "yuv420p", "-shortest", str(p)])
    return str(p)


def test_frame_exact_render_with_reference_audio(tmp_path):
    ref = tmp_path / "ref.wav"
    ff.run(["-f", "lavfi", "-i", "anoisesrc=color=pink:seed=3:sample_rate=44100:duration=3.2", str(ref)])
    a, b, c = _src(tmp_path, "a.mp4", 24), _src(tmp_path, "b.mp4", 60, "640x480"), _src(tmp_path, "c.mp4", 25, "1080x1920")
    shots = [PlanShot(shot_id=1, asset_id="a", path=a, src_in=0.2, src_out=1.5, frames=31, caption="Hello"),
             PlanShot(shot_id=2, asset_id="b", path=b, src_in=1.0, src_out=2.0, frames=17, fit="blur_fit"),
             PlanShot(shot_id=3, asset_id="c", path=c, src_in=0.0, src_out=2.5, frames=42, caption="World")]
    plan = Plan(shots=shots, n_frames=90, music_path=str(ref), music_mode="replace", music_volume=1.0,
                audio_mode="reference")
    final, dur, hits = orchestrator.run("pa", plan, tmp_path, lambda: None)
    assert dur == 3.0 and hits == 0
    assert ff.count_frames(final) == 90
    assert ff.audio_lag(final, ref) == 0
    checks = video.tech_checks(final, dur, str(ref))
    assert checks["audio"]["ok"] and checks["resolution"]["ok"] and checks["duration"]["ok"], checks
    # frames are part of the node hash: changing one slot's length re-renders only that slot (and assemble)
    plan.shots[0].frames, plan.shots[2].frames = 30, 43
    _, _, hits2 = orchestrator.run("pa", plan, tmp_path, lambda: None)
    assert hits2 == 1
    assert compile_plan(plan)[0].params["frames"] == 30
