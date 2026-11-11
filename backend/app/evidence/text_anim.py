"""Text animation in and out, from every frame of each text event's first and last ANIM_WINDOW frames (inside the
event's own shot).

Geometry comes from OCR on a band around the resting box (box size, centre, string). Visibility of faint text comes
from pixels: against a frame of the same shot with no text (P) and the steadiest frame (S), presence
p_f = mean |F_f - P| / mean |S - P| over S's glyph pixels, about the alpha during a fade.
A smaller box is pop, a moved centre is a slide, a shorter prefix of the string is typewriter, a rising presence at
the resting box is fade."""
import numpy as np

from .. import ir
from ..stages.compare import box_iou, text_similarity
from .text import ocr, ocr_size, read_frames

NAME, VERSION, DEPS = "text_anim", 5, ["text", "cuts", "transitions"]
ANIM_WINDOW = 12  # frames examined each side of the readable span
DIFF = 60  # summed RGB difference that counts as a glyph pixel
VISIBLE = 0.1  # presence above this: the text has started to show
STEADY = 0.85  # presence above this, at the resting box: the animation is over
MOVE = 0.4  # centre offset, in line heights, that makes a slide
GROW = 0.85  # height ratio below this makes a pop
BAND = 2.5  # OCR band: this many line heights above and below the resting box
OCR_STEP = 2  # read every 2nd frame until the text rests: animation length is known to 2 frames, half the OCR


def _shot(cuts: list[int], f: int, n: int) -> tuple[int, int]:
    b = [0, *cuts, n]
    return next((a, c) for a, c in zip(b[:-1], b[1:]) if a <= f < c)


def _band(box: dict, lines: int) -> tuple[float, float]:
    lh = box["h"] / max(1, lines)
    return max(0.0, box["y"] - BAND * lh), min(1.0, box["y"] + box["h"] + BAND * lh)


def _read(img: np.ndarray, box: dict, text: str, lines: int) -> tuple[ir.Box, str] | None:
    """OCR the band around the resting box; the detection that is this event's text (or a prefix of it)."""
    h = img.shape[0]
    y0, y1 = _band(box, lines)
    a, b = int(y0 * h), int(y1 * h)
    want = text.replace("\n", " ").lower().replace(" ", "")
    best = None
    dets = ocr(img[a:b])
    if not dets:
        return None
    # lines of one event are read separately: join them back into one box
    keep = [(d, t) for d, t, _ in dets if (s := t.lower().replace(" ", "")) and (s in want or text_similarity(s, want) > 0.5)]
    if not keep:
        return None
    bh = (b - a) / h
    x0 = min(d.x for d, _ in keep)
    yy0 = min(d.y for d, _ in keep)
    x1 = max(d.x + d.w for d, _ in keep)
    yy1 = max(d.y + d.h for d, _ in keep)
    best = ir.Box(x=x0, y=y0 + yy0 * bh, w=x1 - x0, h=(yy1 - yy0) * bh)
    return best, " ".join(t for _, t in sorted(keep, key=lambda k: (k[0].y, k[0].x)))


def _glyphs(S: np.ndarray, P: np.ndarray, box: dict) -> np.ndarray:
    h, w = S.shape[:2]
    m = np.zeros((h, w), bool)
    x0, y0 = int(box["x"] * w), int(box["y"] * h)
    x1, y1 = int((box["x"] + box["w"]) * w), int((box["y"] + box["h"]) * h)
    m[y0:y1, x0:x1] = np.abs(S.astype(np.int16) - P.astype(np.int16)).sum(-1)[y0:y1, x0:x1] > DIFF
    return m


def _presence(F: np.ndarray, P: np.ndarray, S: np.ndarray, glyph: np.ndarray) -> float:
    if not glyph.any():
        return 0.0
    full = np.abs(S.astype(np.int16) - P.astype(np.int16)).sum(-1)[glyph].mean()
    return float(np.abs(F.astype(np.int16) - P.astype(np.int16)).sum(-1)[glyph].mean() / max(1.0, full))


def classify_resting(s: dict, rest: dict, text: str) -> bool:
    """At the resting box, full string, fully shown."""
    rb, b = ir.Box(**rest), s["box"]
    return box_iou(b, rb) > 0.75 and abs(b.h - rb.h) < 0.15 * rb.h and \
        s["txt"].lower().replace(" ", "") == text.replace("\n", " ").lower().replace(" ", "") and \
        (s["p"] is None or s["p"] > STEADY)


