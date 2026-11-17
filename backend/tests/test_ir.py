import json

from app import db, ir


def _template() -> ir.Template:
    k = ir.Key(frame=3, box=ir.Box(x=0.1, y=0.7, w=0.8, h=0.1), scale=1.1, rotation=2, opacity=0.5)
    slot = ir.Slot(id="s01", start=0, end=45, role=ir.F[ir.Role](value="hook", raw="opening hook", conf=0.8,
                                                                  source="gemini", evidence=["cuts_0"]),
                   camera_path=[k], speed=[(0.0, 1.0), (0.5, 2.0)], freeze=[(10, 15)],
                   colour=ir.ColourTarget(l_mean=50, l_std=10, a_mean=0, a_std=3, b_mean=5, b_std=4, saturation=0.4,
                                          contrast=0.3),
                   requirement=ir.Requirement(media="video", footage_frames=60), layout_boxes=[k.box])
    return ir.Template(
        v=1, key="abc", n_frames=90, audio="a.wav",
        slots=[slot, ir.Slot(id="s02", start=45, end=90, media=ir.F[ir.Media](value="photo"))],
        transitions=[ir.Transition(after_slot="s01", type=ir.F[ir.TransitionType](value="other", raw="ink bleed"),
                                   start=40, end=50, params={"dir": "left"}, loss="no ink shader")],
        effects=[ir.Effect(id="e1", type=ir.F[ir.EffectType](value="flash"), start=44, end=46)],
        texts=[ir.TextEvent(id="t1", start=5, end=40, text=ir.F[str](value="Hi", raw="Hi", binding="swap"), keys=[k],
                            anim_in=ir.F[ir.TextAnim](value="pop"), anim_in_frames=6, max_chars=20)],
        overlays=[ir.Overlay(id="o1", kind=ir.F[ir.OverlayKind](value="sticker"), start=0, end=90, keys=[k])],
        narrative={"hook": "x"}, unsupported=["masks_0"], low_conf=["slots.0.role"], dropped={"cuts_9": "too short"},
    )


def test_every_model_round_trips_through_json():
    t = _template()
    assert ir.Template.model_validate_json(t.model_dump_json()) == t
    assert t.cuts() == [45] and t.slots[0].frames == 45
    ev = ir.Evidence(items=[ir.Item(id="cuts_0", track="cuts", start=45, end=45, data={"frame": 45}, tool="t"),
                            ir.Item(id="text_0", track="text", start=0, end=9)])
    assert ir.Evidence.model_validate_json(ev.model_dump_json()) == ev
    assert [i.id for i in ev.track("cuts")] == ["cuts_0"]
    src = ir.Source(key="abc", fingerprint="f", n_frames=90, width=1080, height=1920, src_fps=29.97)
    assert ir.Source.model_validate_json(src.model_dump_json()) == src
    d = ir.Delta(rows=[ir.DeltaRow(track="cuts", metric="f1", ref=1, render=0.9, gap=0.1, ok=False)], coverage=0.5)
    assert ir.Delta.model_validate_json(d.model_dump_json()) == d
    assert json.loads(t.model_dump_json())["transitions"][0]["type"]["raw"] == "ink bleed"


def test_save_load_checks_version_and_inputs():
    t = _template()
    ir.save("abc", "template", t, v=2, inputs="h1")
    assert ir.load("abc", "template", ir.Template) == t
    assert ir.load("abc", "template", ir.Template, v=2, inputs="h1") == t
    assert ir.load("abc", "template", ir.Template, v=3) is None
    assert ir.load("abc", "template", ir.Template, inputs="h2") is None
    assert ir.load("nope", "template", ir.Template) is None
    assert ir.f2s(45) == 1.5 and ir.s2f(1.5) == 45
    assert ir.digest({"a": 1}) == ir.digest({"a": 1}) != ir.digest({"a": 2})


def test_db_migration_adds_columns_once():
    db._migrate()  # second run is a no-op
    cols = {r["name"] for r in db.q("PRAGMA table_info(templates)")}
    assert {"template", "delta", "ir_version"} <= cols
    assert {r["name"] for r in db.q("PRAGMA table_info(refs)")} >= {"key", "validated", "proxy_path"}


