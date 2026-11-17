"""Validation A (docs/mvp-plan.md 5.3): prove the template by rendering it back."""
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from .. import ir
from ..clients import ff
from ..models import Plan, PlanShot
from ..render import assemble, shot

SSIM_MIN = 0.95  # per-frame floor for the same-shot pass; lower hides off-by-one frames, higher trips on encode noise
MAX_LAG_SAMPLES = 0  # audio must be sample-aligned at 8 kHz
# marker pass, text: what counts as "the template reproduced it"
TEXT_SIM_OK = 0.9
TEXT_IOU_OK = 0.6
TEXT_FRAMES_OK = 2
TRANS_FRAMES_OK = 2
TILE_STEPS = (4, 7, 9, 12)
BOX_IOU_OK = 0.7  # layout, inset and overlay boxes
SPEED_OK = 0.25  # relative error of a speed factor
CAMERA_SCALE_OK = 0.05  # relative error of the scale change over a slot


def _evidence_ids(obj) -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "evidence" and isinstance(v, list):
                out |= set(v)
            else:
                out |= _evidence_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _evidence_ids(v)
    return out


def coverage(t: ir.Template, ev: ir.Evidence) -> float:
    """Share of evidence items the template uses, drops with a reason, or lists as unsupported."""
    if not ev.items:
        return 1.0
    seen = _evidence_ids(t.model_dump(mode="json")) | set(t.dropped) | set(t.unsupported)
    return sum(i.id in seen for i in ev.items) / len(ev.items)


def same_shot_plan(t: ir.Template, proxy: str) -> Plan:
    shots = [PlanShot(shot_id=k + 1, asset_id="reference", path=proxy, src_in=ir.f2s(s.start), src_out=ir.f2s(s.end),
                      frames=s.frames) for k, s in enumerate(t.slots)]
    return Plan(shots=shots, n_frames=t.n_frames, music_path=t.audio or None, audio_mode="reference", captions=False)


def marker_plan(t: ir.Template, clips: list[str]) -> Plan:
    """Every slot filled with a plain marker clip; the template's transitions, camera and text layer (reference
    words) applied."""
    from .plan import apply_transitions, camera_moves, shake_of, tile_params_of

    shots = [PlanShot(shot_id=k + 1, asset_id=f"marker{k + 1}", path=c, src_in=0.0, src_out=ir.f2s(s.frames),
                      frames=s.frames, shake=shake_of(s),
                      camera_path=[x.model_dump(mode="json") for x in s.camera_path] if camera_moves(s, t) else [])
             for k, (s, c) in enumerate(zip(t.slots, clips))]
    texts = []
    for e in t.texts:
        d = e.model_dump(mode="json")
        d["text"]["value"] = e.text.raw or e.text.value
        texts.append(d)
    for ps, sl in zip(shots, t.slots):
        if sl.speed != [(0.0, 1.0)] or sl.freeze or sl.reverse:
            ps.speed_curve, ps.freeze, ps.reverse = list(sl.speed), list(sl.freeze), sl.reverse
        if sl.layout.value in ("split_v", "split_h", "pip", "collage", "letterbox", "blur_fill") and sl.layout_boxes:
            ps.layout_boxes = [b.model_dump() for b in sl.layout_boxes]
            ps.tile_params = tile_params_of(sl)
            ps.fit = "blur_fit" if sl.layout.value == "blur_fill" else ps.fit
    plan = Plan(shots=shots, n_frames=t.n_frames, music_path=t.audio or None, audio_mode="reference",
                captions=bool(texts), texts=texts, effects=[e.model_dump(mode="json") for e in t.effects if e.render],
                overlays=[{"box": o.keys[0].box.model_dump(), "start": o.start, "end": o.end,
                           "colour": (o.kind.raw or {}).get("colour", "#FF00FF")} for o in t.overlays])
    apply_transitions(plan, t)
    return plan


