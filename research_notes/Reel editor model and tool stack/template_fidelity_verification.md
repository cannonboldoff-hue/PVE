# Template-fidelity verification and self-correction for an AI Reel editor (as of Nov 2026)

Scope note: ~21 tool calls. Many 2026 arXiv IDs (2606.*, 2607.*, 2608.*) came from search snippets or abstract pages. They were not independently verified, so treat their numbers as author-reported. Tool/library suggestions marked "(not verified this session)" come from model background knowledge, not a fetched source. They live under Inferences or Gaps, never Cited Findings.

## 1. Structural fidelity metrics (cuts, pacing, beat alignment, captions, text boxes, OCR)

### Takeaway
No standard "template-fidelity" metric exists. The closest published building blocks are shot-boundary F1 (TransNetV2) and beat-alignment scores borrowed from music-to-dance work. Their tolerance and normalization are not standardized, so define and pin them explicitly in your own scorer. Caption timing, text-box IoU and OCR match have no template-specific benchmark found; build them from generic OCR/IoU primitives.

### Cited Findings
- TransNet V2 reports F1 of 77.9 (ClipShots), 96.2 (BBC Planet Earth), 93.9 (RAI) at a fixed 0.5 threshold. The paper's own re-run of baselines is flagged with asterisks. The excerpt I saw did not state the boundary-match tolerance. — [TransNet V2 paper](https://arxiv.org/pdf/2008.04838)
- An independent re-evaluation (Cosmos) got F1 0.967 BBC / 0.919 RAI / 0.726 ClipShots for TransNetV2. The ClipShots gap is attributed partly to a different ground-truth convention (midpoint of the annotated transition). Lesson: the ground-truth transition convention changes F1 by several points. — [Cosmos WFM platform](https://arxiv.org/pdf/2501.03575)
- A PyTorch packaging of TransNetV2 exists on PyPI (`transnetv2-pytorch`) and repos such as `PiatrouskiIM/transnetv2`. — [PyPI](https://pypi.org/project/transnetv2-pytorch/1.0.2/), [GitHub](https://github.com/PiatrouskiIM/transnetv2)
- Beat Alignment Score (BAS) originates in music-to-dance work. It is the mean distance from each motion beat to the nearest music beat, with beats from librosa. MV-Crafter adapts it to music-guided video by swapping in visual beats and a 0.1 normalization constant. — [MV-Crafter](https://arxiv.org/pdf/2504.17267), [survey: video-to-music generation](https://arxiv.org/pdf/2502.12489)
- Variants in the literature, with no single standard: Beats Coverage Score and Beats Hit Score, the fraction of scene cuts within 0.1 s of a beat, Transitions-Beats IoU, and Music-Beat Coverage Rate (fraction of musical beats covered by a visual beat within 100 ms). BAS alone can look good when few movements occur, so papers pair it with a coverage metric. — [Video Echoed in Music](https://arxiv.org/pdf/2511.09585), [survey](https://arxiv.org/pdf/2502.12489)

### Inferences
- Cut-list fidelity: run TransNetV2 (or PySceneDetect AdaptiveDetector, not verified this session) on both reference and render. Compute boundary F1 at tolerances of about ±2 frames and ±5 frames, plus a mean absolute cut-time error. Since the renderer knows its own cut list, only the reference needs detection. Check the render against the plan EDL directly (exact), and use detection only to catch unintended cuts such as clip-internal cuts or transition artifacts.
- Pacing: resample the shot-duration sequence into cuts/sec in 1-2 s windows. Compare reference and render with a Pearson/DTW distance, and report ASL (average shot length) ratio. Do this as the cheapest first check; it needs no model.
- Beat alignment: pair a "cut-hit rate" (cuts within ±70-100 ms of a librosa/madmom beat, the 100 ms figure from the Music-Beat Coverage Rate above) with a "beat-coverage rate", which guards against the BAS failure mode. Compute the same metrics on the reference and score the render relative to the reference's value, because a template might be intentionally off-beat.
- Caption timing, text-box IoU, OCR string match: no paper-backed standard found. Practical recipe: sample frames at caption on/off events, OCR them (PaddleOCR / EasyOCR / VLM, not verified this session), compare normalized strings (CER via `jiwer` or `rapidfuzz`, not verified), and compare bounding boxes against the planned text layer with IoU. Since the renderer owns the text layer, the plan-vs-render check is near-deterministic; reference-vs-render is only needed for style fields (font size, position, color, animation).

### Gaps
- No library or paper found that packages "template fidelity" as one score. Weighting across cuts, text and color is unaddressed.
- Tolerance convention for TransNetV2 evaluation was not confirmed.
- No sourced benchmark for caption-timing offsets or text-box IoU in short-form templates.

## 2. Perceptual and semantic similarity (CLIP/SigLIP2, DreamSim, LPIPS, color, motion, audio)

### Takeaway
DreamSim is the best-supported perceptual metric for layout/pose/semantic similarity (it beats LPIPS, which works on patches). SigLIP 2 is the current open image-text encoder family for semantic embeddings. Color, optical-flow and audio comparisons were not source-checked in this pass.

### Cited Findings
- DreamSim ensembles CLIP, OpenCLIP and DINO embeddings, is fine-tuned (LoRA) on about 20k human-labeled synthetic triplets, and reaches 96.16% agreement with human judgments on them. A CVPR 2026 supplement says it tracks pose, layout, shape and semantic changes, which LPIPS does not. — [DreamSim](https://arxiv.org/pdf/2306.09344v3.pdf), [CVPR 2026 supplement](https://openaccess.thecvf.com/content/CVPR2026/supplemental/Jeong_Training-free_Perceptually_Consistent_CVPR_2026_supplemental.pdf)
- LPIPS is the most-used perceptual metric but operates on 64x64 patches. The DreamSim paper argues that patch-level metrics miss mid-level similarity. A 2025 novel-view-synthesis benchmark found DreamSim more robust to minor defects than traditional metrics. — [DreamSim](https://arxiv.org/pdf/2306.09344v3.pdf), [NVS benchmark](https://arxiv.deeppaper.ai/papers/2506.12563v1)
- SigLIP 2 (Google DeepMind, Feb 2025): a multilingual encoder family (ViT-B 86M, L 303M, So400m 400M, g 1B) plus a NaFlex variant that keeps native aspect ratio. It adds captioning-based pretraining and self-supervised losses for better localization and dense features. — [SigLIP 2](https://arxiv.org/pdf/2502.14786)
- Reels and TikTok content is clip-based, so most "template" signal sits in per-shot visuals. ShotFinder (a shot-retrieval benchmark) reports that color and visual style remain major challenges for retrieval. — [ShotFinder](https://arxiv.org/pdf/2601.23232)

### Inferences
- Because user clips differ from reference content, content similarity (per-frame CLIP/SigLIP, DreamSim) between render and reference should NOT be a goal. Use embedding similarity only for (a) shot-to-slot semantic matching in the blueprint ("close-up of food" vs actual clip), and (b) template-style consistency within the render. DreamSim/LPIPS against the reference frame would punish correct behavior.
- Style-only comparisons are the right target. Compare statistics rather than pixels: per-shot mean/percentile luma, saturation, color-temperature, Lab histogram distance (e.g. ΔE2000 between mean Lab or EMD between histograms), contrast, and presence of a LUT/grade. Also compare the motion-energy profile (mean optical-flow magnitude per shot, via OpenCV Farneback for cheap, RAFT for accurate; not verified this session) and the audio energy envelope or onset density. Compare the time-series with correlation/DTW, not absolute values.
- Reference-side per-shot descriptors (shot scale, camera motion type, subject count) can be stored in the blueprint; the render check then asks a cheap model for the same descriptors on the placed clip.

### Gaps
- No source found on SigLIP 2 for video-frame similarity specifically, nor on RAFT-based motion-profile comparison for style transfer.
- No evidence found of ΔE-based grade matching being validated against human "feels like the reference" judgments.
- Audio-similarity metrics (CLAP, onset-envelope correlation) not researched.

## 3. Technical quality checks (VMAF, black/freeze, loudness, safe zones, specs)

### Takeaway
Use cheap FFmpeg filters for freeze/black/silence/loudness, ffmpeg-quality-metrics for VMAF/PSNR/SSIM only when comparing an encode against its own source (not against the reference Reel). Safe-zone and upload specs are community-sourced; no platform-published pixel values were found.

### Cited Findings
- `ffmpeg-quality-metrics` (slhck) wraps FFmpeg to compute VMAF, PSNR, SSIM, VIF (MS-SSIM per PyPI); the current release needs Python 3.9+ and FFmpeg 7.1+, VMAF needs a libvmaf build, and the package bundles VMAF models. A Python class API and CLI (`-m vmaf`, `--vmaf-model-path`, `--vmaf-features` e.g. CAMBI) are available. — [GitHub](https://github.com/slhck/ffmpeg-quality-metrics), [PyPI](https://pypi.org/project/ffmpeg-quality-metrics)
- Core spec: 1080x1920, 9:16 for Reels and TikTok across all spec guides found; Reels accepts up to 4 GB. — [Argil Reel spec sheet](https://argil.ai/blog/instagram-reel-size-e350f), [Blitzcut specs 2026](https://blitzcutai.com/blog/social-video-specs-2026)
- Safe zone figures conflict across sources: a centered 1080x1420 region (most common), a tighter ~856x1094 cross-platform box, TikTok top ~220 px / bottom ~480 px blocked, and Instagram bottom UI ~250 px vs ~350 px. Sources contradict each other on whether Instagram's or TikTok's bottom UI is taller. One source states no platform publishes binding safe-zone pixel values; TikTok's ad spec covers bitrate, size and length only. — [PostSyncer safe areas](https://postsyncer.com/tips/instagram-reels-size-and-safe-areas), [Argil TikTok](https://argil.ai/blog/tiktok-aspect-ratio-cec4c), [Frameo](https://frameo.ai/blog/reel-size/)
- Bitrate guidance 8-16 Mbps with AAC 192 kbps (vendor blogs, not official). — [Argil Reel spec sheet](https://argil.ai/blog/instagram-reel-size-e350f)
- Loudness: consensus is -14 LUFS integrated with a -1 dBTP true-peak ceiling. This is third-party; no official TikTok/Instagram loudness spec found, and one vendor says -16 LUFS. — [DEV: LUFS -14 standard](https://dev.to/arthurvalle1_a2586dd2b4bc/mastering-for-reels-tiktok-and-youtube-shorts-the-lufs-14-standard-2ck5), [Opus loudness normalizers](https://opus.pro/blog/best-loudness-normalizers)
- FFmpeg filter doc locations: freezedetect (11.105), blackdetect (11.12), ebur128 (20.10), loudnorm (8.97), silencedetect (8.107). I could not read parameter details this session (page truncated / connection error). — [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)

### Inferences
- Deterministic gate order (all milliseconds-to-seconds): ffprobe container check (resolution, fps, SAR, pix_fmt yuv420p, duration, audio present, sample rate) -> `freezedetect` (unintended stills) -> `blackdetect` (black frames at joins) -> `silencedetect` -> `ebur128`/`loudnorm` measurement (flag outside roughly -16..-12 LUFS or true peak > -1 dBTP) -> text-layer safe-zone check.
- Safe-zone check is geometric and needs no model: test every planned text/sticker bounding box against a conservative union mask. Safe default: keep key content inside x 64-1016 (about 6% side margin), y ~250-1500; treat it as a configurable constant because values are not official.
- VMAF is a full-reference quality metric against a pristine source; use it only to verify the final encode did not degrade versus the pre-encode master (regression test), never to compare render vs reference Reel.
- Default FFmpeg thresholds I recall (blackdetect pic_th 0.98, d 2.0; freezedetect n -60 dB, d 2 s) are not verified this session. Lower `d` to ~0.1-0.3 s for short-form joins.

### Gaps
- No official Instagram/TikTok safe-zone, bitrate, or loudness doc retrieved; all numbers are third-party and contradictory. Recommend re-verifying in-app.
- FFmpeg filter parameters not re-read this session.

## 4. VLM-as-judge for video (reliability, biases, rubric design, T2V judges)

### Takeaway
VLM judges are usable but biased: position effects can be large, repeat-run agreement is only about 83-87% in one study, and pooling weak judges does not reliably help. Mitigate by swapping order, using per-dimension rubrics with evidence, and gating with deterministic metrics. Specialized judges (VideoScore2) beat general MLLMs on generated-video scoring but target T2V artifacts, not template fidelity.

### Cited Findings
- MEDit-Bench (2607.25300, search-snippet-derived): with Gemini-3.5-flash as A/B judge, swapping slot order shifted win rates substantially (A-slot preference about 17.7 points), consistent across all models. Repeated runs agreed 83-87%, and human agreement reached 66.1% on triples where all runs were unanimous. I could not open the PDF body to confirm. — [MEDit-Bench](https://arxiv.org/pdf/2607.25300)
- "Is Your Video Language Model a Reliable Judge?" (ICLR 2025): pooling multiple video-LM judges does not reliably help; weak judges can drag down a mixed pool, and fine-tuning a weak judge did not make it more reliable. — [arXiv 2503.05977](https://arxiv.org/abs/2503.05977v1)
- "Judging the Judges": position bias in LLM pairwise judging is not random, varies across judges and tasks; pairwise setups are more position-consistent than score-based. This is text-only. — [arXiv 2406.07791](https://arxiv.org/html/2406.07791v8)
- MLLM-as-a-Judge (image-text): GPT-4V and Gemini assign higher scores to longer content (verbosity bias). Not video. — [arXiv 2402.04788](https://arxiv.org/pdf/2402.04788)
- VideoScore2 (TIGER-AI-Lab, Sep 2025): scores generated video on visual quality, text-video alignment, and physical/common-sense consistency with rationales; trained on VideoFeedback2 (27,168 human-annotated videos) via SFT then GRPO; 44.35 in-domain / 50.37 out-of-domain average accuracy. A review reports the best MLLM tested (Claude-Sonnet-4) at 28.93 average on VideoScore-Bench-v2 (secondary source, author-reported figures). — [VideoScore2](https://arxiv.org/abs/2509.22799)
- VBench-2.0 (Mar 2025, rev. Aug 2025): 5 areas / 18 dimensions (Human Fidelity, Controllability, Creativity, Physics, Commonsense), combining VLM captioning and LLM reasoning with pre-filtering and redundant questioning to curb hallucination; validated with human annotation. — [VBench-2.0](https://arxiv.org/html/2503.21755v2)
- EditDuet's judge: GPT-4o compared two timelines via keyframe grids and durations; agreement with the majority human choice was 80.6% vs 78.7% human-human (PABAK 0.61 vs 0.57), 35 raters, 10 pairs each. — [EditDuet](https://arxiv.org/html/2509.10761v1)
- AVE-Compass rubric dimensions (MLLM judge): Instruction Following, Fidelity Preserving, Realism, and a combined Editing Intent; response-gated scoring prevents "no-op" outputs from scoring high on preservation. — [AVE-Compass](https://arxiv.org/html/2607.24821v1)

### Inferences
- Rubric design for this product: one binary or 1-5 question per dimension (cut rhythm feel, text style match, color/grade match, motion energy match, hook strength, overall "same template"), each requiring a timestamped evidence quote. Prefer pairwise reference-vs-render with both orders swapped; accept only order-consistent verdicts and treat disagreement as "uncertain".
- Feed the judge structured side information to avoid hallucination: the blueprint JSON, deterministic metric outputs, and keyframe grids rather than raw long video where possible. EditDuet used keyframe grids successfully.
- Response-gating (AVE-Compass) has a direct analog: do not give a "pacing matches" pass if the render simply has the same duration; require the cut-list metric first.
- Do not rely on one judge's absolute scores; use the judge to produce a ranked list of deviations, and to rank candidate renders (best-of-N), not as a pass/fail gate by itself.

### Gaps
- No study found that tests Gemini 2.5/3 or Claude on reference-vs-candidate short-form template similarity; all bias numbers come from other tasks.
- EvalCrafter and other T2V judges were not researched in this pass.

## 5. Agentic self-correction loops in video-editing research

### Takeaway
The strongest reported loop designs are Editor+Critic (EditDuet) and plan/execute/evaluate with best-candidate retention and bounded retries (AVE-Agent). Both support the same regression defense: keep the highest-scoring candidate and cap retries. Published iteration caps are mostly absent.

### Cited Findings
- EditDuet (SIGGRAPH 2025, Adobe): Editor agent (search/add/remove/switch/move/DONE tools) and Critic agent (give one corrective feedback item or RENDER), both Llama3.1-8B. No max iteration count stated. Failure rate 8.2%, coverage 89.8%, 0.174 repetitions; the Editor-Critic ablation without exploration-based demonstrations had 19.5% failure. Professional human edits were still preferred 75.1% of the time. Failures include hallucinated functions/files and out-of-bounds sub-clips. A VLM critic was not used due to context-length limits. — [EditDuet](https://arxiv.org/html/2509.10761v1)
- AVE-Agent (2607.24821): planner with validator (up to two automatic replans), executor with per-subtask evaluator and improver, and a mixed evaluator that picks the cheapest fix: remix, regenerate a subtask, or replan. It keeps the highest-scoring candidate so a later unstable attempt cannot overwrite a better one. Removing retry lowers Editing Intent by 8.75; removing prompt enhancement lowers it by 7.76. Retry budgets are in an appendix not read. — [AVE-Compass](https://arxiv.org/html/2607.24821v1)
- Kubrick (2024, Blender-based generation, not editing real footage): Director/Programmer/Reviewer agents; the Reviewer gives feedback on intermediate screenshots to the Programmer in an iterate-until-good loop. — [Kubrick](https://arxiv.org/abs/2408.10453)
- Crayotter: multi-agent framework with an observe-diagnose-revise loop inspecting intermediate renders and analysis artifacts, plus trajectory-level RLVR reward. Venue/date unconfirmed. — [Crayotter PDF](https://idwts.github.io/Crayotter/paper/assets/crayotter-paper.pdf)
- LAVE (2024): plan-and-execute conversational editing assistant, no critique loop. — [LAVE review](https://themoonlight.io/review/lave-llm-powered-agent-assistance-and-language-augmentation-for-video-editing)
- Related 2026 items found only via search snippets, unverified: VideoAgent (2606.23327, shot-level storyboards with paired indexing/retrieval), DIRECT (2604.04875, hierarchical multi-agent video mashup with intent-guided shot retrieval), "Thinking on Shots" (2608.26809, multi-shot editing with agentic reasoning), CineAgents (instruction-driven cinematic compilation). — [VideoAgent](https://arxiv.org/pdf/2606.23327), [DIRECT](https://arxiv.org/pdf/2604.04875v1), [Thinking on Shots](https://arxiv.org/pdf/2608.26809)

### Inferences
- Regression avoidance pattern (supported by AVE-Agent): treat every iteration as a candidate with a composite score; always output argmax, never "latest".
- Choose the fix by cost: patch the edit plan (timing, text, clip swap) before re-selecting clips, and clip re-selection before replanning the whole template. This mirrors AVE-Agent's remix / regenerate / replan ladder.
- Use 2-3 revision rounds, with early stop when score gain < epsilon. This is my recommendation, not a sourced number; the papers read here do not give a validated iteration count (EditDuet gives none, AVE-Agent's budget is in an unread appendix).
- Constrain the Editor to a typed edit-operation schema with bounds validation (clip IDs exist, trims within source duration). EditDuet's documented failures (hallucinated functions/files, out-of-bounds trims) are exactly what schema validation prevents.
- Because the renderer is deterministic FFmpeg, a fix-then-re-measure loop can be mostly deterministic: only the "which edit fixes this finding" step needs an LLM.

### Gaps
- "From Shots to Stories", HiVE, ExpressEdit, Reframe Anything: not found/read in this pass (a query for "From Shots to Stories" returned nothing relevant).
- No paper found that does reference-video template extraction and re-rendering with a closed verification loop; this appears to be an open niche.
- No published ablation on number of critique iterations vs quality.

## 6. What makes short-form templates "feel right" (pacing, hook, retention)

### Takeaway
No rigorous, peer-reviewed study linking cuts/sec to retention was found. Available numbers are creator/vendor claims and conflict; use them only as soft priors and always score relative to the reference template.

### Cited Findings
- Cut frequency advice varies: change something on screen every 3-5 s (one source) vs quick cuts every 1.5-2.5 s for Shorts (another); neither cites a study. Another argues for variation rather than speed. — [dev.to Hook Engineering](https://dev.to/bulkdl/hook-engineering-the-science-of-the-first-3-seconds-in-short-form-video-2026-2jp9), [Fluxnote Shorts guide](https://fluxnote.io/guides/increase-audience-retention-youtube-shorts)
- A creator self-test of 120 videos reported a 0.84 correlation between first-3-second retention and overall performance (small personal sample). An ex-Meta creator claims 40-60% drop in the first second and another 20-30% by second 3 (personal claim). — [dev.to Hook Engineering](https://dev.to/bulkdl/hook-engineering-the-science-of-the-first-3-seconds-in-short-form-video-2026-2jp9)
- A TikTok benchmark site claims 70-85% first-3-second retention is "good", citing unnamed "2025 industry data". — [TTS Vibes](https://insights.ttsvibes.com/?p=533)
- A claim that strong openings get 3-5x more impressions is attributed to YouTube's Creator Insider but could not be verified against a primary source. — [Opus retention data](https://www.opus.pro/blog/tiktok-length-format-retention-data)

### Inferences
- Since reference Reels are chosen because they performed well, the reference itself is the best prior. Score hook-window fidelity separately: compare the first 3 s of the render with the reference on first-cut time, cuts in first 3 s, text-on-screen at t<1 s, and motion energy.
- Reasonable soft rubric flags (heuristic, not evidence-backed): no static frame > ~2 s without motion/text change; first visible text or visual change before ~1 s; cut-rate within the reference's local range.

### Gaps
- No controlled or platform-published findings on cuts/sec vs retention; no Instagram-specific retention research found.

## 7. Recommended verification stack and turning findings into plan edits

### Takeaway
Layer checks from free and exact to costly and fuzzy, stop at the first failing layer, and convert every finding into a typed patch against the blueprint/EDL so the LLM only chooses among bounded fixes. Everything below is synthesis, not a sourced standard.

### Cited Findings
- Supporting precedents: AVE-Agent's cheapest-fix selection and best-candidate retention ([AVE-Compass](https://arxiv.org/html/2607.24821v1)); EditDuet's LLM-judge on keyframe grids with 80.6% agreement with majority human vote ([EditDuet](https://arxiv.org/html/2509.10761v1)); order-swap necessity from position-bias evidence ([MEDit-Bench](https://arxiv.org/pdf/2607.25300)).

### Inferences
- Layer 0, plan lint (no render): clip IDs/trim bounds valid, cut times = blueprint times ± tolerance, text boxes inside safe zone, beat-snapped cuts.
- Layer 1, ffprobe/FFmpeg technical gate: resolution/fps/pix_fmt/duration, `freezedetect`, `blackdetect`, `silencedetect`, loudness (-14 LUFS target, -1 dBTP peak, third-party consensus).
- Layer 2, structural fidelity vs blueprint (no model, or small CV models): detect cuts in render and compare to the plan EDL and reference (F1 at ±2/±5 frames), shot-length/pacing curve distance, beat-hit and beat-coverage rates, OCR on sampled frames (CER and IoU vs planned text layer), per-shot color stats/ΔE and motion-energy correlation vs reference.
- Layer 3, semantic checks with small models: SigLIP 2 / DreamSim only for clip-to-slot semantic fit and render-internal consistency (e.g. no duplicate frames across slots), not for content similarity to the reference.
- Layer 4, VLM judge, run only if Layers 0-2 pass or for residual ranking: pairwise reference vs render, both orders, rubric per dimension with timestamp evidence, keyframe grids plus blueprint JSON as context. Ask for a ranked list of deviations, not a score alone.
- Findings -> edits mapping (examples): cut late/early by dt -> retime shot boundary; shot too long -> trim or swap clip; text outside safe zone -> move box; text style mismatch -> change style tokens; color drift -> adjust grade params; beat miss -> snap cut to nearest beat within a limit; energy low -> choose a higher-motion candidate clip. Emit these as JSON Patch-like ops validated by schema, then re-render only the affected segments.
- Loop control: composite score = weighted layers; max 2-3 revision rounds; keep best; stop if no improvement; log per-finding before/after to detect regressions (a fix that worsens a previously-passing check is rejected).
- Calibration: build a small gold set of reference/render pairs with human "same template?" labels (EditDuet-style 10-pair rater study as a template) and fit weights; measure judge order-swap consistency before trusting it.

### Gaps
- No empirical evidence available that this exact stack improves perceived fidelity; weights and thresholds need local calibration.
- Latency/cost per layer not measured.
