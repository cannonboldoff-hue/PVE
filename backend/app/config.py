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
REFS = DATA / "refs"  # per-reference proxy, audio and IR layers (docs/mvp-plan.md 3.4)
for d in (ASSETS, PROJECTS, REF_AUDIO, REFS):
    d.mkdir(exist_ok=True)
KEEP_REFS = os.getenv("PVE_KEEP_REFS") == "1"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5")
TWELVELABS_API_KEY = os.getenv("TWELVELABS_API_KEY", "")
YTDLP_COOKIES = os.getenv("YTDLP_COOKIES", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")  # confirm against the key's model list before setting
VLM_PROVIDER = os.getenv("VLM_PROVIDER") or ("gemini" if GEMINI_API_KEY and GEMINI_MODEL else "pegasus")

# HyperFrames overlay engine: pinned CLI under overlay/hyperframes, telemetry off
_HF = ROOT / "overlay" / "hyperframes" / "node_modules" / ".bin" / ("hyperframes.cmd" if os.name == "nt" else "hyperframes")
if _HF.exists():
    os.environ.setdefault("MCP_VIDEO_HYPERFRAMES_COMMAND", str(_HF))
os.environ.setdefault("HYPERFRAMES_NO_TELEMETRY", "1")
os.environ.setdefault("DO_NOT_TRACK", "1")

W, H, FPS = 1080, 1920, 30  # aspect ratio fixed at 9:16 in v1
MAX_REPAIR_ROUNDS = 3
MIN_INDEX_SECONDS = 4.0  # TwelveLabs rejects shorter clips
