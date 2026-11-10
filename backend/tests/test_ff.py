from app.clients import ff


def _clip(tmp, name, frames=45, delay_ms=0):
    p = tmp / name
    af = f"adelay={delay_ms}," if delay_ms else ""
    ff.run(["-f", "lavfi", "-i", f"testsrc2=size=320x240:rate=30", "-f", "lavfi",
            "-i", "anoisesrc=color=pink:seed=7:sample_rate=48000",
            "-filter_complex", f"[1:a]{af}atrim=0:{frames / 30}[a]", "-map", "0:v", "-map", "[a]",
            "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(p)])
    return p


def test_probe_count_ssim(tmp_path):
    a = _clip(tmp_path, "a.mp4")
    info = ff.probe(a)
    assert ff.video_stream(info)["r_frame_rate"] == "30/1"
    assert ff.count_frames(a) == 45
    s = ff.ssim(a, a)
    assert len(s) == 45 and min(s) > 0.999
    b = tmp_path / "b.mp4"
    ff.run(["-i", str(a), "-vf", "negate", "-c:v", "libx264", str(b)])
    assert max(ff.ssim(a, b)) < 0.9


def test_audio_lag(tmp_path):
    a = _clip(tmp_path, "a.mp4", frames=90)
    assert ff.audio_lag(a, a) == 0
    b = _clip(tmp_path, "b.mp4", frames=90, delay_ms=100)
    assert abs(ff.audio_lag(b, a) - 800) <= 2  # 100 ms at 8 kHz


def test_run_raises_with_stderr(tmp_path):
    try:
        ff.run(["-i", str(tmp_path / "missing.mp4"), str(tmp_path / "x.mp4")])
    except RuntimeError as e:
        assert "missing.mp4" in str(e)
    else:
        raise AssertionError("expected failure")
