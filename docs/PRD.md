# PVE Product Requirements Document

Status: draft, 2026-11-18. Sources: the architecture page (https://claude.ai/artifact/TAGSMnSadw1oRCTHZBRm7y), `docs/mvp-plan.md`, `TODO.md`, and the decisions recorded in the project memory. Where this file and `mvp-plan.md` disagree on the roadmap, this file wins; `mvp-plan.md` stays the record of what M0 to M12 built.

## 1. Summary

PVE turns a reference Instagram-style Reel into a reusable, editable template. The user supplies their own footage. PVE matches clips to template slots, renders a new Reel with the reference's structure and the reference's own audio, and reports how close the result is.

There are two tracks of work:

1. **Shipped web MVP (M0 to M12).** Hand-built detectors, a video AI for meaning, a frame-exact renderer, a chat UI. Template matches the original on about 60% of style checks; text is the weakest track (about 33%).
2. **Template model (the new direction).** A frame gate drops unchanged frames, a fine-tuned Qwen3-VL reads the rest and returns one template JSON, and a converter builds an editable FilmCraft / EffectCraft project from it. Each slot becomes a solid-colour canvas the user replaces with their own footage.

The model replaces the hand-built detectors only if it scores higher on the gold reels.

## 2. Problem

Short-form editors copy the look of a trending Reel by hand: cut timing, speed ramps, transitions, kinetic text. That takes an hour or more per Reel and needs frame-level skill. Existing tools either clone a template from a closed library (CapCut, VN, InShot) or generate new video from prompts. None reads an arbitrary Reel and hands back an editable project.

## 3. Users

| User | Need |
|---|---|
| Beginner to medium creator (primary) | Reuse a trending Reel's structure with their own clips, no frame counting. |
| Template author (secondary) | Turn a finished edit into a reusable template and see exactly what was and was not captured. |
| The developer (internal) | Measure detector and model accuracy against hand-labelled reels and track it over time. |

Talking-head reels are out of scope. Target styles: fast cuts and speed ramps, kinetic or lyric text, zoom and shake with advanced transitions, split screen and multi-layer, b-roll with small text.

## 4. Goals and non-goals

### Goals

- G1. Frame-exact reproduction of structure: slot count, slot lengths and total length come from the reference.
- G2. Coverage of everything a beginner to medium editor uses (CapCut level): cuts, speed, framing, camera motion, transitions, effects, colour, text, overlays, layout, masks. Full list in `mvp-plan.md` section 1.1.
- G3. An honest report: every feature the renderer could not reproduce is listed with the reason (`loss`), every low-confidence field is shown to the user.
- G4. A model path that is measured, not assumed: a fine-tuned checkpoint replaces prompting only if it beats it on the gold reels.
- G5. An editable output: the user can open the result as a FilmCraft / EffectCraft project, not only a flat MP4.

### Non-goals (decided by the user, do not reopen)

- No audio work. The output keeps the reference's audio unchanged. No song swap, beat detection, speech-to-text or stem separation. The research reports advise against carrying the reference audio (copyright); the user was told once and is firm.
- No footage matching quality work beyond the existing flow. "Template fidelity only"; the user supplies the shots.
- No segmentation models (no MediaPipe cutouts, no BiRefNet). A cutout is a shot instruction; the user supplies alpha footage.
- LUT grading, green screen, object-tracked text.
- Face identity matching, generative fill, multi-user accounts, cloud hosting (v1).
- Modded APKs and extraction of locked templates (for example `.vnt`).

## 5. Functional requirements

### 5.1 Reference intake (shipped)

- FR-1. Accept a reference as an uploaded file or a link. Upload is the supported path; link download (yt-dlp) is a platform-terms risk and stays flagged.
- FR-2. Normalise to 30 fps constant frame rate. All times are integer frames at 30 fps (`ir.f2s` converts at the edges only).
- FR-3. Fingerprint the file, cache the analysis by fingerprint, delete the uploaded original after analysis.

### 5.2 Analysis (shipped, to be challenged by the model)

- FR-4. Measure 15 evidence tracks: cuts, transitions, text, text animation, camera, still/photo, speed, effects, layout, overlays, colour and others listed in `mvp-plan.md` section 3.2.
- FR-5. Ask a video AI (Pegasus or Gemini) for typed meaning per slot: role, function, subject, action, shot size, effect names. Closed vocabularies with an `other` escape that keeps the raw word.
- FR-6. Fuse evidence and meaning with one owner per field; conflicts are logged, the owner's value wins.
- FR-7. Extract the template: each field is `keep`, `swap` or `drop`, with a reason for every drop.

### 5.3 Validation (shipped)

- FR-8. Same-shot pass: render every slot with the reference's own footage; frame count, per-frame SSIM and audio lag must match. Failure means the template is wrong.
- FR-9. Marker pass: render the template over plain marker clips and re-measure with the same detectors; at least 90% of rows must agree.
- FR-10. Coverage: every evidence item is used, dropped with a reason, or listed unsupported. Below 100% is a bug.
- FR-11. At most 3 repair rounds; keep the best template.

### 5.4 Production (shipped)

- FR-12. Brief and shot specs, confirmed by the user.
- FR-13. Match user clips to slots (hard filters, then judge, then one global assignment so a clip is not reused when another fits). Labels: exact, similar, adaptable, missing.
- FR-14. Tell the user what to film for missing slots (length, framing, movement, subject).
- FR-15. Approve is an explicit button; the chat agent has no approve tool.
- FR-16. Render with FFmpeg + libass as base and HyperFrames as overlay engine (Remotion second, not installed). Verify in layers; failing deterministic layers force repair.

### 5.5 Template model (new)

- FR-17. **Frame gate (no AI).** Normalise to 30 fps and 544 x 960. Keep a frame when it differs from the previous frame or from the last kept frame by more than a threshold; always keep the frames on both sides of a change; keep at least one frame per 0.5 s. Describe dropped runs with gap notes in the prompt. Starting threshold 12 (keeps about 40% of frames, lost 0 of 164 labelled cuts and flashes on the 9 gold reels of 30 s or less).
- FR-18. **Chunking, only over the token budget (about 240k).** Split at calm points with a 1 s overlap. Plain code joins chunk outputs using burned-in absolute frame numbers, dedupes the overlap and checks that slots tile frames 0 to n.
- FR-19. **Model.** Qwen3-VL fine-tuned to read the gated frames and return one template JSON per reel with exact frame numbers. The JSON is the compact template IR (`backend/app/ir.py`), not a CapCut draft.
- FR-20. **Converter.** Validate the JSON, build a FilmCraft and EffectCraft project. Each slot becomes a solid-colour canvas. Anything that cannot be built goes in a report.
- FR-21. **Promotion rule.** A checkpoint replaces Pegasus prompting only if it scores higher on the gold reels.

### 5.6 Training data (new)

- FR-22. Target mix from the pilot on: 80% real labelled reels, 20% synthetic reels (PVE renderer, random templates, stock footage). The 2B trial uses synthetic only. The 12 gold reels are the test set only.
- FR-23. Real-reel labels come from per-app project-file readers: Premiere Pro (ready), Alight Motion, VN, KineMaster (need testing), CapCut (own edits only), InShot (skipped). Contributors of mobile-editor reels are paid about ₹200 to ₹500 each with a signed IP assignment.
- FR-24. Readers feed FilmCraft only through PVE template JSON. FilmCraft refuses `.mogrt` and `.aep` by design (clean-room rule); do not add `.mogrt` import to it.

## 6. Quality bar

| Measure | Target |
|---|---|
| Timing, same-shot pass | frame count exact, SSIM minimum at least 0.95, audio lag 0 |
| Cuts and flashes | no labelled cut lost by the frame gate; F1 target set from the first gold baseline |
| Style checks vs original | above the 60% baseline; model must beat it to ship |
| Text track | above the 33% baseline; per-region 4 x 4 change test proposed for small captions |
| Coverage | 100% |

No target is set before a real baseline exists. Record the first baseline in `gold/history.jsonl`, then set per-track targets.

## 7. Model plan

| Stage | Model | Hardware | Cost (estimate) |
|---|---|---|---|
| 0 Trial | Qwen3-VL-2B | Kaggle 2x T4 | $0 |
| 1 Pilot | Qwen3-VL-4B | Colab A100 | about $200 to $300 per epoch |
| 2 Whole reel | Qwen3-VL-30B-A3B | 8x H100 | about $5k to $7k |
| 3 Largest | Qwen3-VL-235B-A22B | 16 to 32 H100 | about $26k to $40k |
| 4 Production | best checkpoint | 1x H100 per worker | about $0.05 to $0.15 per reel |

A stage advances only if the previous one stops improving on the gold reels. Cost is not the constraint; quality is. Token counts and chunk sizes are estimates, confirmed by stepping down until they fit.

## 8. Success metrics

- Gold-set F1 per track (cuts, transitions, text, effects, speed, camera, layout) tracked in `gold/history.jsonl`.
- Share of style checks matched vs the original (baseline 60%).
- Share of reels whose template passes validation without user edits.
- Import losses (531 unreadable items across 49 Mixkit After Effects templates: text 255, transforms 124, effects 99, shape layers 20, markers 14, layer styles 13, project data 6) are a floor on reader gaps, not a limit on the converter.
- Cost and time per reel, from `project_events`.

## 9. Constraints

- Windows 11, Python 3.12, FFmpeg 9 with libass, Node 24, RTX 2050 with 4 GB VRAM (local); no Rust toolchain (release binaries in `tools-bin/`).
- Mixkit terms bar "similar or competitive product" use and bot mass downloads. Check the Video Templates licence before training on Mixkit templates.
- Free-tier Gemini content may be used for training: send only reels the user owns.

## 10. Open items

1. Label source for real reels: pipeline plus hand check, or app project files. Not decided.
2. Rights to real reels and stock footage sources. Not decided.
3. Which CapCut (desktop intl, JianYing, mobile) if a CapCut exporter is built. FilmCraft / EffectCraft is the current target instead.
4. Small changes (a caption popping in) may not move a whole-frame average; the per-region test is proposed, not built.
5. Transition windows, text start/end frames and text animations are not yet tested against the frame gate.
6. FilmCraft / EffectCraft capability per field is unmeasured.
7. The join step needs tests.
8. Hand-label gold reels 07 to 13 (TODO GOLD-1) and record the baseline (GOLD-2).
9. Link download (yt-dlp) stays flagged; decision 3 in `mvp-plan.md` section 7.
