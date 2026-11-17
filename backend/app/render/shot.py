"""Single-pass, frame-exact prep of one slot: one ffmpeg run, exactly `frames` frames at 30 fps, 1080x1920, no audio.
Filter order: decode -> fps -> source range -> speed -> fit -> motion -> colour -> exact length."""
import math
import shutil
import subprocess
from pathlib import Path

from .. import config
import numpy as np

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


UP = 2  # zoompan crops in whole input pixels: upscale first so a step is half an output pixel
# shortcut: UP=2 leaves sub-pixel stepping on very slow moves; raise to 4 if a visual check shows it (4x slower)


def _lerp(keys: list[tuple[int, float]]) -> str:
    """Piecewise-linear expression in zoompan's output frame number `on`."""
    if len(keys) == 1:
        return f"{keys[0][1]:.6f}"
    expr = f"{keys[-1][1]:.6f}"
    for (f0, v0), (f1, v1) in reversed(list(zip(keys[:-1], keys[1:]))):
        seg = f"{v0:.6f}+({v1 - v0:.6f})*(on-{f0})/{max(1, f1 - f0)}"
        expr = f"if(lt(on,{f1}),{seg},{expr})"
    return expr


def shake_windows(shake: dict | list | None) -> list[dict]:
    """Shake as a list of {amp, hz[, start, end]} (frames relative to the slot). A plain dict is one window over the
    whole slot; a window without start / end is ungated."""
    ws = [shake] if isinstance(shake, dict) else list(shake or [])
    return [w for w in ws if float(w.get("amp") or 0) > 0 and float(w.get("hz") or 0) > 0]


def _jitter(windows: list[dict]) -> tuple[str, str]:
    """Deterministic shake offsets: two incommensurate sines per window at its amplitude and rate, gated to it."""
    jx, jy = [], []
    for w in windows:
        amp, hz = float(w["amp"]), float(w["hz"])
        gate = f"between(on,{int(w['start'])},{int(w['end']) - 1})*" if "start" in w and "end" in w else ""
        jx.append(f"{gate}{amp:.5f}*(sin(2*PI*{hz:.3f}*on/{FPS})+0.6*sin(2*PI*{hz * 1.7:.3f}*on/{FPS}+1.3))/1.6")
        jy.append(f"{gate}{amp:.5f}*(sin(2*PI*{hz * 1.3:.3f}*on/{FPS}+0.7)+0.6*sin(2*PI*{hz * 2.1:.3f}*on/{FPS}))/1.6")
    return "+".join(jx), "+".join(jy)


def camera_chain(path: list[dict], shake: dict | list | None, w_out: int = W, h_out: int = H) -> str:
    """Reproduce a measured view path (ir.Key dicts: frame relative to the slot, box = visible region) and shake.
    The path is rescaled so its widest view is the whole frame (a zoom out starts zoomed in)."""
    windows = shake_windows(shake)
    amp = max((float(w["amp"]) for w in windows), default=0.0)
    ws = [k["box"]["w"] for k in path] or [1.0]
    m = max(ws) / max(1e-6, 1 - 4 * amp)  # shake needs a margin inside the frame
    keys = []
    for k in path:
        w = k["box"]["w"] / m
        cx, cy = k["box"]["x"] + k["box"]["w"] / 2, k["box"]["y"] + k["box"]["h"] / 2
        cx, cy = min(max(cx, w / 2), 1 - w / 2), min(max(cy, w / 2), 1 - w / 2)
        keys.append((k["frame"], w, cx, cy))
    wexp = _lerp([(f, w) for f, w, _, _ in keys])
    cxe, cye = _lerp([(f, c) for f, _, c, _ in keys]), _lerp([(f, c) for f, _, _, c in keys])
    if windows:
        jx, jy = _jitter(windows)
        cxe, cye = f"({cxe})+{jx}", f"({cye})+{jy}"
    return (f"scale={w_out * UP}:{h_out * UP},zoompan=z='1/({wexp})':x='(({cxe})-({wexp})/2)*iw':"
            f"y='(({cye})-({wexp})/2)*ih':d=1:s={w_out}x{h_out}:fps={FPS}")


def motion_chain(animation: str, frames: int, path: list[dict] | None = None, shake: dict | list | None = None,
                 w_out: int = W, h_out: int = H) -> str:
    if path or shake_windows(shake):
        return camera_chain(path or [{"frame": 0, "box": {"x": 0, "y": 0, "w": 1, "h": 1}}], shake, w_out, h_out)
    if animation not in ("zoom_in", "zoom_out"):
        return ""
    z = f"1+{ZOOM_PER_FRAME}*on" if animation == "zoom_in" else f"1+{ZOOM_PER_FRAME}*({frames - 1}-on)"
    return f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={w_out}x{h_out}:fps={FPS}"


