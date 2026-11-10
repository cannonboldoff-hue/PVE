import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA = Path(os.getenv("PVE_DATA", ROOT / "data"))
DATA.mkdir(parents=True, exist_ok=True)
ASSETS = DATA / "assets"
PROJECTS = DATA / "projects"
REF_AUDIO = DATA / "ref_audio"  # soundtrack of analysed references (audio only; the video is deleted)
for d in (ASSETS, PROJECTS, REF_AUDIO):
    d.mkdir(exist_ok=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5")
TWELVELABS_API_KEY = os.getenv("TWELVELABS_API_KEY", "")
YTDLP_COOKIES = os.getenv("YTDLP_COOKIES", "")

W, H, FPS = 1080, 1920, 30  # aspect ratio fixed at 9:16 in v1
MAX_REPAIR_ROUNDS = 3
MIN_INDEX_SECONDS = 4.0  # TwelveLabs rejects shorter clips
