"""On-screen text: OCR (RapidOCR, PP-OCR models) every SAMPLE_EVERY frames, linked into tracks, start/end refined on
single frames, lines that share timing merged into one event, style measured from pixels at the steadiest frame."""
import threading
from collections import Counter
from functools import lru_cache

import cv2
import numpy as np

from .. import ir
from ..stages.compare import box_iou, text_similarity

NAME, VERSION, DEPS = "text", 8, []
SAMPLE_EVERY = 2  # 15 samples per second; lower finds shorter flashes of text, higher is faster
OCR_LONG = 640  # long side the OCR sees; smaller misses small captions, larger is slower (0.33 s vs 0.55 s at 960)
SAME_FRAME = 4  # max gray difference (0..255) at which a sample reuses the previous sample's OCR
MIN_SCORE = 0.6  # OCR confidence floor per detection
LINK_IOU = 0.3  # box overlap to continue a track (low enough for pops and slides)
LINK_SIM = 0.6  # text similarity to continue a track
MAX_GAP_SAMPLES = 1  # a track survives this many samples without a detection (OCR flicker)
MIN_TEXT_FRAMES = 6  # shorter tracks are dropped as OCR noise, unless they read as sure flash text:
FLASH_FRAMES = 2  # flash text (fast edits) shows for 2-5 frames: kept when it reads this clearly
FLASH_SCORE = 0.85
ROTATED = 3.0  # degrees: text this far off level is drawn rotated
MIN_ANGLE_CHARS = 3  # shorter strings: the detector's box angle is noise
ANGLE_STD = 2.5  # degrees of spread across samples above which the angle is noise
WORD_EDGE = 0.8  # share of a growing string's samples that end on a word: a word-by-word reveal
LIT = 70.0  # colour distance from the fill that makes a word lit (highlighted)
KEY_WORD = 0.8  # lit in this share of the samples: a key word in its own colour, not an animation
LINE_GAP = 0.8  # lines closer than this many line heights, with the same timing, are one event
SAME_TIMING = 3  # frames
# a row/column is glyph when it holds this share of the densest one's glyph pixels (rows lower: ascenders are sparse)
INK_DENSE_ROW, INK_DENSE_COL = 0.04, 0.08
BOX_FLAT = 12.0  # colour spread (std, 0..255) below which a cluster is a flat caption box

_lock = threading.Lock()


def _gpu() -> bool:
    try:
        import onnxruntime as ort

        ort.preload_dlls()  # finds the pip-installed CUDA/cuDNN libraries
        return "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:
        return False


def _build(cuda: bool):
    from rapidocr import RapidOCR

    # default det upscales the short side to 736 (a 540x960 frame becomes 736x1308); cap the long side instead.
    # captions are upright, so the angle classifier is skipped.
    p = {"Global.use_cls": False, "Global.log_level": "warning", "Det.limit_type": "max",
         "Det.limit_side_len": OCR_LONG}
    if cuda:  # EXHAUSTIVE cudnn search can overflow 4 GB with changing input shapes; default is lighter
        p |= {f"EngineConfig.onnxruntime.{k}": v for k, v in
              {"use_cuda": True, "cuda_ep_cfg.cudnn_conv_algo_search": "HEURISTIC"}.items()}
    return RapidOCR(params=p)


@lru_cache
def _engine():
    if _gpu():
        try:
            e = _build(True)
            e(np.zeros((64, 64, 3), np.uint8))  # a broken CUDA setup fails here, not mid-reel
            return e
        except Exception:
            pass  # shortcut: silent CPU fallback; check onnxruntime providers if OCR is slow
    return _build(False)


