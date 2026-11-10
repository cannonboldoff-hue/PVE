"""Deterministic parsing of the reference analysis' free-text style notes into renderable settings.
The analysis (Pegasus) describes looks in words; the renderer needs enums, hex colours and numbers."""
import re

from ..models import CaptionStyle, Collage, Grade

COLORS = {
    "white": "#FFFFFF", "black": "#000000", "red": "#E53935", "pink": "#FF69B4", "hot pink": "#FF1493",
    "light pink": "#F7C6D9", "pastel pink": "#F7C6D9", "yellow": "#FFD400", "gold": "#FFC107", "orange": "#FF9800",
    "green": "#43A047", "blue": "#1E88E5", "light blue": "#90CAF9", "purple": "#8E24AA", "lavender": "#CDB4DB",
    "beige": "#E8D8C3", "cream": "#FFF3D6", "brown": "#8D6E63", "gray": "#9E9E9E", "grey": "#9E9E9E",
    "peach": "#FFCBA4", "mint": "#B8F2D3", "teal": "#14B8A6",
}
_NAMES = sorted(COLORS, key=len, reverse=True)  # "light pink" before "pink"


def to_hex(text: str, default: str) -> str:
    m = re.search(r"#[0-9A-Fa-f]{6}\b", text or "")
    if m:
        return m.group(0).upper()
    low = (text or "").lower()
    return next((COLORS[n] for n in _NAMES if n in low), default)


def _font(text: str) -> str:
    t = text.lower()
    for key, font in (("impact", "Impact"), ("comic", "Comic Sans MS"), ("rounded", "Comic Sans MS"), ("playful", "Comic Sans MS"),
                      ("script", "Segoe Script"), ("handwrit", "Segoe Script"), ("cursive", "Segoe Script"),
                      ("georgia", "Georgia"), ("serif", "Georgia"), ("times", "Times New Roman"),
                      ("typewriter", "Courier New"), ("mono", "Courier New"), ("courier", "Courier New"),
                      ("verdana", "Verdana"), ("trebuchet", "Trebuchet MS")):
        if key in t and not (key == "serif" and "sans" in t):
            return font
    return "Arial"


def _size(text: str) -> int:
    t = text.lower()
    if (n := re.search(r"\d{2,3}", t)):
        return min(140, max(36, int(n.group())))
    for key, px in (("extra large", 120), ("huge", 120), ("very large", 110), ("large", 96), ("big", 96), ("bold", 84),
                    ("small", 56), ("tiny", 44), ("medium", 72)):
        if key in t:
            return px
    return 72


def caption_style(shot: dict) -> CaptionStyle:
    text = shot.get("on_screen_text", "") or ""
    pos = (shot.get("caption_position") or "").lower()
    emphasis = [w for w in re.split(r"[,;/]|\band\b", shot.get("caption_emphasis", "") or "") for w in [w.strip().strip("\"'")] if w]
    letters = [c for c in text if c.isalpha()]
    return CaptionStyle(
        font=_font(shot.get("caption_font", "") or ""),
        size=_size(shot.get("caption_size", "") or ""),
        color=to_hex(shot.get("caption_color", ""), "#FFFFFF"),
        position="top" if "top" in pos else "bottom" if any(k in pos for k in ("bottom", "lower")) else
                 "center" if any(k in pos for k in ("middle", "center", "centre")) else "bottom",
        bold="thin" not in (shot.get("caption_font", "") or "").lower() and "light" not in (shot.get("caption_font", "") or "").lower(),
        uppercase=bool(letters) and all(c.isupper() for c in letters),
        emphasis_words=emphasis[:6],
    )


def caption_timing(shot: dict) -> tuple[float | None, float | None]:
    """The reference's caption window, as seconds after the shot starts (None when the analysis has no timing)."""
    start = shot.get("start", 0.0)
    cs, ce = shot.get("caption_start"), shot.get("caption_end")
    if not isinstance(cs, (int, float)) or not isinstance(ce, (int, float)) or ce <= cs:
        return None, None
    rel_s, rel_e = max(0.0, cs - start), max(0.0, ce - start)
    return (round(rel_s, 2), round(rel_e, 2)) if rel_e - rel_s >= 0.3 else (None, None)


def grade(shot: dict) -> Grade:
    t = (shot.get("color_look", "") or "").lower()
    preset = "none"
    for key, name in (("black and white", "noir"), ("black-and-white", "noir"), ("monochrome", "noir"), ("noir", "noir"),
                      ("vintage", "vintage"), ("retro", "vintage"), ("film", "vintage"), ("faded", "vintage"),
                      ("cinematic", "cinematic"), ("teal", "cinematic"), ("cool", "cool"), ("cold", "cool"), ("blue", "cool"),
                      ("warm", "warm"), ("golden", "warm"), ("orange", "warm")):
        if key in t:
            preset = name
            break
    brightness = 0.1 if any(k in t for k in ("bright", "light and airy", "airy")) else -0.1 if any(k in t for k in ("dark", "moody", "dim")) else 0.0
    contrast = 1.2 if "high contrast" in t or "punchy" in t else 0.85 if any(k in t for k in ("low contrast", "soft", "faded", "flat")) else 1.0
    saturation = 1.3 if any(k in t for k in ("saturated", "vivid", "vibrant", "colourful", "colorful")) else \
        0.8 if any(k in t for k in ("muted", "desaturated", "pastel")) else 1.0
    return Grade(preset=preset, brightness=brightness, contrast=contrast, saturation=saturation)


def layout(shot: dict) -> tuple[str, Collage]:
    """('single' | 'collage', collage settings)."""
    blob = " ".join(str(shot.get(k, "") or "") for k in ("layout", "background", "description")).lower()
    if not any(k in blob for k in ("collage", "grid", "tiles", "multiple photos")) or str(shot.get("layout", "")).lower() == "single":
        return "single", Collage()
    n = shot.get("collage_tiles")
    tiles = min(6, max(2, int(n))) if isinstance(n, (int, float)) and n >= 2 else 4
    style = str(shot.get("collage_style", "") or "").lower()
    return "collage", Collage(
        tiles=tiles,
        background=to_hex(str(shot.get("collage_background", "") or ""), "#F7C6D9"),
        border=not any(k in style for k in ("no border", "borderless", "no frame")),
        tilt=0.0 if any(k in style for k in ("straight", "aligned", "no tilt")) else 4.0,
    )
