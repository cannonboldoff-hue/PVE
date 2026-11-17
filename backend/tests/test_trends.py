"""Trend-style template features: shake windows, zoom punch, word reveal / highlight, text fit and rotation, text
paths, new effects, shape masks, multi-box tiles, match cuts, shot list, optional gold scoring."""
import subprocess

import numpy as np
import pytest

from app import ir
from app.clients import ff
from app.evidence import camera, masks, match_cuts, text
from app.render import capabilities, overlay, shot, textlayer
from app.stages import fusion, requirements
from synth import marker_clip


def _path(n=60, scale=None, jitter=None):
    p = np.zeros((n, 4))
    p[:, 0] = 1.0 if scale is None else scale
    p[:, 1], p[:, 2] = 0.5, 0.5
    if jitter is not None:
        p[:, 1] += jitter
    return p


def test_shake_window_found_where_it_shakes():
    j = np.zeros(90)
    j[30:50] = 0.01 * np.sin(np.arange(20) * 2.5)  # ~12 Hz burst
    ws = camera.shake_windows(_path(90, jitter=j))
    assert len(ws) == 1
    a, b, amp, hz = ws[0]
    assert 26 <= a <= 32 and 48 <= b <= 54 and amp > camera.SHAKE_MIN and hz > camera.SHAKE_HZ
    assert camera.shake_windows(_path(90, jitter=0.01 * np.sin(np.arange(90) * 2.5))) == []  # whole slot: summary


def test_zoom_punch_found_and_kept_in_keys():
    s = np.ones(60)
    s[30:36] = [1.05, 1.15, 1.25, 1.2, 1.1, 1.03]
    p = _path(60, scale=s)
    hits = camera.punches(p)
    assert len(hits) == 1 and hits[0][1] == 32 and hits[0][3] > 1.15
    keys = camera.keyframes(p, hits)
    assert max(k[1] for k in keys) == pytest.approx(1.25)  # the smoothed path alone would flatten the peak


def test_shake_windows_render_gated():
    expr = shot.camera_chain([{"frame": 0, "box": {"x": 0, "y": 0, "w": 1, "h": 1}}],
                             [{"start": 10, "end": 20, "amp": 0.01, "hz": 8}])
    assert "between(on,10,19)" in expr
    assert shot.shake_windows({"amp": 0.01, "hz": 8}) == [{"amp": 0.01, "hz": 8}]


def test_word_reveal_by_words_not_characters():
    b = ir.Box(x=0.1, y=0.4, w=0.8, h=0.1)
    words = [(0, b, "wait", 0.9), (8, b, "wait for", 0.9), (16, b, "wait for it", 0.9), (24, b, "wait for it", 0.9)]
    got = text.reveal_words(words, "wait for it")
    assert [w["start"] for w in got] == [0, 8, 16]
    chars = [(0, b, "wa", 0.9), (2, b, "wai", 0.9), (4, b, "wait f", 0.9), (6, b, "wait fo", 0.9),
             (8, b, "wait for it", 0.9)]
    assert text.reveal_words(chars, "wait for it") == []  # typewriter: grows by characters


def _ev(value, raw=None, anim="none", **kw):
    e = {"id": "t01", "start": 0, "end": 60, "text": {"value": value, "raw": raw or value},
         "keys": [{"frame": 30, "box": {"x": 0.2, "y": 0.4, "w": 0.6, "h": 0.05}, "rotation": 0.0}],
         "style": {"font": "Arial", "bold": True, "size": 0.05, "fill": "#FFFFFF", "outline": "#000000", "box": None},
         "anim_in": {"value": anim}, "anim_out": {"value": "none"}, "anim_in_frames": 6, "anim_out_frames": 0}
    return {**e, **kw}


