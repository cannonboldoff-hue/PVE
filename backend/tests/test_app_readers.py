import base64
import json

from app import ir
from tools import app_readers as ar


def blob(d: dict) -> str:
    s = json.dumps(d).encode("utf-16-le")
    return base64.b64encode(len(s).to_bytes(4, "little") + b"\0\0\0\0" + s).decode()


def test_kf_value_types():
    assert ar.kf_value("-914,100.,0,0") == 100.0
    assert ar.kf_value("-914,0.5:0.25") == [0.5, 0.25]
    assert ar.kf_value("-914,true,0") is True


def test_source_text_reads_text_font_fill():
    st = ar.source_text(blob({"mTextParam": {"mAlignment": 2, "mStyleSheet": {
        "mText": "HELLO", "mFontName": {"mParamValues": [[0, "Muli-Bold"], [5, "58724202-DD58-420B-A6F0-2FBBC812F7B5"]]},
        "mFontSize": {"mParamValues": [[0, 58]]}, "mFillColor": {"mParamValues": [[0, 0x0000FF]]}}}}))
    assert st["text"] == "HELLO" and st["font"] == "Muli-Bold" and st["size"] == 58
    assert st["fill"] == "#FF0000"  # Premiere stores 0xBBGGRR
    assert ar.source_text("not base64!") is None


def test_scene_to_valid_template_with_fade_in():
    samples = [{"t": t / 30, "opacity": min(1.0, t / 10), "box": [400, 900, 280, 60]} for t in range(0, 60, 2)]
    scene = {"app": "after_effects", "file": "x.aep", "name": "main", "width": 1080, "height": 1920, "src_fps": 30, "duration": 2.0,
             "unsupported": ["effectcraft import: effects: Fill"],
             "layers": [ar.layer("text", "title", 0.0, 2.0, text="HI", size_px=60, samples=samples),
                        ar.layer("solid", "bg", 0.0, 2.0, color="#112233",
                                 effects=[{"match": "ADBE Fill", "name": "Fill", "params": {}}])]}
    t = ar.to_template(scene, "k")
    t = ir.Template.model_validate(t.model_dump(mode="json"))
    assert [(s.start, s.end) for s in t.slots] == [(0, 60)]  # one slot tiles the whole template
    assert t.texts[0].anim_in.value == "fade" and t.texts[0].anim_out.value == "none"
    assert t.texts[0].keys[0].box.x == 400 / 1080
    assert t.effects[0].type.value == "other" and t.effects[0].type.raw["match"] == "ADBE Fill"
    assert t.unsupported == ["effectcraft import: effects: Fill"]


def test_anim_samples_pop_and_slide():
    def k(f, x, w):
        return ir.Key(frame=f, box=ir.Box(x=x, y=0.5, w=w, h=w / 4))
    pop = [k(0, 0.45, 0.05), k(4, 0.4, 0.2), k(30, 0.4, 0.2), k(60, 0.4, 0.2)]
    assert ar.anim_samples(pop, True, 90)[0] == "pop"
    slide = [k(0, 0.0, 0.2), k(6, 0.4, 0.2), k(30, 0.4, 0.2), k(60, 0.4, 0.2)]
    assert ar.anim_samples(slide, True, 90)[0] == "slide_right"


