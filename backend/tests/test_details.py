import pytest

from app.clients import video
from app.models import CaptionStyle, PatchOp, Plan, PlanShot
from app.stages import editor, orchestrator
from app.stages import plan as plan_mod
from helpers import ff

BS = chr(92)


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    p = tmp_path_factory.mktemp("c") / "a.mp4"
    ff("-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=4", "-f", "lavfi", "-i", "sine=duration=4",
       "-pix_fmt", "yuv420p", "-shortest", str(p))
    return str(p)


def test_caption_animation_tags():
    plan = Plan(shots=[PlanShot(shot_id=i, asset_id="a", path="x", src_in=0, src_out=2, caption="Hi", caption_animation=a)
                       for i, a in enumerate(["none", "fade", "pop", "slide_up"], 1)])
    lines = [l for l in editor._ass(plan, [0, 2, 4, 6]).splitlines() if l.startswith("Dialogue")]
    assert BS + "fad" not in lines[0] and lines[0].endswith("}Hi")
    assert BS + "fad(180,180)" in lines[1] and BS + "fscx60" in lines[2] and BS + "move(540,1660,540,1590" in lines[3]


def test_caption_style_in_ass():
    st = CaptionStyle(font="Impact", size=96, color="#FF0000", outline_color="#0000FF", position="top", uppercase=True,
                      emphasis_words=["friends"], emphasis_color="#00FF00", bold=False)
    plan = Plan(shots=[PlanShot(shot_id=1, asset_id="a", path="x", src_in=0, src_out=2, caption="we are friends", caption_style=st,
                                caption_animation="slide_up")])
    line = [l for l in editor._ass(plan, [0]).splitlines() if l.startswith("Dialogue")][0]
    assert BS + "an8" in line and BS + "fnImpact" in line and BS + "fs96" in line and BS + "b0" in line
    assert BS + "c&H0000FF&" in line  # red -> ASS blue-green-red order
    assert BS + "3c&HFF0000&" in line  # blue outline
    assert "WE ARE {" + BS + "c&H00FF00&}FRIENDS{" + BS + "c&H0000FF&}" in line  # emphasis word recoloured, then back
    assert BS + "move(540,400,540,330" in line  # slide_up starts below the top anchor


def test_patch_new_fields_are_enum_checked():
    plan = Plan(shots=[PlanShot(shot_id=1, asset_id="a", path="x", src_in=0, src_out=2)])
    notes = plan_mod.apply_patches(plan, [PatchOp(shot_id=1, field="fit", value="blur_fit"),
                                          PatchOp(shot_id=1, field="animation", value="zoom_out"),
                                          PatchOp(shot_id=1, field="caption_animation", value="spin")], lambda _i: None)
    assert plan.shots[0].fit == "blur_fit" and plan.shots[0].animation == "zoom_out" and len(notes) == 1


@pytest.mark.parametrize("fit,anim", [("blur_fit", "none"), ("cover", "zoom_in"), ("blur_fit", "zoom_out")])
def test_fit_and_animation_render(clip, tmp_path, fit, anim):
    out = tmp_path / "p.mp4"
    editor.prep_clip({"path": clip, "in": 0, "out": 2, "speed": 1.0, "fit": fit, "animation": anim}, out)
    i = video.info(out)
    assert (i["width"], i["height"], i["has_audio"]) == (1080, 1920, True) and abs(i["duration"] - 2) < 0.3


def test_blur_fit_keeps_whole_frame(clip, tmp_path):
    """16:9 source: with blur_fit the sharp frame is 1080 wide and ~608 tall, so rows far from centre are the blurred backdrop."""
    out = tmp_path / "b.mp4"
    editor.prep_clip({"path": clip, "in": 0, "out": 2, "speed": 1.0, "fit": "blur_fit", "animation": "none"}, out)
    from PIL import Image

    png = tmp_path / "f.png"
    ff("-ss", "1", "-i", str(out), "-frames:v", "1", str(png))
    im = Image.open(png).convert("L")
    # sharp test pattern has large pixel-to-pixel contrast; the blurred backdrop above/below does not
    def contrast(y):
        row = [im.getpixel((x, y)) for x in range(0, 1080, 3)]
        return max(abs(a - b) for a, b in zip(row, row[1:]))
    assert contrast(960) > 40 and contrast(200) < 30


def test_patch_caption_style_fields():
    plan = Plan(shots=[PlanShot(shot_id=1, asset_id="a", path="x", src_in=0, src_out=2)])
    notes = plan_mod.apply_patches(plan, [PatchOp(shot_id=1, field="caption_color", value="#112233"),
                                          PatchOp(shot_id=1, field="caption_size", value=100),
                                          PatchOp(shot_id=1, field="caption_position", value="center"),
                                          PatchOp(shot_id=1, field="caption_color", value="red")], lambda _i: None)
    st = plan.shots[0].caption_style
    assert (st.color, st.size, st.position) == ("#112233", 100, "center") and len(notes) == 1


def test_grade_keeps_audio_and_changes_pixels(clip, tmp_path):
    from PIL import Image

    plain, graded = tmp_path / "p.mp4", tmp_path / "g.mp4"
    base = {"path": clip, "in": 0, "out": 2, "speed": 1.0, "fit": "cover", "animation": "none"}
    editor.prep_clip({**base, "grade": {"preset": "none", "brightness": 0, "contrast": 1, "saturation": 1}}, plain)
    editor.prep_clip({**base, "grade": {"preset": "vintage", "brightness": -0.2, "contrast": 1.2, "saturation": 0.5}}, graded)
    assert video.info(graded)["has_audio"] and abs(video.info(graded)["duration"] - 2) < 0.3

    def mean(path):
        png = tmp_path / (path.stem + ".png")
        ff("-ss", "1", "-i", str(path), "-frames:v", "1", str(png))
        px = list(Image.open(png).convert("RGB").resize((20, 20)).getdata())
        return [sum(c[i] for c in px) / len(px) for i in range(3)]

    assert max(abs(a - b) for a, b in zip(mean(plain), mean(graded))) > 10


@pytest.mark.parametrize("n,border,tilt", [(2, True, 4), (4, True, 4), (5, False, 0), (6, True, 6), (3, True, 0)])
def test_collage_tiles(clip, tmp_path, n, border, tilt):
    out = tmp_path / "col.mp4"
    params = {"path": clip, "tile_paths": [clip] * (n - 1), "in": 0, "out": 2, "speed": 1.0, "fit": "cover", "animation": "none",
              "grade": None, "collage": {"tiles": n, "background": "#F7C6D9", "border": border, "tilt": tilt}}
    editor.prep_clip(params, out)
    i = video.info(out)
    assert (i["width"], i["height"], i["has_audio"]) == (1080, 1920, True) and abs(i["duration"] - 2) < 0.3


def test_collage_background_visible(clip, tmp_path):
    from PIL import Image

    out = tmp_path / "col.mp4"
    editor.prep_clip({"path": clip, "tile_paths": [clip] * 3, "in": 0, "out": 2, "speed": 1.0, "fit": "cover", "animation": "none",
                      "grade": None, "collage": {"tiles": 4, "background": "#F7C6D9", "border": True, "tilt": 0}}, out)
    png = tmp_path / "c.png"
    ff("-ss", "1", "-i", str(out), "-frames:v", "1", str(png))
    im = Image.open(png).convert("RGB")
    assert all(abs(a - b) < 12 for a, b in zip(im.getpixel((20, 960)), (0xF7, 0xC6, 0xD9)))  # margin between tiles shows the backdrop
    assert im.getpixel((300, 500)) != im.getpixel((20, 960))  # a tile sits inside the margin
