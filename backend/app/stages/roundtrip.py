"""Validation A (docs/mvp-plan.md 5.3): prove the template by rendering it back."""
import shutil
from concurrent.futures import ThreadPoolExecutor

from .. import ir
from ..clients import ff
from ..models import Plan, PlanShot
from ..render import assemble, shot

SSIM_MIN = 0.95  # per-frame floor for the same-shot pass; lower hides off-by-one frames, higher trips on encode noise
MAX_LAG_SAMPLES = 0  # audio must be sample-aligned at 8 kHz


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
