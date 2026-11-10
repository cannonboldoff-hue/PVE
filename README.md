# AI Reel Editor (web MVP)

Paste a Reel link, get a shot blueprint, match it against your own clips, film what is missing, approve, render, verify, revise by chat.

## Setup
1. Install FFmpeg with libass (mcp-video drives it): `winget install Gyan.FFmpeg`
2. `copy .env.example .env` and fill `OPENROUTER_API_KEY`, `TWELVELABS_API_KEY` (the OpenRouter model must support `json_schema` and tool calls).
3. Backend: `cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt`
4. Frontend: `cd frontend && npm install && npm run build`
5. Run: `cd backend && .venv\Scripts\uvicorn app.main:app --port 8787` and open http://127.0.0.1:8787
   (dev: `npm run dev` in `frontend`, proxies `/api` to port 8787)

Tests: `cd backend && .venv\Scripts\python -m pytest` (render tests use real FFmpeg; the flow test stubs OpenRouter, TwelveLabs and yt-dlp).

## Notes
- Data lives in `data/` (SQLite, uploaded clips, renders). Reference videos are deleted after analysis.
- Instagram downloads often need `YTDLP_COOKIES`; if a download fails the chat asks for a screen recording or file.
- Approval is an HTTP call from the Approve button only; the chat agent has no approve tool.