def classify(seq: list[dict], rest: dict, text: str, lines: int) -> tuple[str, int, int, float]:
    """seq: per frame {f, p (presence or None), box, txt}, ordered from outside the event inward.
    Returns (anim, first visible frame from outside, frames until resting, confidence)."""
    vis = next((k for k, s in enumerate(seq) if (s["p"] is not None and s["p"] > VISIBLE) or s["box"]), None)
    if vis is None:
        return "none", seq[-1]["f"] if seq else 0, 0, 0.3
    rb = ir.Box(**rest)
    lh = rb.h / max(1, lines)
    full = text.replace("\n", " ").lower().replace(" ", "")
    done = next((k for k in range(vis, len(seq)) if seq[k]["box"] and classify_resting(seq[k], rest, text)),
                len(seq) - 1)
    n = abs(seq[done]["f"] - seq[vis]["f"])
    if n < 2:
        return "none", seq[vis]["f"], 0, 0.8
    g = next((s for s in seq[vis:done] if s["box"]), None)
    if g is None:  # visible to pixels, never readable until it rests: faded in
        return "fade", seq[vis]["f"], n, 0.6
    b = g["box"]
    dy = ((b.y + b.h / 2) - (rb.y + rb.h / 2)) / lh
    dx = ((b.x + b.w / 2) - (rb.x + rb.w / 2)) / lh
    t = g["txt"].lower().replace(" ", "")
    if abs(dy) > MOVE and abs(dy) >= abs(dx):
        return ("slide_up" if dy > 0 else "slide_down"), seq[vis]["f"], n, 0.8
    if abs(dx) > MOVE:
        return ("slide_left" if dx > 0 else "slide_right"), seq[vis]["f"], n, 0.7
    if b.h < GROW * rb.h:
        return "pop", seq[vis]["f"], n, 0.8
    if len(t) < len(full) and full.startswith(t):
        return "typewriter", seq[vis]["f"], n, 0.7
    return "fade", seq[vis]["f"], n, 0.7


def run(ctx) -> list[ir.Item]:
    src, n = ctx.source, ctx.source.n_frames
    from . import boundaries

    cuts = [f for f, _, _ in boundaries(ctx.ev)]
    plans, want = [], set()
    for t in ctx.ev["text"]:
        s0, s1 = _shot(cuts, t.start, n)
        e0, e1 = _shot(cuts, t.end - 1, n)
        pre = max(s0, t.start - ANIM_WINDOW - 1)  # background frame before the text, same shot
        post = min(e1 - 1, t.end + ANIM_WINDOW)  # and after it
        ins = list(range(pre + 1, min(t.end, s1, t.start + ANIM_WINDOW + 1))) if pre < t.start else []
        outs = list(range(post - 1, max(t.start, e0, t.end - 1 - ANIM_WINDOW) - 1, -1)) if post >= t.end else []
        # the steady frame for each side must share that side's shot, or the glyph mask is the cut itself
        sampled = [b[0] for b in t.data["boxes"]]
        mid_in, mid_out = (t.start + min(t.end, s1)) / 2, (max(t.start, e0) + t.end) / 2
        st_in = min((f for f in sampled if t.start <= f < s1), key=lambda f: abs(f - mid_in), default=t.data["steady"])
        st_out = min((f for f in sampled if e0 <= f < t.end), key=lambda f: abs(f - mid_out), default=t.data["steady"])
        plans.append((t, pre, post, ins, outs, st_in, st_out))
        want |= {pre, post, st_in, st_out, *ins, *outs}
    size = ocr_size(src)
    frames = read_frames(ctx.proxy, {f for f in want if 0 <= f < n}, size)
    items = []
    for k, (t, pre, post, ins, outs, st_in, st_out) in enumerate(plans):
        rest, text, lines = t.data["box"], t.data["text"], t.data.get("lines", 1)
        result = {}
        for side, bg, order, st in (("in", pre, ins, st_in), ("out", post, outs, st_out)):
            if not order or bg not in frames:
                result[side] = ("none", t.start if side == "in" else t.end - 1, 0, 0.5)
                continue
            P, S = frames[bg], frames[st]
            glyph = _glyphs(S, P, rest)
            seq = [{"f": f, "p": _presence(frames[f], P, S, glyph), "box": None, "txt": "", "read": False}
                   for f in order]

            def read(j: int) -> None:  # OCR is the cost: read only the frames the classifier needs
                if not seq[j]["read"]:
                    r = _read(frames[seq[j]["f"]], rest, text, lines)
                    seq[j].update(box=r[0] if r else None, txt=r[1] if r else "", read=True)

            read(0)  # a slide or pop can be readable before it covers the resting glyphs
            y0, y1 = _band(rest, lines)
            hh = P.shape[0]
            need = max(20, 0.2 * glyph.sum())

            def stirred(s) -> bool:  # something new in the band: text arriving from elsewhere (or other motion)
                D = np.abs(frames[s["f"]][int(y0 * hh):int(y1 * hh)].astype(np.int16) -
                           P[int(y0 * hh):int(y1 * hh)].astype(np.int16)).sum(-1)
                return (D > DIFF).sum() >= need

            j = 0 if seq[0]["box"] else next((i for i, s in enumerate(seq) if s["p"] > VISIBLE or stirred(s)), None)
            while j is not None and j < len(seq):
                read(j)
                if seq[j]["box"] and classify_resting(seq[j], rest, text):
                    break
                j += OCR_STEP
            result[side] = classify(seq, rest, text, lines)
        (a_in, start, n_in, c_in), (a_out, last, n_out, c_out) = result["in"], result["out"]
        items.append(ir.Item(id=f"text_anim_{k}", track=NAME, start=min(start, t.start), end=max(last + 1, t.end),
                             conf=min(c_in, c_out), tool="ocr band + pixel presence",
                             data={"text_id": t.id, "in": a_in, "in_frames": n_in, "out": a_out, "out_frames": n_out,
                                   "in_conf": c_in, "out_conf": c_out}))
    return items