def _lossy(t: ir.Template) -> dict:
    """What compact() is allowed to forget: engine output, provenance, logs; floats to 4 places."""
    d = ir.compact(ir.expand(ir.compact(t)))
    return d


def test_compact_round_trips_and_shrinks():
    t = _template()
    c = ir.compact(t)
    assert "unsupported" not in c and "loss" not in c["transitions"][0]
    assert c["slots"][1]["media"] == "photo" and c["effects"][0]["type"] == "flash"
    assert c["transitions"][0]["type"] == {"v": "other", "raw": "ink bleed"}  # "other" keeps its raw
    assert c["texts"][0]["text"] == {"v": "Hi", "binding": "swap"}  # raw == value is dropped
    assert _lossy(t) == c  # expand(compact(x)) compacts to the same thing
    e = ir.expand(c)
    assert e.cuts() == t.cuts() and e.slots[0].speed == t.slots[0].speed and e.texts[0].keys == t.texts[0].keys
    assert len(json.dumps(c)) < len(t.model_dump_json()) / 2


def test_compact_keys_keep_holds_and_motion():
    box = ir.Box(x=0.1, y=0.2, w=0.3, h=0.1)
    moved = ir.Box(x=0.5, y=0.2, w=0.3, h=0.1)
    keys = [ir.Key(frame=f, box=box) for f in (0, 0, 4, 8, 12)] + [ir.Key(frame=20, box=moved)]
    t = _template()
    t.texts[0].keys = keys
    out = ir.compact(t)["texts"][0]["keys"]
    assert [k[0] for k in out] == [0, 12, 20]  # hold ends at 12, move starts there


def test_compact_drops_empties_but_keeps_meaningful_nulls():
    t = _template()
    t.effects[0].params = {"layer": "BG", "params": {"Map": {"value": 3.0}, "Dir": {"keys": []}}, "x": None}
    t.texts[0].style.outline = None  # no outline; the default is black
    c = ir.compact(t)
    assert c["effects"][0]["params"] == {"layer": "BG", "params": {"Map": {"value": 3.0}}}  # a free dict is not an F
    e = ir.expand(c)
    assert e.texts[0].style.outline is None and e.effects[0].params["params"]["Map"] == {"value": 3.0}


def test_compact_hoists_the_effect_app():
    t = _template()
    raw = {"app": "after_effects", "match": "ADBE Fill", "name": "Fill"}
    t.effects = [ir.Effect(id=f"e{i}", type=ir.F[ir.EffectType](value="other", raw=dict(raw)), start=0, end=9)
                 for i in range(2)]
    c = ir.compact(t)
    assert c["app"] == "after_effects" and "app" not in c["effects"][0]["type"]["raw"]
    assert ir.expand(c).effects[1].type.raw == raw
    t.effects[1].type.raw["app"] = "premiere"  # mixed apps stay where they are
    assert "app" not in ir.compact(t) and ir.compact(t)["effects"][0]["type"]["raw"]["app"] == "after_effects"


def test_compact_keys_are_arrays_and_straight_runs_collapse():
    keys = [ir.Key(frame=f, box=ir.Box(x=0.1 + f * 0.01, y=0.2, w=0.3, h=0.1), opacity=1.0 if f < 8 else 0.5)
            for f in range(0, 11)]
    t = _template()
    t.texts[0].keys = keys
    out = ir.compact(t)["texts"][0]["keys"]
    assert out[0] == [0, 0.1, 0.2, 0.3, 0.1] and out[-1][5:] == [1.0, 0.0, 0.5]  # trailing defaults trimmed
    assert [k[0] for k in out] == [0, 7, 8, 10]  # line, then the opacity step, then the line again
    e = ir.expand(ir.compact(t)).texts[0].keys
    assert e[1] == ir.Key(frame=7, box=ir.Box(x=0.17, y=0.2, w=0.3, h=0.1))
