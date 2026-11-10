# Best models for reel-to-blueprint analysis and the LLM planning layer (state as of 2026-11-04)

Scope: updates and ranks the earlier note `research_notes/AI reel editor competitor landscape/video_understanding_models.md` (call it "Prior note"; it already covers TwelveLabs Marengo/Pegasus limits and pricing, Gemini video token math, Gemini Embedding 2, CameraBench, TransNetV2/AutoShot, cost tables). I do not repeat those details; I add new evidence from this pass and make picks. Access date for all URLs: 2026-11-04. Many pages were summarised by the fetch tool, and many leaderboards are third-party aggregators with inconsistent dates and self-reported vendor numbers; each is flagged. Model names in this period are unstable and differ across aggregators (e.g. one board lists "Claude Opus 4.8", Anthropic's own price list shows Opus 5.5), so verify IDs on the OpenRouter model page before wiring them in. Nothing below was run by me; no hands-on test on reels was done.

## 1. Which multimodal models are strongest at native video understanding with timestamp precision?

### Takeaway
Gemini (3 Pro now, Gemini 4 Argon / 3.8 Flash per the Prior note) is the top general video model and the only major closed API that takes video natively; but all VLMs, Gemini included, are poor at frame-accurate timestamps. Qwen3-VL (Apache-2.0) is the best open-weight base, with a temporal-grounding fine-tune (TimeLens). Claude and OpenAI show no native video input in their docs, so they only work as frame-based reasoners. Video-MME is near-saturated (about 87-90%) so it no longer separates the top models; Video-MME-v2 and temporal-grounding benchmarks are more informative.

### Cited Findings
- Video-MME snapshots are inconsistent across aggregators. A Sept 2026 aggregator snapshot lists Seed 2.1 Pro 89.2%, Seed 2.1 Turbo 89%, Qwen3.7-Plus 88%, MiMo-V2.5 87.7%, Kimi K2.5 87.4%, Gemini 2.5 Pro 84.8%. BenchLM (March 2026): Gemini 3 Pro 88.4% with subtitles / 87.7% without, Qwen3.6 Plus 87.8%, Qwen3.5 397B 87.5%, GPT-5.2 85.8% (no subs). LLM Stats: Kimi K2.5 0.874 (no subs), Qwen3.6-27B 0.877 (with subs). Seed 2.0 Pro 89.50% is vendor self-reported. — [anotherwrapper](https://anotherwrapper.com/tools/llm-pricing/evals/video-mme), [BenchLM w/ sub](https://benchlm.ai/benchmarks/videoMmeWithSub), [BenchLM no sub](https://benchlm.ai/benchmarks/videoMmeNoSub), [LLM Stats](https://llm-stats.com/benchmarks/video-mme); aggregator search summary of these boards at [anotherwrapper](https://anotherwrapper.com/tools/llm-pricing/evals/videomme). Seed and Gemini 4 scores could not be matched to an official source.
- Video-MME-v2 (arXiv 2604.05015, April 2026) names Gemini-3-Pro as the best model with a "substantial gap" to human experts; errors in visual aggregation and temporal modelling propagate upward; thinking-based reasoning leans on text cues, improving with subtitles but sometimes degrading on purely visual input. — [arXiv 2604.05015](https://arxiv.org/abs/2604.05015)
- No official Video-MME or timestamp score for Gemini 4 Argon was found; a third-party blog confirms Argon accepts text, image, video, audio, PDF and offers an "agentic" video mode (static is default) and advises verifying timestamps against visible evidence. — [Atlas Cloud](https://www.atlascloud.ai/blog/tips/gemini-4-argon-multimodal-capabilities) (low authority)
- Temporal grounding (Charades-STA mIoU), numbers differ by paper and setting: InternVideo3 paper reports Gemini 2.5 Pro 52.8, Gemini 2.5 Flash 48.6, Qwen3-VL-8B 48.3, InternVideo3 50.4. TimeLens paper finds 20.6% of Charades-STA samples violate query uniqueness and 34.9% have annotation accuracy issues; its table gives Gemini-2.5-Flash 31.1 on original Charades-STA vs 48.6 on its refined Charades-TimeLens; TimeLens-8B (a Qwen3-VL-8B fine-tune) beats GPT-5 and Gemini-2.5-Flash on TimeLens-Bench. — [InternVideo3 arXiv 2606.12195](https://arxiv.org/pdf/2606.12195), [TimeLens arXiv 2512.14698](https://arxiv.org/pdf/2512.14698); the search summary carrying these numbers is secondary and the TimeLens PDF table could not be parsed by me.
- Qwen3-VL tech report compares Gemini 2.5 Pro, GPT-5, Claude Opus 4.1 on Charades-STA (4 fps for Charades, 2 fps elsewhere; 512 frames cap for Gemini 2.5 Pro; authors admit comparison is not perfectly fair). Textual timestamps + interleaved MRoPE; flagship 235B-A22B near 100% needle-in-haystack at 30 min, 99.5% at 2 h; 8B competitive with Qwen2.5-VL 72B. Apache-2.0 weights. — [Qwen3-VL report arXiv 2511.21631](https://arxiv.org/pdf/2511.21631), [unite.ai summary](https://www.unite.ai/alibaba-releases-qwen3-vl-technical-report-detailing-two-hour-video-analysis/)
- Qwen successor line: one wiki says Qwen moved to natively multimodal Qwen3.5 (Feb 2026), so no separate "Qwen3.7-VL" is expected (unverified). Qwen3.7-Plus is on OpenRouter at $0.32/$1.28 per 1M with 1M context and JSON-schema structured output; whether OpenRouter passes video through is contested (OpenRouter page says text+image; another page says text+image+video). — [aiwiki Qwen3-VL](https://www.aiwiki.ai/wiki/qwen3_vl/raw), [OpenRouter Qwen3.7 Plus](https://openrouter.ai/models/qwen/qwen3.7-plus-20260602), [shopot](https://api3.shopot.ai/qwen/qwen3.7-plus)
- InternVL3 is evaluated on Video-MME, MVBench, MMBench-Video, MLVU, LongVideoBench, CG-Bench; a 2026 benchmark paper lists InternVL-3.5-4B trailing similar-size Qwen3-VL. A May 2026 practitioner guide calls Qwen the strongest all-round open family. — [InternVL3 arXiv 2504.10479](https://arxiv.org/pdf/2504.10479), [Video-MME-v2](https://arxiv.org/pdf/2604.05015), [Fora Soft guide](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/llava-qwen-vl-llava-next-open-frontier-vlms) (vendor blog)
- OpenAI API vision doc covers images only (PNG/JPEG/WEBP/non-animated GIF, up to 1,500 images and 512 MB per request); models listed include gpt-6-astra, gpt-5.5. No video input documented. Claude vision is images only (Prior note, [Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)). — [OpenAI images guide](https://developers.openai.com/api/docs/guides/images-vision)
- GLM 5.3 FlashX Legal on OpenRouter lists text+image+video input at $0.37/$1.25 per 1M with 1.05M context; the only OpenRouter row on that page explicitly listing video. — [OpenRouter models](https://openrouter.ai/models?fmt=table&order=top-weekly)
- Gemini timestamp problems (forum reports, 2.0/2.5) and 1 fps default: see Prior note section 2 and 5.

### Inferences
- Ranking for native video semantics (shot description, text style, mood): 1) Gemini top tier (Argon, or 3.8 Flash for cost) given Gemini-3-Pro leads Video-MME-v2 and every open model is behind it on aggregate; 2) Qwen3.x family (Plus via API or Qwen3-VL open weights) within a few points on Video-MME; 3) TwelveLabs Pegasus 1.5/1.6, whose value is the `segment_definitions` structured API rather than proven benchmark lead (no independent benchmark found); 4) Claude/GPT on frames only.
- Because Video-MME is saturated and the Charades-STA labels are noisy (TimeLens), do not choose by those headline numbers; run a 10-reel hand-labelled bake-off on your own fields.
- Open-weight fallback: Qwen3-VL-8B/32B, optionally TimeLens-8B for timestamp work; a single 24 GB GPU can host the 8B.

### Gaps
- No official Gemini 4 / 3.8 Flash video benchmark scores; no GPT-6 video support confirmation; no Molmo, LLaVA-Video, VideoLLaMA3 current numbers found (older than the 2026 field and probably superseded; treat as possibly outdated).
- The TimeLens table was not parseable; mIoU values above come from search summaries.
- Seed 2.x (ByteDance) appears at the top of Video-MME boards but API availability via OpenRouter was not checked.

## 2. Frame-accurate tasks: specialist models or a general VLM?

### Takeaway
Use specialists for anything needing frame accuracy. On a purpose-built transition benchmark (TransVLM), Gemini 2.5/3 Pro beat TransNetV2/AutoShot only on synthetic gradual transitions but lost on real public videos, and all of them lose to a VLM fine-tuned for transitions (TransVLM). Practical pattern: detector for cut candidates, VLM for transition type and semantics, OCR engine for text boxes and timing, geometric tracking for camera motion.

### Cited Findings
- TransVLM benchmark (5,215 videos, about 100.3 h, 45,239 transitions; cut <0.1 s, normal <=1 s, long >1 s). Frame F1 / absolute boundary error in seconds, public split: TransNetV2 0.528 / 1.87; AutoShot 0.532 / 1.78; PySceneDetect Adaptive 0.457 / 1.93; Gemini 2.5 Pro 0.401 / 3.62; Gemini 3 Pro 0.393 / 2.18; Qwen3-VL-32B Instruct 0.241 / 3.96; Qwen3-VL-8B Instruct 0.184 / 34.39; TransVLM 0.568 / 1.58. Synthetic split F1: Gemini 2.5 Pro 0.686, Gemini 3 Pro 0.568, AutoShot 0.102, TransNetV2 0.063, TransVLM 0.938. Real-time factor: AutoShot 0.03, TransNetV2 0.07, Gemini 2.5 Pro 0.81, Gemini 3 Pro 1.32 (units unstated). — [TransVLM project page](https://chence17.github.io/TransVLM/) (authors' own benchmark, not independent)
- TransNetV2 F1: 77.9 ClipShots, 96.2 BBC, 93.9 RAI; AutoShot F1 78.7 ClipShots, +4.2 over TransNetV2 on its short-video SHOT set; the Cosmos paper found TransNetV2 holds up better than AutoShot on harder shot changes. — [TransNetV2 GitHub](https://github.com/soCzech/TransNetV2), [AutoShot arXiv 2304.06116](https://arxiv.org/pdf/2304.06116), [Cosmos arXiv 2501.03575](https://arxiv.org/pdf/2501.03575), [ClipShots leaderboard](https://hyper.ai/en/sota/tasks/camera-shot-boundary-detection/benchmark/camera-shot-boundary-detection-on-clipshots)
- Camera motion: CameraBench shows VLMs weak on geometric motion, SfM weak on semantic motion; Qwen2.5-VL SFT on ~1,400 videos matched MegaSAM AP. — Prior note section 4, [CameraBench](https://linzhiqiu.github.io/papers/camerabench/)
- OCR: PP-OCRv5 (about 5M-param specialist; distills from GOT-OCR2.0) reports 0.067 overall edit distance on OmniDocBench (lower is better) vs 0.077 for GOT-OCR per a secondary write-up; PaddleOCR 3.0 report's own comparisons use a self-built set. These are document benchmarks, not video. — [PaddleOCR 3.0 report](https://arxiv.org/pdf/2507.05595), [papernotes PP-OCRv5](https://en.papernotes.org/CVPR2026/multimodal_vlm/pp-ocrv5_a_specialized_5m-parameter_model_rivaling_billion-parameter_vision-lang/)
- Video OCR practice: per-frame engines (Tesseract, Florence-2) treat frames independently, so a tracking/aggregation stage is needed to merge per-frame (polygon, text, confidence) into one timed string; a vendor estimates PaddleOCR detection plus recognition at about 30-60 ms/frame on a T4 for 1080p with ten text regions; a scrolling-text extractor defaults to 5 fps. — [Fora Soft PaddleOCR video](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/paddleocr-text-detection-video), [Mixpeek scrolling text](https://www.mixpeek.com/docs/processing/extractors/scrolling-text) (both vendor content)
- Gemini 1.5-era write-up: slow videos get flawless text recognition but quickly flashed captions are missed and text timing can be off by about a second. Possibly outdated (1.5 era, pre-2025 flagging threshold applies to model generation). — [Sieve video OCR guide](https://sievedata.com/blog/video-ocr-guide) via search summary
- No source found for caption font-family recognition or for transition-type classification benchmarks besides TransVLM.

### Inferences
- Shot boundaries: TransNetV2 or AutoShot as the primary (fast, F1 about 0.53 on the hard public split but still the best classical), PySceneDetect Adaptive as fallback. Because VLM boundary error is 2-4 s on the public split, never trust Gemini timestamps; give Gemini the cut list. For gradual transitions (dissolves, glitch, whip) a VLM looking at the surrounding 1-2 s clip is better than the detectors on synthetic data (0.57-0.69 vs 0.06-0.10) but synthetic is not reels; test on yours. TransVLM is a research artifact; I did not verify weights or license.
- On-screen text: PaddleOCR (PP-OCRv5) at about 5-10 fps for boxes, timing and position, with a tracker to merge frames; VLM (Gemini Flash) only for style words (font category, weight, animation type, colour) per text track crop. Font identification to an exact font file is unsolved in what I found; plan a "nearest of N licensed fonts" classifier or VLM label.
- Camera motion: OpenCV homography/optical flow for magnitude, direction and zoom, VLM label as tie-break, as in the Prior note; fine-tuning Qwen3-VL on CameraBench is the upgrade path.

### Gaps
- No head-to-head of PaddleOCR vs Florence-2 vs GOT-OCR vs Gemini on short-form social video with stylised captions; no caption font or animation recognition benchmark found.
- TransVLM numbers are self-reported and only the page was read, not the paper.
- AutoShot vs TransNetV2 on Reel-style content (speed ramps, glitch, whip pans) untested.

## 3. Best LLMs for the planning/agent layer via OpenRouter (structured JSON, tool calls, reliability)

### Takeaway
For reliability, pick Claude Sonnet 5.5 as the default planner/chat agent ($2/$10 per 1M, 1M context) and Claude Haiku 5.5 ($0.10/$0.50) or Gemini Flash or DeepSeek V4.1 Flash for cheap bulk steps; reserve Opus 5.5 ($4/$20) for hard replans. Public tool-calling leaderboards disagree on the winner, and many use vendor IDs that differ, so run your own 30-case eval on your JSON schema and tool set.

### Cited Findings
- Anthropic first-party price list (per 1M, in/out): Fable 5.1 $10/$50; Opus 5.5 $4/$20; Opus 5 / 4.8 / 4.7 / 4.6 / 4.5 $5/$25; Sonnet 5.5 $2/$10; Sonnet 5 $2/$10; Sonnet 4.6 $3/$15; Haiku 5.5 $0.10/$0.50 (prompts up to 100K tokens; $0.50/$2.50 above 100K); Haiku 4.5 $1/$5. Batch is 50% off, stackable with caching; Sonnet 5.5 cache read $0.10/M. Claude 4.6+ models (not Haiku 5.5) get the full 1M context. — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- LLM Stats tool-calling leaderboard (updated 2026-11-04; 54 benchmarks incl. BFCL; 230 models reviewed): GPT-6 Astra 36.0, Claude Sonnet 5.5 35.9, Gemini 4 Carbon 35.4 (top three; margins are tiny). It lists Opus 5.5 $4/$20, DeepSeek-V4.1-Flash $0.22/$0.66, DeepSeek-V4.1-Flash-1017 $0.30/$1.20, all 1.0M context. — [LLM Stats](https://llm-stats.com/leaderboards/best-ai-for-tool-calling)
- BenchLM tool-use top 20 (updated 2026-11-04; BFCL v4, MCP Atlas, Toolathlon, Tau Bench): Qwen3.7 Plus 72, Claude Opus 4.8 70.6, GLM-5.1 70.1 (top open-weight), Gemini 3.5 Flash 69.8, GPT-5.5 67.8, Kimi K2.5 54.2 (#20). The two boards use different model sets and disagree on rank 1. — [BenchLM tool use](https://benchlm.ai/best/tool-use)
- OpenRouter's tool-calling collection ranks by weekly token usage (adoption, not quality); one source warns that structured output, tool calling, caching, multimodal input and reasoning controls can differ per model/provider and should be checked on each model's supported-parameters page. — [OpenRouter tool-calling collection](https://openrouter.ai/collections/tool-calling-models)
- Qwen3.7 Plus on OpenRouter: $0.32/$1.28 per 1M, 1M context, JSON-schema `response_format` supported (per several sources). — [OpenRouter Qwen3.7 Plus](https://openrouter.ai/models/qwen/qwen3.7-plus-20260602), [LLM Reference](https://www.llmreference.com/model/qwen3.7-plus/openrouter)
- Gemini per-token prices (Prior note section 2): Argon $2/$10 until 2026-11-30 then $4/$20; 3.8 Flash $0.75/$3.75 until 2026-12-31 then $1.50/$7.50; 3.5 Flash-Lite $0.30/$2.50. OpenAI list: gpt-6-astra $10/$50, gpt-6.1-sol $2/$10, gpt-6.1-terra $1/$5 (Prior note, [OpenAI models](https://developers.openai.com/api/docs/models)).
- Kimi K2.5 and GLM-5.1: scores above; OpenRouter pricing and structured-output flags for DeepSeek V4.1, Kimi K2.5, GLM-5.1 were not retrievable in this pass.

### Inferences
- Candidates by role: (a) blueprint-to-clip matching planner, edit-plan JSON, verifier-revision loop: Sonnet 5.5; (b) chat revisions that call tools (trim, retime, replace text): Sonnet 5.5, with Haiku 5.5 as a cheaper first attempt that escalates on schema failure; (c) cheap cost-sensitive classification/captioning of clips: Gemini 3.5 Flash-Lite or Haiku 5.5; (d) budget alternative with open weights: GLM-5.1 or Qwen3.7 Plus (highest on one tool-use board, priced about 1/6 of Sonnet's input).
- Prices on OpenRouter normally track provider list prices but I did not confirm that for these models; budget a 5% platform fee on credits as a rule of thumb (unsourced; verify).
- Strict JSON: use `response_format: json_schema` with `strict`, and a validate-and-retry loop; check each model's supported-parameters list because tool calling and structured outputs are not universal across providers.

### Gaps
- No primary evidence on schema-adherence rates per model; leaderboards aggregate coding and agentic suites and do not isolate JSON validity.
- DeepSeek V4.1 / Kimi / GLM OpenRouter prices and provider-level structured-output support unverified. Gemini 4 Carbon vs Argon naming not clarified.
- No hands-on reliability reports (GitHub issues, r/LocalLLaMA) were surfaced by search; I could not cite practitioner opinion for late 2026.

## 4. Embedding models for matching user clips to blueprint slots

### Takeaway
Hosted options with video input: Marengo 3.x (TwelveLabs, 512-d), Gemini Embedding 2 (<=120 s clips, 32 frames, no audio), Voyage multimodal-3.5. Open options (SigLIP 2, InternVideo2, VideoPrism) are image-text or research video encoders; I found no head-to-head benchmark among them on short-form clip retrieval. The slot-match task is mostly "does this clip depict the described subject/action/shot size", so use embeddings for recall and a VLM re-rank for precision.

### Cited Findings
- Marengo 3.5 (Aug 2026) embeddings for video/audio/image/text/document, 512-d default (128/256/512 configurable), composed queries; use Marengo 3.0 for platform search; reported video rate $0.26/1M tokens ($0.042/min earlier) and Pro plan $99. — Prior note section 1, [TwelveLabs release notes](https://docs.twelvelabs.io/v1.3/docs/get-started/release-notes), [pricing](https://www.twelvelabs.io/pricing)
- Gemini Embedding 2: video $12/1M tokens (~$0.00079/frame), 120 s limit, 32 frames max, 128-3072 dims, audio in video ignored. — Prior note section 2, [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- Voyage multimodal-3.5 supports video (32K context, 1024-d default); release date conflicts (Jan vs Jul 2026). — Prior note section 3, [MongoDB/Voyage](https://www.mongodb.com/products/updates/now-available-voyage-multimodal-3-5/)
- InternVideo2-6B MSR-VTT text-to-video R@1: 55.9 zero-shot and 62.8 under the non-zero-shot setting, per leaderboard listings; VideoPrism (Google, arXiv 2402.13217) reports zero-shot video-text retrieval but I could not confirm an MSR-VTT figure; SigLIP 2 is evaluated on image-text tasks only. — [Wizwand MSR-VTT](https://www.wizwand.com/sota/video-to-text-retrieval-on-msr-vtt-1k-test), [VideoPrism](https://arxiv.org/pdf/2402.13217), [InternVideo2](https://PapersWithCode.com/paper/internvideo2-scaling-video-foundation-models). InternVideo2/VideoPrism are 2024 and possibly outdated. Note an InternVideo3 paper exists (arXiv 2606.12195) but I did not read its retrieval results.
- Cohere Embed v4 and Jina v4 are text+image only (Prior note). A new Cohere Embed 5 Fast/Pro ($0.08/$0.12 per 1M) appears on OpenRouter, but its modalities were not checked. — [OpenRouter models](https://openrouter.ai/models?fmt=table&order=top-weekly)

### Inferences
- Pick: Marengo 3.5 if you already pay for the TwelveLabs plan (audio + visual fused, one SDK, managed search), else Gemini Embedding 2 for the cheapest self-managed vector index (about $0.76-2.84 per hour of footage per the Prior note), chunked by shot. SigLIP 2 over 1-3 keyframes per shot is the free local fallback and is good at object/scene matching but blind to motion.
- Accuracy claims between these are unproven for your task; build a small (50 query, 200 clip) retrieval set from real user footage before committing.

### Gaps
- No independent benchmark comparing Marengo 3.5, Gemini Embedding 2, Voyage multimodal-3.5, SigLIP 2, InternVideo2, VideoPrism on the same retrieval set; SigLIP 2 / VideoPrism video-retrieval numbers not found.
- Marengo 3.5 clip-length parameters unconfirmed (Prior note gap).

## 5. Recommended combination and rough per-reel cost

### Takeaway
Hybrid: deterministic specialists for time and geometry, one Gemini Flash call for semantics, Sonnet 5.5 for planning and chat, Gemini Embedding 2 or Marengo for matching. Analysis per reference reel costs roughly 2-6 cents of API spend; planning and revisions add a few cents; the whole flow stays under about 20 cents per reel plus rendering compute.

### Cited Findings
(The prices used are cited above; Gemini token math is from the Prior note: about 300 tokens/s default, 6-9K input tokens for a 20-30 s reel; Sonnet 5.5 $2/$10; Haiku 5.5 $0.10/$0.50; Gemini Embedding 2 $0.00079/frame.) — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [Gemini video docs](https://ai.google.dev/gemini-api/docs/video-understanding), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)

### Inferences (my picks and arithmetic; assumptions stated)
| Step | Pick | Fallback / note | Approx cost |
|---|---|---|---|
| Download | yt-dlp | none | $0 |
| Shot boundaries, frame-exact | TransNetV2 or AutoShot, snapped with ffprobe; PySceneDetect Adaptive fallback | VLM only for dissolve/glitch/whip classification on the +-1 s window | CPU/GPU seconds |
| Per-shot semantics (shot size, angle, subject, action, mood, transition type, colour grade words) | Gemini 3.8 Flash with JSON schema, cut list supplied as ground truth, `fps` 2-4 | Argon for hard clips; Pegasus 1.6 `segment_definitions`; Qwen3-VL-32B self-host | about $0.02-0.04 per 20-30 s reel on Flash; about $0.05-0.10 on Argon after the Dec 1 price rise (Prior note math) |
| On-screen text, position, timing | PP-OCRv5 at 5-10 fps + tracker merge; style words from Gemini on crops | VLM-only OCR for slow captions | a few CPU/GPU seconds |
| Camera motion | OpenCV homography/flow per shot + VLM tie-break | fine-tuned Qwen3-VL (CameraBench) | local |
| Music beats, pacing | librosa/madmom, deterministic from the cut list | not researched | local |
| Library embeddings | Gemini Embedding 2 per shot (<=32 s) or Marengo 3.5 | SigLIP 2 keyframes local | about $0.76-2.84 per hour of footage |
| Slot matching planner, edit plan JSON, "what to film" | Claude Sonnet 5.5 (json_schema + tools) | Haiku 5.5 first pass; GLM-5.1 / Qwen3.7 Plus budget; Opus 5.5 for tough replans | 10K in + 3K out per call = $0.02 + $0.03 = about $0.05 on Sonnet; about $0.002 on Haiku 5.5 |
| Verify render vs blueprint | Same analysis pipeline on the render (specialists + Gemini Flash), diff against blueprint | | about $0.02-0.04 |
| Chat revision | Sonnet 5.5 with caching (cache read $0.10/M) | Haiku first | about $0.01-0.03 per turn |

Rough totals per reel: analysis $0.03-0.06, planning/matching $0.05, verify $0.03, 2-3 chat turns $0.05, so about $0.15-0.20 with Sonnet and about $0.08-0.12 if Haiku/Flash-Lite handle most steps (arithmetic, not measured). Biggest unknown is thinking-token spend, which bills as output.

### Gaps
- No measured latency or accuracy for the hybrid; no reel-specific benchmark exists in what I found. Recommend a 10-reel hand-labelled eval comparing Gemini Flash vs Argon vs Pegasus 1.6 vs Qwen3-VL on each blueprint field before locking the choice.
- OpenRouter-specific pricing/limits for video-capable models not verified; Gemini video should likely go direct to Google or via OpenRouter only after checking that video parts are supported there.
