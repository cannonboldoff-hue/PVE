"""Soundtrack: the reference Reel's audio (kept as audio only). It is used unchanged and never analysed."""
from pathlib import Path

from .. import config
from ..clients import video

REFERENCE_VOLUME = 0.7  # legacy plans only: songs are mastered near 0 dBFS; reference-mode plans play at 1.0


def audio_path(key: str) -> Path:
    return config.REF_AUDIO / (key.replace(":", "_") + ".wav")


def extract(src: Path, key: str) -> Path | None:
    """Pull the audio track out of the reference video before the video is deleted. None if it has no audio."""
    dest = audio_path(key)
    try:
        video.client().extract_audio(str(src), output=str(dest), format="wav", overwrite=True)
    except Exception:
        dest.unlink(missing_ok=True)
        return None
    return dest if dest.exists() else None


def music_for(brief: dict, project: dict, assets: dict[str, dict]) -> tuple[str | None, str]:
    """(music file, mode). 'replace' = the song becomes the soundtrack; 'duck' = it sits under the clip audio."""
    if brief["music"] == "reference" and project["reference_id"]:
        p = audio_path(project["reference_id"])
        if p.exists():
            return str(p), "replace"
    if brief["music"] == "uploaded" and project["music_asset"] in assets:
        return assets[project["music_asset"]]["path"], "duck"
    return None, "duck"
