from pytest import approx

from app.ir import Box
from app.stages.compare import box_iou, match_events, match_spans, span_iou, text_similarity


def test_match_events():
    assert match_events([10, 20, 30], [10, 20, 30], 0) == (1.0, 1.0, 1.0, 0.0)
    p, r, f1, mae = match_events([11, 22, 50], [10, 20, 30], 2)
    assert (p, r, mae) == (approx(2 / 3), approx(2 / 3), approx(1.5))
    assert f1 == approx(2 / 3)
    # one prediction cannot match two truths
    p, r, _, _ = match_events([10], [9, 11], 1)
    assert (p, r) == (1.0, 0.5)
    # closest pair wins
    _, _, _, mae = match_events([10, 12], [11], 2)
    assert mae == 1.0
    assert match_events([], [], 2)[:3] == (1.0, 1.0, 1.0)
    assert match_events([5], [], 2)[:2] == (0.0, 1.0)


def test_match_spans():
    assert span_iou((0, 10), (5, 15)) == approx(5 / 15)
    assert span_iou((0, 10), (20, 30)) == 0
    p, r, f1, mae = match_spans([(0, 10), (40, 50)], [(1, 11), (100, 110)], 0.5)
    assert (p, r) == (0.5, 0.5) and mae == 1.0
    assert match_spans([(0, 10)], [(8, 20)], 0.5)[:2] == (0.0, 0.0)


def test_box_iou():
    a = Box(x=0, y=0, w=0.5, h=0.5)
    assert box_iou(a, a) == 1.0
    assert box_iou(a, (0.25, 0, 0.5, 0.5)) == approx(1 / 3)
    assert box_iou({"x": 0.6, "y": 0.6, "w": 0.1, "h": 0.1}, a) == 0.0


def test_text_similarity():
    assert text_similarity("Hello  World", "hello world") == 1.0
    assert text_similarity("", "") == 1.0
    assert 0.8 < text_similarity("hello world", "helo world") < 1.0
    assert text_similarity("abc", "xyz") == 0.0
