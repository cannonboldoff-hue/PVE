"""M3: typed meaning behind one interface, fusion with one owner per field. Provider stubbed; no live API."""
from app import ir
from app.stages import extract, fusion, meaning

SRC = ir.Source(key="mkey", fingerprint="fp-m3", n_frames=90, width=540, height=960, src_fps=30)
EV = ir.Evidence(items=[ir.Item(id="cuts_0", track="cuts", start=45, end=45, data={"frame": 45}, tool="t")])


def ans(v, conf=0.9, note=None):
    return {"value": v, "note": note if note is not None else f"because {v}", "confidence": conf}


class Stub(meaning.Session):
    def __init__(self, answers):
        super().__init__("mkey", "unused.mp4", "pegasus")
        self.answers, self.calls = answers, []

    def ask(self, prompt, schema, start=None, end=None):
        self.calls.append((start, end))
        return self.answers(start) if start is not None else {"hook": "q", "arc": "a", "payoff": "p", "cta": "c",
                                                              "overall_style": "bold"}


def _answers(start):
    return {"media": ans("video"), "role": ans("hook" if start == 0 else "payoff"), "function": ans("grab attention"),
            "subject": ans("a baker"), "action": ans("kneads dough"), "shot_size": ans("Close"),
            "angle": ans("top down"), "layout": ans("single"), "camera": ans("zoom in", 0.8),
            "style": {"on_screen_text": "3 tips", "color_look": "warm", "unknown_key": "x"}}


def test_slot_description_round_trips_into_slot_fields():
    ir.save("mkey", "source", SRC)
    slots, _ = fusion.slots_from_cuts(SRC, EV)
    s = Stub(_answers)
    found = meaning.describe_slots(s, slots, EV)
    assert sorted(s.calls) == [(0, 45), (45, 90)]  # each call sees only its measured window
    obs = fusion.fuse(SRC, EV, found, meaning.describe_reel(s, slots))
    a, b = obs.slots
    assert (a.role.value, a.role.raw, a.role.conf, a.role.source) == ("hook", "because hook", 0.9, "pegasus")
    assert b.role.value == "payoff" and a.shot_size.value == "close"  # case-normalised into the vocabulary
    assert a.subject.value == "a baker" and a.camera.value == "zoom_in"
    assert a.camera.conf < 0.8  # evidence-owned field with no measurement yet: trusted less
    assert obs.style[0] == {"on_screen_text": "3 tips", "color_look": "warm"} and obs.narrative["hook"] == "q"
    t = extract.build(obs)
    assert t.slots[0].subject.binding == "swap" and t.slots[0].role.binding == "keep"
    assert t.cuts() == [45] and t.narrative["overall_style"] == "bold"
    # cached: a second describe makes no provider call
    s2 = Stub(_answers)
    meaning.describe_slots(s2, slots, EV)
    assert s2.calls == []


def test_out_of_vocabulary_lands_as_other_with_note():
    a = meaning.normalise("camera", ans("dolly zoom", 0.7, "vertigo effect"))
    assert (a.value, a.note, a.confidence) == ("other", "dolly zoom: vertigo effect", 0.7)
    assert meaning.normalise("role", None).value == "other" and meaning.normalise("role", None).confidence == 0
    assert meaning.normalise("subject", ans("anything goes")).value == "anything goes"  # free text stays


def test_forced_disagreement_is_kept_as_conflict():
    ev = ir.Evidence(items=[*EV.items, ir.Item(id="camera_0", track="camera", start=0, end=45,
                                               data={"value": "static"}, conf=0.9, tool="flow")])
    m = meaning.SlotMeaning(slot="s01", start=0, end=45, provider="gemini",
                            fields={"camera": meaning.Answer(value="zoom_in", note="slow push", confidence=0.8)})
    obs = fusion.fuse(SRC, ev, [m])
    cam = obs.slots[0].camera
    assert (cam.value, cam.source, cam.evidence) == ("static", "camera", ["camera_0"])
    assert cam.conf == 0.9 * fusion.CONFLICT_FACTOR
    assert [(c.path, c.kept, c.other, c.other_source) for c in obs.conflicts] == \
        [("slots.0.camera", "static", "zoom_in", "gemini")]
    t = extract.build(obs)
    assert "slots.0.camera" in t.low_conf


def _gradual(kind, conf):
    ev = ir.Evidence(items=[ir.Item(id="transitions_0", track="transitions", start=40, end=50, conf=conf, tool="t",
                                    data={"frame": 45, "type": kind, "cuts": []})])
    return fusion.slots_from_cuts(SRC, ev)[1], ev


def test_transition_window_is_measured_and_the_name_comes_from_the_model():
    ir.save("mkey", "source", SRC)
    trans, ev = _gradual("fade", 0.4)
    calls = []

    class S(meaning.Session):
        def ask(self, prompt, schema, start=None, end=None):
            calls.append((start, end, prompt))
            return ans("Dissolve", 0.85, "cross mix")

    named = meaning.describe_transitions(S("mkey", "unused.mp4", "pegasus"), trans, SRC.n_frames)
    assert calls[0][:2] == (10, 80) and "'fade'" in calls[0][2]  # window plus a second each side, coarse class sent
    obs = fusion.fuse(SRC, ev, named=named)
    t = obs.transitions[0]
    assert (t.type.value, t.type.source, t.start, t.end) == ("dissolve", "pegasus", 40, 50)
    assert t.render and obs.conflicts[0].other == "fade"


def test_sure_measured_class_keeps_its_name_and_records_the_conflict():
    trans, ev = _gradual("fade_black", 0.8)
    m = meaning.TransitionMeaning(after_slot="s01", start=40, end=50, provider="gemini",
                                  answer=meaning.Answer(value="dissolve", note="mix", confidence=0.9))
    obs = fusion.fuse(SRC, ev, named=[m])
    assert obs.transitions[0].type.value == "fade_black"
    c = obs.conflicts[0]
    assert (c.kept, c.other, c.other_source) == ("fade_black", "dissolve", "gemini")
    other = m.model_copy(update={"answer": meaning.Answer(value="other", note="ink splash", confidence=0.9)})
    assert fusion.fuse(SRC, _gradual("fade", 0.4)[1], named=[other]).transitions[0].type.value == "fade"


def test_video_ai_layers_become_low_confidence_layers_with_a_loss():
    box = {"x": 0.2, "y": 0.3, "w": 0.4, "h": 0.4}
    m = meaning.SlotMeaning(slot="s01", start=0, end=45, provider="gemini", layers=[
        {"kind": "shape_mask", "shape": "circle", "box": box, "confidence": 0.9},
        {"kind": "moving_layer", "box": box, "end_box": {**box, "x": 0.5}, "note": "photo slides right"},
        {"kind": "sparkles", "box": box}, {"kind": "cutout", "box": {"x": 0.1}}])  # last one: no usable box
    t = extract.build(fusion.fuse(SRC, EV, [m]))
    a, b, c = t.layers
    assert (a.kind.value, a.shape, a.kind.conf, len(a.keys)) == ("shape_mask", "circle", fusion.LAYER_CONF, 1)
    assert [k.frame for k in b.keys] == [0, 44] and b.keys[1].box.x == 0.5 and c.kind.value == "other"
    assert a.render == "ffmpeg:geq" and not a.loss  # a circle shape mask is drawn
    assert all(x.loss for x in t.layers if x.kind.value != "shape_mask")
