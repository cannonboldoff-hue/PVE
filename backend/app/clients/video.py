"""mcp-video (kinocut) client: every edit and every media probe goes through it.
It shells out to ffmpeg, so ffmpeg must be on PATH."""
import os
import shutil
import warnings
from functools import lru_cache
from pathlib import Path

warnings.filterwarnings("ignore", message=r"\[MERGE GUARDRAIL\]")


def _ensure_ffmpeg_on_path() -> None:
    if shutil.which("ffmpeg"):
        return
    # winget installs ffmpeg but a running shell may not have the new PATH yet
    for hit in Path.home().glob("AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/**/bin/ffmpeg.exe"):
        os.environ["PATH"] = str(hit.parent) + os.pathsep + os.environ["PATH"]
        return
    raise RuntimeError("ffmpeg not found; install FFmpeg (winget install Gyan.FFmpeg)")


_ensure_ffmpeg_on_path()


@lru_cache
def client():
    from mcp_video import Client

    return Client()


def info(path: str | Path) -> dict:
    i = client().info(str(path))
    w, h = (i.height, i.width) if i.rotation in (90, 270) else (i.width, i.height)  # displayed size
    return {"duration": float(i.duration), "width": w, "height": h, "fps": i.fps, "has_audio": bool(i.audio_codec)}


def scene_cuts(path: str | Path, threshold: float = 0.3) -> list[float]:
    d = client().detect_scenes(str(path), threshold=threshold, min_scene_duration=0.3)
    return [float(s["start"]) for s in d.scenes[1:]]


def tech_checks(path: str | Path, expect_duration: float) -> dict:
    """Layer-1 verifier checks. Each value is {ok, detail}."""
    i = info(path)
    q = client().quality_check(str(path))
    q = q if isinstance(q, dict) else q.model_dump()
    by = {c["name"]: c for c in q["checks"]}

    def check(name: str, label: str) -> dict:
        c = by.get(name)
        return {"ok": c["passed"] if c else True, "detail": c["message"] if c else f"{label} not measured"}

    out = {
        "duration": {"ok": abs(i["duration"] - expect_duration) <= max(0.5, expect_duration * 0.05),
                     "detail": f"{i['duration']:.2f}s vs planned {expect_duration:.2f}s"},
        "resolution": {"ok": (i["width"], i["height"]) == (1080, 1920), "detail": f"{i['width']}x{i['height']}"},
        # quality_check has no black-frame detector; brightness catches a black render, motion catches a frozen one
        "black_frames": check("brightness", "brightness"),
        "frozen_frames": check("temporal_motion", "motion"),
    }
    peak = (by.get("audio_levels") or {}).get("details", {}).get("true_peak")
    if not i["has_audio"]:
        out["audio"] = {"ok": False, "detail": "no audio track"}
    else:
        out["audio"] = {"ok": peak is None or peak < -0.1, "detail": f"true peak {peak} dBTP" if peak is not None else "ok"}
    return out


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
STILL_SECONDS = 5  # TwelveLabs needs at least ~4 s to index a clip


def image_to_clip(src: str | Path, out: str | Path) -> None:
    """Photo -> 5 s still clip, so photos go through the same index/match/render path as video (motion comes from the shot).
    Pillow applies the EXIF rotation and makes the size even and at least 720 px on the short side."""
    from PIL import Image, ImageOps

    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    f = max(1.0, 720 / min(im.size))
    w, h = (int(im.width * f) // 2 * 2, int(im.height * f) // 2 * 2)
    out = Path(out)
    jpg = out.with_suffix(".still.jpg")
    im.resize((w, h), Image.LANCZOS).save(jpg, quality=95)
    try:
        client().create_from_images(images=[str(jpg)] * (STILL_SECONDS * 30), fps=30.0, output=str(out), overwrite=True)
    finally:
        jpg.unlink(missing_ok=True)