def ocr_quads(img: np.ndarray) -> list[tuple[ir.Box, str, float, float, float]]:
    """(axis-aligned box, text, score, angle in degrees clockwise, line height as share of frame height). The angle
    and height come from the detector's rotated rectangle (top-left, top-right, bottom-right, bottom-left)."""
    h, w = img.shape[:2]
    with _lock:  # one onnxruntime session, not re-entrant across threads
        r = _engine()(img)
    out = []
    for pts, txt, sc in zip(r.boxes if r.boxes is not None else [], r.txts or [], r.scores or []):
        if sc < MIN_SCORE or not any(ch.isalnum() for ch in txt):  # symbols-only reads are texture noise
            continue
        p = np.asarray(pts, dtype=float)
        x0, y0 = p.min(axis=0)
        x1, y1 = p.max(axis=0)
        ang = float(np.degrees(np.arctan2(p[1, 1] - p[0, 1], p[1, 0] - p[0, 0]))) if len(p) == 4 else 0.0
        qh = float(np.hypot(*(p[3] - p[0]))) / h if len(p) == 4 else (y1 - y0) / h
        out.append((ir.Box(x=x0 / w, y=y0 / h, w=(x1 - x0) / w, h=(y1 - y0) / h), txt.strip(), float(sc), ang, qh))
    return out


def ocr(img: np.ndarray) -> list[tuple[ir.Box, str, float]]:
    return [(b, t, s) for b, t, s, _, _ in ocr_quads(img)]


def ocr_size(src: ir.Source) -> tuple[int, int]:
    f = min(1.0, OCR_LONG / max(src.width, src.height))
    return int(src.width * f) // 2 * 2, int(src.height * f) // 2 * 2


