# PVE Implementation Plan

Forward plan, written 2026-11-18. `docs/mvp-plan.md` records M0 to M12 (the shipped web MVP); this file covers what comes next: the gold baseline, the frame gate, the model stages, the converter, and the data. Every threshold and cost here is an estimate to confirm by measurement. One milestone per session, in order, unless a dependency line says otherwise.

## 0. Rules for every milestone

1. Read the files listed under "Read first" before editing.
2. Run `cd backend && .venv\Scripts\python -m pytest -q` before and after. The suite (96 tests at M12) must stay green.
3. Reuse before writing. The IR in `backend/app/ir.py` is the only template schema; the model emits it.
4. Thresholds are named constants at the top of their module, each with a one-line comment on the trade-off.
5. New tracks get a test on a synthetic reel with exact ground truth (`tests/synth.py`).
6. A milestone is done when its "Done when" line is shown true, not when the code exists. Tick the box in this file and add one dated line to section 9.
7. If this plan is wrong, fix it in the same commit and say so in section 9.
8. Subagents follow `CLAUDE.md` rule 5 (model one tier below the main agent).
9. Do not reopen decisions listed in `docs/PRD.md` section 4 (audio, shots-only fidelity, no segmentation models).

## 1. Dependency map

```
G1 gold labels -> G2 baseline -> F1 gate -> F2 chunker -> F3 join
                               \                          |
                                -> D1 synthetic data ---> T0 trial -> T1 pilot -> T2 whole reel -> T3 largest -> T4 production
                                -> D2 real-reel readers --^
                                                    C1 converter (can start after F3; needed before T1 results are usable)
                                                    E1 evaluator (needed before T0)
```

## 2. Milestones

### G1. Hand-label the gold reels (TODO GOLD-1, P0)
- [ ] Reels `gold/reel01` to `gold/reel13`. `reel01` to `reel06` drafts exist; 07 to 13 were still generating. Note: the working tree currently shows `gold/` deleted (`git status`); restore it from git before starting, and keep only `labels.json` and shots committed, never the `.mp4` files.
- [ ] Scrub each video frame by frame (mpv `.` / `,`), correct the draft, save as `labels.json`. Include the optional fields (tiles, masks, match cuts, reverse, tilt) on reels that show them (TREND-1).
- Done when: every reel has a checked `labels.json`; no `labels.draft.json` committed.
- Complexity: L (human time).

### G2. Baseline (TODO GOLD-2, P0)
- [ ] `cd backend && .venv\Scripts\python -m tools.score`; first line into `gold/history.jsonl`; run `--providers` for the Gemini vs Pegasus table when a key exists.
- [ ] One TODO item per detector below target, with its numbers. Write `gold/targets.json` from the baseline (`tests/test_ops.py` enforces it).
- Done when: history line exists, targets file exists.

### E1. Model evaluator
Read first: `tools/score.py`, `app/stages/compare.py`.
- [ ] Add `tools/score_model.py`: take a `Template` JSON per gold reel (from any source), score it with the same comparators and the same per-track F1 as `score.py`, plus the 60% style-check agreement used as today's baseline.
- [ ] Output one table: pipeline arm vs model arm, per track.
- Done when: running it on the current pipeline's templates reproduces `score.py` numbers.

### F1. Frame gate
Read first: `app/evidence/frames.py`, `app/clients/ff.py`.
- [ ] `app/gate.py: gate(proxy, threshold=12) -> Gated(kept: list[int], gaps: list[(start, end)], n_frames)`.
- [ ] Normalise to 30 fps, 544 x 960. Keep a frame if it differs from the previous frame or the last kept frame by more than `THRESHOLD`; always keep both sides of a change; keep at least one per `MAX_GAP_FRAMES = 15`. Output absolute frame numbers burned into the image (small corner stamp) or passed in text; decide by checking Qwen reads them reliably.
- [ ] Per-region variant: 4 x 4 grid, trigger if any cell exceeds the threshold, so a caption popping in is kept.
- [ ] Gap notes: "frames a to b unchanged, same as frame a".
- Done when: on the gold reels at 30 s or less, kept share near 40% and zero labelled cuts, flashes, transition windows or text start/end frames lost (the artifact only proved cuts and flashes; the other three are the new test); sweep 4, 8, 12 recorded in section 9.

