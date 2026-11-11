"""Text events -> ASS (libass): absolute frame timing, measured box, size, colours and animation."""
import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .. import config
from ..stages.editor import BS, _bgr

W, H = config.W, config.H
# font size from the measured ink box (glyphs incl. outline): the box is BOX_PER_INK x PIL's ink height of the string
# without stroke, and libass draws K_FONT x the ink of PIL at the same size (Arial Bold, measured 2026-11-11: 0.892).
BOX_PER_INK = 1.08
K_FONT = 0.892
FONT_FILES = {"Arial": ("arial.ttf", "arialbd.ttf"), "Impact": ("impact.ttf", "impact.ttf"),
              "Georgia": ("georgia.ttf", "georgiab.ttf"), "Comic Sans MS": ("comic.ttf", "comicbd.ttf"),
              "Segoe Script": ("segoesc.ttf", "segoescb.ttf"), "Times New Roman": ("times.ttf", "timesbd.ttf"),
              "Courier New": ("cour.ttf", "courbd.ttf"), "Verdana": ("verdana.ttf", "verdanab.ttf"),
              "Trebuchet MS": ("trebuc.ttf", "trebucbd.ttf")}
OUTLINE_PER_FS = 0.06  # outline width when the reference has one but its width was not measured
SLIDE_BOXES = 2.0  # slide distance in line heights (the measured offset is not stored yet)
HIGHLIGHT = "#FFD400"  # word highlight colour when none was measured

HEAD = (
    "[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
    "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Outline,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n"
    "Style: Box,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,0,0,5,0,0,0,1\n\n"
    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)


def ts(frame: int, fps: int = config.FPS) -> str:
    """ASS time (centiseconds) that makes frame `frame` the first one shown: libass shows an event at t >= start,
    frame f is at f / fps, so start just before it and after frame f - 1."""
    cs = max(0, math.floor(frame * 100 / fps - 0.5))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    return f"{h}:{m:02d}:{rem // 100:02d}.{rem % 100:02d}"


def _escape(text: str) -> str:
    return text.replace(BS, "").replace("{", "(").replace("}", ")").replace("\n", BS + "N")


@lru_cache(maxsize=512)
def ink_per_px(text: str, font: str = "Arial", bold: bool = True) -> float:
    """Ink height of one line of text per pixel of font size (PIL, same TTF libass loads)."""
    name = FONT_FILES.get(font, FONT_FILES["Arial"])[1 if bold else 0]
    try:
        f = ImageFont.truetype(f"C:/Windows/Fonts/{name}", 100)
    except OSError:
        f = ImageFont.load_default(100)
    _, y0, _, y1 = ImageDraw.Draw(Image.new("L", (4, 4))).textbbox((0, 0), text or "Ag", font=f)
    return max(1, y1 - y0) / 100


def font_size(text: str, line_box_h: float, font: str, bold: bool, h: int = H) -> int:
    """ASS \\fs that reproduces an OCR line box of line_box_h (fraction of frame height) for this string."""
    line = max(text.split("\n"), key=len)
    return max(8, round(line_box_h * h / BOX_PER_INK / (ink_per_px(line, font, bold) * K_FONT)))


def _ms(frames: int, fps: int) -> int:
    return int(round(frames * 1000 / fps))