def grade_chain(g: dict | None) -> str:
    if not g:
        return ""
    parts = [PRESETS[g["preset"]]] if g.get("preset", "none") in PRESETS else []
    b, c, s = g.get("brightness", 0), g.get("contrast", 1), g.get("saturation", 1)
    if abs(b) > 1e-6 or abs(c - 1) > 1e-6 or abs(s - 1) > 1e-6:
        parts.append(f"eq=brightness={b}:contrast={c}:saturation={s}")
    return ",".join(parts)


def pieces(frames: int, curve=None, freeze=None) -> list[tuple[int, int, float, float]]:
    """Output frames [0, frames) as constant-speed pieces (out start, out end, source position at start, speed).
    curve: [(position 0..1 in the slot, factor)], piecewise constant; freeze: [(start, end)] output frames that hold
    one frame (speed 0, no footage used)."""
    curve = sorted(curve or [(0.0, 1.0)])
    freeze = [(max(0, a), min(frames, b)) for a, b in (freeze or []) if b > a]
    cuts = {0, frames, *(round(p * frames) for p, _ in curve), *(x for f in freeze for x in f)}
    cuts = sorted(c for c in cuts if 0 <= c <= frames)
    out, src, was_held = [], 0.0, False
    for a, b in zip(cuts[:-1], cuts[1:]):
        held = any(fa <= a < fb for fa, fb in freeze)
        speed = 0.0 if held else next(f for p, f in reversed(curve) if round(p * frames) <= a)
        if was_held and not held:  # frames [fa, fb) show the held frame; frame fb already moves on by one step
            src += speed
        out.append((a, b, src, speed))
        src += speed * (b - a)
        was_held = held
    return out


def footage(frames: int, curve=None, freeze=None) -> int:
    """Source frames a slot consumes: the area under its speed curve, freezes excluded."""
    a, b, src, s = pieces(frames, curve, freeze)[-1]
    return math.ceil(src + s * (b - a) - 1e-6)  # includes the step a held frame moves on by


def src_at(o: int, pcs: list[tuple[int, int, float, float]]) -> float:
    a, b, src, s = next(p for p in pcs if p[0] <= o < p[1]) if o < pcs[-1][1] else pcs[-1]
    return src + s * (min(o, b) - a)


def timing_chain(pcs: list[tuple[int, int, float, float]]) -> str:
    """setpts placing source frame N (30 fps) at its output time; fps=30 then fills freezes by repeating the frame
    before them. A freeze at the very start holds the first frame (tpad)."""
    moving = [p for p in pcs if p[3] > 0]
    if all(abs(p[3] - 1) < 1e-9 for p in pcs):
        return ""
    hold = pcs[0][1] if pcs[0][3] == 0 else 0
    expr = "0"
    for a, b, src, s in moving:  # later pieces wrap earlier ones: the outermost test is the last piece
        expr = f"if(gte(N,{src:.4f}),{a - hold}+(N-{src:.4f})/{s:.6f}-0.001,{expr})"
    # fps keeps the last frame of each output slot; with round=up slot o ends at o, so it keeps floor(src_at(o))
    # settb first: after fps=30 the timebase is 1/30 and fractional output times would floor to whole frames
    out = f"settb=1/30000,setpts='max(0,{expr})/(FRAME_RATE*TB)',fps={FPS}:round=up"
    return out + (f",tpad=start_mode=clone:start={hold}" if hold else "")


def chain(params: dict, skip: int, size: tuple[int, int] | None = None) -> str:
    """One source through speed, fit, reverse, motion and colour. size: a layout tile (bw, bh) instead of the
    whole frame; tiles are covered into their box and graded once on the composite, not here."""
    frames, speed = params["frames"], max(MIN_SPEED, float(params.get("speed") or 1.0))
    curve = [(p, f * speed) for p, f in (params.get("speed_curve") or [(0.0, 1.0)])]
    pcs = pieces(frames, curve, params.get("freeze"))
    need = footage(frames, curve, params.get("freeze")) + 1
    bw, bh = size or (W, H)
    fit = fit_chain(params.get("fit", "cover")) if size is None else \
        f"scale={bw}:{bh}:force_original_aspect_ratio=increase:force_divisible_by=2,crop={bw}:{bh}"
    steps = [f"fps={FPS}", f"trim=start_frame={skip}:end_frame={skip + need}", "setpts=PTS-STARTPTS",
             fit, "reverse" if params.get("reverse") else "", timing_chain(pcs)]
    steps += [
              motion_chain(params.get("animation", "none"), frames, params.get("camera_path"), params.get("shake"), bw, bh),
              "" if size else params.get("colour_filter") or grade_chain(params.get("grade")),
              "" if size else mask_chain(params.get("mask")), "setsar=1",
              "format=yuv420p",
              f"tpad=stop_mode=clone:stop={frames}"]  # source too short even after slowing: hold the last frame
    return ",".join(s for s in steps if s)


