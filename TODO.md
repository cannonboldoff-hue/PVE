# TODO

Sorted by priority (P0 first). Each item follows the same fields.

---

### GOLD-1 — Hand-label the 13 gold reels (`gold/reel01` … `gold/reel13`)
- **Priority:** P0
- **Category:** Accuracy & Testing
- **Description:** Each reel in [`gold/`](gold/) has a `labels.draft.json` (detector prefill) and `shots/` contact sheets made by `python -m tools.label`. Open each video in a frame-stepping player (mpv `.` / `,`, VLC `e`), correct the draft by watching the video, and save it as `labels.json`. Cover cuts, transitions, texts, effects, speed, camera, layout and overlays. Times are integer frames at 30 fps (`frame = round(seconds * 30)`). Format and allowed values: [`gold/README.md`](gold/README.md) and `backend/app/ir.py`.
- **Why required:** the gold set is the only measure of real detector accuracy. A draft accepted without checking comes from the same detectors being scored, so the score would mean nothing.
- **Business value:** lets us say how accurate reel analysis is, with numbers, before users see it.
- **Technical value:** gives `tools.score` a ground truth, so detector changes can be compared run to run in `gold/history.jsonl`.
- **Dependencies:** drafts for all 13 reels. `reel01`–`reel06` are done; `reel07`–`reel13` were still generating when this was written.
- **Suggested order:** immediate.
- **Complexity:** L — about 13 reels, frame-level checking by a human.
- **Success criteria:** every `gold/reelNN/` has a `labels.json` checked against the video; no `labels.draft.json` is committed; only `labels.json` files are committed (the `.mp4` files stay gitignored).
- **Found via:** direct instruction (2026-11-13).

---

### GOLD-2 — Run the scoring harness and record a baseline
- **Priority:** P0
- **Category:** Accuracy & Testing
- **Description:** From `backend/`, run `.venv\Scripts\python -m tools.score` once the labels exist. Save the result as the first line of `gold/history.jsonl`. List the weakest detectors (cuts, transitions, text, effects) and file each as its own item.
- **Why required:** without a baseline, later detector work cannot be shown to help or hurt.
- **Business value:** an accuracy number we can track and quote.
- **Technical value:** a regression check for every detector change.
- **Dependencies:** GOLD-1.
- **Suggested order:** right after GOLD-1.
- **Complexity:** S.
- **Success criteria:** `gold/history.jsonl` has a baseline line; each detector scoring below target has its own TODO item with the numbers.
- **Found via:** `gold/README.md` workflow (2026-11-13).

---

### PERF-1 — Run label/OCR analysis on the GPU
- **Priority:** P1
- **Category:** Performance
- **Description:** `tools.label` takes about 1–5 minutes per reel, and the GPU (RTX 2050, 4 GB) sat idle at 0% use. The installed `onnxruntime` 1.31.1 is the CPU-only build (providers: `AzureExecutionProvider`, `CPUExecutionProvider`). Replace it with `onnxruntime-gpu`, install the matching CUDA/cuDNN libraries, and turn on CUDA in the RapidOCR settings in `backend/app/evidence/text.py:37`. Time one reel before and after. Profile first to confirm OCR is the bottleneck, since that is not yet measured.
- **Why required:** analysis time slows every gold-set rerun and every product run.
- **Business value:** faster turnaround on a reel.
- **Technical value:** frees the CPU and shortens the scoring loop.
- **Dependencies:** none, but do it while no label run is active, because changing the venv breaks a running job. Watch the 4 GB memory limit for out-of-memory errors; keep a CPU fallback.
- **Suggested order:** after the current label run finishes.
- **Complexity:** M.
- **Success criteria:** a profile shows where the time goes; one reel runs measurably faster on the GPU with the same `labels.draft.json` output; the CPU path still works if CUDA is missing.
- **Found via:** direct question from the user (2026-11-13).

---

### GOLD-3 — Decide what `gold/shots/` is and tidy `gold/reels/`
- **Priority:** P2
- **Category:** Cleanup
- **Description:** `gold/shots/` holds 7 loose clips (`450w-*.mp4`, `document_810w-*.mp4`) that are not in the per-reel layout. `gold/reels/` is now empty because the 13 reels were moved into `gold/reelNN/`. Decide whether the clips are footage for matching or leftovers, then keep, move or delete them, and remove the empty `gold/reels/` folder.
- **Why required:** the `gold/` layout in the README is one folder per reel; stray files confuse the tools and the next person.
- **Business value:** none directly.
- **Technical value:** a clean, predictable `gold/` tree.
- **Dependencies:** none.
- **Suggested order:** whenever convenient.
- **Complexity:** S.
- **Success criteria:** every file under `gold/` has a stated purpose; no empty folders remain.
- **Found via:** directory listing of `gold/` (2026-11-13).