def event_tags(e: dict, fps: int, w: int = W, h: int = H) -> tuple[str, str, list[str]]:
    """(override tags, text with per-character / per-word tags, losses) for one TextEvent dict."""
    st, box = e["style"], e["keys"][0]["box"]
    lines = max(1, e["text"]["value"].count("\n") + 1)
    # size from the reference's own words: a swapped string keeps the reference's glyph size, not its box
    fs = font_size(e["text"].get("raw") or e["text"]["value"], st["size"], st["font"], st.get("bold", True), h)
    x, y = round((box["x"] + box["w"] / 2) * w), round((box["y"] + box["h"] / 2) * h)
    a_in, a_out = e["anim_in"]["value"], e["anim_out"]["value"]
    n_in, n_out = _ms(e.get("anim_in_frames", 0), fps), _ms(e.get("anim_out_frames", 0), fps)
    dur = _ms(e["end"] - e["start"], fps)
    boxed = bool(st.get("box"))
    border = st.get("box") if boxed else st.get("outline")
    bord = round(st.get("outline_w", 0) * h) or (round(fs * OUTLINE_PER_FS) if border else 0)
    tags = [f"{BS}an5", f"{BS}fn{st['font']}", f"{BS}fs{fs}", f"{BS}b{1 if st.get('bold', True) else 0}",
            f"{BS}1c{_bgr(st['fill'])}"]
    if border:
        tags += [f"{BS}3c{_bgr(border)}", f"{BS}bord{max(bord, 6 if boxed else 1)}"]
    else:
        tags.append(f"{BS}bord0")
    tags.append(f"{BS}shad{2 if st.get('shadow') else 0}")
    losses: list[str] = []
    dy = round(SLIDE_BOXES * box["h"] / lines * h)
    dx = round(SLIDE_BOXES * box["h"] / lines * h)
    moves = {"slide_up": (0, dy), "slide_down": (0, -dy), "slide_left": (dx, 0), "slide_right": (-dx, 0)}
    if a_in in moves:
        ox, oy = moves[a_in]
        tags.append(f"{BS}move({x + ox},{y + oy},{x},{y},0,{n_in})")
        if a_out in moves:
            losses.append(f"{a_out} out: one move per event in libass; text holds still at the end")
    elif a_out in moves:
        ox, oy = moves[a_out]
        tags.append(f"{BS}move({x},{y},{x - ox},{y - oy},{dur - n_out},{dur})")
    else:
        tags.append(f"{BS}pos({x},{y})")
    fin = n_in if a_in == "fade" else 0
    fout = n_out if a_out == "fade" else 0
    if fin or fout:
        tags.append(f"{BS}fad({fin},{fout})")
    if a_in == "pop":
        tags.append(f"{BS}fscx50{BS}fscy50{BS}t(0,{n_in},{BS}fscx100{BS}fscy100)")
    if a_out == "pop":
        tags.append(f"{BS}t({dur - n_out},{dur},{BS}fscx50{BS}fscy50)")
    text = _escape(e["text"]["value"])
    if a_in == "typewriter":
        chars = [c for c in e["text"]["value"]]
        per = max(1, round(n_in / 10 / max(1, len(chars))))  # \ko is in centiseconds
        tags.append(f"{BS}2a&HFF&")
        text = "".join(f"{{{BS}ko{per}}}" + _escape(c) for c in chars)
    elif a_in == "word_highlight":
        words = e["text"]["value"].split(" ")
        per = max(1, round(dur / 10 / max(1, len(words))))
        tags += [f"{BS}2c{_bgr(st['fill'])}", f"{BS}1c{_bgr(HIGHLIGHT)}"]
        text = " ".join(f"{{{BS}k{per}}}" + _escape(wd) for wd in words)
        losses.append("word highlight: words stay highlighted once reached (libass karaoke)")
    for a in {a_in, a_out} - {"none", "fade", "pop", "typewriter", "word_highlight", *moves}:
        losses.append(f"{a}: not drawable with libass, shown without it (overlay engine, M9)")
    return "".join(tags), text, losses


def ass(texts: list[dict], fps: int = config.FPS, w: int = W, h: int = H) -> tuple[str, dict[str, list[str]]]:
    """(ASS document, losses per event id)."""
    lines, losses = [], {}
    for e in sorted(texts, key=lambda e: e["start"]):
        if not e["text"]["value"].strip():
            continue
        tags, text, lost = event_tags(e, fps, w, h)
        style = "Box" if e["style"].get("box") else "Outline"
        lines.append(f"Dialogue: 0,{ts(e['start'], fps)},{ts(e['end'], fps)},{style},,0,0,0,,{{{tags}}}{text}")
        if lost:
            losses[e["id"]] = lost
    return HEAD.format(w=w, h=h) + "\n".join(lines) + "\n", losses