def render_markers(key: str) -> tuple[ir.Template, "Path"]:
    from . import markers, orchestrator

    t = ir.load(key, "template", ir.Template)
    mk = ir.ref_dir(key) / "mk"
    shutil.rmtree(mk, ignore_errors=True)
    mk.mkdir()
    raw = [mk / f"marker{k + 1:03d}.mp4" for k in range(len(t.slots))]
    plan = marker_plan(t, [str(p) for p in raw])  # clip lengths include transition overlaps
    # long enough for the slot's speed curve (a 3x stretch needs 3x the footage); +2 for rounding
    need = [max(ps.frames, shot.footage(ps.frames, ps.speed_curve, ps.freeze)) + 2 for ps in plan.shots]
    def size(box: dict | None) -> tuple[int, int]:  # the box's own shape: cover-fit then does not blow it up
        if not box:
            return markers.W, markers.H
        return max(64, round(markers.W * box["w"] / 2) * 2), max(64, round(markers.H * box["h"] / 2) * 2)

    jobs = [(k + 1, n, p, size(ps.layout_boxes[0] if ps.layout_boxes else None))
            for k, (n, p, ps) in enumerate(zip(need, raw, plan.shots))]
    for k, ps in enumerate(plan.shots):  # a separate marker clip (other colour, own bar) for every extra box
        ps.tiles = [str(mk / f"tile{k + 1:03d}_{j}.mp4") for j in range(1, len(ps.layout_boxes))]
        # hue steps by the golden angle per number: +4, +7, +9, +12 land far from the main marker's hue
        jobs += [(k + 1 + TILE_STEPS[j % len(TILE_STEPS)], need[k], Path(tp), size(ps.layout_boxes[j + 1]))
                 for j, tp in enumerate(ps.tiles)]
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda a: markers.marker_clip(a[0], a[1], a[2], textured=True, size=a[3], number=False), jobs))
    final, _, _ = orchestrator.run(f"markers:{key}", plan, mk, lambda: None)
    out = mk / "render.mp4"
    shutil.copy2(final, out)
    return t, out


def compare_transitions(ref: list[ir.Transition], got: list[ir.Item]) -> list[ir.DeltaRow]:
    """Each template boundary against the render's nearest one: window start, length, coarse class."""
    rows = []
    for k, tr in enumerate(ref):
        mid = tr.start + (tr.end - tr.start) // 2
        g = min(got, key=lambda i: abs(i.data["frame"] - mid), default=None)
        if g is None or abs(g.data["frame"] - mid) > TRANS_FRAMES_OK + (tr.end - tr.start):
            rows.append(ir.DeltaRow(track="transitions", metric=f"{tr.after_slot} found", ref=mid, render=None, gap=1,
                                    ok=False))
            continue
        want = tr.type.value
        rows += [
            ir.DeltaRow(track="transitions", metric=f"{tr.after_slot} window start", ref=tr.start, render=g.start,
                        gap=abs(g.start - tr.start), ok=abs(g.start - tr.start) <= TRANS_FRAMES_OK),
            ir.DeltaRow(track="transitions", metric=f"{tr.after_slot} window length", ref=tr.end - tr.start,
                        render=g.end - g.start, gap=abs((g.end - g.start) - (tr.end - tr.start)),
                        ok=abs((g.end - g.start) - (tr.end - tr.start)) <= TRANS_FRAMES_OK),
            ir.DeltaRow(track="transitions", metric=f"{tr.after_slot} class", ref=want, render=g.data["type"],
                        gap=0 if want == g.data["type"] else 1,
                        ok=want == g.data["type"] or bool(tr.loss) or want in UNMEASURED_TRANSITIONS),
        ]
    return rows


UNMEASURED_TRANSITIONS = {"glitch", "blur", "other"}  # named by the video AI only: the render cannot measure them back
MEASURED_EFFECTS = {"flash", "rgb_split", "blur", "vignette", "glitch"}  # what the effects track can find in a render


def _measured_in(text_item: ir.Item, anim_item: ir.Item | None) -> str | None:
    """The in-animation as fusion reads it: word-level measurements (text track) before the text_anim class."""
    lit, words = text_item.data.get("lit") or [], text_item.data.get("words") or []
    if len({w["start"] for w in lit}) >= 2:
        return "word_highlight"
    if words:
        return "typewriter"
    return anim_item.data["in"] if anim_item else None


