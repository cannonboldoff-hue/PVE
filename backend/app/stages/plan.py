"""Production Plan: approved shot->clip mapping as a timeline, plus the one patch applier
shared by chat revisions and verifier repairs."""
from collections.abc import Callable

from ..models import CaptionStyle, Match, PatchOp, Plan, PlanShot, ShotSpec

CAP_PAD = 0.2


def build(shots: list[dict], matches: list[dict], assets: dict[str, dict], music_path: str | None, captions: bool,
          template=None) -> Plan:
    """template (ir.Template): frame-exact timing pinned to the reference; skipped slots' frames go to a neighbour
    so the total stays n_frames and the reference audio stays in sync."""
    by_shot = {m["shot_id"]: Match(**m) for m in matches}
    slot_frames = {k + 1: s.end - s.start for k, s in enumerate(template.slots)} if template else {}
    out, orphan = [], 0
    for raw in shots:
        s = ShotSpec(**raw)
        m = by_shot.get(s.shot_id)
        if s.skipped or not m or not m.asset_id or m.asset_id not in assets:
            if template:
                if out:
                    out[-1].frames += slot_frames[s.shot_id]
                else:
                    orphan += slot_frames[s.shot_id]
            continue
        if template:  # the slot's exact length, plus any leading skipped slots
            s = s.model_copy(update={"end": s.start + (slot_frames[s.shot_id] + orphan) / 30})
        seg = max(0.1, m.end - m.start)
        if seg >= s.duration:
            src_out, speed = m.start + s.duration, 1.0
        else:  # source segment shorter than the slot: slow down, never below 0.5x
            src_out, speed = m.end, max(0.5, seg / s.duration)
        ps = PlanShot(shot_id=s.shot_id, asset_id=m.asset_id, path=assets[m.asset_id]["path"],
                      src_in=m.start, src_out=src_out, speed=speed, caption=s.text, transition=s.transition_out,
                      fit=s.fit, animation=s.animation, caption_animation=s.caption_animation,
                      caption_style=s.caption_style, grade=s.grade)
        if template:
            ps.frames, orphan = slot_frames[s.shot_id] + orphan, 0
            ps.transition = "cut"  # M2: transitions are rebuilt from the template (M6), not from ShotSpec
        if s.layout == "collage":
            tiles = [assets[a]["path"] for a in m.extra_assets if a in assets][: s.collage.tiles - 1]
            if tiles:  # one tile alone is just a single shot
                ps.collage, ps.tiles = s.collage, tiles
        _fit_caption(ps)
        _custom_caption_timing(ps, s)
        out.append(ps)
    plan = Plan(shots=out, music_path=music_path, captions=captions)
    if template and out:
        plan.n_frames = template.n_frames
        assert sum(p.frames for p in out) == template.n_frames, "slot frames must add up to the reference length"
    return plan


def _fit_caption(ps: PlanShot) -> None:
    ps.cap_start = CAP_PAD
    ps.cap_end = max(ps.cap_start + 0.3, ps.duration - CAP_PAD)


def _custom_caption_timing(ps: PlanShot, s: ShotSpec) -> None:
    """Use the reference's caption timing when the shot spec has it (seconds after the shot starts)."""
    if s.caption_start is not None:
        ps.cap_start = min(max(0.0, s.caption_start), ps.duration - 0.3)
    if s.caption_end is not None:
        ps.cap_end = min(ps.duration, max(ps.cap_start + 0.3, s.caption_end))


def total_duration(plan: Plan) -> float:
    return sum(s.duration for s in plan.shots)


def apply_patches(plan: Plan, ops: list[PatchOp], resolve_asset: Callable[[str], dict | None]) -> list[str]:
    """Apply ops in place. Returns notes for ops that were rejected (unknown shot, bad value)."""
    notes = []
    for op in ops:
        shot = next((s for s in plan.shots if s.shot_id == op.shot_id), None)
        if not shot:
            notes.append(f"shot {op.shot_id} not in plan")
            continue
        try:
            _apply(plan, shot, op, resolve_asset)
        except (ValueError, TypeError) as e:
            notes.append(f"shot {op.shot_id} {op.field}: {e}")
    return notes


def _apply(plan: Plan, shot: PlanShot, op: PatchOp, resolve_asset) -> None:
    v = op.value
    f = op.field
    if f == "drop":
        if shot.frames is not None:  # frame-exact plan: a neighbour takes the frames so the audio stays in sync
            if len(plan.shots) == 1:
                raise ValueError("cannot drop the only shot")
            i = plan.shots.index(shot)
            plan.shots[i - 1 if i else 1].frames += shot.frames
        plan.shots.remove(shot)
    elif f == "in":
        shot.src_in = max(0.0, float(v))
        if shot.src_out <= shot.src_in + 0.2:
            raise ValueError("in must stay before out")
        _fit_caption(shot)
    elif f == "out":
        if float(v) <= shot.src_in + 0.2:
            raise ValueError("out must stay after in")
        shot.src_out = float(v)
        _fit_caption(shot)
    elif f == "speed":
        shot.speed = min(2.0, max(0.5, float(v)))
        _fit_caption(shot)
    elif f == "caption":
        shot.caption = str(v or "")
    elif f == "cap_start":
        shot.cap_start = min(max(0.0, float(v)), shot.duration - 0.3)
    elif f == "cap_end":
        shot.cap_end = min(shot.duration, max(shot.cap_start + 0.3, float(v)))
    elif f == "caption_color":
        shot.caption_style = CaptionStyle.model_validate({**shot.caption_style.model_dump(), "color": str(v)})
    elif f == "caption_size":
        shot.caption_style = CaptionStyle.model_validate({**shot.caption_style.model_dump(), "size": int(float(v))})
    elif f == "caption_position":
        shot.caption_style = CaptionStyle.model_validate({**shot.caption_style.model_dump(), "position": str(v)})
    elif f in ("transition", "fit", "animation", "caption_animation"):
        attr = "transition" if f == "transition" else f
        setattr(shot, attr, getattr(PlanShot.model_validate({**shot.model_dump(), attr: str(v)}), attr))  # enum-checked
    elif f == "clip":
        a = resolve_asset(str(v))
        if not a:
            raise ValueError(f"unknown clip {v}")
        shot.asset_id, shot.path = a["id"], a["path"]
        shot.src_in, shot.src_out, shot.speed = 0.0, min(a["duration"], shot.duration), 1.0
        _fit_caption(shot)
