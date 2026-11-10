"""Reference analysis pipeline: ingest -> evidence -> meaning -> template -> validation (docs/mvp-plan.md 3.1)."""
from pathlib import Path

from .. import config, db, ir
from ..clients import ff
from . import extract, music

PROXY_LONG_SIDE = 1080
PROXY_CRF = 16  # near-transparent; the proxy is the reference for every measurement


def proxy_path(key: str) -> Path:
    return config.REFS / key / "proxy.mp4"


def _rate(s: str) -> float:
    n, d = s.split("/")
    return int(n) / int(d) if int(d) else 0.0


def ingest(path: str | Path, audio_key: str | None = None) -> ir.Source:
    """Fingerprint, constant 30 fps proxy (no audio), reference audio wav, ir/source.json and the refs row."""
    from .reference import fingerprint

    path = Path(path)
    fp = fingerprint(path)
    key = fp[:16]
    src = ir.load(key, "source", ir.Source)
    if not (src and src.fingerprint == fp and proxy_path(key).exists()):
        proxy = proxy_path(key)
        ir.ref_dir(key)
        side = f"trunc(min({PROXY_LONG_SIDE},%s)/2)*2"
        scale = f"scale='if(gte(iw,ih),{side % 'iw'},-2)':'if(gte(iw,ih),-2,{side % 'ih'})'"
        ff.run(["-i", str(path), "-vf", f"fps={config.FPS},{scale},setsar=1", "-an", "-c:v", "libx264",
                "-preset", "veryfast", "-crf", str(PROXY_CRF), "-pix_fmt", "yuv420p", "-video_track_timescale",
                "15360", str(proxy)])
        v = ff.video_stream(ff.probe(proxy))
        orig = ff.video_stream(ff.probe(path))
        src = ir.Source(key=key, fingerprint=fp, n_frames=ff.count_frames(proxy), width=int(v["width"]),
                        height=int(v["height"]), src_fps=_rate(orig.get("avg_frame_rate") or orig["r_frame_rate"]))
        ir.save(key, "source", src)
        db.run("INSERT OR REPLACE INTO refs(key,fingerprint,n_frames,proxy_path,validated,created) VALUES(?,?,?,?,0,?)",
               (key, fp, src.n_frames, str(proxy), db.now()))
    if not music.audio_path(audio_key or key).exists():
        music.extract(path, audio_key or key)
    return src


def run(path: str | Path, audio_key: str | None = None, provider: str | None | bool = None
        ) -> tuple[str, ir.Template, ir.Delta]:
    """ingest -> evidence -> meaning -> fusion -> template -> same-shot pass. Saves observed, template, delta.
    provider: "gemini" / "pegasus", None for config.VLM_PROVIDER, False to measure only (no video AI)."""
    from .. import evidence
    from . import fusion, meaning, roundtrip

    src = ingest(path, audio_key)
    ev = evidence.run_all(src.key)
    slots, _ = fusion.slots_from_cuts(src, ev)
    found, reel = [], {}
    if provider is not False:
        with meaning.Session(src.key, Path(path), provider or None) as s:
            found = meaning.describe_slots(s, slots, ev)
            reel = meaning.describe_reel(s, slots)
    obs = fusion.fuse(src, ev, found, reel)
    ir.save(src.key, "observed", obs, inputs=ir.digest(ev.model_dump(mode="json")))
    audio = music.audio_path(audio_key or src.key)
    t = extract.build(obs, audio=str(audio) if audio.exists() else "")
    ir.save(src.key, "template", t, v=extract.VERSION, inputs=ir.digest(obs.model_dump(mode="json")))
    rows = roundtrip.same_shot_pass(src.key)
    delta = ir.Delta(rows=rows, coverage=roundtrip.coverage(t, ev), passed=all(r.ok for r in rows))
    ir.save(src.key, "delta", delta)
    return src.key, t, delta
