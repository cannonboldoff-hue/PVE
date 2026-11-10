"""Thin ffprobe / ffmpeg subprocess helpers. Frame-exact work goes through here, not through Kinocut."""
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from app.clients.video import _ensure_ffmpeg_on_path

_ensure_ffmpeg_on_path()

AUDIO_RATE = 8000  # audio_lag works on mono 8 kHz: enough for alignment, cheap to correlate


def run(args: list[str]) -> None:
    """ffmpeg with args; raises with the last stderr lines on failure."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        tail = "\n".join(p.stderr.strip().splitlines()[-8:])
        raise RuntimeError(f"ffmpeg failed ({p.returncode}): {tail}")


def probe(path: str | Path, count: bool = False) -> dict:
    """ffprobe JSON (format + streams). count=True decodes to fill nb_read_frames (exact, slower)."""
    args = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams"]
    if count:
        args += ["-count_frames"]
    p = subprocess.run([*args, str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise RuntimeError(f"ffprobe failed on {path}: {p.stderr.strip()[-400:]}")
    return json.loads(p.stdout)


def video_stream(info: dict) -> dict:
    return next(s for s in info["streams"] if s["codec_type"] == "video")


def fps(path: str | Path) -> float:
    n, d = video_stream(probe(path))["r_frame_rate"].split("/")
    return int(n) / int(d)


def count_frames(path: str | Path) -> int:
    return int(video_stream(probe(path, count=True))["nb_read_frames"])


def ssim(a: str | Path, b: str | Path) -> list[float]:
    """Per-frame SSIM (All) of a against b. Both must have the same size and frame count to be meaningful."""
    with tempfile.TemporaryDirectory() as d:
        # stats_file path goes through the filter parser: run in that dir and use a bare name to avoid escaping C:\
        p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(Path(a).resolve()),
                            "-i", str(Path(b).resolve()), "-lavfi", "[0:v][1:v]ssim=stats_file=s.log", "-f", "null", "-"],
                           cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode:
            raise RuntimeError(f"ssim failed: {p.stderr.strip()[-400:]}")
        out = []
        for line in (Path(d) / "s.log").read_text().splitlines():
            all_ = next(t for t in line.split() if t.startswith("All:"))
            out.append(float(all_[4:]))
        return out


def decode(path: str | Path, width: int, height: int, gray: bool = False, vf: str = "") -> np.ndarray:
    """Every frame scaled to width x height as uint8 (n, h, w, 3) RGB, or (n, h, w) when gray."""
    chain = ",".join(x for x in (vf, f"scale={width}:{height}:flags=area") if x)
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path), "-vf", chain,
                        "-f", "rawvideo", "-pix_fmt", "gray" if gray else "rgb24", "-"], capture_output=True)
    if p.returncode:
        raise RuntimeError(f"decode failed on {path}: {p.stderr.decode(errors='replace')[-400:]}")
    shape = (-1, height, width) if gray else (-1, height, width, 3)
    return np.frombuffer(p.stdout, dtype=np.uint8).reshape(shape)


def audio_samples(path: str | Path, rate: int = AUDIO_RATE) -> np.ndarray:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path), "-vn",
                        "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"], capture_output=True)
    if p.returncode:
        raise RuntimeError(f"audio decode failed on {path}: {p.stderr.decode(errors='replace')[-400:]}")
    return np.frombuffer(p.stdout, dtype=np.float32)


def audio_lag(a: str | Path, b: str | Path, max_lag_s: float = 2.0) -> int:
    """Lag of a's audio relative to b's, in samples at AUDIO_RATE. Positive: a starts later than b."""
    x, y = audio_samples(a), audio_samples(b)
    n = min(len(x), len(y))
    if n == 0:
        raise ValueError("no audio samples")
    x, y = x[:n] - x[:n].mean(), y[:n] - y[:n].mean()
    size = 1 << (2 * n - 1).bit_length()
    c = np.fft.irfft(np.fft.rfft(x, size) * np.conj(np.fft.rfft(y, size)), size)
    m = int(max_lag_s * AUDIO_RATE)
    lags = np.r_[np.arange(0, m + 1), np.arange(-m, 0)]
    vals = np.r_[c[: m + 1], c[-m:]]
    return int(lags[int(np.argmax(vals))])