### F2. Chunker
- [ ] `app/chunk.py`: estimate tokens per kept frame; if over `TOKEN_BUDGET` (about 240k, confirm), split at calm points (low frame-difference) with `OVERLAP_FRAMES = 30`.
- [ ] Chunk size for small models: about 16 to 24k tokens (2B on a 16 GB T4, about 30 to 45 kept frames); about 64 to 96k for the 4B on a 40 GB A100. Confirm by stepping down until it fits.
- Done when: chunks cover every kept frame, overlaps are exactly 1 s, and token estimates are within 10% of the tokenizer's real count on 5 reels.

### F3. Join
- [ ] `app/join.py`: merge chunk templates by absolute frame; dedupe the overlap (keep the version whose slot or event sits furthest from a chunk edge; edge flags set by the model); check slots tile `0..n`; on failure, report which seam and re-run that chunk once.
- [ ] Tests: synthetic chunked outputs with cuts, transitions and texts straddling a seam.
- Done when: seam tests pass and a reel run as 3 chunks joins to the same template as the same reel in one chunk on a stubbed model.

### D1. Synthetic data generator
Read first: `tests/synth.py`, `app/render/*`.
- [ ] Random template sampler over the closed vocabularies (cuts, transitions, speed, effects, text, camera, layout, overlays), rendered by the PVE renderer over stock footage, label = the template used to render it. Ground truth is exact by construction.
- [ ] Stock footage source with a licence that allows training (undecided; see `docs/Security.md` 4.2). Use synthetic marker footage until decided.
- [ ] Output records `{reel_id, source: synthetic, frames, gap_notes, label}` under `training/`.
- Done when: 100 reels generate with no tiling error and labels reload through `ir.Template`; 800 for the trial (all synthetic at stage 0).

### D2. Real-reel labels (parallel, human + readers)
Read first: `backend/tools/app_readers.py`, `filmcraft_bridge.py`, `data/mixkit/STATUS.md`.
- [ ] Premiere Pro `.prproj` reader: ready. Alight Motion, VN, KineMaster: test on one real project each. CapCut: own edits only. InShot: skipped.
- [ ] Contributor process: paid about ₹200 to ₹500 per reel, signed IP assignment, per-reel record. Needs the user's decision on label source and rights (PRD open items 1 and 2) before any paid collection.
- [ ] Reader loss counts per app go in a table so the "floor" on reader gaps is tracked (Mixkit baseline: 531 unreadable items over 49 templates).
- Done when: 20 real reels with labels read from project files, converted to `ir.Template`, round-tripped through the renderer and checked against the video by eye.

### T0. Trial: Qwen3-VL-2B on Kaggle 2x T4
- [ ] About 800 reels, synthetic only (80/20 real/synthetic starts at T1), 1 to 2 epochs, about 40 h per epoch, chunked samples of 16 to 24k tokens, QLoRA.
- [ ] Training loop, prompt format and JSON-only output constraint; evaluate each epoch with E1 on the gold reels (test set only).
- Done when: the model returns valid `ir.Template` JSON on at least 95% of gold chunks and a per-track score table exists. Gate: any track above the pipeline arm, or a clear learning curve, before T1.
- Cost: $0.

### T1. Pilot: Qwen3-VL-4B on Colab A100
- [ ] 80% real, 20% synthetic. Chunks 64 to 96k tokens (about 125 to 190 frames, 10 to 15 s). About $200 to $300 per epoch.
- Done when: the 4B beats the 2B on the gold reels; plateau curve recorded.

### T2. Whole reel: Qwen3-VL-30B-A3B on 8x H100
- [ ] Whole-reel context (256k window) with sequence parallel; chunking only when a reel exceeds the budget. About $5k to $7k. Only if T1 plateaus.
- Done when: it beats T1 on the gold reels.

### T3. Largest: Qwen3-VL-235B-A22B on 16 to 32 H100
- [ ] About $26k to $40k. Only if T2 plateaus on a capacity ceiling (not a data ceiling: check data first).
- Done when: it beats T2.

