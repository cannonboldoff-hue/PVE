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


ENGINE_TRANSITIONS = {"whip_left", "whip_right", "whip_up", "whip_down"}  # drawn by the overlay engine (M9)


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
EFFECTS = {"flash": "drawbox", "rgb_split": "rgbashift", "blur": "gblur", "vignette": "vignette", "grain": "noise"}
EFFECT_LOSS = {"glow": "glow: not drawn yet (overlay engine, M9)", "scanlines": "scanlines: not drawn yet",
               "glitch": "glitch: not drawn yet (overlay engine, M9)", "zoom_punch": "zoom punch: not drawn yet",
               "shake": "shake: reproduced by the camera path, not as an effect", "other": "unknown effect: not drawn"}


def effect(kind: str) -> tuple[str, str]:
    if kind in EFFECTS:
        return f"ffmpeg:{EFFECTS[kind]}", ""
    return "", EFFECT_LOSS.get(kind, EFFECT_LOSS["other"])


def effect_filter(e: dict) -> str:
    """ffmpeg filter for one Effect dict, enabled on its output frames only."""
    on = f"enable='between(n,{e['start']},{e['end'] - 1})'"
    kind, k = e["type"]["value"], float(e.get("strength") or 1.0)
    if kind == "flash":
        return f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{min(1.0, max(0.2, k * 1.9)):.2f}:t=fill:{on}"
    if kind == "rgb_split":
        px = int(round((e.get("params") or {}).get("px", 2) * 1080 / 160))
        return f"rgbashift=rh=-{px}:bh={px}:{on}"
    if kind == "blur":
        return f"gblur=sigma=12:{on}"
    if kind == "vignette":
        return f"vignette=PI/4:{on}"
    if kind == "grain":
        return f"noise=alls=20:allf=t:{on}"
    return ""
