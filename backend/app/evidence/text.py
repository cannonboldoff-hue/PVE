"""On-screen text: OCR (RapidOCR, PP-OCR models) every SAMPLE_EVERY frames, linked into tracks, start/end refined on
single frames, lines that share timing merged into one event, style measured from pixels at the steadiest frame."""
import threading
from collections import Counter
from functools import lru_cache

import cv2
import numpy as np

from .. import ir
from ..stages.compare import box_iou, text_similarity

NAME, VERSION, DEPS = "text", 7, []
SAMPLE_EVERY = 3  # 10 samples per second; lower finds shorter flashes of text, higher is faster
OCR_LONG = 640  # long side the OCR sees; smaller misses small captions, larger is slower (0.33 s vs 0.55 s at 960)
SAME_FRAME = 4  # max gray difference (0..255) at which a sample reuses the previous sample's OCR
MIN_SCORE = 0.6  # OCR confidence floor per detection
LINK_IOU = 0.3  # box overlap to continue a track (low enough for pops and slides)
LINK_SIM = 0.6  # text similarity to continue a track
MAX_GAP_SAMPLES = 1  # a track survives this many samples without a detection (OCR flicker)
MIN_TEXT_FRAMES = 6  # shorter tracks are dropped as OCR noise
LINE_GAP = 0.8  # lines closer than this many line heights, with the same timing, are one event
SAME_TIMING = 3  # frames
# a row/column is glyph when it holds this share of the densest one's glyph pixels (rows lower: ascenders are sparse)
INK_DENSE_ROW, INK_DENSE_COL = 0.04, 0.08
BOX_FLAT = 12.0  # colour spread (std, 0..255) below which a cluster is a flat caption box

_lock = threading.Lock()


@lru_cache
def _engine():
    from rapidocr import RapidOCR

    # default det upscales the short side to 736 (a 540x960 frame becomes 736x1308); cap the long side instead.
    # captions are upright, so the angle classifier is skipped.
    return RapidOCR(params={"Global.use_cls": False, "Global.log_level": "warning", "Det.limit_type": "max",
                            "Det.limit_side_len": OCR_LONG})


def ocr(img: np.ndarray) -> list[tuple[ir.Box, str, float]]:
    h, w = img.shape[:2]
    with _lock:  # one onnxruntime session, not re-entrant across threads
        r = _engine()(img)
    out = []
    for pts, txt, sc in zip(r.boxes if r.boxes is not None else [], r.txts or [], r.scores or []):
        if sc < MIN_SCORE or not any(ch.isalnum() for ch in txt):  # symbols-only reads are texture noise
            continue
        p = np.asarray(pts)
        x0, y0 = p.min(axis=0)
        x1, y1 = p.max(axis=0)
        out.append((ir.Box(x=x0 / w, y=y0 / h, w=(x1 - x0) / w, h=(y1 - y0) / h), txt.strip(), float(sc)))
    return out


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
            prev["text"] += "\n" + e["text"]
            prev["box"] = _union([prev["box"], e["box"]])
            prev["boxes"] = [[f, *_union([ir.Box(x=a, y=b, w=c, h=d), e["box"]]).model_dump().values()]
                             for f, a, b, c, d in prev["boxes"]]
            prev["lines"] += 1
            prev["samples"] += e["samples"]
        else:
            out.append(e)
    return out


def run(ctx) -> list[ir.Item]:
    src = ctx.source
    size = ocr_size(src)
    frames = read_frames(ctx.proxy, set(range(0, src.n_frames, SAMPLE_EVERY)), size)
    samples, prev = {}, None
    for f in sorted(frames):  # a frame identical to the previous sample reads the same: skip the OCR
        g = frames[f].max(axis=2)
        if prev is not None and int(np.abs(g.astype(np.int16) - prev[1]).max()) <= SAME_FRAME:
            samples[f] = samples[prev[0]]
        else:
            samples[f] = ocr(frames[f])
            prev = (f, g.astype(np.int16))
    events = []
    for tr in (piece for t in link(samples) for piece in split_changes(t)):
        if tr[-1][0] - tr[0][0] + 1 < MIN_TEXT_FRAMES - SAMPLE_EVERY:
            continue
        start, end = refine(ctx.proxy, tr, size, src.n_frames)
        if end - start < MIN_TEXT_FRAMES:
            continue
        text = Counter(t for _, _, t, _ in tr).most_common(1)[0][0]
        boxes = [b for _, b, _, _ in tr]
        med = _median_box(boxes)
        # steadiest: at the median box and furthest from both ends (animations live at the ends)
        mid = (start + end) / 2
        at_rest = [d for d in tr if box_iou(d[1], med) > 0.9] or tr
        steady = min(at_rest, key=lambda d: abs(d[0] - mid))[0]
        events.append({"text": text, "start": start, "end": end, "box": med, "steady": steady, "lines": 1,
                       "samples": len(tr), "boxes": [[f, b.x, b.y, b.w, b.h] for f, b, _, _ in tr],
                       "score": float(np.mean([s for *_, s in tr]))})
    items = []
    for k, e in enumerate(sorted(merge_lines(events), key=lambda e: e["start"])):
        style = measure_style(frames[e["steady"]], e["box"], e["lines"])
        items.append(ir.Item(id=f"text_{k}", track=NAME, start=e["start"], end=e["end"], conf=e["score"],
                             tool="rapidocr pp-ocr", data={"text": e["text"], "box": e["box"].model_dump(),
                                                          "boxes": e["boxes"], "samples": e["samples"],
                                                          "lines": e["lines"], "steady": e["steady"], "style": style}))
    return items
