"""Comparators shared by the scoring harness (tools/score.py) and validation (stages/roundtrip.py)."""
import difflib
import re

from ..ir import Box


def _prf(tp: int, n_pred: int, n_truth: int) -> tuple[float, float, float]:
    p = tp / n_pred if n_pred else 1.0
    r = tp / n_truth if n_truth else 1.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def match_events(pred: list[int], truth: list[int], tol_frames: int) -> tuple[float, float, float, float]:
    """One-to-one matching of point events within tol_frames, closest pairs first.
    Returns (precision, recall, f1, mean absolute frame error over matches)."""
    pairs = sorted((abs(p - t), i, j) for i, p in enumerate(pred) for j, t in enumerate(truth) if abs(p - t) <= tol_frames)
    used_p, used_t, errs = set(), set(), []
    for d, i, j in pairs:
        if i not in used_p and j not in used_t:
            used_p.add(i); used_t.add(j); errs.append(d)
    return (*_prf(len(errs), len(pred), len(truth)), sum(errs) / len(errs) if errs else 0.0)


def span_iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else float(a == b)


def match_spans(pred: list[tuple[int, int]], truth: list[tuple[int, int]], min_iou: float
                ) -> tuple[float, float, float, float]:
    """One-to-one matching of [start, end) spans with IoU >= min_iou, best pairs first.
    Returns (precision, recall, f1, mean absolute boundary error: mean of |start| and |end| differences)."""
    pairs = sorted(((span_iou(p, t), i, j) for i, p in enumerate(pred) for j, t in enumerate(truth)), reverse=True)
    used_p, used_t, errs = set(), set(), []
    for iou, i, j in pairs:
        if iou < min_iou or (iou == 0 and min_iou == 0):
            break
        if i not in used_p and j not in used_t:
            used_p.add(i); used_t.add(j)
            errs.append((abs(pred[i][0] - truth[j][0]) + abs(pred[i][1] - truth[j][1])) / 2)
    return (*_prf(len(errs), len(pred), len(truth)), sum(errs) / len(errs) if errs else 0.0)


def _xywh(b) -> tuple[float, float, float, float]:
    if isinstance(b, Box):
        return b.x, b.y, b.w, b.h
    if isinstance(b, dict):
        return b["x"], b["y"], b["w"], b["h"]
    return tuple(b)  # type: ignore[return-value]


def box_iou(a, b) -> float:
    """IoU of two boxes given as Box, {x,y,w,h} or (x, y, w, h)."""
    ax, ay, aw, ah = _xywh(a)
    bx, by, bw, bh = _xywh(b)
    iw = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    ih = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def text_similarity(a: str, b: str) -> float:
    """0..1, 1 for strings equal after lower-casing and collapsing whitespace."""
    a, b = _norm(a), _norm(b)
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()