def test_text_fit_shrinks_long_swap_and_wraps():
    ref = _ev("SAVE THIS")
    fs0, t0 = textlayer.fit(ref)
    fs1, t1 = textlayer.fit(_ev("SAVE THIS FOR YOUR NEXT TRIP TO GOA PLEASE", "SAVE THIS"))
    assert t0 == "SAVE THIS" and fs1 < fs0
    assert textlayer.width_per_px(t1, "Arial", True) * fs1 <= textlayer.SAFE_W * textlayer.W + 1
    fs2, t2 = textlayer.fit(_ev("ONE TWO THREE FOUR", "LINE ONE\nLINE TWO"))
    assert t2.count("\n") == 1 and fs2 <= textlayer.font_size("LINE ONE\nLINE TWO", 0.05, "Arial", True)


def test_word_timing_rotation_and_key_words_in_ass():
    e = _ev("wait for it", anim="word_highlight", words=[{"i": 0, "start": 0}, {"i": 1, "start": 9},
                                                         {"i": 2, "start": 15}], highlight="#00FF00")
    e["keys"][0]["rotation"] = -8.0
    tags, body, _ = textlayer.event_tags(e, 30)
    assert "\\frz8.0" in tags and "\\1c&H00FF00&" in tags
    assert body.count("\\k") == 3 and "\\k30" in body and "\\k20" in body  # 9 frames = 30 cs, 6 frames = 20 cs
    k = _ev("best food in town", highlight="#FFD400", key_words=[1])
    _, body, _ = textlayer.event_tags(k, 30)
    assert "\\1c&H00D4FF&}food" in body


def test_text_path_needs_engine_only_when_it_moves():
    still = _ev("hello")
    still["keys"] += [{"frame": f, "box": still["keys"][0]["box"]} for f in range(8, 56, 2)]
    assert overlay.path_keys(still) == []
    fly = _ev("hello")
    fly["keys"] += [{"frame": f, "box": {"x": 0.2 + 0.01 * f / 2, "y": 0.4, "w": 0.6, "h": 0.05}}
                    for f in range(8, 56, 2)]
    assert overlay.path_keys(fly)
    div, tw = overlay._text_html(0, fly, 1080, 1920)
    assert any('ease:"none"' in t for t in tw)


def test_new_effect_filters_run():
    fx = [{"type": {"value": k}, "start": 5, "end": 15, "strength": 1.0, "params": {}}
          for k in ("glow", "scanlines", "glitch", "grain")]
    vf = ",".join(capabilities.effect_filter(e) for e in fx) + ",format=yuv420p"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc2=s=1080x1920:r=30:d=1", "-vf", vf, "-f", "null", "-"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert capabilities.effect("zoom_punch") == ("camera", "")
    assert capabilities.transition("spin")[0] in ("overlay:spin", "ffmpeg:radial")


def test_shape_mask_render(tmp_path):
    clip = marker_clip(3, 30, tmp_path / "m.mp4", textured=True)
    out = tmp_path / "r.mp4"
    mask = {"shape": "circle", "bg": "#FF0000", "keys": [{"frame": 0, "box": {"x": 0.25, "y": 0.35, "w": 0.5, "h": 0.3}}]}
    shot.prep({"path": str(clip), "in": 0, "frames": 30, "mask": mask}, out)
    assert ff.count_frames(out) == 30
    f = ff.decode(out, 108, 192)[10].astype(int)
    assert abs(f[5, 5] - [255, 0, 0]).max() < 40  # corner: the background colour
    assert abs(f[96, 54] - [255, 0, 0]).max() > 40  # centre: the footage


def test_multi_box_tiles_get_their_own_motion(tmp_path):
    a = marker_clip(1, 40, tmp_path / "a.mp4", textured=True)
    b = marker_clip(2, 40, tmp_path / "b.mp4", textured=True)
    out = tmp_path / "r.mp4"
    boxes = [{"x": 0, "y": 0, "w": 1, "h": 0.5}, {"x": 0, "y": 0.5, "w": 1, "h": 0.5}]
    tp = [{}, {"reverse": True, "speed_curve": [(0.0, 0.5)],
               "camera_path": [{"frame": 0, "box": {"x": 0, "y": 0, "w": 1, "h": 1}},
                               {"frame": 29, "box": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}}]}]
    g = shot.layout_graph({"layout_boxes": boxes, "tile_params": tp, "frames": 30}, [(str(a), 0), (str(b), 0)], 30)
    assert "reverse" in g and "zoompan" in g and g.count("trim=") == 2
    shot.prep({"path": str(a), "in": 0, "frames": 30, "layout_boxes": boxes, "tile_paths": [str(b)],
               "tile_params": tp}, out)
    assert ff.count_frames(out) == 30