def compare_texts(ref: list[ir.TextEvent], got: list[ir.Item], anims: list[ir.Item]) -> list[ir.DeltaRow]:
    """Each reference text event against the best-matching measured event in the render."""
    from .compare import box_iou, span_iou, text_similarity

    anim = {a.data["text_id"]: a for a in anims}
    rows = []
    for e in ref:
        words = e.text.raw or e.text.value
        cands = [(span_iou((e.start, e.end), (i.start, i.end)) + text_similarity(words, i.data["text"]), i)
                 for i in got]
        best = max(cands, key=lambda c: c[0], default=(0, None))[1]
        if best is None or text_similarity(words, best.data["text"]) < 0.5:
            rows.append(ir.DeltaRow(track="text", metric=f"{e.id} found", ref=words, render=None, gap=1, ok=False))
            continue
        a = anim.get(best.id)
        got_in = _measured_in(best, a)
        start, end = (a.start, a.end) if a else (best.start, best.end)
        sim = text_similarity(words, best.data["text"])
        iou = box_iou(e.keys[0].box, best.data.get("style", {}).get("ink") or best.data["box"])
        rows += [
            ir.DeltaRow(track="text", metric=f"{e.id} string", ref=words, render=best.data["text"],
                        gap=round(1 - sim, 3), ok=sim >= TEXT_SIM_OK),
            ir.DeltaRow(track="text", metric=f"{e.id} box IoU", ref=1.0, render=round(iou, 3), gap=round(1 - iou, 3),
                        ok=iou >= TEXT_IOU_OK),
            ir.DeltaRow(track="text", metric=f"{e.id} start frame", ref=e.start, render=start, gap=abs(start - e.start),
                        ok=abs(start - e.start) <= TEXT_FRAMES_OK),
            ir.DeltaRow(track="text", metric=f"{e.id} end frame", ref=e.end, render=end, gap=abs(end - e.end),
                        ok=abs(end - e.end) <= TEXT_FRAMES_OK),
            ir.DeltaRow(track="text_anim", metric=f"{e.id} in", ref=e.anim_in.value, render=got_in,
                        gap=0 if got_in == e.anim_in.value else 1, ok=got_in == e.anim_in.value),
            ir.DeltaRow(track="text_anim", metric=f"{e.id} out", ref=e.anim_out.value,
                        render=a.data["out"] if a else None, gap=0 if a and a.data["out"] == e.anim_out.value else 1,
                        ok=bool(a) and a.data["out"] == e.anim_out.value),
        ]
    return rows


def marker_pass(key: str, tracks: list[str] | None = None) -> list[ir.DeltaRow]:
    """The whole template applied to plain marker clips, then measured again with the same instruments. Whatever is
    measured on the render was put there by the template, so a gap is a renderer downgrade, a vocabulary loss, or a
    detector that disagrees with itself. tracks: limit the comparison (default: every one built so far)."""
    from .. import evidence
    from .analyze import ingest

    want = tracks or ["transitions", "text", "text_anim", "camera", "speed", "effects", "layout", "overlays"]
    from .. import config, db

    t, out = render_markers(key)
    src = ingest(out)
    ev = evidence.run_all(src.key, only=want)
    if not config.KEEP_REFS:  # the render was ingested like a reference only to be measured
        shutil.rmtree(ir.ref_dir(src.key), ignore_errors=True)
        db.run("DELETE FROM refs WHERE key=?", (src.key,))
    rows = []
    if "transitions" in want:
        rows += compare_transitions(t.transitions, ev.track("transitions"))
    if "text" in want:
        rows += compare_texts(t.texts, ev.track("text"), ev.track("text_anim"))
    if "camera" in want:
        rows += compare_camera(t.slots, ev.track("camera"))
    if "speed" in want:
        rows += compare_speed(t.slots, ev.track("speed"))
    if "effects" in want:
        rows += compare_effects(t.effects, ev.track("effects"))
    if "layout" in want:
        rows += compare_layout(t.slots, ev.track("layout"))
    if "overlays" in want:
        rows += compare_overlays(t.overlays, ev.track("overlays"))
    return rows


def _best_iou(box, cands) -> float:
    from .compare import box_iou

    return max((box_iou(box, c) for c in cands), default=0.0)