### C1. Converter to FilmCraft / EffectCraft
Read first: `backend/tools/filmcraft_bridge.py`, `app/render/capabilities.py`.
- [ ] `app/convert.py: to_project(template) -> (.fcproj, report)`: validate against `ir.Template`; each slot becomes a solid-colour canvas; transitions, text, effects mapped where FilmCraft / EffectCraft can write them; everything else listed in the report with its reason.
- [ ] Measure per-field FilmCraft / EffectCraft capability (currently unmeasured) and record it in a table; the report must match the table.
- [ ] `.fcproj` is schema-1; FilmCraft migrates it.
- Done when: a gold reel's template opens in FilmCraft with the right slot count and lengths, and the report lists every dropped field.

### T4. Production serving
- [ ] Best checkpoint on 1x H100 per worker, about $0.05 to $0.15 per reel. Worker queue behind the existing project states.
- [ ] A model arm in the pipeline selectable per reel; promote the checkpoint only if it scores higher than the Pegasus path on the gold set (PRD FR-21).
- Done when: a reel uploaded in the UI produces a template via the model, validates through the same-shot and marker passes, and renders.

## 3. Cross-cutting work

| Item | Source | When |
|---|---|---|
| TREND-1: tune `camera.SHAKE_MIN/PUNCH_MIN`, `match_cuts.EDGE_MATCH/COLOUR_CHANGE`, `masks.MIN_BG`, `text.LIT` on real reels; 4 open checks | TODO.md | after G2 |
| Security gaps: upload limits, subprocess timeouts, URL allow-list, remote asset deletion, secret scan | `docs/Security.md` | before any hosted use; timeouts and limits soon |
| Front end gaps: mobile drawer, focus rings, aria-live | `docs/UI-UX-Brief.md` | any time |
| Loss review: list the most frequent `loss` strings on gold reels; they are the next renderer features | `mvp-plan.md` M12 | after G2 |
| `Remotion` adapter | `mvp-plan.md` M9 | only if HyperFrames fails somewhere |
| Add `PERF` follow-ups (GPU OCR done; model inference cost) | TODO.md | as needed |

## 4. Order of work (recommended)

1. G1, G2 (nothing else can be judged without them).
2. E1, F1 (gate test on the 3 untested properties).
3. F2, F3, D1 in parallel.
4. T0, C1.
5. D2 once the user decides label source and rights.
6. T1 onward, each stage only when the previous plateaus.

## 5. Risks

1. **Gate loses small changes.** A caption popping in may not move a whole-frame average. Mitigation: per-region 4 x 4 test (F1). Check text start/end frames explicitly.
2. **Token estimates are guesses.** Step down until it fits; measure with the real tokenizer.
3. **Join bugs create silent tiling errors.** The tiling check is mandatory and unit-tested.
4. **Real-reel rights undecided.** Do not collect paid data until decided.
5. **Overfitting to synthetic data.** Real share is 80% from the pilot on; gold reels never train.
6. **Costs scale 100x between stages.** Gates are score-driven, never calendar-driven.
7. **FilmCraft capability unknown per field.** Converter report is the safety net; measure first.
8. **Hand-label bias.** Drafts come from the detectors being scored; labellers must scrub the video, not accept the draft.

## 6. Environment facts

Windows 11, Python 3.12 in `backend/.venv`, FFmpeg 9.0.2 full build, Node 24, RTX 2050 (4 GB) for local detectors, no Rust toolchain (`tools-bin/` holds FilmCraft and EffectCraft release binaries, SHA256-checked). Training runs off-machine (Kaggle, Colab, rented H100).

## 7. Acceptance for the whole programme

The model path ships when: a fine-tuned checkpoint scores above the pipeline arm on the gold reels in every track that matters to the user; the converter produces an openable FilmCraft project with a loss report; validation A passes on its output; per-reel cost is inside the stated range.

## 8. Tracking

Tick boxes here. Failed or reshaped items stay listed with a dated note.

## 9. Decisions log

- 2026-11-18: plan written from the architecture page, `mvp-plan.md` and the memory notes. Nothing in sections 2 to 7 has been run.
