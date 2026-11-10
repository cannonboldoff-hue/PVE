import subprocess

from app.clients import video  # noqa: F401  (puts ffmpeg on PATH)


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)