def compare_layout(slots: list[ir.Slot], got: list[ir.Item]) -> list[ir.DeltaRow]:
    rows = []
    by_start = {i.start: i for i in got}
    for s in slots:
        g = by_start.get(s.start)
        if g is None or s.layout.value == "single":
            continue
        rows.append(ir.DeltaRow(track="layout", metric=f"{s.id} layout", ref=s.layout.value, render=g.data["value"],
                                gap=0 if s.layout.value == g.data["value"] else 1, ok=s.layout.value == g.data["value"]))
        for k, b in enumerate(s.layout_boxes):
            iou = _best_iou(b, g.data["boxes"])
            rows.append(ir.DeltaRow(track="layout", metric=f"{s.id} box {k} IoU", ref=1.0, render=round(iou, 3),
                                    gap=round(1 - iou, 3), ok=iou >= BOX_IOU_OK))
    return rows


def compare_overlays(ref: list[ir.Overlay], got: list[ir.Item]) -> list[ir.DeltaRow]:
    rows = []
    for o in ref:
        iou = _best_iou(o.keys[0].box, [i.data["box"] for i in got])
        rows.append(ir.DeltaRow(track="overlays", metric=f"{o.id} box IoU", ref=1.0, render=round(iou, 3),
                                gap=round(1 - iou, 3), ok=iou >= BOX_IOU_OK))
    return rows


def _factor_at(curve, pos: float) -> float:
    return next(f for p, f in reversed(sorted(curve)) if p <= pos + 1e-9)


def compare_speed(slots: list[ir.Slot], got: list[ir.Item]) -> list[ir.DeltaRow]:
    """Speed curve shape (factor in the middle of each template piece) and freeze ranges."""
    rows = []
    by_start = {i.start: i for i in got}
    for s in slots:
        g = by_start.get(s.start)
        if g is None:
            continue
        pts = sorted(s.speed)
        if len(pts) > 1:
            for k, (p, f) in enumerate(pts):
                q = pts[k + 1][0] if k + 1 < len(pts) else 1.0
                m = _factor_at(g.data["curve"], (p + q) / 2)
                gap = abs(m - f) / max(f, 1e-6)
                rows.append(ir.DeltaRow(track="speed", metric=f"{s.id} factor @{(p + q) / 2:.2f}", ref=f, render=m,
                                        gap=round(gap, 3), ok=gap <= SPEED_OK))
        for a, b in s.freeze:
            near = min(g.data["freeze"], key=lambda x: abs(x[0] - a) + abs(x[1] - b), default=None)
            err = abs(near[0] - a) + abs(near[1] - b) if near else b - a
            rows.append(ir.DeltaRow(track="speed", metric=f"{s.id} freeze {a}-{b}", ref=[a, b], render=near, gap=err,
                                    ok=near is not None and max(abs(near[0] - a), abs(near[1] - b)) <= 2))
    return rows


def compare_effects(ref: list[ir.Effect], got: list[ir.Item]) -> list[ir.DeltaRow]:
    rows = []
    for e in ref:
        if not e.render or e.type.value not in MEASURED_EFFECTS:
            continue  # not drawn (a recorded loss), or drawn but not measurable (camera punch, video-AI looks)
        same = [i for i in got if i.data["type"] == e.type.value]
        g = min(same, key=lambda i: abs(i.start - e.start), default=None)
        err = abs(g.start - e.start) + abs(g.end - e.end) if g else e.end - e.start
        exact = e.type.value == "flash"
        rows.append(ir.DeltaRow(track="effects", metric=f"{e.id} {e.type.value} frames", ref=[e.start, e.end],
                                render=[g.start, g.end] if g else None, gap=err,
                                ok=g is not None and (err == 0 if exact else err <= 4)))
    return rows


def compare_camera(slots: list[ir.Slot], got: list[ir.Item]) -> list[ir.DeltaRow]:
    """Per slot: move class, scale change over the slot, travel direction, shake amplitude."""
    rows = []
    for s, g in zip(slots, got):
        want = s.camera.value
        rows.append(ir.DeltaRow(track="camera", metric=f"{s.id} move", ref=want, render=g.data["value"],
                                gap=0 if want == g.data["value"] else 1, ok=want == g.data["value"]))
        if s.camera_path and want != "static":
            ref_s = s.camera_path[-1].scale / max(1e-6, s.camera_path[0].scale)
            got_s = g.data.get("scale_end", 1.0)
            gap = abs(got_s - ref_s) / ref_s
            rows.append(ir.DeltaRow(track="camera", metric=f"{s.id} scale change", ref=round(ref_s, 4),
                                    render=round(got_s, 4), gap=round(gap, 4), ok=gap <= CAMERA_SCALE_OK))
        if s.shake:
            a, b = s.shake["amp"], g.data.get("shake", {}).get("amp", 0.0)
            rows.append(ir.DeltaRow(track="camera", metric=f"{s.id} shake amp", ref=a, render=b,
                                    gap=round(abs(a - b) / max(a, 1e-6), 3), ok=abs(a - b) <= 0.5 * a))
    return rows


