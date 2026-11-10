"""Single-pass, frame-exact prep of one slot: one ffmpeg run, exactly `frames` frames at 30 fps, 1080x1920, no audio.
Filter order: decode -> fps -> source range -> speed -> fit -> motion -> colour -> exact length."""
import shutil
from pathlib import Path

from .. import config
from ..clients import ff

FPS, W, H = config.FPS, config.W, config.H
CRF = 14
MIN_SPEED = 0.5  # same floor as plan.build: slower than this looks broken, so hold the last frame instead
BLUR_SIGMA = 40
ZOOM_PER_FRAME = 0.0015  # legacy ShotSpec.animation; M5 replaces it with measured camera paths

# shortcut: approximations of Kinocut's colour presets as plain ffmpeg filters, replace when M8 matches colour stats
PRESETS = {
    "warm": "colorbalance=rs=0.08:gs=0.02:bs=-0.08:rm=0.06:bm=-0.06",
    "cool": "colorbalance=rs=-0.08:bs=0.08:rm=-0.05:bm=0.06",
    "vintage": "curves=preset=vintage",
    "cinematic": "colorbalance=rs=-0.1:bs=0.1:rh=0.08:bh=-0.08,eq=contrast=1.08",
    "noir": "hue=s=0,eq=contrast=1.15",
}


def fit_chain(fit: str) -> str:
    cover = f"scale={W}:{H}:force_original_aspect_ratio=increase:force_divisible_by=2,crop={W}:{H}"
    if fit != "blur_fit":
        return cover
    return (f"split[fa][fb];[fa]{cover},gblur=sigma={BLUR_SIGMA}[bg];"
            f"[fb]scale={W}:{H}:force_original_aspect_ratio=decrease:force_divisible_by=2[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2")


def motion_chain(animation: str, frames: int) -> str:
    if animation not in ("zoom_in", "zoom_out"):
        return ""
    z = f"1+{ZOOM_PER_FRAME}*on" if animation == "zoom_in" else f"1+{ZOOM_PER_FRAME}*({frames - 1}-on)"
    return f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={FPS}"


def grade_chain(g: dict | None) -> str:
    if not g:
        return ""
    parts = [PRESETS[g["preset"]]] if g.get("preset", "none") in PRESETS else []
    b, c, s = g.get("brightness", 0), g.get("contrast", 1), g.get("saturation", 1)
    if abs(b) > 1e-6 or abs(c - 1) > 1e-6 or abs(s - 1) > 1e-6:
        parts.append(f"eq=brightness={b}:contrast={c}:saturation={s}")
    return ",".join(parts)


def chain(params: dict, skip: int) -> str:
    frames, speed = params["frames"], float(params.get("speed") or 1.0)
    steps = [f"fps={FPS}", f"trim=start_frame={skip}", "setpts=PTS-STARTPTS"]
    if abs(speed - 1.0) > 1e-6:
        steps += [f"setpts=PTS/{max(MIN_SPEED, speed)}", f"fps={FPS}"]
    steps += [fit_chain(params.get("fit", "cover")), motion_chain(params.get("animation", "none"), frames),
              grade_chain(params.get("grade")), "setsar=1", "format=yuv420p",
              f"tpad=stop_mode=clone:stop={frames}"]  # source too short even after slowing: hold the last frame
    return ",".join(s for s in steps if s)


def prep(params: dict, out: Path) -> None:
    """params: path, in (seconds), frames, speed, fit, animation, grade; collage + tile_paths for collage shots."""
    out = Path(out)
    src, src_in = params["path"], float(params.get("in") or 0.0)
    tmp = None
    if params.get("collage") and params.get("tile_paths"):
        from ..stages import editor  # collage layout still comes from the legacy compositor

        tmp = out.with_suffix(".collage.mp4")
        editor.prep_clip({**params, "out": src_in + params["frames"] / FPS * float(params.get("speed") or 1.0)}, tmp)
        src, src_in, params = str(tmp), 0.0, {**params, "speed": 1.0, "fit": "cover"}
    try:
        coarse = max(0, int(src_in) - 1)  # whole seconds: exact in every timebase, so the frame index stays exact
        skip = int(round((src_in - coarse) * FPS))
        ff.run([*(["-ss", str(coarse)] if coarse else []), "-i", src, "-filter_complex", f"[0:v]{chain(params, skip)}[v]",
                "-map", "[v]", "-an", "-frames:v", str(params["frames"]), "-r", str(FPS), "-c:v", "libx264",
                "-preset", "veryfast", "-crf", str(CRF), "-pix_fmt", "yuv420p", "-video_track_timescale", "15360",
                str(out)])
    finally:
        if tmp:
            Path(tmp).unlink(missing_ok=True)
            shutil.rmtree(Path(tmp).with_suffix(".tmp"), ignore_errors=True)