def test_match_cut_edges_line_up_colours_change():
    img = np.zeros((90, 160, 3), np.uint8)
    img[20:70, 50:110] = (200, 40, 40)
    other = np.zeros_like(img)
    other[20:70, 50:110] = (40, 200, 40)
    other[:, :] = np.where(other.sum(-1, keepdims=True) > 0, other, (0, 0, 120))
    ov, _ = match_cuts.edge_overlap(img, other)
    assert ov > match_cuts.EDGE_MATCH and match_cuts.colour_change(img, other) > match_cuts.COLOUR_CHANGE
    moved = np.zeros_like(img)
    moved[5:30, 5:40] = (40, 200, 40)
    assert match_cuts.edge_overlap(img, moved)[0] < match_cuts.EDGE_MATCH


def test_shape_region_measures_circle_box():
    rng = np.random.default_rng(1)
    n, h, w = 8, 90, 160
    yy, xx = np.mgrid[:h, :w]
    inside = ((xx - 80) / 40) ** 2 + ((yy - 45) / 30) ** 2 <= 1
    frames = np.zeros((n, h, w, 3), np.uint8)
    for k in range(n):
        frames[k][inside] = rng.integers(0, 255, (inside.sum(), 3))
    r = masks.shape_region(frames)
    assert r and abs(r["box"]["x"] - 40 / 160) < 0.03 and abs(r["box"]["w"] - 80 / 160) < 0.03
    assert 0.7 < r["fill"] < 0.86 and r["bg"] == "#000000"
    assert fusion.mask_shape("", r["fill"])[0] == "ellipse" and fusion.mask_shape("Heart shape")[0] == "heart"


def _template_with_match_cut() -> ir.Template:
    slots = [ir.Slot(id="s01", start=0, end=30), ir.Slot(id="s02", start=30, end=60)]
    ev = ir.Evidence(items=[ir.Item(id="match_cuts_0", track="match_cuts", start=30, end=30, conf=0.5,
                                    data={"frame": 30, "box": {"x": 0.2, "y": 0.2, "w": 0.5, "h": 0.5}})])
    trans = [ir.Transition(after_slot="s01", start=30, end=30)]
    fusion.match_cuts(ev, slots, trans, {})
    assert trans[0].params["match_cut"] and trans[0].type.evidence == ["match_cuts_0"]
    return ir.Template(v=4, key="k", n_frames=60, audio="", slots=slots, transitions=trans)


def test_match_cut_reaches_the_shot_list():
    t = _template_with_match_cut()
    req = requirements.derive(t)
    assert any("Match cut from shot 1" in x for x in req[1].instructions)
    assert not any("Match cut" in x for x in req[0].instructions)


def test_optional_gold_fields_scored_only_when_labelled():
    from tools import score

    pred = {"cuts": [30], "effects_all": [{"type": "glitch", "start": 100, "end": 106}], "shake": [(120, 132)],
            "match_cuts": [30], "layers": [], "texts": [{"text": "x", "start": 0, "end": 60, "anim_in": "bounce"}]}
    rows = score.score({"cuts": [30]}, pred)
    assert set(rows) == {"cuts", "texts"}  # texts is a base track; none of the optional ones without labels
    lab = {"cuts": [30], "effects": [{"type": "glitch", "frame": 100, "length": 6}], "shake": [{"start": 120, "end": 130}],
           "match_cuts": [30], "texts": [{"text": "x", "start": 0, "end": 60, "anim_in": "bounce"}]}
    rows = score.score(lab, pred)
    assert rows["fx:glitch"]["f1"] == 1.0 and rows["shake"]["f1"] == 1.0 and rows["match_cuts"]["f1"] == 1.0
    assert rows["text_anim"]["f1"] == 1.0
