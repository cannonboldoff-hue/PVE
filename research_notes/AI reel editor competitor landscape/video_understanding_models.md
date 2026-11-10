# Video-understanding models and APIs for a "reference Reel analyzer" and "media library indexer" (state as of 2026-11-02)

Access date for all URLs: 2026-11-02. Prices and model names in this space change monthly. Several vendor pages (Gemini, TwelveLabs) show scheduled price changes in Dec 2026 / Jan 2027, noted below. Facts under "Cited Findings" come from the cited page; anything I derived is under "Inferences". Many official pages were only partly retrievable (the fetch tool summarizes pages), so "Gaps" lists what I could not verify. Several search-result sources are low-authority aggregators and are flagged as such.

## 1. TwelveLabs (Marengo, Pegasus): versions, limits, pricing, capabilities

### Takeaway
Current line is Marengo 3.5 (embeddings only) plus Marengo 3.0 (still needed for search), and Pegasus 1.6 (Oct 2026) for video-language/structured output with timestamped segments. Billing moved from pay-as-you-go to subscription plans on 2026-10-15 (existing customers migrate from 2027-01-04), so older per-hour rates are now "overage/legacy" figures. Nothing found documents camera-motion quality; treat it as unproven for fine camera moves.

### Cited Findings
- Marengo 3.5 (released Aug 31, 2026): embeddings for video, audio, images, text and documents, 512-dim by default, composed (cross-modal) queries; "Marengo 3.5 creates embeddings only. For search, use Marengo 3.0." Dimensions configurable to 128/256/512 since Sept 30. — [Release notes](https://docs.twelvelabs.io/v1.3/docs/get-started/release-notes)
- Marengo 3.0 creates embeddings from video/audio/images/text and supports platform search; Marengo 2.7 sunset March 30, 2026. — [Marengo docs](https://docs.twelvelabs.io/v1.3/docs/concepts/models/marengo), [Release notes](https://docs.twelvelabs.io/v1.3/docs/get-started/release-notes)
- Marengo 3.5 fuses time-aligned metadata into the segments it overlaps (segment-level embeddings); per-modality token-based rate limits. — [Release notes](https://docs.twelvelabs.io/v1.3/docs/get-started/release-notes)
- Marengo 3.5 page: "uncertainty signal on each match"; "rich embeddings" combining several input types in one query via a 16K-token synchronous endpoint. — [Models overview](https://www.twelvelabs.io/product/models-overview)
- Pegasus 1.6 (Oct 6, 2026): egocentric video understanding, 1-20 images per request, improved entity recognition, timestamped in-segment events. Pegasus 1.5 (Apr-May 2026): video segmentation, structured prompts with up to 4 reference images, video clipping, 261,120-token context, 98,304-token max response. Pegasus 1.2 removed Aug 18. — [Release notes](https://docs.twelvelabs.io/v1.3/docs/get-started/release-notes)
- Structured output: `response_format` = `segment_definitions` with user-defined segment types (id, description, typed fields with optional enum values), `analysis_mode: time_based_metadata`, `min_segment_duration`; results grouped by segment id with `start_time`, `end_time` (seconds) and `metadata`; segments can be made contiguous. Timestamp format options `seconds`, `hh:mm:ss`, `hh:mm:ss.fff`. — [Pegasus docs](https://docs.twelvelabs.io/v1.3/docs/concepts/models/pegasus), [Release notes](https://docs.twelvelabs.io/v1.3/docs/get-started/release-notes)
- Entity search launched in 2025; 2026 added `entity_collection_id` and list-entities-by-asset endpoint. — [Release notes](https://docs.twelvelabs.io/v1.3/docs/get-started/release-notes)
- Limits: multipart upload up to 10 GB video/audio (direct upload 4 GB), images 32 MB; async analysis window must be within 2 hours (up to 4 h tasks when analyzing a portion), sync analysis 1 hour, min analyzed duration 1 s; batch analysis up to 1,000 requests per call; uploads are validated asynchronously (poll until `ready`). — [Release notes](https://docs.twelvelabs.io/v1.3/docs/get-started/release-notes)
- Plans (official page, monthly): Free $0 / 3 GB; Plus $29 / 50 GB (no overage); Pro $99 / 200 GB (optional overage); Enterprise custom. Storage billed on original file size. Analyze, Segment, Embed, Marengo Search count against a "Workload" allowance; official page does not list per-unit rates. Marengo 3.0 named for indexes. — [TwelveLabs pricing](https://www.twelvelabs.io/pricing)
- Per a third-party tracker (usagepricing.com, secondary source): Pro overage storage $0.065/GB/mo, Analyze $1.75/hour, Embed from $0.065/1M tokens, Search $4/1,000 queries; replaced Developer rates were indexing $2.50/hour, embedding infra $0.09/hour/month, Analyze $1.75/hour + $7.50/1M output tokens; new plans take effect 2026-10-15, existing customers migrate from 2027-01-04. — [usagepricing.com Oct 15 entry](https://www.usagepricing.com/blueprint/activity/twelve-labs-2026-10-15-subscription-plans-replace-payg)
- Same tracker for Marengo 3.5 Embed per-token rates (Sept 11, 2026 snapshot): video $0.260/1M tokens, audio $0.065, image $0.080, text $0.200, document $0.162; video previously $0.042/min. — [usagepricing.com Sept 11 entry](https://www.usagepricing.com/blueprint/activity/twelve-labs-2026-09-11-embed-api-token-pricing); $0.042/min also shown on [TwelveLabs pricing calculator](https://www.twelvelabs.io/pricing-calculator-2)
- Toolradar (aggregator, checked Oct 19, 2026) lists Pegasus 1.6: input video $1.75/h, image $3/1M tokens, output $7.50/1M tokens; search $4/1,000 queries; Free tier 10 hours indexing, 100 videos/index, 90-day index access; Pegasus 1.6 markets action segmentation and dense captioning of hand-object interactions, clip quality scoring and PII/minor flagging. — [Toolradar](https://toolradar.com/tools/pegasus-1-6-by-twelvelabs)
- Pegasus 1.5 positioned as "from clip-based QA to time-based metadata"; Pegasus integrates visual, audio and speech. — [Models overview](https://www.twelvelabs.io/product/models-overview)
- Also available on Amazon Bedrock (Marengo Embed 3.0, Pegasus 1.2 per AWS docs). — [AWS Bedrock TwelveLabs params](https://docs.aws.amazon.com/ja_jp/bedrock/latest/userguide/model-parameters-twelvelabs.md)

### Inferences
- For the reel analyzer, Pegasus 1.5/1.6 `segment_definitions` is the closest off-the-shelf "shot table" API (you define fields such as shot_size, camera_movement, subject_action, direction, transition). I found no evidence of how accurate those fields are for camera movement; Pegasus docs only show egocentric/robotics-style examples.
- Cost for one 15-30 s reel via Pegasus is cents (see section 6). For library indexing the cost is dominated by Marengo embedding/storage, and the Oct 2026 plan change makes it a flat monthly fee plus workload cap rather than per-hour.
- Inverse-derived: if $0.042/min equals $0.26/1M tokens, a video minute is about 160k tokens; this is my arithmetic, not documented.

### Gaps
- Official video resolution/min-duration/format requirements for Marengo 3.5 / Pegasus 1.6 not retrievable (doc pages fetched did not list them).
- Official per-unit workload rates and Marengo 3.5 token rates not on the official pricing page I could read; only third-party trackers.
- No latency figures, no independent benchmarks vs Gemini, no evidence on camera-motion accuracy. TwelveLabs-published benchmarks not found in this pass.
- Whether Marengo 3.5 emits fixed-length clip embeddings with configurable segment length (as Marengo 2.7 did) was not confirmed; release notes say it fuses time-aligned metadata into segments but give no segment-length parameters.

## 2. Google Gemini (video understanding, embeddings)

### Takeaway
Gemini is the strongest single-API option for analyzing a short reel: native video + audio input at ~300 tokens/s, structured JSON, cheap Flash tier. Current lineup: Gemini 4 Argon (flagship), 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite, plus gemini-embedding-2 for multimodal embeddings (video up to 120 s). Absolute timestamps and shot boundaries are not reliable on their own, so cross-check them with a shot detector.

### Cited Findings
- Models: gemini-4-argon (flagship, 1M context), gemini-3.8-flash, gemini-3.6-flash, gemini-3.5-flash-lite, gemini-3.1-flash-lite stable; gemini-3.1-pro-preview and gemini-3-flash-preview in preview; gemini-embedding-2 multimodal. — [Gemini models](https://ai.google.dev/gemini-api/docs/models)
- Pricing (Standard, per 1M tokens, in/out): Argon $2/$10 until Nov 30, 2026 then $4/$20; 3.8 Flash $0.75/$3.75 until Dec 31, 2026 then $1.50/$7.50; 3.6 Flash same as 3.8 Flash; 3.5 Flash-Lite $0.30/$2.50; 3.1 Flash-Lite $0.25/$1.50; 2.5 Flash $0.30/$2.50; 2.5 Pro $1.25/$10. Batch is about 50% off; context caching available. — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Video input: default sampling 1 fps; 66 tokens/frame at low media resolution, 258 otherwise; audio 32 tokens/s; about 100 tokens/s (low) or about 300 tokens/s (default). 1M-context models handle up to ~3 h at low resolution or ~1 h at default. Custom `fps` and `start_offset`/`end_offset` clipping available (static mode). Timestamps in prompts use MM:SS. File API up to 20 GB paid; inline under 20 MB request; up to 10 videos per request on 2.5+; YouTube URLs supported. — [Video understanding docs](https://ai.google.dev/gemini-api/docs/video-understanding)
- "Agentic mode" (Gemini 4 Argon, 3.8 Flash, 3.6 Flash, 3.5 Flash Lite): model navigates the timeline on demand, up to 88% fewer tokens on long-form content but may add latency on short clips. — [Video understanding docs](https://ai.google.dev/gemini-api/docs/video-understanding)
- Gemini Embedding 2 pricing: video $12.00/1M tokens (~$0.00079/frame), image $0.45/1M (~$0.00012/image), audio $6.50/1M (~$0.00016/s), text $0.20/1M; batch half price; free tier for non-batch. — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Gemini Embedding 2 limits: video up to 120 s, MP4/MOV; max 32 frames processed ("short videos (<=32s) are sampled at 1 fps, while longer videos are uniformly sampled to 32 frames"); audio track in video files is not processed; output 128-3072 dims (default 3072); 8,192-token cap across modalities, silently truncated; for longer videos "chunk the video into overlapping segments and embed those chunks individually". Query format `task: search result | query: {content}`. — [Embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- Timestamp reliability: developer forum reports of timestamps beyond video length, invented timecodes on longer Gemini 2.0/2.5 videos, burned-in timecode overlays not helping on 2.5 Pro. — [Google AI forum 2.5 Pro](https://discuss.ai.google.dev/t/gemini-2-5-pro-severe-timestamp-timecode-jumping-issues-in-video-transcription-need-workarounds/87242), [forum 2.0 Flash](https://discuss.ai.google.dev/t/gemini-2-0-flash-video-undestanding-issues/66037)
- A controlled study ("The Low Frequency Trap", arXiv 2608.06361, not independently checked by me) reports Gemini omitting intermediate events and giving timestamps outside a 1.0 s tolerance under high temporal load. — [arXiv 2608.06361](https://arxiv.org/pdf/2608.06361)
- Vertex AI `multimodalembedding` returns 1408-dim video embeddings per segment (dimension parameter applies to text/image only); video segment interval configurable. — [Vertex multimodal embeddings API reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/models/multimodal-embeddings-api) (via search snippet; page body not fully read)
- Vertex video embedding tiers are interval-based (Essential >=15 s, Standard 8-14 s, Plus 4-7 s) per a Google developer forum post; third-party guide cites $0.0005-$0.002 per embedding. Unofficial. — [Google developer forum](https://discuss.google.dev/t/mastering-multimodal-embeddings-mathematics-cross-modal-physics-audio-visual-math-and-mrag-architecture-in-google-vertex-ai/378754), [Mixpeek guide](https://mixpeek.com/guides/video-embedding-models)

### Inferences
- Reel analysis cost on Gemini 3.8 Flash is about 2 cents (section 6). Thinking tokens, if enabled, bill as output; I did not verify the billing rule on the pages read.
- Structured JSON output with a schema is a standard Gemini feature, but I did not re-verify it on the pages read for the 2026 models.
- Gemini Embedding 2 is a viable single-vendor library index: embed 10-30 s clips (1 fps up to 32 s), but it ignores audio in video, so pair with a transcript/music embedding.
- The 32-frame cap means ~1 fps resolution only for clips up to 32 s; index by chunking into ~10-30 s windows.

### Gaps
- No official Google accuracy number for timestamp or shot boundary detection; evidence is forum/anecdote plus one unverified preprint.
- Gemini 4 Argon / 3.8 Flash-specific video benchmark scores and camera-motion results not found.
- Official Vertex pricing and current status of multimodalembedding@001 vs Gemini Embedding 2 not confirmed.
- Google Video Intelligence API prices not retrievable (page truncated); recollection only: shot change ~$0.05/min, label ~$0.10/min (Azure aggregator and Google pricing snippet say shot detection $0.05/min, first 1,000 min/month free — [Google Video Intelligence pricing](https://cloud.google.com/video-intelligence/pricing) via search snippet).

## 3. Other models and APIs (OpenAI, Claude, Qwen, Nova, NVIDIA, embeddings, Azure/Google legacy)

### Takeaway
Only Gemini and TwelveLabs offer first-party video-in/timestamped-out APIs that I could verify. Claude takes images only (send frames). OpenAI's 2026 video support is unconfirmed. Qwen3-VL (Apache-2.0) and NVIDIA Cosmos-Reason2 are the open candidates for self-hosting; Nova 2 Lite is a cheap Bedrock video option without structured-output support. For embeddings, Voyage multimodal-3.5 and Gemini Embedding 2 handle video; Cohere Embed v4 and Jina v4 are documented for text/image only.

### Cited Findings
- Claude: vision doc covers images only (no video mentioned in the page); up to 600 images per request on the first-party API (128 MB request limit), max 8000x8000 px; a 1920x1080 frame costs ~1,560 tokens (resized to 1456x819) or ~2,691 at the higher-resolution setting. Supported models include claude-opus-5-5, claude-sonnet-5-5, claude-haiku-5-5. — [Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- OpenAI: current API model list shows gpt-6-astra ($10/$50 per 1M in/out), gpt-6.1-sol ($2/$10), gpt-6.1-terra ($1/$5), gpt-6-luna ($0.10/$0.50); page states text and image input and does not mention video. — [OpenAI models](https://developers.openai.com/api/docs/models)
- A low-authority blog claims GPT-5.4/5.5 added native video input; unverified. — [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/gemini-gpt5-claude-opus-4-closed-frontier-2026)
- Amazon Nova 2 Lite (launched Dec 2, 2025): input text/image/video, 1M context, 64K output; Bedrock "Structured outputs" feature marked not supported; pricing deferred to the Bedrock pricing page. — [Nova 2 Lite model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-lite.md). Third-party trackers list ~$0.30/$2.50 per 1M in/out (global endpoint) — [AWS blog](https://aws.amazon.com/blogs/aws/introducing-amazon-nova-2-lite-a-fast-cost-effective-reasoning-model/), [cloudprice.net](https://cloudprice.net/models/amazon-nova-2-lite)
- Qwen3-VL: Apache-2.0; native 256K context expandable to 1M; "second-level indexing" of hours-long video; explicit textual timestamp alignment (moved away from T-RoPE absolute time encoding). — [HF Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct), [Qwen3-VL tech report](https://arxiv.org/pdf/2511.21631v1)
- TimeLens-8B (TencentARC) is a Qwen3-VL-8B fine-tune for video temporal grounding. — [Mixpeek model page](https://mixpeek.com/model/TencentARC/TimeLens-8B)
- NVIDIA Cosmos-Reason2 (8B, 32B): improved spatio-temporal understanding and timestamp precision; reads timestamps drawn on frames; third-party test returns event start/end in mm:ss.ff with ~1 s temporal patches. — [HF Cosmos-Reason2-32B](https://huggingface.co/nvidia/Cosmos-Reason2-32B), [NVIDIA model card](https://build.nvidia.com/nvidia/cosmos-reason2-8b/modelcard), [Classmethod test](https://dev.classmethod.jp/en/articles/dgx-spark-cosmos-reason2-structured-reasoning/)
- Video-MME snapshots (low reliability, mixed settings): BenchLM lists Gemini 3 Pro 88.4% with subtitles, 87.7% without; Qwen3.6 Plus 87.8%; another snapshot lists Qwen3 VL 30B A3B Instruct at 74.5%. — [BenchLM](https://benchlm.ai/benchmarks/videoMmeWithSub), [anotherwrapper](https://anotherwrapper.com/tools/llm-pricing/evals/video-mme)
- Voyage `voyage-multimodal-3.5` supports video embedding (32K context, 1024 default dims; 256/512/2048 options). Vendor blog says Jan 2026, an OpenRouter listing says Jul 27, 2026 (conflict). — [MongoDB/Voyage](https://www.mongodb.com/products/updates/now-available-voyage-multimodal-3-5/), [Voyage docs](https://www.mongodb.com/docs/voyageai/models/multimodal-embeddings/)
- Cohere Embed v4 (text/image/mixed), Jina Embeddings v4 (3.8B, text+image): no video support found. — [Cohere changelog](https://docs.cohere.com/v2/changelog/embed-multimodal-v4), [Jina v4](https://jina.ai/models/jina-embeddings-v4/)
- Azure AI Video Indexer: Basic preset includes object detection, visual labels, OCR, keyframe extraction, scene and shot detection; per-minute rates only via Azure calculator (an aggregator lists ~$0.05/$0.10/$0.15 per min Basic/Standard/Advanced, unverified). — [Azure Video Indexer pricing](https://azure.microsoft.com/en-us/pricing/details/video-indexer/), [ki-syndikat](https://www.ki-syndikat.de/tools/azure-video-indexer/)

### Inferences
- A frames-only path (Claude, GPT) loses audio/beat information and costs more per second than Gemini video input: e.g., a 20 s reel at 2 fps with 40 frames x ~1,560 tokens is ~62K tokens, vs ~6K tokens for Gemini default. Claude per-token prices were not retrieved, so a dollar figure is not given.
- Open VLMs (Qwen3-VL, Cosmos-Reason2) need a GPU and prompt engineering for timestamps; for a product they matter mainly as privacy/self-host or fine-tune bases (CameraBench shows fine-tuning helps camera motion).

### Gaps
- Not covered (no sources found in this pass): InternVL/InternVideo, Video-LLaVA, LLaVA-Video, VideoLLaMA, Molmo, NVIDIA VILA, Nomic, Amazon Nova Pro/2 Pro video limits, Nova Embeddings, Google Vertex Vision beyond embeddings.
- OpenAI video input support and limits, Claude per-token pricing, Nova official video limits (length/size) not verified.
- Claude does not document any native video input in the page read; assume frame-based.

## 4. Open-source building blocks (shot detection, camera motion, action, tracking, face)

### Takeaway
Use classical/neural detectors for deterministic facts (cuts, camera-motion vectors, tracks, face match) and reserve VLMs for semantics. TransNetV2 and AutoShot are the neural shot detectors; PySceneDetect is the lightweight default; CameraBench shows VLMs are weak on geometric camera moves while SfM/SLAM is weak on semantic ones.

### Cited Findings
- TransNetV2 (MIT): F1 77.9 ClipShots, 96.2 BBC Planet Earth, 93.9 RAI (author-reported). — [TransNetV2 GitHub](https://github.com/soCzech/TransNetV2)
- AutoShot (CVPRW 2023): built on a short-video dataset (SHOT: 853 videos, 11,606 shot annotations); authors report +4.2 F1 points over TransNetV2 on SHOT (0.841 vs 0.799, per secondary summary) and +1.1/+0.9/+1.2 on ClipShots/BBC/RAI; no independent replication found. — [CVPRW paper](https://openaccess.thecvf.com/content/CVPR2023W/NAS/html/Zhu_AutoShot_A_Short_Video_Dataset_and_State-of-the-Art_Shot_Boundary_Detection_CVPRW_2023_paper.html), [arXiv 2304.06116](https://arxiv.org/abs/2304.06116v1)
- PySceneDetect (BSD-3-Clause), latest v0.7.2 dated 2026-10-11: ContentDetector (default threshold 27), AdaptiveDetector (handles fast camera movement better), ThresholdDetector (fades). — [PySceneDetect GitHub](https://github.com/Breakthrough/PySceneDetect)
- CameraBench (NeurIPS 2025): ~3,000 expert-annotated videos, >150K binary labels, taxonomy built with cinematographers. MegaSAM and CUT3R beat COLMAP but SfM still fails on lead-tracking shots with unchanged subject framing/low texture and low-parallax roll shots. VLMs struggle with geometric primitives needing precise trajectory estimation; SfM struggles with semantic primitives. Generative VLMs (VQAScore) beat discriminative (CLIPScore). SFT of Qwen2.5-VL on ~1,400 videos gave 1-2x improvement, matched MegaSAM AP and, per the project page, captioned camera motion better than GPT-4o and Gemini-2.5-Pro. Zoom-in (intrinsics) vs forward dolly (extrinsics) is a noted confusion. — [CameraBench project page](https://linzhiqiu.github.io/papers/camerabench/), [arXiv 2504.15376](https://arxiv.org/abs/2504.15376)
- SAM 3 (Meta, Nov 19, 2025): detects/segments/tracks all instances of a concept prompt (noun phrase or exemplar) in images and video; custom Meta license (a mirror claims commercial use is permitted; unverified); inference cost scales linearly with number of tracked objects. — [arXiv 2511.16719](https://arxiv.org/pdf/2511.16719), [Roboflow](https://blog.roboflow.com/what-is-sam3/), [GitHub](https://github.com/facebookresearch/sam3)
- InsightFace: code MIT, but pretrained models (e.g. buffalo_l) need a commercial license from InsightFace per its site; a LocalAI mirror describes buffalo packs as non-commercial and suggests Apache-2.0 YuNet + SFace for commercial use. — [InsightFace licensing](https://www.insightface.ai/solutions/face-recognition-licensing), [LocalAI face-detect-gguf](https://huggingface.co/mudler/face-detect-gguf)

### Inferences
- Deterministic camera-motion pipeline (my design, not sourced): estimate per-shot global motion with OpenCV (feature tracking + homography/affine, or RAFT flow) to get pan/tilt/zoom/roll magnitudes and sign, which also yields direction-of-motion of the camera; combine with subject tracking (YOLO/SAM) to distinguish "camera follows subject" from "subject moves across frame". Pan vs dolly/truck and zoom vs dolly need parallax or depth cues, which CameraBench shows is hard even for MegaSAM.
- Shot-size and camera-angle can be classified per keyframe by a VLM or CLIP-style zero-shot classifier; this is inexpensive and does not need temporal reasoning.
- Face "is this the user" must respect the InsightFace model license; ArcFace-style alternatives with permissive weights (e.g. YuNet+SFace) are safer for a commercial product.

### Gaps
- No sources fetched in this pass for RAFT, OpenCV optical-flow camera-motion estimation, MediaPipe, RTMPose, VideoMAE, X-CLIP, YOLO versions, SAM 2, or independent shot-detection benchmarks on short-form/Reel content (transitions like whip pans, glitch, and speed ramps).
- TransNetV2/AutoShot runtime numbers not found.
- PySceneDetect gradual-transition limitations not documented on the page read.

## 5. Best model per sub-task, hybrid stack, known weaknesses

### Takeaway
No single model is reliable for all fields. Recommended: deterministic detectors for boundaries, motion and identity; Gemini Flash (or Pegasus structured output) for per-shot semantics and on-screen text; audio signal processing for beats; embeddings for the library.

### Cited Findings
- Gemini and TwelveLabs both return timestamps but with documented/anecdotal unreliability on dense or long videos (see sections 1-2). — [Google forum](https://discuss.ai.google.dev/t/gemini-2-5-pro-severe-timestamp-timecode-jumping-issues-in-video-transcription-need-workarounds/87242), [arXiv 2608.06361](https://arxiv.org/pdf/2608.06361)
- VLMs are weak at precise geometric camera motion; SfM is weak at semantic ones; fine-tuning on CameraBench helps. — [CameraBench](https://linzhiqiu.github.io/papers/camerabench/)
- Gemini 1 fps default can lose detail on fast motion or quick scene changes; custom fps supported. — [Video understanding docs](https://ai.google.dev/gemini-api/docs/video-understanding)
- Gemini Embedding 2 ignores audio in video and caps at 32 frames. — [Embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- Practitioner guidance: treat model-returned boundaries as candidates and check them against the actual edit. — summarized in search result from [InVideo FAQ](https://invideo.io/faq/how-do-you-use-gemini-for-video-analysis-and-scene/) (low authority)

### Inferences
Sub-task recommendations (all my synthesis):
- Shot boundaries and timestamps: TransNetV2 or AutoShot (fallback PySceneDetect AdaptiveDetector), snapped to frame times via ffprobe. Do not rely on VLM timestamps. Feed the cut list to the VLM as ground truth and ask it to describe shot N between t_start and t_end (or send per-shot clips), which also fixes timestamp drift.
- Shot size, camera angle, subject action, transitions, on-screen text, style: Gemini 3.8 Flash (or Argon for hard clips) per shot clip with a JSON schema; use `fps` 2-4 for fast cuts. Pegasus 1.6 `segment_definitions` is the alternative; run both on a sample and compare.
- On-screen text: VLM OCR is adequate for style; add PaddleOCR/EasyOCR with frame timestamps if exact timing and positions are required (not researched).
- Camera movement: optical-flow/homography per shot (OpenCV/RAFT), plus a VLM label as a tie-break for semantic cases (e.g. tracking shot). Expect errors on dolly vs zoom and subtle handheld. If volume justifies it, fine-tune Qwen3-VL on CameraBench.
- Direction of motion ("toward camera vs diagonal"): VLMs are unreliable; derive from object tracks (YOLO/SAM 3 tracker box centroid and scale change) and optical flow, then convert to words ("toward camera" = bbox area growing, "left to right" = centroid dx>0).
- Pacing: from shot list (cuts per second, average shot length) - deterministic.
- Music/beat sync: librosa/madmom beat tracking on audio compared to cut times (not researched; standard tooling). Gemini Embedding 2 ignores video audio, so do not rely on it for music.
- Library indexer: chunk user footage into scenes (shot detector) or 10-30 s windows; embed with Gemini Embedding 2 (video, 3072 or truncated dims) or Marengo 3.x (managed search, entity search) or Voyage multimodal-3.5; add per-clip VLM caption (Flash-Lite) and a face-match flag; store vectors in a local vector DB; hybrid search (vector + caption BM25).
- Face "is this the user": SCRFD/YuNet detection + ArcFace/SFace embedding against enrolled selfies; license caveat above.

### Gaps
- No head-to-head benchmark of Gemini vs Pegasus vs Qwen3-VL on shot-level annotation of short-form reels. A small internal eval (10 reels hand-labeled) is the only way to settle this.
- Beat-sync detection tooling and OCR options not researched.

## 6. Cost model (one 15-30 s reel; one hour of user footage)

### Takeaway
Reel analysis is about 1-5 cents on any managed option; library indexing is about $0.80-$3 per hour of footage for embeddings only (Gemini Embedding 2 or TwelveLabs), plus about $1-2 per hour if you also caption every clip with a Flash model. Local open-source stages cost only compute.

### Cited Findings (inputs used in the arithmetic)
- Gemini ~300 tokens/s default (about 100 tokens/s low media resolution); 3.8 Flash $0.75/$3.75 per 1M until 2026-12-31 then $1.50/$7.50; 3.5 Flash-Lite $0.30/$2.50; Argon $2/$10 until 2026-11-30 then $4/$20; batch ~50% off. — [Video docs](https://ai.google.dev/gemini-api/docs/video-understanding), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Gemini Embedding 2 video ~$0.00079/frame ($12/1M tokens), 32-frame cap, 120 s cap. — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- TwelveLabs: Pegasus analyze $1.75/hour of input video + $7.50/1M output tokens; legacy indexing $2.50/hour + $0.09/hour/month; search $4/1,000 queries; plans Plus $29, Pro $99. — [Toolradar](https://toolradar.com/tools/pegasus-1-6-by-twelvelabs), [usagepricing.com](https://www.usagepricing.com/blueprint/activity/twelve-labs-2026-10-15-subscription-plans-replace-payg), [TwelveLabs pricing](https://www.twelvelabs.io/pricing)
- Azure Video Indexer Basic ~ $0.05/min and Google Video Intelligence shot detection $0.05/min (unofficial/snippet; see sections 2-3).

### Inferences (my arithmetic; assumptions stated)
Assumptions: output about 3,000 tokens of JSON for a 20-30 s reel; 20 s reel = 6K input tokens, 30 s = 9K at default resolution; "thinking" tokens not included.

| Task | Option | Approx cost |
|---|---|---|
| Analyze 15-30 s reel | Gemini 3.8 Flash (promo to Dec 31, 2026) | 6-9K in x $0.75/M = $0.005-0.007; 3K out x $3.75/M = $0.011; total about $0.02 (about $0.04 after price rise) |
| Analyze 15-30 s reel | Gemini 3.5 Flash-Lite | about $0.002 in + $0.0075 out = about $0.01 |
| Analyze 15-30 s reel | Gemini 4 Argon (to Nov 30, 2026) | 9K x $2/M = $0.018 + 3K x $10/M = $0.03; about $0.05 (double after Dec 1) |
| Analyze 15-30 s reel | TwelveLabs Pegasus 1.6 | $1.75/h x (20-30 s) = $0.010-0.015 + 3K out x $7.50/M = $0.0225; about $0.03-0.04 (overage-equivalent; on Plus/Pro it draws from workload allowance) |
| Analyze 15-30 s reel | Claude (frames, 2 fps) | 40-60 frames x ~1,560 tokens = 62-94K input tokens; dollar cost not computed (Claude pricing not retrieved) |
| Local pipeline stages (TransNetV2, OpenCV flow, YOLO, beats) | self-hosted | no API fee; GPU/CPU seconds per reel |
| Index 1 h footage, embeddings only | Gemini Embedding 2, 120 s chunks (32 frames each, 30 chunks) | about 960 frames x $0.00079 = about $0.76 |
| Index 1 h footage, embeddings only | Gemini Embedding 2, 32 s chunks at 1 fps (113 chunks) | about 3,600 frames x $0.00079 = about $2.84; batch half = $1.42 |
| Index 1 h footage | TwelveLabs legacy PAYG | $2.50 index + $0.09/month storage-infra = about $2.59 first month; new plans: flat $29/$99 monthly with workload cap (size of allowance not published) |
| Index 1 h footage + VLM caption of every clip | Gemini 3.5 Flash-Lite, 1 h at ~300 tok/s = 1.08M tokens | $0.32 input + captions (e.g. 120 clips x 150 tokens x $2.50/M = $0.045) = about $0.37 |
| Index 1 h footage + caption | Gemini 3.8 Flash | $0.81 input (promo) + small output = about $0.85 ($1.62 after Jan 1, 2027) |
| Per search query | TwelveLabs | $4/1,000 = $0.004; Gemini Embedding 2 query is text embedding at $0.20/1M tokens (negligible) |

Notes: Gemini token-per-second is documented; the frame counts and caption sizes above are assumptions. Low media resolution (about 100 tokens/s) cuts the caption cost about 3x. Re-embedding is only paid when footage changes; TwelveLabs plans bill storage on original file size (50 GB on Plus, 200 GB on Pro), which may bind before workload for HD footage.

### Gaps
- Claude/OpenAI/Nova per-video dollar costs not computed because per-token prices and video input rules were not verified.
- Latency (seconds per reel) for every option not measured or found; TwelveLabs async indexing latency not documented in sources read.
- Vertex multimodalembedding official price per second/segment not verified.
