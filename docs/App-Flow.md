# PVE App Flow

How a reference Reel moves through the product, from the user's click to the final MP4. Written against the code on 2026-11-18 (`backend/app/state.py`, `pipeline.py`, `main.py`). The model path in section 5 is planned, not built.

## 1. Surfaces

- **Chat UI** (`frontend/src`): one conversation per project. The thread holds text bubbles and cards. Cards carry the buttons that move the project forward.
- **Backend** (`backend/app`): FastAPI on port 8787, SQLite in `data/pve.db`, files under `data/`.
- **Event stream**: `GET /api/conversations/{cid}/events` pushes changes so the thread refreshes without polling.

## 2. Project state machine

States live in `projects.state`. `state.ALLOWED` is the only list of legal moves.

```
NEW -> ANALYZING -> BRIEF -> SHOT_SPECS -> PREPRODUCTION -> AWAITING_UPLOADS
                                                  |               |
                                                  v               v
                                           AWAITING_APPROVAL <----+
                                                  |
                                                  v
                      PLANNED -> PRODUCING -> VERIFYING <-> REPAIRING
                                                  |
                                                  v
                                                FINAL
(any state -> FAILED; FAILED -> any state via retry)
```

Background states (`RUNNING`): ANALYZING, PREPRODUCTION, PLANNED, PRODUCING, VERIFYING, REPAIRING. On server start, `pipeline.resume_all()` restarts the work of every project found in one of them.

## 3. Happy path, step by step

| # | User does | System does | State after |
|---|---|---|---|
| 1 | Opens the app, clicks New Reel | `POST /api/conversations` creates a conversation and a project, posts a welcome message | NEW |
| 2 | Pastes a Reel link or drags in the file, says what their Reel is about | `POST /api/conversations/{cid}/messages`; the chat agent calls `submit_reference`. File path: `POST /api/projects/{pid}/reference-file` | ANALYZING |
| 3 | Waits (progress messages) | `run_analyze`: ingest (30 fps proxy, audio), evidence tracks, meaning, fusion, extraction, validation A (same-shot pass, marker pass, coverage, omission critic, up to 3 repairs). Template saved; proxy removed unless `PVE_KEEP_REFS=1` | BRIEF |
| 4 | Reads the **template card**: delta table, downgrades, items to confirm. Accepts or edits low-confidence fields | `POST confirm-template-field` writes `source = "user"`, `conf = 1.0`. Timing fields are refused | BRIEF |
| 5 | Edits and confirms the brief | `edit-brief`, `confirm-brief`; `run_shots` fills text slots (retry once if text exceeds `max_chars`) | SHOT_SPECS |
| 6 | Edits, skips or confirms shots | `edit-shot`, `skip-shot`, `confirm-shots` | PREPRODUCTION |
| 7 | Drops in their own clips any time | `POST /api/assets` stores the clip and indexes it with TwelveLabs; `run_ingest` | unchanged |
| 8 | Sees match chips per shot (exact, similar, adaptable, missing) and filming instructions for gaps | `run_preproduction`: hard filters, search, judge, global assignment | AWAITING_UPLOADS or AWAITING_APPROVAL |
| 9 | Swaps clips, skips missing slots (`swap-clip`, `skip-missing`) | `run_rematch` for changed shots | same |
| 10 | Clicks **Approve** | `POST approve`. Only this button approves; the chat agent has no approve tool | PLANNED |
| 11 | Watches the progress list | `run_production`: compile plan, prep each slot clip, transitions, overlay layer, assemble with reference audio | PRODUCING |
| 12 | Waits | Verification layers: plan lint, file checks, structure vs template, clip-to-slot fit, LLM judge. A failing deterministic layer forces repair, at most 3 rounds | VERIFYING, REPAIRING |
| 13 | Watches the draft, downloads it (`GET /api/projects/{pid}/video`) | Final path stored, drafts kept | FINAL |
| 14 | Types a change ("make the first cut faster") | `revise`; `run_revision` re-plans and re-renders | PRODUCING |

## 4. Branches and failure handling

- **Link download fails.** The project stays in ANALYZING with an error and asks for the file; the user uploads it through the reference-file endpoint.
- **Template validation fails.** Same-shot failure (frame count, SSIM, audio lag) is reported on the template card as a wrong template, not a soft score. The best of up to 3 repair rounds is kept.
- **Clip deleted.** `DELETE /api/assets/{aid}` marks the affected matches missing and reverts an approved project to AWAITING_APPROVAL.
- **Any stage error.** State goes to FAILED with the error stored; `POST retry` re-enters the stage. Chat shows the error banner.
- **Server restart.** `resume_all()` resumes RUNNING states.
- **Reuse.** `GET /api/templates` lists saved templates; `use-template` starts a new project from one without re-analysing.

## 5. Planned model path (not built)

```
reference reel
  -> frame gate        30 fps, 544x960; keep changed frames (+ both sides of each change)
  -> chunker           only if over about 240k tokens; split at calm points, 1 s overlap
  -> Qwen3-VL          gated frames + gap notes -> template JSON per chunk
  -> join              absolute frame numbers, dedupe overlap, check slots tile 0..n
  -> validator         ir.Template schema check
  -> converter         FilmCraft / EffectCraft project, solid-colour canvas per slot, loss report
```

Gating rule for rollout: run the model arm next to the current pipeline on the gold reels, compare per-track F1 and style-check agreement, switch `VLM`-style provider selection only when the checkpoint scores higher. Until then the chat flow above is unchanged.

## 6. Template-reader side flow (offline, developer)

```
mixkit/prproj/VN folders -> backend/tools/app_readers.py (+ effectcraft_import.py for .aep)
                         -> labels (PVE template JSON)
                         -> backend/tools/filmcraft_bridge.py -> .fcproj
```

`.vnt` archives are encrypted and are not read. Unpacked VN folders come from the app itself. Status table: `data/mixkit/STATUS.md`.

## 7. Gold loop (offline, developer)

`tools.label` prefills `gold/<reel>/labels.draft.json` and contact sheets, the developer corrects it frame by frame into `labels.json`, `tools.score` appends the run to `gold/history.jsonl`. `tests/test_ops.py` fails on a regression beyond 0.05 F1 once `gold/targets.json` exists.
