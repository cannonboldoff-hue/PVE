import pytest

from app.clients import twelvelabs
from app.models import Match, ShotSpec
from app.stages import brief as brief_mod
from app.stages import plan as plan_mod
from app.stages import preproduction, reference, styles


def test_caption_style_from_analysis_text():
    st = styles.caption_style({"on_screen_text": "WE'RE JUST FRIENDS", "caption_font": "bold playful rounded font",
                               "caption_color": "bright yellow text", "caption_position": "bottom center",
                               "caption_size": "large", "caption_emphasis": "FRIENDS, just"})
    assert (st.font, st.size, st.color, st.position, st.uppercase) == ("Comic Sans MS", 96, "#FFD400", "bottom", True)
    assert st.emphasis_words == ["FRIENDS", "just"]
    top = styles.caption_style({"caption_position": "top of the frame", "caption_color": "#ff00aa", "caption_font": "elegant script"})
    assert (top.position, top.color, top.font) == ("top", "#FF00AA", "Segoe Script")
    assert styles.caption_style({}).font == "Arial"  # nothing known -> defaults


def test_caption_timing_is_relative_to_the_shot():
    assert styles.caption_timing({"start": 4.0, "caption_start": 4.5, "caption_end": 7.0}) == (0.5, 3.0)
    assert styles.caption_timing({"start": 4.0}) == (None, None)
    assert styles.caption_timing({"start": 4.0, "caption_start": 4.1, "caption_end": 4.2}) == (None, None)  # too short to be real


@pytest.mark.parametrize("look,preset", [("warm golden tones, soft", "warm"), ("cool blue tint", "cool"), ("vintage film grain", "vintage"),
                                         ("black and white", "noir"), ("neutral", "none"), ("", "none")])
def test_grade_presets(look, preset):
    assert styles.grade({"color_look": look}).preset == preset


def test_grade_numbers():
    g = styles.grade({"color_look": "bright, high contrast, vivid colours"})
    assert (g.brightness, g.contrast, g.saturation) == (0.1, 1.2, 1.3)
    m = styles.grade({"color_look": "dark moody muted"})
    assert (m.brightness, m.saturation) == (-0.1, 0.8)
    assert styles.grade({"color_look": "neutral"}).is_neutral


def test_layout_detection():
    lay, col = styles.layout({"background": "photo collage on a pastel pink backdrop", "collage_tiles": 5,
                              "collage_background": "light pink", "collage_style": "tilted white frames"})
    assert (lay, col.tiles, col.background, col.border, col.tilt) == ("collage", 5, "#F7C6D9", True, 4.0)
    assert styles.layout({"background": "a bathroom mirror"})[0] == "single"
    assert styles.layout({"background": "collage", "layout": "single"})[0] == "single"  # an explicit single wins
    assert styles.layout({"layout": "collage", "collage_style": "straight, no border"})[1].tilt == 0.0
    assert styles.layout({"background": "collage"})[1].tiles == 4 and styles.layout({"layout": "collage", "collage_tiles": 99})[1].tiles == 6


def test_template_carries_the_new_structure():
    analysis = {"shots": [
        {"start": 0, "end": 2.5, "description": "d", "subject": "s", "action": "a", "on_screen_text": "HAPPY BIRTHDAY",
         "caption_font": "impact", "caption_color": "white", "caption_position": "middle", "caption_start": 0.4, "caption_end": 2.2,
         "color_look": "warm", "layout": "single"},
        {"start": 2.5, "end": 6.5, "description": "d2", "subject": "s2", "action": "a2", "background": "photo collage",
         "collage_tiles": 4, "collage_background": "#F7C6D9", "color_look": "vintage"}]}
    t = brief_mod.extract_template(analysis)
    assert (t[0].caption_style.font, t[0].caption_style.position, t[0].caption_start, t[0].caption_end, t[0].grade.preset) == \
        ("Impact", "center", 0.4, 2.2, "warm")
    assert (t[1].layout, t[1].collage.tiles, t[1].asset_type, t[1].grade.preset) == ("collage", 4, "photo", "vintage")
    # the LLM fill only rewrites content, so these structural fields survive it
    filled = t[0].model_copy(update={"purpose": "new", "text": "HELLO"})
    assert filled.caption_style.font == "Impact" and filled.grade.preset == "warm"


def test_pick_analysis_prefers_the_run_matching_detected_cuts():
    cuts = [2.0, 4.0, 6.0, 8.0]  # 5 shots expected
    runs = iter([{"shots": [{"start": 0, "end": 5}, {"start": 5, "end": 10}]},  # 2 shots: off by 3
                 {"shots": [{"start": i * 2, "end": i * 2 + 2} for i in range(5)]}])  # 5 shots: matches
    data, passes = reference.pick_analysis(lambda: next(runs), cuts, 10.0)
    assert len(data["shots"]) == 5 and passes == 2


def test_pick_analysis_trusts_the_model_when_cuts_are_soft():
    calls = []
    data, passes = reference.pick_analysis(lambda: calls.append(1) or {"shots": [{"start": 0, "end": 5}, {"start": 5, "end": 10}]}, [5.0], 10.0)
    assert passes == 1 and len(calls) == 1 and len(data["shots"]) == 2  # one detected cut can't judge a model run


def test_collage_match_uses_ranked_hits_then_the_rest(monkeypatch):
    assets = [{"id": f"a{i}", "tl_indexed_id": f"t{i}", "duration": 5.0, "created": i} for i in range(5)]
    monkeypatch.setattr(twelvelabs, "search", lambda q, limit=10: [
        {"indexed_id": "t3", "start": 0, "end": 5, "rank": 0}, {"indexed_id": "t1", "start": 0, "end": 5, "rank": 1}])
    shot = ShotSpec(shot_id=1, start=0, end=3, purpose="p", subject="friends", action="together", layout="collage",
                    collage={"tiles": 4}).model_dump()
    m = preproduction.match_shot(shot, assets)
    assert m.asset_id == "a3" and m.extra_assets == ["a1", "a0", "a2"] and m.label == "similar"
    few = preproduction.match_shot(shot, assets[:1])
    assert few.label == "missing" and "at least 2" in few.reason
    two = preproduction.match_shot({**shot, "collage": {**shot["collage"], "tiles": 6}}, assets[:2])
    assert len(two.extra_assets) == 1  # fewer pictures than tiles: use what exists


def test_plan_build_collects_collage_tiles():
    assets = {k: {"id": k, "path": f"{k}.mp4", "duration": 5.0} for k in ("a", "b", "c")}
    shot = ShotSpec(shot_id=1, start=0, end=3, purpose="p", subject="s", action="a", layout="collage", collage={"tiles": 3},
                    caption_start=0.5, caption_end=2.5).model_dump()
    plan = plan_mod.build([shot], [Match(shot_id=1, asset_id="a", end=3, extra_assets=["b", "c"]).model_dump()], assets, None, True)
    ps = plan.shots[0]
    assert ps.tiles == ["b.mp4", "c.mp4"] and ps.collage.tiles == 3 and (ps.cap_start, ps.cap_end) == (0.5, 2.5)
    single = plan_mod.build([ShotSpec(shot_id=1, start=0, end=3, purpose="p", subject="s", action="a").model_dump()],
                            [Match(shot_id=1, asset_id="a", end=3).model_dump()], assets, None, True)
    assert single.shots[0].collage is None and single.shots[0].tiles == []