def same_shot_pass(key: str) -> list[ir.DeltaRow]:
    """Every slot filled with the reference's own footage, hard cuts, nothing added: the render must equal the proxy.
    Proves slot lengths add up, rendering is frame-exact and audio is in sync. Says nothing about cut placement."""
    from .analyze import proxy_path

    t = ir.load(key, "template", ir.Template)
    proxy = str(proxy_path(key))
    rt = ir.ref_dir(key) / "rt"
    shutil.rmtree(rt, ignore_errors=True)
    rt.mkdir()
    plan = same_shot_plan(t, proxy)
    clips = [rt / f"slot{s.shot_id:03d}.mp4" for s in plan.shots]
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda a: shot.prep({"path": a[0].path, "in": a[0].src_in, "frames": a[0].frames}, a[1]),
                      zip(plan.shots, clips)))
    render = rt / "render.mp4"
    assemble.assemble(plan, clips, rt, render)
    ref = rt / "reference.mp4"  # the proxy through the same fit, as one shot
    shot.prep({"path": proxy, "in": 0.0, "frames": t.n_frames}, ref)

    n = ff.count_frames(render)
    rows = [ir.DeltaRow(track="timing", metric="frame count", ref=t.n_frames, render=n, gap=abs(n - t.n_frames),
                        ok=n == t.n_frames)]
    s = ff.ssim(render, ref)
    worst = min(s) if s else 0.0
    rows.append(ir.DeltaRow(track="timing", metric="per-frame SSIM min", ref=SSIM_MIN, render=round(worst, 4),
                            gap=round(max(0.0, SSIM_MIN - worst), 4), ok=worst >= SSIM_MIN and len(s) == t.n_frames))
    if t.audio:
        lag = ff.audio_lag(render, t.audio)
        a_len, v_len = ff.audio_duration(render) or 0.0, t.n_frames / ir.FPS
        rows.append(ir.DeltaRow(track="audio", metric="lag (samples @8 kHz)", ref=0, render=lag, gap=abs(lag),
                                ok=abs(lag) <= MAX_LAG_SAMPLES))
        rows.append(ir.DeltaRow(track="audio", metric="length (s)", ref=round(v_len, 3), render=round(a_len, 3),
                                gap=round(abs(a_len - v_len), 3), ok=abs(a_len - v_len) <= 1 / ir.FPS))
    return rows


# ---- M11: validation A as a loop ----

MAX_TEMPLATE_ROUNDS = 3
MARKER_OK = 0.9  # share of marker-pass rows that must agree (the rest are listed on the template card)


def score(d: ir.Delta) -> float:
    return (sum(r.ok for r in d.rows) / len(d.rows) if d.rows else 0.0) + d.coverage


def tiling_patches(t: ir.Template) -> list[tuple[str, int]]:
    """Slots must tile [0, n_frames): each slot ends where the next starts, the last at n_frames."""
    out = []
    for k, (s, nxt) in enumerate(zip(t.slots, t.slots[1:])):
        if s.end != nxt.start:
            out.append((f"slots.{k}.end", nxt.start))
    if t.slots and t.slots[-1].end != t.n_frames:
        out.append((f"slots.{len(t.slots) - 1}.end", t.n_frames))
    if t.slots and t.slots[0].start != 0:
        out.append(("slots.0.start", 0))
    return out


