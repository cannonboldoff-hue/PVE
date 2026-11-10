# Persistent Personal Media Memory: Technology Stack (as of 2026-11-02)

Research note: tool budget was exceeded slightly and the search tool rate-limited twice (Gemini Embedding 2, Resolve search both retried successfully via fetch). Items marked [UNVERIFIED] come from model knowledge or tool-summary text without a fetched primary source. Items with no URL are in Gaps.

## 1. Existing products: what they index, limits, video segmentation, people recognition

### Takeaway
Every shipping product indexes at clip or keyframe granularity with CLIP-like embeddings plus separate speech/face/metadata indexes. None found documents structured shot attributes (shot size, direction, camera move) as first-class filters; Adobe is the closest (it says camera angle and shot type are searchable). Pro NLE tools (Premiere, Resolve) run locally; consumer cloud tools (Google) use Gemini and are still gated.

### Cited Findings
- Google Photos Ask Photos: Gemini-based; classic search merged into Ask Photos; simple queries return immediately while complex ones run in the background. The Google post says it is "opening up beyond early access", rollout limited to eligible US users at that time (June 2025); no latency figures given. — [Google blog](https://blog.google/products-and-platforms/products/photos/updates-ask-photos-search/)
- Google paused Ask Photos in June 2025 because a PM said it "isn't where it needs to be, in terms of latency, quality and UX". — [PetaPixel](https://petapixel.com/2025/06/27/google-resumes-rollout-of-ai-based-ask-photos-image-search); [Thurrott](https://www.thurrott.com/music-videos/321744/google-pauses-the-rollout-of-experimental-ask-photos-feature)
- A query is passed to an agent model that picks the best RAG tool for the task (secondary description). — [PetaPixel 2024](https://petapixel.com/2024/05/14/gemini-powered-ask-photos-brings-an-ai-assistant-to-google-photos)
- 2026: Japan rollout reported Feb 2026 (third-party blog); Google Photos added a toggle to disable Ask Photos and return to classic search (Thurrott, date not shown, appears ~Mar 2026). No official 2026 Google announcement found. — [Jetstream](https://jetstream.blog/2026/02/15/google-photos-ask-photos-japan-rollout/); [Thurrott](https://www.thurrott.com/a-i/333542/google-photos-now-lets-users-disable-ask-photos-search-experience)
- Adobe Premiere Media Intelligence: analyzes visuals (people, objects, locations, camera angles, shot type like "tight shot", season) plus transcripts/metadata in the Search panel; auto-creates in/out points for matching shots; analysis runs locally and Adobe states footage is not used for training; broad queries return many results (a "drone" search returned over a thousand). — [Adobe Learn](https://www.adobe.com/learn/premiere-pro/web/media-intelligence-search-ai)
- Premiere limits (secondary sources summarized via search tool): model samples downscaled stills so it can miss small details and fast motion; does not read text on signs; March 2025 community feedback said generic queries ("person spinning", "interview") gave weak/too-similar results. Adobe FAQ page returned 403 so this is not verified against Adobe docs. — [Adobe FAQ (not fetched)](https://helpx.adobe.com/vn_vi/premiere-pro/using/media-intelligence-and-search-panel-faq.html); [Adobe community](https://community.adobe.com/announcements-732/now-released-search-panel-finds-the-shot-faster-with-visual-search-311756); [Pro Video Coalition](https://www.provideocoalition.com/unlocking-efficiency-with-media-intelligence-in-adobe-premiere-pro/)
- DaVinci Resolve 21 (final release 3 June 2026, Studio only) added IntelliSearch: two downloadable models, "Faster" and "Better" (Better about 6x slower to analyze per reviewer estimate); media must be pre-analyzed for dialog and visual content; indexes objects/scenes, faces (Face Gallery; faces as small as 15x15 px per reviewer), and dialog; visual and face results return whole clips, transcript results are moment-level; scope is the open project, not a library; results can be saved as dynamic Smart Bins. — [Larry Jordan](https://larryjordan.com/articles/the-power-of-intellisearch-in-davinci-resolve-21/); [Newsshooter](https://www.newsshooter.com/2026/06/02/davinci-resolve-21-final-release/); [Blackmagic AI page](https://www.blackmagicdesign.com/products/davinciresolve/ai)
- Blackmagic: Neural Engine face detection sorts clips into bins by the people in shot; Neural Engine is in Studio, not free. — [Blackmagic](https://www.blackmagicdesign.com/products/davinciresolve/ai)
- Immich: smart search uses CLIP-style models stored in Postgres with the VectorChord extension; default model is fast, larger/multilingual options include nllb, xlm, siglip2; changing model requires rerunning Smart Search jobs. Advanced filters: people, contextual, filename, path, description, OCR, location, tags, camera make/model/lens, date range, media type, favorites/archive, star rating. — [Immich docs](https://docs.immich.app/features/searching)
- Immich face recognition uses InsightFace (default pack buffalo_l, detection then recognition; re-run face job after model change). — search-tool summary of Immich docs, [Immich docs](https://docs.immich.app/features/searching) (face-model detail is from the mirrored docs listed by the search; not re-fetched)
- Immich docs do not state how video is sampled for smart search; I could not confirm single-frame vs multi-frame. — [Immich docs](https://docs.immich.app/features/searching)
- Apple Photos: user guide covers people and pets, date, location, media type, Live Text, Visual Look Up; the fetched page did not describe natural-language search internals or on-device processing. — [Apple Photos guide](https://support.apple.com/guide/photos/search-for-photos-phts1d9b0e3e/mac)

### Inferences
- The clip-level (not moment-level) result granularity in Resolve and the "whole shot with auto in/out" in Premiere imply that segmenting into shots first, then embedding per shot, is the dominant design.
- Google's pause and the opt-out toggle suggest LLM-agent search over a personal library had latency/quality problems even for Google; a purpose-built structured+vector pipeline with no agent loop in the hot path is a defensible differentiator.
- PhotoPrism, Mylio, Memories, Eagle, Amazon Photos, Final Cut Pro, Descript, Frame.io were not researched in this pass (see Gaps).

### Gaps
- No primary docs fetched for: PhotoPrism, Mylio, Memories (Nextcloud), Eagle, Amazon Photos, Final Cut Pro, Descript, Frame.io, TwelveLabs-powered consumer tools.
- Adobe FAQ (403), Apple's natural-language search internals, Immich video frame sampling: not verified.
- Resolve IntelliSearch model architecture undocumented in sources found.

## 2. Embedding options, weaknesses, and hybrid retrieval research

### Takeaway
Dense embeddings handle scene/object/mood well and are weak on direction, action negation, agent-action binding, and camera motion. Research supports a cascade: structured tags and dense recall, then a stronger cross-encoder/VLM reranker; camera-motion needs dedicated models (CameraBench). Natively video-aware API embeddings now exist (TwelveLabs Marengo 3.5, Gemini Embedding 2).

### Cited Findings
- Gemini Embedding 2 (`gemini-embedding-2`, stable, updated April 2026) is "the first multimodal embedding model in the Gemini API": text up to 8,192 tokens; image up to 6 per request; video up to 120 s (MP4/MOV), up to 32 frames processed; audio up to 180 s; PDF up to 6 pages; default 3072 dims, flexible 128-3072 (768/1536/3072 recommended); Batch API is 50% of price. — [Gemini embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- Gemini Embedding 2 pricing (paid): text $0.20/1M tokens; image $0.45/1M tokens ($0.00012 per image); audio $6.50/1M ($0.00016/s); video $12.00/1M tokens ($0.00079 per frame); batch is half. At 32 frames per segment, about $0.025 per 120 s segment at standard price (inference: 32 x $0.00079). — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- TwelveLabs Marengo 3.5 (blog byline Aug 31 2026, page metadata Oct 30 2026; date ambiguous): one shared space for video, audio, image, text, PDF pages; composable queries (text plus image/video/audio into one query embedding); time-based metadata fusion; optional uncertainty signal; Matryoshka 128/256/512 dims (default 512; 256 keeps 98.3%, 128 keeps 94.6% of score); no duration cap for async ingestion (3.0 had a 4 h limit). Vendor-reported: mean 70.57 on five text-to-video datasets (+6.29 vs Marengo 3.0); 8-group aggregate 67.38 at 512 dims vs Gemini Embedding 2 62.35 and Amazon Nova Multimodal 50.34 at 3,072 dims. — [TwelveLabs Marengo 3.5](https://www.twelvelabs.io/blog/marengo-3.5)
- Marengo 3.5 pricing per 1M billable tokens: video $0.260, audio $0.065, image $0.080, document $0.162, text $0.200 (metered per modality, summed). Token-to-minute conversion not stated on the page. — [TwelveLabs Marengo 3.5](https://www.twelvelabs.io/blog/marengo-3.5)
- TwelveLabs plans: Free ($0, 3 GB), Plus ($29/mo, 50 GB), Pro ($99/mo, 200 GB), Enterprise custom; workload allowances unquantified. — [TwelveLabs pricing](https://www.twelvelabs.io/pricing-calculator)
- Marengo 3.0 on Bedrock: video uses dynamic segmentation with shot boundary detection; dimension reduced from 1024 to 512 (search-tool summary of AWS docs). — [AWS Bedrock docs](https://docs.aws.eu/bedrock/latest/userguide/model-parameters-marengo-3.html)
- SigLIP 2 (Feb 2025): captioning-based pretraining plus self-distillation and masked prediction; checkpoints ViT-B (86M), L (303M), So400m (400M), g (1B); some variants support native aspect ratio and multiple resolutions; improved multilingual and localization. — [arXiv 2502.14786](https://arxiv.org/abs/2502.14786)
- MobileCLIP2 (Apple): S0 71.5% ImageNet zero-shot with 11.4M image-tower params and about 1.5 ms image latency; S2 77.2%; B 79.4% at 10.4 ms; latency device is iPhone 12 Pro Max per highlights; models under Apple ML Research Model TOU (check commercial terms), code MIT. — [apple/ml-mobileclip](https://github.com/apple/ml-mobileclip)
- CLIP weaknesses: little spatial reasoning off the shelf; NegCLIP failed to improve left vs right on VG-Relations; CLIP-based video retrieval has poor object-attribute binding and weak sensitivity to action negation/replacement. — [ReCLIP paper](https://nlp.cs.berkeley.edu/pubs/Subramanian-Merrill-Darrell-Gardner-Singh-Rohrbach_2022_ReCLIP_paper.pdf); [What's left can't be right](https://ar5iv.labs.arxiv.org/html/2311.11477); [ICSVR](https://arxiv.org/html/2306.16533v3)
- ViLMA and VELOCITI benchmark temporal grounding and agent-action binding in video-language models (details not verified beyond abstracts). — [ViLMA](https://arxiv.org/pdf/2311.07022)
- CameraBench (NeurIPS 2025): ~3,000 expert-annotated videos, camera-motion taxonomy built with cinematographers; SfM models miss semantic motion primitives, VLMs miss precise geometric trajectories; fine-tuning a VLM on it gives the best of both and improves video-text retrieval. — [arXiv 2504.15376](https://arxiv.org/abs/2504.15376)
- Cascaded retrieval pattern: dual-encoder first stage (BEiT-3 plus SigLIP) then BLIP-2-based reranker, fused with OCR/ASR, for interactive moment retrieval (AAAI 2026 workshop). Another CVPR 2025 workshop system uses FAISS over keyframe embeddings plus reranking and bidirectional temporal search. — [arXiv 2512.12935](https://arxiv.org/abs/2512.12935v1); [arXiv 2504.09298](https://arxiv.org/abs/2504.09298v1)

### Inferences
- A practical stack: (a) shot-boundary segmentation, (b) per-shot embedding with Marengo 3.5 or Gemini Embedding 2 (or SigLIP 2 on keyframes locally), (c) VLM-extracted structured tags per shot (shot size, direction of motion, subject count, location, lighting) stored as columns, (d) hard filter on tags then ANN, (e) VLM rerank of top 10-20 against the full slot spec.
- Since Gemini Embedding 2 processes at most 32 frames from a clip up to 120 s, segments should be short (a few seconds) for action fidelity. Marengo 3.5 aggregate scores are vendor-reported and compared against competitors at different dimensions; treat as marketing until reproduced.
- Direction ("walking left to right"), camera movement, and shot size are likely better produced by a VLM/optical-flow tagger at ingest than by embedding similarity (supported by the CLIP spatial-reasoning and CameraBench findings, but no direct head-to-head on personal footage was found).

### Gaps
- No fetched primary source for Jina CLIP, ColPali-style video retrieval, InternVideo2, LanguageBind, VideoCLIP, or a direct benchmark of SigLIP 2 vs Marengo vs Gemini on action/direction queries.
- No published benchmark of hybrid (tag + dense + VLM rerank) on personal videos.

## 3. Vector DB / search infrastructure and cost at personal scale

### Takeaway
A personal library (thousands to a few hundred thousand segments at 512-1536 dims) fits in a few GB; pgvector or embedded stores are sufficient and cheapest. Managed serverless minimums ($16-$50/mo) dominate cost at small scale. On-device sqlite-vec is viable but pre-v1.

### Cited Findings
- pgvector v0.8.7: HNSW and IVFFlat; `vector` indexes up to 2,000 dims, `halfvec` up to 4,000, `bit` up to 64,000; halfvec and binary quantization with rerank to shrink working set; filters apply after the ANN scan (with default ef_search 40 and a 10%-selective filter, about 4 rows returned on average) so iterative scan (`hnsw.iterative_scan`, max_scan_tuples default 20,000) is needed for filtered queries. — [pgvector](https://github.com/pgvector/pgvector)
- sqlite-vec: pre-v1, "expect breaking changes"; float/int8/binary vectors in vec0 tables, KNN via MATCH, metadata/partition-key columns; pure C; runs on Linux/macOS/Windows/WASM/Raspberry Pi; iOS/Android not mentioned on README; no benchmark numbers on README. — [sqlite-vec](https://github.com/asg017/sqlite-vec)
- Pinecone: Starter free 2 GB storage, 2M write units/mo, 1M read units/mo, one region (AWS us-east-1), 5 indexes; Standard $50/mo minimum; storage $0.33/GB/mo; writes $4-4.50 per million units; reads $16-18 per million units. — [Pinecone pricing](https://www.pinecone.io/pricing/)
- turbopuffer: Launch $16/mo minimum, Scale $256/mo, Enterprise $4,096/mo plus 35% premium; storage up to $0.33/GB; example of 1M docs (~3 GB), 1M writes, 1M queries is about $7/mo, so the $16 minimum applies. — [turbopuffer pricing](https://turbopuffer.com/pricing)
- Qdrant Cloud: free forever 1 node (0.5 vCPU, 1 GB RAM, 4 GB disk); Standard billed hourly by vCPU/memory/storage (no rates on the page; calculator is separate). — [Qdrant pricing](https://qdrant.tech/pricing/)
- Secondary: LanceDB 0.38 test ingested 1.18M glove-100 vectors in 1 s with 488 MiB on disk, recall@10 0.91, p95 near 6 ms; pgvector reportedly degrades beyond ~50M vectors on one node; Qdrant self-hosted 10M vectors est. $60-120/mo. No controlled head-to-head found. — [computingforgeeks (via search)](https://computingforgeeks.com/?p=171566); [web3aiblog](https://www.web3aiblog.com/blog/vector-database-showdown-pinecone-weaviate-qdrant-lancedb-chroma-may-2026)
- Immich runs pgvector-family search in Postgres (VectorChord) at self-hoster scale. — [Immich docs](https://docs.immich.app/features/searching)

### Inferences
- Size math (inference): 100k segments x 512 dims x 4 B = about 200 MB (about 100 MB as halfvec); even 1M segments at 1536 dims float32 is about 6 GB. Multi-tenant SaaS with per-user namespaces fits turbopuffer or pgvector with user_id partitioning; per-user cost is negligible vs embedding cost.
- Embedding cost dominates infra cost (inference): 10 hours of video at 4 s segments = 9,000 segments; at 8 frames per segment and $0.00079/frame (Gemini Embedding 2 standard) that is about $57 (half with Batch); at 32 frames per segment about $227.

### Gaps
- Weaviate, Elasticsearch/OpenSearch, Vespa, Chroma pricing not fetched. Qdrant per-GB rates not found. Core ML / Android on-device vector store specifics (e.g., ObjectBox, SQLite on iOS) not researched.

## 4. Person identification in a personal library

### Takeaway
Self-hosted face stacks (Immich) use InsightFace, but the pretrained InsightFace model weights are non-commercial by default; commercial products need a license or an alternative (e.g., OpenCV YuNet+SFace, Apache-2.0 per a packager). AWS Rekognition is cheap per image but stores biometric vectors. Biometric consent law (BIPA) has produced a $100M Google settlement.

### Cited Findings
- InsightFace code is MIT, but pretrained models (including buffalo_l auto-downloads) are available for non-commercial research only; commercial use requires contacting recognition-oss-pack@insightface.ai (README update 2025-11-24). — [PyPI insightface](https://pypi.org/project/insightface/); [InsightFace licensing](https://www.insightface.ai/llms.txt/solutions/face-recognition-licensing); [zengxs fork README](https://github.com/zengxs/insightface)
- Packager claims OpenCV Zoo YuNet + SFace are Apache-2.0 and suited to commercial deployment (third-party claim; verify). — [face-detect-gguf](https://huggingface.co/mudler/face-detect-gguf)
- AWS Rekognition face search: $1.00 per 1,000 images for the first 1M (tiers down to $0.40/1,000); face vector storage $0.00001 per face per month; free tier 1,000 images/mo for 12 months; stored-video label detection $0.10/min, shot detection $0.05/min; video face metadata $0.00001 per object per month. — [AWS Rekognition pricing](https://aws.amazon.com/rekognition/pricing/)
- Google Photos Face Grouping BIPA class action settled for $100M (about 420,000 people, no admission of wrongdoing); Google committed to notice, opt-in consent for face grouping starting in Illinois, and deletion of templates when the feature is disabled or after two years of inactivity. — [IAPP](https://iapp.org/news/b/google-to-pay-settlement-to-illinois-residents-for-bipa-violations); [Android Central](https://androidcentral.com/apps-software/google-photos-biometrics-violation-100-million-settlement)
- Resolve face recognition groups clips into bins by person (Face Gallery) locally in Studio. — [Larry Jordan](https://larryjordan.com/articles/the-power-of-intellisearch-in-davinci-resolve-21/)

### Inferences
- "Who is the user" enrollment: let the user tag one cluster as "me" (or take a selfie), store a centroid of several embeddings, and match with a cosine threshold; "user with another person" = shot where the user cluster and at least one other cluster co-occur in the same segment. This is design reasoning, not sourced.
- Third parties appearing in clips are not enrolled consenting subjects; storing their face embeddings is the BIPA/GDPR risk. On-device clustering with embeddings never leaving the device, or keeping only "user vs not-user" and a person count, reduces exposure (inference; legal advice needed).

### Gaps
- GDPR treatment of face grouping, Apple/Google API access to their on-device person clusters (Apple does not expose Photos people to third-party apps, per general knowledge but unverified here), and Google Cloud Vision/Video Intelligence face pricing: not researched.

## 5. Asset quality scoring and "match score"

### Takeaway
DOVER gives separate aesthetic and technical quality scores usable as a quality prior; cheap classical metrics (Laplacian variance, exposure histograms, motion-stabilization residuals, resolution/orientation) cover the rest. No product documents its "94% vs 87%" formula; any such percentage is a design choice (weighted blend or calibrated probability).

### Cited Findings
- DOVER outputs aesthetic and technical scores plus a fused overall score in [0,1]; DOVER-Mobile is about 1.4 s per video on CPU vs 3.6 s for DOVER (authors' environment); DOVER-Mobile is 9.86M params, 52.3 GFLOPs; PLCC DOVER 0.883 KoNViD-1k, 0.854 LIVE-VQC, 0.889 LSVQ-test, 0.830 LSVQ-1080p; ONNX conversion script provided; weights on GitHub releases and Hugging Face. License files (LICENSE, S-Lab-LICENSE) exist but terms not read, check commercial terms. — [DOVER GitHub](https://github.com/VQAssessment/DOVER)
- Marengo 3.5 offers an optional uncertainty signal that is not a calibrated probability; thresholds must be calibrated on labeled data. — [TwelveLabs Marengo 3.5](https://www.twelvelabs.io/blog/marengo-3.5)
- CameraBench supports camera-motion labeling as an input for shake/movement tags. — [arXiv 2504.15376](https://arxiv.org/abs/2504.15376)

### Inferences
- Suggested decomposition of a match score: score = w1*semantic (embedding/VLM rerank, calibrated) + w2*structured-slot satisfaction (fraction of required tags matched, with hard gates for orientation/duration) + w3*quality (DOVER/blur/exposure/stability) + w4*person constraint. Calibrate with isotonic regression on user accept/reject logs so "94%" has empirical meaning (e.g., accepted-rate); otherwise show a rank-based badge. This is a design recommendation, not sourced.
- FAST-VQA, NIMA, LAION aesthetic predictor were not researched; LAION aesthetic is CLIP-embedding based so it is nearly free if CLIP/SigLIP embeddings already exist (inference).

### Gaps
- No fetched source for NIMA, LAION aesthetic, FAST-VQA, stabilization metrics, or published match-score formulas from any product.

## 6. On-device vs cloud indexing for mobile

### Takeaway
Picker-based access (PHPicker, Android Photo Picker) is permission-light but gives per-selection access only; full-library background indexing needs PhotoKit/MediaStore permissions and is throttled by the OS. Proxy-resolution upload plus on-device lightweight models is the likely best fit.

### Cited Findings
- Android Photo Picker needs no manifest permission, grants access only to selected items, native on Android 11+ (API 30) with module updates, backported to Android 4.4-10 via Play services; `PickMultipleVisualMedia(maxItems)` with platform max from `MediaStore.getPickImagesMaxLimit()`; access normally lasts until device restart or app stop, extend with `takePersistableUriPermission()`; apps can hold up to 5,000 media grants before oldest are evicted. — [Android Photo Picker docs](https://developer.android.com/training/data-storage/shared/photo-picker)
- iOS BGProcessingTask is discretionary: system decides when it runs, typically charging, idle, often overnight; tasks must be declared in Info.plist; force-quitting the app stops background tasks; a developer thread reports processing tasks killed for high CPU even while plugged in. — [Apple Developer Forums](https://developer.apple.com/forums/thread/690666) and third-party skill guides ([axiom summary](https://skills.cat/skills/charleswiltgen/axiom/axiom-background-processing)); not Apple's primary doc
- Adobe and Blackmagic both index locally on the user's machine (desktop-class hardware), taking "a few minutes" for hours of footage in Adobe's case. — [Adobe Learn](https://www.adobe.com/learn/premiere-pro/web/media-intelligence-search-ai)
- MobileCLIP2-S0 image encoder about 1.5 ms on iPhone-class hardware (Apple's reported number), so on-device keyframe embedding of tens of thousands of frames is feasible in minutes of compute. — [apple/ml-mobileclip](https://github.com/apple/ml-mobileclip)
- Gemini Embedding 2 and Marengo cloud inputs are limited (120 s / 32 frames for Gemini), implying upload of clipped proxies, not originals. — [Gemini embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)

### Inferences
- [UNVERIFIED from tool, general knowledge] PHPicker needs no library authorization and returns NSItemProvider; `assetIdentifier` is only set when the app has library authorization. Apple's documentation fetch returned only the title, so verify before relying on it.
- Suggested design: on-device shot detection + keyframes + MobileCLIP/SigLIP embeddings + Vision framework face/pose features; upload only 360p-480p proxy segments (a few MB each) for cloud VLM tagging/reranking; keep originals on device and reference by local identifier; schedule heavy work via BGProcessingTask with external power. Android equivalent: WorkManager with charging+Wi-Fi constraints (not researched).

### Gaps
- PhotoKit limited-library behavior, iCloud-optimized originals (download-on-demand), Live Photos/HDR/HEVC handling, iOS/Android thermal limits, Apple Foundation Models/Vision APIs for scene/shot analysis: not researched. No upload-cost data beyond the cloud embedding prices above.

## 7. Cold-start and expected hit rates

### Takeaway
No published data found on how often a personal library satisfies structured shot-slot requirements. Only qualitative evidence: generic queries return too many or weak matches in Premiere.

### Cited Findings
- Premiere: broad query "drone" returned over 1,000 results; community reports weak results for generic queries ("person spinning", "interview"), and Adobe says descriptive queries are more precise. — [Adobe Learn](https://www.adobe.com/learn/premiere-pro/web/media-intelligence-search-ai); [Adobe community](https://community.adobe.com/announcements-732/now-released-search-panel-finds-the-shot-faster-with-visual-search-311756)
- Resolve IntelliSearch needs a full pre-analysis pass and works only within the open project (no cross-library memory). — [Larry Jordan](https://larryjordan.com/articles/the-power-of-intellisearch-in-davinci-resolve-21/)

### Inferences
- Expect a long tail: personal libraries are skewed to a few subject types (family, travel, pets, food) so slot types like "wide establishing shot, subject walking left to right, golden hour" will often have zero strong matches; the product should treat a low-score "no good match" outcome as a first-class state (suggest reshoot, relax constraints, show partial matches). Any hit-rate claim must be measured by the team with a pilot (e.g., 20-50 libraries, label slot fill at top-1/top-5).
- Cold-start mitigations: ask user to import a seed set (best 50-100 clips), ingest incrementally, show progress, relax slot constraints in priority order (hard: orientation, duration, person; soft: shot size, direction).

### Gaps
- No analogous-system studies (Google Photos, Apple, stock-footage search click-through) with fill-rate numbers were found in this pass; the search tool rate-limited. This is the least-supported question.
