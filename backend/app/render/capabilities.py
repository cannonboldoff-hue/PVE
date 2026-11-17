"""Template feature -> (engine, name) the renderer uses, and what is lost when only a nearby feature exists.
The template never names an engine; extraction fills Transition.render / .loss from here."""

# exact equivalents in ffmpeg's xfade (names checked against this build, docs/mvp-plan.md section 8)
TRANSITIONS = {
    "fade": "fade", "dissolve": "dissolve", "fade_black": "fadeblack", "fade_white": "fadewhite",
    "wipe_left": "wipeleft", "wipe_right": "wiperight", "wipe_up": "wipeup", "wipe_down": "wipedown",
    "slide_left": "coverleft", "slide_right": "coverright", "slide_up": "coverup", "slide_down": "coverdown",
    "push_left": "slideleft", "push_right": "slideright", "push_up": "slideup", "push_down": "slidedown",
    "zoom_in": "zoomin",
}
# nearest basic transition until the overlay engine draws the real one (M9)
DOWNGRADES = {
    "whip_left": ("smoothleft", "whip: no motion blur"), "whip_right": ("smoothright", "whip: no motion blur"),
    "whip_up": ("smoothup", "whip: no motion blur"), "whip_down": ("smoothdown", "whip: no motion blur"),
    "zoom_out": ("fade", "zoom out: shown as a fade"), "spin": ("radial", "spin: shown as a radial wipe"),
    "glitch": ("pixelize", "glitch: shown as pixelize"), "blur": ("hblur", "blur: horizontal blur only"),
    "other": ("fade", "unknown transition: shown as a fade"),
}


ENGINE_TRANSITIONS = {"whip_left", "whip_right", "whip_up", "whip_down", "spin", "zoom_out", "glitch"}  # overlay engine


def engine_available() -> bool:
    """An overlay engine can run here (HyperFrames CLI pinned under overlay/hyperframes)."""
    import os

    cmd = os.environ.get("MCP_VIDEO_HYPERFRAMES_COMMAND", "")
    return bool(cmd) and os.path.exists(cmd)


def transition(kind: str) -> tuple[str, str]:
    """(render, loss) for a TransitionType. render is "ffmpeg:<xfade name>" or "" for a hard cut."""
    if kind == "cut":
        return "", ""
    if kind in TRANSITIONS:
        return f"ffmpeg:{TRANSITIONS[kind]}", ""
    if kind in ENGINE_TRANSITIONS and engine_available():
        return f"overlay:{kind}", ""
    name, loss = DOWNGRADES.get(kind, DOWNGRADES["other"])
    return f"ffmpeg:{name}", loss


# effects drawn in the final assemble pass, over absolute frames [start, end)
EFFECTS = {"flash": "drawbox", "rgb_split": "rgbashift", "blur": "gblur", "vignette": "vignette", "grain": "noise",
           "glow": "glow", "scanlines": "geq", "glitch": "glitch"}
# drawn as part of the slot's camera path (render/shot.py), not as a filter over the finished frame
CAMERA_EFFECTS = {"zoom_punch", "shake"}
EFFECT_LOSS = {"other": "unknown effect: not drawn"}


def effect(kind: str) -> tuple[str, str]:
    if kind in EFFECTS:
        return f"ffmpeg:{EFFECTS[kind]}", ""
    if kind in CAMERA_EFFECTS:
        return "camera", ""
    return "", EFFECT_LOSS.get(kind, EFFECT_LOSS["other"])


def effect_filter(e: dict) -> str:
    """ffmpeg filter for one Effect dict, enabled on its output frames only."""
    a, b = e["start"], e["end"] - 1
    on = f"enable='between(n,{a},{b})'"
    kind, k = e["type"]["value"], float(e.get("strength") or 1.0)
    p = e.get("params") or {}
    if kind == "flash":
        return f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{min(1.0, max(0.2, k * 1.9)):.2f}:t=fill:{on}"
    if kind == "rgb_split":
        px = min(255, int(round(p.get("px", 2) * 1080 / 160)))  # rgbashift rejects shifts beyond +-255
        return f"rgbashift=rh=-{px}:bh={px}:{on}"
    if kind == "blur":
        return f"gblur=sigma={float(p.get('sigma', 12)):.1f}:{on}"
    if kind == "vignette":
        return f"vignette={float(p.get('angle', 0.785)):.3f}:{on}"
    if kind == "grain":
        return f"noise=alls={int(p.get('amount', 20))}:allf=t:{on}"
    if kind == "glow":  # screen-blend a blurred copy of the bright parts back over the frame
        sig, tag = float(p.get("sigma", 18)), f"g{a}_{b}"  # labels unique per effect window
        return (f"split[{tag}a][{tag}b];[{tag}b]curves=all='0/0 0.6/0.1 1/1',gblur=sigma={sig:.1f}[{tag}c];"
                f"[{tag}a][{tag}c]blend=all_mode=screen:all_opacity={min(1.0, 0.6 * k):.2f}:{on}")
    if kind == "scanlines":  # darken every period-th pair of rows
        per = max(2, int(p.get("period", 4)))
        dark = min(0.9, 0.35 * k)
        return f"geq=lum='lum(X,Y)*(1-{dark:.2f}*lt(mod(Y,{per}),{per // 2}))':cb='cb(X,Y)':cr='cr(X,Y)':{on}"
    if kind == "glitch":  # colour split plus a sideways jump of horizontal bands, changing every 2 frames
        px = min(255, int(round(p.get("px", 12))))
        return (f"rgbashift=rh=-{px}:bh={px}:{on},"
                f"geq=lum='lum(X+{px * 3}*lt(mod(Y+37*floor(N/2),97),23),Y)':cb='cb(X,Y)':cr='cr(X,Y)':{on}")
    return ""