def text_patches(t: ir.Template, rows: list[ir.DeltaRow]) -> list[tuple[str, int]]:
    """A caption the render shows k frames late is moved k frames earlier (and the other way round)."""
    out = []
    ids = {e.id: k for k, e in enumerate(t.texts)}
    for r in rows:
        if r.track == "text" and not r.ok and r.metric.endswith((" start frame", " end frame")) and r.render is not None:
            eid, what = r.metric.split(" ", 1)
            k = ids.get(eid)
            if k is not None:
                field = "start" if what.startswith("start") else "end"
                cur = getattr(t.texts[k], field)
                out.append((f"texts.{k}.{field}", int(cur - (r.render - r.ref))))
    return out


def apply_patch(t: ir.Template, path: str, value) -> None:
    obj, parts = t, path.split(".")
    for p in parts[:-1]:
        obj = obj[int(p)] if p.isdigit() else getattr(obj, p)
    setattr(obj, parts[-1], value)


def omissions(key: str, t: ir.Template, provider=None) -> list[str]:
    """The video AI watches the reference with the template summary and names what the template leaves out."""
    from .analyze import proxy_path
    from .meaning import Session

    summary = {"slots": len(t.slots), "transitions": [x.type.value for x in t.transitions],
               "texts": [e.text.value for e in t.texts], "effects": [e.type.value for e in t.effects],
               "overlays": [o.kind.value for o in t.overlays], "layouts": [s.layout.value for s in t.slots],
               "camera": [s.camera.value for s in t.slots]}
    schema = {"type": "object", "properties": {"missing": {"type": "array", "items": {"type": "string"}}},
              "required": ["missing"]}
    try:
        with Session(key, proxy_path(key), provider) as s:
            r = s.ask("This template was measured from the video: " + str(summary) + ". List visible editing "
                      "features (effects, stickers, text, transitions, motion, layout) that it does not mention. "
                      "Empty list if nothing is missing.", schema)
        return [str(x) for x in r.get("missing", [])][:20]
    except Exception as e:  # no provider configured or the call failed: the critic is advisory
        return [f"(omission check not run: {str(e)[:120]})"]


def validate(key: str, ev: ir.Evidence, tracks: list[str] | None = None, critic: bool = True,
             provider=None, progress=None) -> tuple[ir.Template, ir.Delta]:
    """Same-shot pass, marker pass, coverage, omission critic; typed patches applied by code; up to
    MAX_TEMPLATE_ROUNDS; the best-scoring template is kept and saved with its delta."""
    say = progress or (lambda m: None)
    t = ir.load(key, "template", ir.Template)
    best: tuple[ir.Template, ir.Delta] | None = None
    for rnd in range(MAX_TEMPLATE_ROUNDS):
        say(f"Checking the template (round {rnd + 1}): rendering it back and measuring the result…")
        rows: list[ir.DeltaRow] = []
        tiles = not tiling_patches(t)
        if tiles:
            rows += same_shot_pass(key)
        else:
            rows.append(ir.DeltaRow(track="timing", metric="slots tile the reel", ref=t.n_frames,
                                    render=[(s.start, s.end) for s in t.slots], gap=1, ok=False))
        timing_ok = tiles and all(r.ok for r in rows)
        marker = marker_pass(key, tracks) if timing_ok and tracks != [] else []
        rows += marker
        cov = coverage(t, ev)
        ok_marker = sum(r.ok for r in marker) / len(marker) if marker else 1.0
        d = ir.Delta(rows=rows, coverage=cov, passed=timing_ok and cov >= 1.0 and ok_marker >= MARKER_OK)
        if best is None or score(d) > score(best[1]):
            best = (t.model_copy(deep=True), d)
        if d.passed:
            break
        fixes = tiling_patches(t) or text_patches(t, rows)
        if not fixes:
            break
        for path, value in fixes:
            apply_patch(t, path, value)
        ir.save(key, "template", t)
    t, d = best
    if critic:
        t.narrative["omissions"] = omissions(key, t, provider)
    ir.save(key, "template", t)
    ir.save(key, "delta", d)
    return t, d


def cleanup(key: str, keep: bool) -> None:
    """After validation: mark the reference validated; drop the proxy and the renders unless kept for development."""
    from .. import db
    from .analyze import proxy_path

    db.run("UPDATE refs SET validated=1 WHERE key=?", (key,))
    if keep:
        return
    proxy_path(key).unlink(missing_ok=True)
    for sub in ("rt", "mk", "frames"):
        shutil.rmtree(ir.ref_dir(key) / sub, ignore_errors=True)
