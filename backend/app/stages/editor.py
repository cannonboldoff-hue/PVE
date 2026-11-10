"""Video Editor worker: one function per node type, every edit done by mcp-video."""
import json
import math
import re
import shutil
from pathlib import Path

from .. import config
from ..clients import video
from ..models import Plan, PlanShot

XFADE_SECONDS = 0.4  # mcp-video's merge takes one transition duration for the whole timeline


def _even(n: int) -> int:
    return n + n % 2  # the encoder needs even crop and resize sizes


def _cover(c, step: str, i: dict, nxt, w: int = config.W, h: int = config.H) -> str:
    """Scale to fill w x h and crop the overflow."""
    f = max(w / i["width"], h / i["height"])
    nw, nh = _even(math.ceil(i["width"] * f)) + 2, _even(math.ceil(i["height"] * f)) + 2  # +2 px: resize letterboxes on rounding
    step = c.resize(step, width=nw, height=nh, output=nxt(), overwrite=True).output_path
    return c.crop(step, width=w, height=h, x=_even((nw - w) // 2), y=_even((nh - h) // 2), output=nxt(), overwrite=True).output_path


def _blur_fit(c, step: str, i: dict, nxt) -> str:
    """Whole frame, uncropped, centred over a blurred copy of itself that fills the 9:16 canvas."""
    bg = c.blur(_cover(c, step, i, nxt), radius=30, strength=2, output=nxt(), overwrite=True).output_path
    f = min(config.W / i["width"], config.H / i["height"])
    fg = c.resize(step, width=_even(int(i["width"] * f)), height=_even(int(i["height"] * f)), output=nxt(), overwrite=True).output_path
    return c.overlay_video(bg, fg, position="center", opacity=1.0, output=nxt(), overwrite=True).output_path


ZOOM_PER_FRAME = 0.0015


def _animate(c, step: str, animation: str, nxt) -> str:
    if animation == "zoom_in":
        return c.filter(step, "ken_burns", params={"zoom_speed": ZOOM_PER_FRAME}, output=nxt(), overwrite=True).output_path
    if animation == "zoom_out":  # zoom in on the reversed clip, then reverse back (audio is reversed twice, so it is unchanged)
        r = c.reverse(step, output=nxt(), overwrite=True).output_path
        r = c.filter(r, "ken_burns", params={"zoom_speed": ZOOM_PER_FRAME}, output=nxt(), overwrite=True).output_path
        return c.reverse(r, output=nxt(), overwrite=True).output_path
    return step


def _grade(c, step: str, g: dict | None, nxt) -> str:
    """Colour look: an optional preset, then brightness / contrast / saturation where they differ from neutral."""
    if not g:
        return step
    if g["preset"] != "none":
        step = c.color_grade(step, preset=g["preset"], output=nxt(), overwrite=True).output_path
    for name, level, neutral in (("brightness", g["brightness"], 0), ("contrast", g["contrast"], 1), ("saturation", g["saturation"], 1)):
        if abs(level - neutral) > 1e-6:
            step = c.filter(step, name, params={"level": level}, output=nxt(), overwrite=True).output_path
    return step


# tile boxes (x, y, w, h) on the 1080x1920 canvas, by tile count
COLLAGE_BOXES = {
    2: [(90, 170, 900, 820), (90, 1000, 900, 820)],
    3: [(90, 170, 900, 760), (90, 960, 440, 760), (550, 960, 440, 760)],
    4: [(60, 160, 450, 800), (570, 160, 450, 800), (60, 980, 450, 800), (570, 980, 450, 800)],
    5: [(60, 150, 450, 740), (570, 150, 450, 740), (60, 980, 290, 740), (395, 980, 290, 740), (730, 980, 290, 740)],
    6: [(60, 130, 450, 520), (570, 130, 450, 520), (60, 730, 450, 520), (570, 730, 450, 520), (60, 1330, 450, 520), (570, 1330, 450, 520)],
}
FRAME = 12  # px of white border around a tile


def _collage(c, params: dict, length: float, nxt, tmp: Path) -> str:
    """Several clips as tilted, framed tiles over a coloured background (composite_layers)."""
    col = params["collage"]
    sources = [params["path"], *params["tile_paths"]][: col["tiles"]]
    boxes = COLLAGE_BOXES[len(sources)] if len(sources) in COLLAGE_BOXES else COLLAGE_BOXES[min(COLLAGE_BOXES, key=lambda k: abs(k - len(sources)))]
    layers = []
    for k, (src, (x, y, w, h)) in enumerate(zip(sources, boxes)):
        start = params["in"] if k == 0 else 0.0
        t = c.trim(src, start=start, duration=length, output=nxt(), accurate=True, overwrite=True).output_path
        t = _cover(c, t, video.info(t), nxt, w, h)
        name = f"tile{k}.mp4"
        shutil.move(t, tmp / name)
        rot = col["tilt"] * (1 if k % 2 == 0 else -1)
        cx, cy = x + w / 2, y + h / 2  # with pivot "center", position is the tile's centre
        if col["border"]:
            layers.append({"id": f"frame{k}", "type": "solid", "color": "#FFFFFF", "position": {"x": cx, "y": cy},
                           "width": w + 2 * FRAME, "height": h + 2 * FRAME, **({"rotation": rot, "pivot": "center"} if rot else {})})
        layers.append({"id": f"tile{k}", "type": "video", "src": name, "position": {"x": cx, "y": cy}, "width": w, "height": h,
                       **({"rotation": rot, "pivot": "center"} if rot else {})})
        if not col["border"] and not rot:  # position is a top-left corner when there is no rotation pivot
            layers[-1]["position"] = {"x": x, "y": y}
        elif col["border"] and not rot:
            layers[-2]["position"] = {"x": x - FRAME, "y": y - FRAME}
            layers[-1]["position"] = {"x": x, "y": y}
    spec = {"canvas": {"width": config.W, "height": config.H, "fps": config.FPS, "duration": length, "background": col["background"]},
            "layers": layers}
    (tmp / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    return c.composite_layers(str(tmp / "spec.json"), output=nxt(), overwrite=True).output_path


def prep_clip(params: dict, out: Path) -> None:
    """Trim, speed, fit to 1080x1920 (fill, blurred backdrop or collage), animate, colour grade, and guarantee an
    audio track (silent when there is none) so merge never sees a mismatch."""
    c = video.client()
    src_len = params["out"] - params["in"]
    out_len = src_len / params["speed"]
    tmp = out.parent / f"{out.stem}.tmp"
    tmp.mkdir(exist_ok=True)
    n = 0

    def nxt() -> str:
        nonlocal n
        n += 1
        return str(tmp / f"{n}.mp4")

    try:
        if params.get("collage") and params.get("tile_paths"):
            step, has_audio = _collage(c, params, out_len, nxt, tmp), False
        else:
            step = c.trim(params["path"], start=params["in"], duration=src_len, output=nxt(), accurate=True, overwrite=True).output_path
            if params["speed"] != 1.0:
                step = c.speed(step, factor=params["speed"], output=nxt(), overwrite=True).output_path
            i = video.info(step)  # after the re-encode, so rotation metadata is already applied
            step, has_audio = (_blur_fit if params.get("fit") == "blur_fit" else _cover)(c, step, i, nxt), i["has_audio"]
        step = _animate(c, step, params.get("animation", "none"), nxt)
        step = _grade(c, step, params.get("grade"), nxt)
        if not has_audio:
            wav = str(tmp / "silence.wav")
            c.audio_synthesize(wav, waveform="sine", frequency=440, duration=out_len + 1, volume=0.0, overwrite=True)
            step = c.add_audio(step, wav, output=nxt(), overwrite=True).output_path
        shutil.move(step, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


BS = "\\"
AN = {"top": 8, "center": 5, "bottom": 2}  # ASS alignment codes
Y = {"top": 330, "center": 960, "bottom": 1590}  # anchor y on the 1920 canvas (330 px safe margin)


def _bgr(hex_: str) -> str:
    h = hex_.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&"  # ASS colours are blue-green-red


def _entrance(animation: str, position: str) -> str:
    y = Y[position]
    return {
        "none": "",
        "fade": f"{BS}fad(180,180)",
        "pop": f"{BS}fscx60{BS}fscy60{BS}t(0,200,{BS}fscx100{BS}fscy100){BS}fad(100,120)",
        "slide_up": f"{BS}move(540,{y + 70},540,{y},0,250){BS}fad(150,150)",
    }[animation]


def _caption_text(s: PlanShot) -> str:
    st = s.caption_style
    text = s.caption.upper() if st.uppercase else s.caption
    text = text.replace(BS, "").replace("{", "(").replace("}", ")").replace("\n", BS + "N")
    for w in st.emphasis_words:
        if w.strip():
            text = re.sub(rf"(?i)\b({re.escape(w.strip())})\b",
                          lambda m: f"{{{BS}c{_bgr(st.emphasis_color)}}}{m.group(1)}{{{BS}c{_bgr(st.color)}}}", text)
    tags = (f"{BS}an{AN[st.position]}{BS}fn{st.font}{BS}fs{st.size}{BS}c{_bgr(st.color)}{BS}3c{_bgr(st.outline_color)}"
            f"{BS}bord{st.outline}{BS}b{1 if st.bold else 0}{_entrance(s.caption_animation, st.position)}")
    return f"{{{tags}}}{text}"


def _ass(plan: Plan, starts: list[float]) -> str:
    def t(x: float) -> str:
        h, rem = divmod(x, 3600)
        m, sec = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{sec:05.2f}"

    head = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,1,2,90,90,330,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = [f"Dialogue: 0,{t(start + s.cap_start)},{t(start + s.cap_end)},Default,,0,0,0,,{_caption_text(s)}"
             for s, start in zip(plan.shots, starts) if s.caption.strip()]
    return head + "\n".join(lines) + "\n"


def timeline(plan: Plan, durs: list[float]) -> tuple[float, list[float], float]:
    """(crossfade seconds, start time of each clip, total length). Hard cuts overlap nothing."""
    cuts = [s.transition == "cut" for s in plan.shots[:-1]]
    runs, acc = [], durs[0]  # lengths of the clip runs between crossfades
    for i, cut in enumerate(cuts):
        if cut:
            acc += durs[i + 1]
        else:
            runs.append(acc)
            acc = durs[i + 1]
    runs.append(acc)
    td = min(XFADE_SECONDS, 0.5 * min(runs)) if len(runs) > 1 else 0.0
    starts = [0.0]
    for i, cut in enumerate(cuts):
        starts.append(starts[i] + durs[i] - (0.0 if cut else td))
    return td, starts, sum(durs) - td * (len(runs) - 1)


def assemble(plan: Plan, prep_paths: list[Path], workdir: Path, out: Path) -> float:
    """Join runs of cut clips, crossfade between runs, duck looped music under the clip audio, burn ASS captions.
    Returns the planned length (the verifier compares the real file against it)."""
    c = video.client()
    durs = [video.info(p)["duration"] for p in prep_paths]
    td, starts, total = timeline(plan, durs)
    tmp = workdir / "assemble_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        runs, names = [[0]], []
        for i, s in enumerate(plan.shots[:-1]):
            if s.transition == "cut":
                runs[-1].append(i + 1)
            else:
                names.append(s.transition)
                runs.append([i + 1])
        segs = []
        for k, r in enumerate(runs):
            paths = [str(prep_paths[i]) for i in r]
            segs.append(paths[0] if len(paths) == 1 else c.merge(paths, output=str(tmp / f"run{k}.mp4"), overwrite=True).output_path)
        step = segs[0]
        if len(segs) > 1:
            step = c.merge(segs, output=str(tmp / "xfade.mp4"), transitions=names, transition_duration=td, overwrite=True).output_path

        if plan.music_path:
            # duck_audio can't loop, so build a full-length looped bed first
            replace = plan.music_mode == "replace"
            bedvid = c.add_audio(step, plan.music_path, mix=False, duration_policy="loop_audio",
                                 volume=plan.music_volume if replace else 1.0, output=str(tmp / "bedvid.mp4"), overwrite=True)
            if replace:  # the song is the whole soundtrack; clip audio is dropped
                step = bedvid.output_path
            else:
                bed = c.extract_audio(bedvid.output_path, output=str(tmp / "bed.wav"), format="wav", overwrite=True)
                step = c.duck_audio(step, bed.output_path, output=str(tmp / "ducked.mp4"), music_volume=plan.music_volume,
                                    threshold=0.03, ratio=8.0, attack=20.0, release=300.0, overwrite=True).output_path

        if plan.captions and any(s.caption.strip() for s in plan.shots):
            ass = tmp / "captions.ass"
            ass.write_text(_ass(plan, starts), encoding="utf-8")
            step = c.subtitles(step, str(ass), output=str(tmp / "captioned.mp4"), overwrite=True).output_path
        shutil.copy2(step, out)  # copy: step may be a cached prep clip
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return total