def _yuv(hex_: str) -> tuple[int, int, int]:
    """BT.601 limited-range Y, Cb, Cr of an #RRGGBB colour (what yuv420p stores)."""
    r, g, b = (int(hex_[k:k + 2], 16) / 255 for k in (1, 3, 5))
    return (round(16 + 65.481 * r + 128.553 * g + 24.966 * b), round(128 - 37.797 * r - 74.203 * g + 112 * b),
            round(128 + 112 * r - 93.786 * g - 18.214 * b))


def _lerp_n(keys: list[tuple[int, float]]) -> str:
    return _lerp(keys).replace("on", "N")


def mask_chain(mask: dict | None) -> str:
    """Show the footage only inside the mask's shape; outside, the reference's flat background colour. The box moves
    between keys (slot-relative frames). geq expressions use plane-normalised X/W, Y/H, so chroma planes agree."""
    keys = sorted((mask or {}).get("keys") or [], key=lambda k: k["frame"])
    if not keys:
        return ""
    cx = _lerp_n([(k["frame"], k["box"]["x"] + k["box"]["w"] / 2) for k in keys])
    cy = _lerp_n([(k["frame"], k["box"]["y"] + k["box"]["h"] / 2) for k in keys])
    rx = _lerp_n([(k["frame"], k["box"]["w"] / 2) for k in keys])
    ry = _lerp_n([(k["frame"], k["box"]["h"] / 2) for k in keys])
    u, v = f"(X/W-({cx}))/({rx})", f"(Y/H-({cy}))/({ry})"
    inside = {
        "rect": f"lte(abs({u}),1)*lte(abs({v}),1)",
        "rounded_rect": f"lte(pow(abs({u}),4)+pow(abs({v}),4),1)",
        "heart": f"lte(pow(pow(1.2*{u},2)+pow(0.2-1.2*{v},2)-1,3)-pow(1.2*{u},2)*pow(0.2-1.2*{v},3),0)",
    }.get(mask.get("shape") or "", f"lte(pow({u},2)+pow({v},2),1)")  # circle / ellipse
    y, cb, cr = _yuv(mask.get("bg") or "#000000")
    return (f"format=yuv420p,geq=lum='if({inside},lum(X,Y),{y})':cb='if({inside},cb(X,Y),{cb})':"
            f"cr='if({inside},cr(X,Y),{cr})'")


TILE_KEYS = ("speed_curve", "freeze", "reverse", "camera_path", "shake")


def tile_params(params: dict, k: int) -> dict:
    """Box k's own timing and motion from params["tile_params"][k] (measured per box); without it box 0 takes the
    slot's and the other boxes play at 1x, still. The plan's slow-down factor (short clip) stays with box 0."""
    own = (params.get("tile_params") or [])[k:k + 1]
    if k == 0 and not own:
        return params
    base = {x: v for x, v in params.items() if x not in TILE_KEYS and (k == 0 or x != "animation")}
    return {**base, "speed": params.get("speed", 1.0) if k == 0 else 1.0, **(own[0] if own else {})}


MAX_SHIFT = 0.35  # colour match: contrast / saturation factors stay within 1 +- this, brightness within +- this / 2
WARM_GAIN = 0.6  # colorbalance shift per unit of Lab b* (or a*) difference / 128


def sample(path: str, src_in: float, seconds: float, n: int = 8) -> np.ndarray:
    """n frames of the source range, small, RGB (for colour statistics)."""
    step = max(seconds / n, 1 / FPS)
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{src_in:.3f}", "-i", path,
                        "-t", f"{max(seconds, 1 / FPS):.3f}", "-vf", f"fps={1 / step:.4f},scale=160:-2:flags=area",
                        "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    v = ff.video_stream(ff.probe(path))
    h = int(round(160 * int(v["height"]) / int(v["width"]) / 2)) * 2
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, 160, 3) if p.stdout else np.zeros((0, h, 160, 3), np.uint8)


