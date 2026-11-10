"""Reference Analyzer: URL -> cached blueprint. The reference video is deleted after analysis."""
import hashlib
import json
import re
import shutil
from pathlib import Path

from .. import config, db
from ..clients import twelvelabs, video
from . import music

SHOT = {
    "type": "object",
    "properties": {
        "start": {"type": "number"}, "end": {"type": "number"},
        "description": {"type": "string"}, "subject": {"type": "string"}, "action": {"type": "string"},
        "camera": {"type": "string"}, "camera_motion": {"type": "string"},
        "on_screen_text": {"type": "string"}, "transition_out": {"type": "string"},
        "background": {"type": "string"}, "frame_motion": {"type": "string"},
        "overlays": {"type": "string"}, "caption_animation": {"type": "string"},
        "caption_font": {"type": "string"}, "caption_color": {"type": "string"}, "caption_position": {"type": "string"},
        "caption_size": {"type": "string"}, "caption_emphasis": {"type": "string"},
        "caption_start": {"type": "number"}, "caption_end": {"type": "number"},
        "color_look": {"type": "string"}, "layout": {"type": "string"}, "collage_tiles": {"type": "integer"},
        "collage_background": {"type": "string"}, "collage_style": {"type": "string"},
    },
    "required": ["start", "end", "description", "subject", "action"],
}
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_style": {"type": "string"}, "pacing": {"type": "string"},
        "music_mood": {"type": "string"}, "caption_style": {"type": "string"},
        "shots": {"type": "array", "items": SHOT},
    },
    "required": ["overall_style", "pacing", "shots"],
}
PROMPT = ("Break this short-form video into its shots. For each shot give start and end seconds, what is shown, "
          "the subject, the action, camera framing, camera motion, any on-screen text and the transition into the "
          "next shot (cut, fade, wipe, slide, zoom). Also give, per shot: the background (what is behind or around "
          "the subject, whether the picture is shown full-frame or inset over a blurred or coloured backdrop or in a "
          "collage), frame_motion (zoom in/out, pan, scrolling, shake, none), overlays (stickers, emoji, frames, "
          "graphics) and how the on-screen text animates in (fade, pop, slide, typewriter, none). For on-screen text also give "
          "caption_font (look: bold sans, script, serif, impact, playful...), caption_color, caption_position (top, middle, "
          "bottom), caption_size (small, medium, large), caption_emphasis (words shown in a different colour), and "
          "caption_start and caption_end in seconds of the video. Per shot also give color_look (warm, cool, vintage, "
          "cinematic, black and white, bright, dark, high contrast, muted, saturated...), layout ('single' or "
          "'collage'), and for a collage: collage_tiles (number of pictures), collage_background (colour) and "
          "collage_style (tilted, framed, straight). Also describe overall style, pacing, music mood and caption style.")


ANALYSIS_VERSION = 3  # 3: caption style and timing, colour look, collage layout; 2: background, motion, overlays


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


def snap(shots: list[dict], cuts: list[float], duration: float, tol: float = 0.6) -> list[dict]:
    """Model timestamps drift; snap each internal boundary to the nearest detected scene cut."""
    shots = sorted(shots, key=lambda s: s["start"])
    bounds = [0.0]
    for s in shots[1:]:
        near = min(cuts, key=lambda c: abs(c - s["start"]), default=None)
        bounds.append(near if near is not None and abs(near - s["start"]) <= tol else s["start"])
    bounds.append(duration)
    out = []
    for i, s in enumerate(shots):
        lo, hi = bounds[i], bounds[i + 1]
        if hi - lo >= 0.3:
            out.append({**s, "start": round(lo, 2), "end": round(hi, 2)})
    return out


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


def _analyze_file(path: Path) -> dict:
    info = video.info(path)
    cuts = video.scene_cuts(path)
    aid = twelvelabs.upload_asset(str(path))
    try:
        data, passes = pick_analysis(lambda: twelvelabs.analyze(aid, PROMPT, ANALYSIS_SCHEMA), cuts, info["duration"])
    finally:
        twelvelabs.delete_asset(aid)  # reference leaves TwelveLabs as well as local disk
    data["duration"] = info["duration"]
    data["v"] = ANALYSIS_VERSION
    data["cut_check"] = {"detected_cuts": len(cuts), "shots": len(data["shots"]), "passes": passes}
    return data


def pick_analysis(run, cuts: list[float], duration: float, max_passes: int = 3) -> tuple[dict, int]:
    """Pegasus' shot count varies between runs. Where the frames show clear cuts (2+), re-run up to max_passes
    times and keep the analysis whose shot count is closest to the detected cuts + 1."""
    best, best_gap, passes = None, 10**9, 0
    for passes in range(1, max_passes + 1):
        data = run()
        data["shots"] = snap(data["shots"], cuts, duration)
        if len(cuts) < 2:  # soft transitions (scrolls, fades): the frame check can't judge, trust the model
            return data, passes
        gap = abs(len(data["shots"]) - (len(cuts) + 1))
        if gap < best_gap:
            best, best_gap = data, gap
        if best_gap <= max(1, round(0.25 * (len(cuts) + 1))):
            break
    return best, passes


def analyze(url: str | None, workdir: Path, file: Path | None = None) -> tuple[str, dict]:
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
        if (hit := lookup_fp(fp)) and not key:
            return hit
        analysis = _analyze_file(path)
        key = key or f"file:{fp[:16]}"
        music.extract(path, key)
        db.run("INSERT OR REPLACE INTO reference_cache(key,platform,fingerprint,analysis,created) VALUES(?,?,?,?,?)",
               (key, key.split(":")[0], fp, json.dumps(analysis), db.now()))
        return key, analysis
    finally:
        shutil.rmtree(workdir, ignore_errors=True)  # no reference video stays on disk


def _keep_audio_only(key: str, url: str | None, workdir: Path, file: Path | None) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        music.extract(file or download(url, workdir), key)
    except DownloadFailed:
        pass  # no soundtrack then; the brief falls back to no music
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
