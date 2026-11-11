"""Reference Analyzer: URL -> cached blueprint. The uploaded/downloaded original is deleted after analysis; the
30 fps proxy stays under data/refs/<key>/ until template validation decides (M11)."""
import hashlib
import json
import re
import shutil
from pathlib import Path

from .. import config, db, ir
from . import music

ANALYSIS_VERSION = 4  # 4: measured cut list + typed per-slot meaning (IR template); 3: whole-video analysis


class DownloadFailed(Exception):
    pass


def normalize(url: str) -> tuple[str, str]:
    """(platform, platform id). Unknown sites fall back to a hash of the cleaned URL."""
    pats = [
        ("youtube", r"(?:youtu\.be/|[?&]v=|/shorts/|/embed/)([\w-]{11})"),
        ("instagram", r"instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/([\w-]+)"),
        ("tiktok", r"tiktok\.com/.*?/video/(\d+)"),
    ]
    for plat, pat in pats:
        m = re.search(pat, url)
        if m:
            return plat, m.group(1)
    return "web", hashlib.sha1(url.split("#")[0].split("?")[0].rstrip("/").encode()).hexdigest()[:16]


def cache_key(url: str) -> str:
    plat, pid = normalize(url)
    return f"{plat}:{pid}"


def fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> Path:
    import yt_dlp

    opts = {"outtmpl": str(dest / "ref.%(ext)s"), "quiet": True, "noplaylist": True,
            "format": "bv*[height<=1080]+ba/b[height<=1080]/b", "merge_output_format": "mp4",
            "max_filesize": 300 * 1024 * 1024}
    if config.YTDLP_COOKIES:
        opts["cookiefile"] = config.YTDLP_COOKIES
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.extract_info(url, download=True)
    except Exception as e:
        raise DownloadFailed(str(e)[:300]) from e
    files = list(dest.glob("ref.*"))
    if not files:
        raise DownloadFailed("nothing downloaded")
    return files[0]


def lookup(key: str) -> dict | None:
    r = db.one("SELECT * FROM reference_cache WHERE key=?", (key,))
    return r["analysis"] if r else None


def lookup_fp(fp: str) -> tuple[str, dict] | None:
    r = db.one("SELECT * FROM reference_cache WHERE fingerprint=?", (fp,))
    return (r["key"], r["analysis"]) if r else None


def _pacing(t: ir.Template) -> str:
    lens = [ir.f2s(s.frames) for s in t.slots]
    return f"{len(lens)} shots, average {sum(lens) / len(lens):.1f} s (shortest {min(lens):.1f} s, longest {max(lens):.1f} s)"


def _analyze_file(path: Path, audio_key: str, progress=None) -> dict:
    from . import analyze as pipeline
    from .fusion import Observed

    ref_key, t, delta = pipeline.run(path, audio_key, progress=progress)
    obs = ir.load(ref_key, "observed", Observed)
    # legacy per-shot fields for the ShotSpec adapter: the typed meaning plus the style notes styles.py parses
    shots = [{**style, "description": s.function.value, "subject": s.subject.value, "action": s.action.value,
              "camera": s.angle.value, "start": ir.f2s(s.start), "end": ir.f2s(s.end)}
             for s, style in zip(t.slots, obs.style)]
    return {"v": ANALYSIS_VERSION, "ref_key": ref_key, "duration": ir.f2s(t.n_frames), "n_frames": t.n_frames,
            "overall_style": t.narrative.get("overall_style", ""), "pacing": _pacing(t),
            "shots": shots,
            "cut_check": {"detected_cuts": len(t.cuts()), "shots": len(t.slots)},
            "validation": {"passed": delta.passed, "rows": [r.model_dump(mode="json") for r in delta.rows]}}


def analyze(url: str | None, workdir: Path, file: Path | None = None, progress=None) -> tuple[str, dict]:
    """Returns (cache key, analysis). Raises DownloadFailed when the link cannot be fetched and no file given."""
    key = cache_key(url) if url else None
    if key and (hit := lookup(key)) and hit.get("v") == ANALYSIS_VERSION:
        if not music.audio_path(key).exists():  # analysed before audio was kept: fetch just the audio
            _keep_audio_only(key, url, workdir, file)
        return key, hit
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        path = file or download(url, workdir)
        fp = fingerprint(path)
        if (hit := lookup_fp(fp)) and not key and hit[1].get("v") == ANALYSIS_VERSION:
            return hit
        key = key or f"file:{fp[:16]}"
        analysis = _analyze_file(path, key, progress)
        db.run("INSERT OR REPLACE INTO reference_cache(key,platform,fingerprint,analysis,created) VALUES(?,?,?,?,?)",
               (key, key.split(":")[0], fp, json.dumps(analysis), db.now()))
        return key, analysis
    finally:
        shutil.rmtree(workdir, ignore_errors=True)  # the original goes; only the proxy stays, until validation (M11)


def _keep_audio_only(key: str, url: str | None, workdir: Path, file: Path | None) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        music.extract(file or download(url, workdir), key)
    except DownloadFailed:
        pass  # no soundtrack then; the brief falls back to no music
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