def colour_filter(target: dict, frames: np.ndarray) -> str:
    """eq + colorbalance moving a clip's Lab mean / spread and saturation toward the target, limited to MAX_SHIFT."""
    from ..evidence.colour import stats

    if not len(frames):
        return ""
    c = stats(frames)
    clamp = lambda v, lo, hi: min(hi, max(lo, v))  # noqa: E731
    con = clamp(target["l_std"] / max(1.0, c["l_std"]), 1 - MAX_SHIFT, 1 + MAX_SHIFT)
    bri = clamp(((target["l_mean"] - 128) - (c["l_mean"] - 128) * con) / 255, -MAX_SHIFT / 2, MAX_SHIFT / 2)
    sat = clamp(target["saturation"] / max(0.02, c["saturation"]), 1 - MAX_SHIFT, 1 + MAX_SHIFT)
    warm = clamp((target["b_mean"] - c["b_mean"]) / 128 * WARM_GAIN * 4, -MAX_SHIFT, MAX_SHIFT)
    mag = clamp((target["a_mean"] - c["a_mean"]) / 128 * WARM_GAIN * 4, -MAX_SHIFT, MAX_SHIFT)
    out = f"eq=brightness={bri:.4f}:contrast={con:.4f}:saturation={sat:.4f}"
    if abs(warm) > 0.01 or abs(mag) > 0.01:  # +b* is yellow (more red and green, less blue); +a* is magenta
        out += f",colorbalance=rm={warm:.3f}:gm={-mag + warm / 2:.3f}:bm={-warm:.3f}"
    return out


def layout_graph(params: dict, inputs: list[tuple[str, float]], frames: int) -> str:
    """Several sources into the slot's content boxes over a black canvas (split screen, picture in picture,
    collage, letterbox). Input k fills box k; the main clip is input 0."""
    if params.get("fit") == "blur_fit":  # blurred fill: the main clip, covered and blurred, behind its box
        bg = len(params["layout_boxes"])  # the main clip again, as an extra input (an input label is read once)
        _, skip0 = inputs[bg]
        parts = [f"[{bg}:v]fps={FPS},trim=start_frame={skip0},setpts=PTS-STARTPTS,{fit_chain('cover')},"
                 f"gblur=sigma={BLUR_SIGMA},tpad=stop_mode=clone:stop={frames}[c0]"]
    else:
        parts = [f"color=c=black:s={W}x{H}:r={FPS}:d={frames / FPS + 1:.3f}[c0]"]
    last = "c0"
    for k, (box, (_, skip)) in enumerate(zip(params["layout_boxes"], inputs)):
        bw, bh = max(2, round(box["w"] * W / 2) * 2), max(2, round(box["h"] * H / 2) * 2)
        x, y = round(box["x"] * W), round(box["y"] * H)
        parts.append(f"[{k}:v]" + chain({**tile_params(params, k), "frames": frames}, skip, (bw, bh)) + f"[s{k}]")
        parts.append(f"[{last}][s{k}]overlay={x}:{y}:eof_action=repeat[c{k + 1}]")
        last = f"c{k + 1}"
    tail = [params.get("colour_filter") or grade_chain(params.get("grade")), "setsar=1", "format=yuv420p"]
    parts.append(f"[{last}]" + ",".join(t for t in tail if t) + "[v]")
    return ";".join(parts)


def prep(params: dict, out: Path) -> None:
    """params: path, in (seconds), frames, speed, fit, animation, grade; collage + tile_paths for collage shots;
    layout_boxes (+ tile_paths) for split / pip / collage / letterbox; colour (ColourTarget dict)."""
    out = Path(out)
    src, src_in = params["path"], float(params.get("in") or 0.0)
    if params.get("colour"):
        need = footage(params["frames"], params.get("speed_curve"), params.get("freeze"))
        params = {**params, "colour_filter": colour_filter(params["colour"], sample(src, src_in, need / FPS))}
    if params.get("layout_boxes"):
        boxes = params["layout_boxes"]
        tiles = list(params.get("tile_paths") or [])
        tin = [float(tp.get("in") or 0.0) for tp in params.get("tile_params") or []]
        srcs = [(src, src_in)] + [(tiles[k - 1], tin[k] if k < len(tin) else 0.0) if k - 1 < len(tiles) else (src, src_in)
                                  for k in range(1, len(boxes))]  # too few clips: the main clip fills the rest
        if params.get("fit") == "blur_fit":
            srcs.append(srcs[0])
        args, inputs = [], []
        for path, t0 in srcs:
            coarse = max(0, int(t0) - 1)
            args += [*(["-ss", str(coarse)] if coarse else []), "-i", path]
            inputs.append((path, int(round((t0 - coarse) * FPS))))
        ff.run([*args, "-filter_complex", layout_graph(params, inputs, params["frames"]), "-map", "[v]", "-an",
                "-frames:v", str(params["frames"]), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                "-crf", str(CRF), "-pix_fmt", "yuv420p", "-video_track_timescale", "15360", str(out)])
        return
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