def read_frames(path, frames: set[int], size: tuple[int, int]) -> dict[int, np.ndarray]:
    """Decode the proxy once, sequentially, keeping only the wanted frame indices (RGB at size)."""
    cap = cv2.VideoCapture(str(path))
    out, i, last = {}, 0, max(frames) if frames else -1
    try:
        while i <= last:
            ok, bgr = cap.read()
            if not ok:
                break
            if i in frames:
                out[i] = cv2.cvtColor(cv2.resize(bgr, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
            i += 1
    finally:
        cap.release()
    return out


def _linkable(a: tuple, b: tuple) -> bool:
    (ba, ta), (bb, tb) = a, b
    na, nb = ta.lower().replace(" ", ""), tb.lower().replace(" ", "")
    grows = (na.startswith(nb) or nb.startswith(na)) and box_iou(ba, bb) > 0  # typewriter
    return (box_iou(ba, bb) >= LINK_IOU and text_similarity(ta, tb) >= LINK_SIM) or grows


def link(samples: dict[int, list[tuple[ir.Box, str, float]]]) -> list[list[tuple[int, ir.Box, str, float]]]:
    """Detections per sampled frame -> tracks of (frame, box, text, score)."""
    tracks: list[list] = []
    open_: list[int] = []  # indices into tracks
    order = sorted(samples)
    for k, f in enumerate(order):
        used = set()
        for box, txt, sc in sorted(samples[f], key=lambda d: -d[2]):
            best = None
            for ti in open_:
                if ti in used:
                    continue
                lf, lb, lt, _ = tracks[ti][-1]
                if _linkable((lb, lt), (box, txt)):
                    iou = box_iou(lb, box)
                    if best is None or iou > best[1]:
                        best = (ti, iou)
            if best:
                tracks[best[0]].append((f, box, txt, sc))
                used.add(best[0])
            else:
                tracks.append([(f, box, txt, sc)])
                open_.append(len(tracks) - 1)
                used.add(len(tracks) - 1)
        step = SAMPLE_EVERY * (MAX_GAP_SAMPLES + 1)
        open_ = [ti for ti in open_ if f - tracks[ti][-1][0] < step]
    return tracks


def _norm(t: str) -> str:
    return t.lower().replace(" ", "")


def split_changes(track: list) -> list[list]:
    """A track whose string changes and stays changed is two events (one caption replaced by the next in the same
    place). Single-sample changes are OCR flicker; a string that only grows is typewriter: both stay one event."""
    groups: list[list] = []
    for d in track:
        if groups and _norm(groups[-1][-1][2]) == _norm(d[2]):
            groups[-1].append(d)
        else:
            groups.append([d])
    merged: list[list] = []
    for g in groups:
        if merged and (len(g) < 2 or _norm(g[0][2]).startswith(_norm(merged[-1][-1][2])) or
                       _norm(merged[-1][-1][2]).startswith(_norm(g[0][2]))):
            merged[-1] += g  # flicker or growth: same event
        elif merged and len(merged[-1]) < 2:
            merged[-1] += g  # the previous piece was flicker
        else:
            merged.append(g)
    return merged


def _present(img: np.ndarray, box: ir.Box, text: str) -> bool:
    return any(box_iou(b, box) > 0.2 and (text_similarity(t, text) >= LINK_SIM or _linkable((b, t), (box, text)))
               for b, t, _ in ocr(img))


def refine(path, track: list, size, n_frames: int) -> tuple[int, int]:
    """First and last readable frame, checked on the single frames between samples."""
    first, last = track[0], track[-1]
    start = first[0]
    cand = [f for f in range(first[0] - 1, max(-1, first[0] - SAMPLE_EVERY), -1)]
    end_c = [f for f in range(last[0] + 1, min(n_frames, last[0] + SAMPLE_EVERY))]
    imgs = read_frames(path, set(cand) | set(end_c), size)
    for f in cand:  # walk outwards while still readable
        if f in imgs and _present(imgs[f], first[1], first[2]):
            start = f
        else:
            break
    end = last[0] + 1
    for f in end_c:
        if f in imgs and _present(imgs[f], last[1], last[2]):
            end = f + 1
        else:
            break
    return start, end


def _union(boxes: list[ir.Box]) -> ir.Box:
    x0, y0 = min(b.x for b in boxes), min(b.y for b in boxes)
    x1, y1 = max(b.x + b.w for b in boxes), max(b.y + b.h for b in boxes)
    return ir.Box(x=x0, y=y0, w=x1 - x0, h=y1 - y0)


def _median_box(boxes: list[ir.Box]) -> ir.Box:
    a = np.array([[b.x, b.y, b.w, b.h] for b in boxes])
    m = np.median(a, axis=0)
    return ir.Box(x=float(m[0]), y=float(m[1]), w=float(m[2]), h=float(m[3]))


def _hex(c) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[int(round(v)) for v in c])


def measure_style(img: np.ndarray, box: ir.Box, lines: int = 1) -> dict:
    """Glyph height, fill / outline / background-box colours and alignment from the pixels of one frame."""
    h, w = img.shape[:2]
    x0, y0 = int(box.x * w), int(box.y * h)
    x1, y1 = int((box.x + box.w) * w), int((box.y + box.h) * h)
    inner = img[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3).astype(np.float32)
    px, py = max(4, int(box.w * w * 0.15)), max(4, int(box.h * h * 0.4))
    X0, Y0, X1, Y1 = max(0, x0 - px), max(0, y0 - py), min(w, x1 + px), min(h, y1 + py)
    ring_mask = np.ones((Y1 - Y0, X1 - X0), bool)
    ring_mask[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = False
    ring = img[Y0:Y1, X0:X1][ring_mask].reshape(-1, 3).astype(np.float32)
    style = {"size": round(box.h / max(1, lines), 4), "align": "left" if box.x < 0.12 and box.x + box.w < 0.8 else
             "right" if box.x + box.w > 0.88 and box.x > 0.2 else "center", "fill": "#FFFFFF", "outline": None,
             "box": None}
    if len(inner) < 30 or len(ring) < 30:
        return style
    k = 3
    _, labels, cent = cv2.kmeans(inner, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3,
                                 cv2.KMEANS_PP_CENTERS)
    labels = labels.ravel()
    share_in = np.bincount(labels, minlength=k) / len(labels)
    d = np.linalg.norm(ring[:, None, :] - cent[None, :, :], axis=2)
    share_out = np.array([(d[:, j] < 30).mean() for j in range(k)])
    rare = [j for j in range(k) if share_in[j] > 0.04 and share_out[j] < 0.15]  # inside the box, not around it
    if not rare:
        return style
    # a rare cluster covering most of the box is a filled background box; text is drawn on it
    spread = [float(inner[labels == j].std(axis=0).max()) if (labels == j).any() else 999.0 for j in range(k)]
    # a filled caption box is one flat colour; textured footage behind big glyphs only looks "rare" outside
    boxy = [j for j in rare if share_in[j] > 0.5 and spread[j] < BOX_FLAT and share_out[j] < 0.05]
    lab = labels.reshape(y1 - max(0, y0), x1 - max(0, x0))
    ground = boxy[0] if boxy else int(np.argmax(share_out))  # what the glyphs sit on
    if boxy:
        style["box"] = _hex(cent[boxy[0]])
        rare = [j for j in rare if j != boxy[0]] or [int(np.argmin(share_out))]
    # outline pixels touch the ground, fill pixels touch the outline: fill is the rare cluster least adjacent to it
    near = np.zeros_like(lab, bool)
    g = lab == ground
    near[1:] |= g[:-1]; near[:-1] |= g[1:]; near[:, 1:] |= g[:, :-1]; near[:, :-1] |= g[:, 1:]
    adj = {j: near[lab == j].mean() for j in rare}
    rare.sort(key=lambda j: adj[j])
    style["fill"] = _hex(cent[rare[0]])
    if len(rare) > 1 and share_in[rare[1]] > 0.03:
        style["outline"] = _hex(cent[rare[1]])
    # tight ink box: rows / columns holding glyph pixels (fill or outline); the OCR box is padded
    ink = np.isin(lab, rare[:2])
    # texture that happens to share a glyph colour is scattered: keep rows/columns dense in glyph pixels
    r_n, c_n = ink.sum(1), ink.sum(0)
    rows = np.nonzero(r_n >= max(2, INK_DENSE_ROW * r_n.max()))[0]
    cols = np.nonzero(c_n >= max(2, INK_DENSE_COL * c_n.max()))[0]
    if len(rows) and len(cols):
        ox, oy = max(0, x0), max(0, y0)
        style["ink"] = {"x": (ox + cols[0]) / w, "y": (oy + rows[0]) / h, "w": (cols[-1] - cols[0] + 1) / w,
                        "h": (rows[-1] - rows[0] + 1) / h}
        style["size"] = round(style["ink"]["h"] / max(1, lines), 4)
    return style


def merge_lines(events: list[dict]) -> list[dict]:
    """Lines that appear and disappear together and sit on top of each other are one event."""
    events = sorted(events, key=lambda e: (e["start"], e["box"].y))
    out: list[dict] = []
    for e in events:
        prev = next((o for o in out if abs(o["start"] - e["start"]) <= SAME_TIMING and abs(o["end"] - e["end"]) <=
                     SAME_TIMING and 0 <= e["box"].y - (o["box"].y + o["box"].h) < LINE_GAP * e["box"].h
                     and min(o["box"].x + o["box"].w, e["box"].x + e["box"].w) > max(o["box"].x, e["box"].x)), None)
        if prev:
            n0 = len(prev["text"].split())
            if prev.get("words") or e.get("words"):  # word indices run on across the lines
                prev["words"] = (prev.get("words") or [{"i": i, "start": prev["start"]} for i in range(n0)]) + \
                    [{"i": n0 + w["i"], "start": w["start"]} for w in (e.get("words") or
                                                                     [{"i": i, "start": e["start"]}
                                                                      for i in range(len(e["text"].split()))])]
            prev["text"] += "\n" + e["text"]
            prev.setdefault("line_boxes", [prev["box"]]).append(e["box"])
            prev["box"] = _union([prev["box"], e["box"]])
            prev["boxes"] = [[f, *_union([ir.Box(x=a, y=b, w=c, h=d), e["box"]]).model_dump().values()]
                             for f, a, b, c, d in prev["boxes"]]
            prev["lines"] += 1
            prev["samples"] += e["samples"]
        else:
            out.append(e)
    return out


def reveal_words(tr: list, text: str) -> list[dict]:
    """Word-by-word reveal: the string grows and its samples end on whole words. [{i, start}] per word of text
    (one line), or [] when it is not a reveal (all at once, or growing by characters: typewriter)."""
    full = text.split()
    if len(full) < 2:
        return []
    ends = {len(_norm(" ".join(full[:k]))): k for k in range(1, len(full) + 1)}
    starts, grow, on_word = {}, 0, 0
    whole = _norm(text)
    for f, _, t, _ in tr:
        s = _norm(t)
        if not s or not whole.startswith(s):
            continue
        if len(s) < len(whole):
            grow += 1
            on_word += len(s) in ends
        k = ends.get(len(s), len(t.split()))
        for i in range(k):
            starts.setdefault(i, f)
    if grow < 1 or on_word < WORD_EDGE * grow or len(set(starts.values())) < 2:
        return []
    last = max(starts.values())
    return [{"i": i, "start": starts.get(i, last)} for i in range(len(full))]


def _word_boxes(line: ir.Box, words: list[str]) -> list[ir.Box]:
    """Each word's share of its line box, split by character count (spaces included)."""
    total = max(1, len(" ".join(words)))
    out, x = [], line.x
    for wd in words:
        wv = line.w * len(wd) / total
        out.append(ir.Box(x=x, y=line.y, w=wv, h=line.h))
        x += wv + line.w / total
    return out


def _glyph_colour(img: np.ndarray, b: ir.Box, bg: np.ndarray) -> np.ndarray | None:
    """Median colour of the brighter glyph pixels in a word box (outline pixels are the darker ones)."""
    h, w = img.shape[:2]
    crop = img[int(b.y * h):max(int(b.y * h) + 1, int((b.y + b.h) * h)),
               int(b.x * w):max(int(b.x * w) + 1, int((b.x + b.w) * w))].reshape(-1, 3).astype(np.float32)
    px = crop[np.linalg.norm(crop - bg, axis=1) > 80]
    if len(px) < 15:
        return None
    lum = px.max(axis=1)
    return np.median(px[lum >= np.quantile(lum, 0.6)], axis=0)


def highlight_words(frames: dict, ev: dict, fill: str) -> tuple[list[dict], str | None]:
    """Words that turn another colour than the fill: in turn (word highlight, first lit frame per word) or the whole
    time (key words, start = the event's start). ([{i, start, fill}], highlight colour)."""
    f0 = np.array([int(fill[k:k + 2], 16) for k in (1, 3, 5)], np.float32)
    lines = ev["text"].split("\n")
    boxes = ev.get("line_boxes") or [ev["box"]] * len(lines)
    words = [(lb, wb) for line, lb in zip(lines, boxes) for wb in _word_boxes(lb, line.split())]
    if len(words) < 2:
        return [], None
    fs = [f for f in sorted(frames) if ev["start"] <= f < ev["end"]][::2]  # every 4th frame
    lit: dict[int, list[tuple[int, np.ndarray]]] = {}
    for f in fs:
        img = frames[f]
        h, w = img.shape[:2]
        for i, (lb, wb) in enumerate(words):
            y0, y1 = max(0, int((lb.y - lb.h) * h)), min(h, int((lb.y + 2 * lb.h) * h))
            ring = np.r_[img[y0:max(y0 + 1, int(lb.y * h))].reshape(-1, 3), img[min(h - 1, int((lb.y + lb.h) * h)):y1].reshape(-1, 3)]
            c = _glyph_colour(img, wb, np.median(ring, axis=0) if len(ring) else np.zeros(3))
            if c is not None and np.linalg.norm(c - f0) > LIT:
                lit.setdefault(i, []).append((f, c))
    if not lit or len(fs) < 2:
        return [], None
    colour = _hex(np.median(np.array([c for v in lit.values() for _, c in v]), axis=0))
    key = {i for i, v in lit.items() if len(v) >= KEY_WORD * len(fs)}
    turn = {i: v[0][0] for i, v in lit.items() if i not in key}
    if len(turn) >= 2 and len(set(turn.values())) >= 2:  # lights move through the words
        return [{"i": i, "start": turn.get(i, ev["start"]), "fill": colour} for i in range(len(words))], colour
    if key and len(key) < len(words):
        return [{"i": i, "start": ev["start"], "fill": colour} for i in sorted(key)], colour
    return [], None


def run(ctx) -> list[ir.Item]:
    src = ctx.source
    size = ocr_size(src)
    frames = read_frames(ctx.proxy, set(range(0, src.n_frames, SAMPLE_EVERY)), size)
    samples, angles, prev = {}, {}, None
    for f in sorted(frames):  # a frame identical to the previous sample reads the same: skip the OCR
        g = frames[f].max(axis=2)
        if prev is not None and int(np.abs(g.astype(np.int16) - prev[1]).max()) <= SAME_FRAME:
            samples[f], angles[f] = samples[prev[0]], angles[prev[0]]
        else:
            q = ocr_quads(frames[f])
            samples[f] = [(b, t, s) for b, t, s, _, _ in q]
            angles[f] = {(t, round(b.x, 4), round(b.y, 4)): (a, qh) for b, t, _, a, qh in q}
            prev = (f, g.astype(np.int16))
    events = []
    for tr in (piece for t in link(samples) for piece in split_changes(t)):
        flash = float(np.mean([s for *_, s in tr])) >= FLASH_SCORE and len(_norm(tr[0][2])) >= 2
        if tr[-1][0] - tr[0][0] + 1 < (FLASH_FRAMES if flash else MIN_TEXT_FRAMES) - SAMPLE_EVERY:
            continue
        start, end = refine(ctx.proxy, tr, size, src.n_frames)
        if end - start < (FLASH_FRAMES if flash else MIN_TEXT_FRAMES):
            continue
        text = Counter(t for _, _, t, _ in tr).most_common(1)[0][0]
        boxes = [b for _, b, _, _ in tr]
        med = _median_box(boxes)
        # steadiest: at the median box and furthest from both ends (animations live at the ends)
        mid = (start + end) / 2
        at_rest = [d for d in tr if box_iou(d[1], med) > 0.9] or tr
        steady = min(at_rest, key=lambda d: abs(d[0] - mid))[0]
        quad = [angles.get(f, {}).get((t, round(b.x, 4), round(b.y, 4))) for f, b, t, _ in tr]
        ang = [[f, round(q[0], 2)] for (f, *_), q in zip(tr, quad) if q]
        # a glyph or two gives no reliable angle; nor do readings that disagree
        steady_ang = len(_norm(text)) >= MIN_ANGLE_CHARS and ang and float(np.std([a for _, a in ang])) < ANGLE_STD
        rest_ang = float(np.median([a for _, a in ang])) if steady_ang else 0.0
        qh = float(np.median([q[1] for q in quad if q])) if any(quad) else med.h
        words = reveal_words(tr, text)
        if words:
            words[0]["start"] = start
        events.append({"text": text, "start": start, "end": end, "box": med, "steady": steady, "lines": 1,
                       "samples": len(tr), "boxes": [[f, b.x, b.y, b.w, b.h] for f, b, _, _ in tr],
                       "score": float(np.mean([s for *_, s in tr])), "angles": ang,
                       "rotation": round(rest_ang, 1) if abs(rest_ang) >= ROTATED else 0.0, "quad_h": qh,
                       "words": words, "line_boxes": [med]})
    items = []
    for k, e in enumerate(sorted(merge_lines(events), key=lambda e: e["start"])):
        style = measure_style(frames[e["steady"]], e["box"], e["lines"])
        if e["rotation"]:  # the axis-aligned box of turned text is too tall: the rotated rectangle's height
            style["size"] = round(e["quad_h"], 4)
        lit, hi = highlight_words(frames, e, style.get("fill") or "#FFFFFF")
        items.append(ir.Item(id=f"text_{k}", track=NAME, start=e["start"], end=e["end"], conf=e["score"],
                             tool="rapidocr pp-ocr", data={"text": e["text"], "box": e["box"].model_dump(),
                                                          "boxes": e["boxes"], "samples": e["samples"],
                                                          "lines": e["lines"], "steady": e["steady"], "style": style,
                                                          "angles": e["angles"], "rotation": e["rotation"],
                                                          "words": e["words"], "lit": lit, "highlight": hi}))
    return items