def vn_folder(tmp_path):
    """A two-clip VN template folder: black card, then a clip that fades in; one layer clip, one title."""
    kf = lambda t=0, **kw: {"timeOffsetUs": t, "alpha": 1, "centerX": 0.5, "centerY": 0.5, "scale": 1, **kw}  # noqa: E731
    clip = lambda start, dur, media, **kw: {"startTimeUs": start, "displayDurationUs": dur, "beginUs": 0, "endUs": dur, "mSpeed": 1,  # noqa: E731
                                            "scaleMode": 1001, "mediaInfo": media, "keyframeContext": {"original": kf()}, **kw}
    video = {"type": 1000, "imageWidth": 1080, "imageHeight": 1920, "videoPath": "vnTargetDirectory:///Asset/a.mov",
             "location": {"latitude": 1.5, "longitude": 2.5}}
    steps = {
        "renderRatioWidth": 1080, "renderRatioHeight": 1920, "mDurationMs": 2000, "tailTransition": {"type": 1001, "intervalUs": 200000},
        "mVideoSlices": [clip(0, 1000000, {"type": 1002, "imagePath": "vnTargetDirectory:///Asset/000000FF.svg"}, manualLocked=True),
                         clip(1000000, 500000, video, transition={"type": 1001, "intervalUs": 200000}, speedCurve=[1, 2]),
                         clip(1500000, 500000, video)],
        "mStickerItems": [{"mZOrder": 2, "stickerVideoSlice": clip(
            500000, 1000000, video, mCropRectF={"left": 0, "right": 1, "top": 0.25, "bottom": 0.75},
            keyframeContext={"original": kf(), "keyframeArray": [kf(-9000000, scale=0.5), kf(-8000000, scale=0.5), kf(500000, scale=1)]})}],
        "mSubtitleItems": [{"startUs": 0, "lengthUs": 1000000, "textArray": ["hello"], "fontName": "Love", "fontPointSize": 36, "alignment": 2,
                            "animatorParameters": {"inItem": {"type": 0, "interval": 0.6}, "outItem": {"type": 100, "interval": 0.5}},
                            "keyframeContext": {"original": kf(color=-907021313, centerY=0.25)}}],
        "mFlowFrames": [{}]}
    (tmp_path / "Data" / "P" / "Steps").mkdir(parents=True)
    (tmp_path / "Data" / "BriefSteps").mkdir()
    (tmp_path / "Data" / "P" / "Steps" / "1.json").write_text(json.dumps(steps))
    (tmp_path / "Data" / "BriefSteps" / "1.json").write_text(json.dumps({"latestPageLocalID": "P", "pages": [{"localID": "P", "step": "/P/Steps/1.json"}]}))
    (tmp_path / "Data" / "brief.json").write_text(json.dumps({"briefSteps": ["BriefSteps/1.json"]}))
    (tmp_path / "template.json").write_text(json.dumps({"title": "T", "clips": 3, "video_filename": "p.mp4"}))
    return tmp_path


def test_vn_folder_to_template(tmp_path):
    scene = ar.read(vn_folder(tmp_path))
    assert "latitude" not in json.dumps(scene)  # GPS never leaves the reader
    t = ir.Template.model_validate(ar.to_template(scene, "k").model_dump(mode="json"))
    assert [(s.start, s.end, s.media.value, s.media.binding) for s in t.slots] == [
        (0, 30, "other", "keep"), (30, 45, "video", "swap"), (45, 60, "video", "swap")]
    assert t.slots[0].media.raw["colour"] == "#000000"
    join, cut = t.transitions  # one per boundary: a clip's transition is centred on its first frame, a hard cut has no width
    assert (join.after_slot, join.type.value, join.start, join.end) == ("s01", "fade_black", 27, 33)
    assert (cut.after_slot, cut.type.value, cut.start, cut.end) == ("s02", "cut", 45, 45)
    assert t.narrative["source"]["tail"] == {"code": 1001, "type": "fade_black", "frames": 6}  # the reel-end fade joins no two slots
    o = t.overlays[0]  # cropped to half height, so half the frame tall; the parent clip's old keys clamp to its start
    assert (o.start, o.end, o.binding) == (15, 45, "swap")
    assert [(k.frame, k.box.w, k.box.h) for k in o.keys] == [(15, 0.5, 0.25), (30, 1.0, 0.5)]
    x = t.texts[0]
    assert (x.text.value, x.style.fill, x.anim_in.value, x.anim_out.value, x.anim_out_frames) == ("hello", "#C9EFF3", "none", "fade", 15)
    assert abs(x.keys[0].box.y + x.keys[0].box.h / 2 - 0.25) < 1e-6  # VN positions are centres, y down
    assert t.narrative["source"]["swappable"] == t.narrative["source"]["declared_clips"] == 3
    assert any("speedCurve" in u for u in t.unsupported) and any("mFlowFrames" in u for u in t.unsupported)  # unread fields are named
