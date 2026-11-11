# AI Reel Editor (web MVP)

Upload or link a reference Reel. The system measures it, builds a reusable template, proves the template by rendering it back, works out what footage each slot needs, matches your own clips, renders a new Reel with the same structure and the reference's own audio, and reports the difference.

## Setup
1. Install FFmpeg with libass: `winget install Gyan.FFmpeg`. Node 22+ for the overlay engine.
2. `copy .env.example .env` and fill the keys (below).
3. Backend: `cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt`
4. Overlay engine (HyperFrames, optional but needed for bounce / word-highlight text and whip transitions): `cd overlay\hyperframes && npm ci`
5. Frontend: `cd frontend && npm install && npm run build`
6. Run: `cd backend && .venv\Scripts\uvicorn app.main:app --port 8787` and open http://127.0.0.1:8787
   (dev: `npm run dev` in `frontend`, proxies `/api` to port 8787)

Tests: `cd backend && .venv\Scripts\python -m pytest`. Detector and renderer tests run on synthetic reels with exact ground truth (`tests/synth.py`); the flow test stubs OpenRouter, TwelveLabs and yt-dlp but runs real analysis and rendering. A full run takes 15-20 minutes on CPU (OCR is the slow part).

## Environment keys (`.env`)
| Key | What it is for |
|---|---|
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Chat, brief, shot fill, template decisions, verifier judge. The model must support `json_schema` output and tool calls. |
| `TWELVELABS_API_KEY` | Clip search and Pegasus (the default video AI). |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Optional second video AI. Pick the model from `clients.gemini.models()`. Free-tier content may be used for training: only send reels you own. |
| `VLM_PROVIDER` | `gemini` or `pegasus` (default: gemini when its key and model are set). |
| `PVE_KEEP_REFS` | `1` keeps each reference's 30 fps proxy and round-trip renders under `data/refs/<key>/` after validation (development). |
| `YTDLP_COOKIES` | cookies.txt for link downloads (Instagram often needs it). |

## How a reference becomes a template
`data/refs/<key>/ir/` holds each layer as JSON: `source` (proxy facts), `evidence` (measurements: cuts, transitions, text, text animation, camera, still/photo, speed, effects, layout, overlays, colour), `observed` (evidence + the video AI's typed descriptions, with conflicts), `template` (bindings keep / swap / drop, requirements per slot), `delta` (validation). Every time is an integer frame at 30 fps.

## Reading the template check (delta report)
The template card in the chat shows what validation proved:
- **timing / audio**: the same-shot pass renders every slot with the reference's own footage. Frame count, per-frame SSIM and audio lag must match exactly. If these fail, the template is wrong, not just imperfect.
- **marker pass rows** (text, transitions, camera, speed, effects, layout, overlays): the template is applied to plain test footage and measured again with the same tools. A failed row is a renderer downgrade, a vocabulary loss, or a detector that disagrees with itself. The template passes with 90% of these rows in agreement.
- **coverage**: every measurement must be used by the template, dropped with a reason, or listed as unsupported. Below 100% is a bug.
- **Shown differently**: features the renderer approximates (for example a spin transition drawn as a radial wipe).
- **Please confirm**: low-confidence fields. Accept keeps the value, Edit sets your own; both are stored with source `user`.

## Adding a gold reel
Gold reels are the only measure of real accuracy. See `gold/README.md`: put a reel you own in `gold/<name>/`, run `.venv\Scripts\python -m tools.label ..\gold\<name>\<file>.mp4`, correct `labels.draft.json` by scrubbing the video frame by frame, save it as `labels.json`, then `.venv\Scripts\python -m tools.score` (appends to `gold/history.jsonl`; `--providers` compares Gemini and Pegasus). After the first baseline, write per-track F1 targets to `gold/targets.json`; `tests/test_ops.py` then fails on a regression of more than 0.05.

## Notes
- `data/` holds SQLite, uploads and renders. The uploaded or downloaded reference video is deleted after analysis; its proxy is deleted after validation unless `PVE_KEEP_REFS=1`.
- Stage durations and LLM token usage are logged to the `project_events` table (`stage_time`, `llm_usage`).
- Approval is an HTTP call from the Approve button only; the chat agent has no approve tool.
- Link download through yt-dlp is a platform-terms risk (see the research reports); uploading the file avoids it.
