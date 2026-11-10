# Executor-side tooling for an AI Reel editor: rendering, captions, audio, generative fill, agentic editing (state as of 2026-11-02)

Evidence-quality note: many pricing figures below come from vendor pages fetched directly (marked "primary") and many from third-party aggregators/blogs (marked "secondary"; several aggregators disagree with each other). GitHub stats were pulled from api.github.com on 2026-11-02. "Stale" = no push in 12+ months.

## 1. Programmatic / deterministic rendering (FFmpeg, Remotion, Revideo, Editly, MoviePy, SaaS render APIs, mobile-native, serverless)

### Takeaway
For a JSON-timeline-to-9:16 pipeline the realistic choices are (a) self-run FFmpeg or Remotion on serverless CPU (cents per Reel, you own determinism and per-shot caching) or (b) a JSON render API (Shotstack / JSON2Video / Creatomate, roughly $0.02-0.30 per 20 s Reel). Remotion is source-available, not OSS: free only for individuals, non-profits and for-profits with up to 3 employees; larger companies need a paid license. Editly is stale; Revideo and MoviePy are maintained.

### Cited Findings
**Remotion (React, source-available)**
- GitHub: 69.7k stars, last push 2026-11-01; GitHub detects license as "Other/NOASSERTION" (custom license, not OSI) — [GitHub API](https://api.github.com/repos/remotion-dev/remotion) (primary).
- Free license: individuals, for-profit orgs "up to 3 employees", non-profits, and anyone evaluating. Company License required for everyone else; copying/modifying Remotion to resell a derivative is disallowed; license "will change slightly in Remotion 5.0" — [Remotion LICENSE.md](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md) (primary).
- Official docs say "completely free to use for any individual or small company... For bigger companies, we charge a license fee" but the price table is an embedded component I could not read — [Remotion license/pricing docs](https://www.remotion.dev/docs/license/pricing).
- Company license prices (SECONDARY only, not verified on remotion.pro): "Automators" $0.01 per render with $100/month minimum; "Creators" $25/seat/month (manual use); Enterprise from $500/month; AWS costs separate — [Wireflow summary](https://www.wireflow.ai/blog/remotion-pricing), [search results incl. remotion.dev/docs/pricing](https://www.remotion.dev/docs/pricing). One reviewer's "10,000 renders included" claim could not be confirmed.
- Lambda cost (official example, 2048 MB, us-east-1, warm): Hello World about $0.001; 1-minute video about $0.021; 10-minute remote HD video about $0.162; compute only, S3/CloudWatch extra; videos embedded in a composition raise cost "significantly"; Remotion says to measure your own composition — [Remotion Lambda cost example](https://remotion.dev/docs/lambda/cost-example).
- Speed claim (marketing): 80 s video rendered in 15 s on Lambda; fewer Lambdas = cheaper but slower — [Remotion Lambda docs](https://remotion.dev/docs/lambda), [optimizing cost](https://www.remotion.dev/docs/lambda/optimizing-cost).

**Revideo, Editly, MoviePy, Diffusion Studio, OpenCut, Etro (GitHub API, 2026-11-02)**
- Revideo: repo moved from redotvideo to midrender/revideo; 4,165 stars; MIT; last push 2026-07-15; not archived — [GitHub API](https://api.github.com/repos/midrender/revideo).
- Editly (JSON-edit-spec to video via FFmpeg + node-canvas): 5,576 stars; MIT; last push 2025-05-12 (about 18 months, STALE) — [GitHub API](https://api.github.com/repos/mifi/editly).
- MoviePy: 15.1k stars; MIT; last push 2026-08-26 — [GitHub API](https://api.github.com/repos/zulko/moviepy).
- Diffusion Studio Core (browser WebCodecs engine): 1,252 stars; MPL-2.0; last push 2025-11-18 (about 11.5 months, borderline stale); npm README also references commercial/non-commercial terms; v3 (Feb 2025) removed FFmpeg dependency — [GitHub API](https://api.github.com/repos/diffusionstudio/core), [docs version 3](https://docs.diffusion.studio/docs/version-3), [README](https://cdn.jsdelivr.net/npm/@diffusionstudio/core-v2@2.0.1/README.md).
- OpenCut (open-source editor app, not a headless render engine): 97k stars; MIT; last push 2026-09-24 — [GitHub API](https://api.github.com/repos/OpenCut-app/OpenCut).
- Etro (canvas/WebGL browser video-effects library): 1,154 stars; GPL-3.0 (copyleft; relevant to commercial closed-source use); last push 2026-10-24 — [GitHub API](https://api.github.com/repos/etro-js/etro).

**SaaS JSON render APIs**
- Shotstack (PRIMARY, fetched 2026-11-02): PAYG $10 once for 50 min (20 c/min), 1080p; Starter $39/mo 250 min (15.6 c/min), 1080p; Pro $99/mo 750 min (13.2 c/min), 4K; Scale $199/mo 2,000 min (10 c/min); Volume $499/mo 10,000 min (5 c/min); rendering pauses when minutes run out, top-ups at plan rate — [Shotstack pricing](https://shotstack.io/pricing/). (Third-party sites list older/conflicting figures such as $0.30/min PAYG and $0.20/min subscription; use the vendor page.)
- JSON2Video (PRIMARY): Hobby $16.63/mo (billed yearly) 3,000 credits (about 50 min); Professional $49.95 12,000 credits (about 200 min); Startup $99.95 30,000 credits (about 500 min); credits = 1 per second of video; free plan 600 credits with watermark; subscription credits expire monthly; no per-minute overage listed — [JSON2Video pricing](https://json2video.com/pricing/).
- Creatomate (PRIMARY partial): credit-based; plans Essential (2,000 credits), Growth (10k-40k), Beyond (50k-200k); dollar amounts not rendered in fetch; 720p/25fps about 14 credits per minute; one image = 1 credit — [Creatomate pricing](https://creatomate.com/pricing), [credit docs](https://creatomate.com/docs/account/how-are-credits-calculated). Prices from third parties conflict ($54/mo for 2,000 credits; Growth $99 or $129 for 10k) — [Wireflow](https://www.wireflow.ai/blog/creatomate-pricing), [Toolradar](https://toolradar.com/tools/creatomate/pricing). Credit formula (secondary): width x height x fps x seconds / 100,000,000.
- Rendi (hosted FFmpeg API, PRIMARY): Free 4 vCPU, 50 GB processing/mo, 1-minute max command runtime; Pro $25/mo 4 vCPU, 250 GB, 10-minute runtime; larger tiers up to 256 vCPU; processing metered as input+output GB, "as low as $0.10 per GB processed"; no per-minute pricing; no egress fees — [Rendi pricing](https://rendi.dev/pricing).
- Mux (encode/store/deliver, not a compositor): on-demand encoding about $0.032/min for first 5,000 min at 720p or lower, $0.12/min 4K; storage about $0.003/min/month; delivery about $0.00096/min; docs show inconsistent tier figures — [Mux pricing](https://docs.mux.com/pricing/video).
- Cloudinary: video transformations counted per second of processed video, depends on delivered resolution; rate table not retrieved — [Cloudinary transformation counts](https://cloudinary.com/documentation/transformation_counts). Bannerbear: image & video API credits (Automate $49/mo for 1,000 credits per a secondary listing); credits-per-video not confirmed — [Bannerbear pricing](https://bannerbear.com/pricing), [Toolradar](https://toolradar.com/tools/bannerbear/pricing).

**Mobile-native**
- Android Media3 Transformer: Apache-2.0 repo androidx/media, 3,063 stars, last push 2026-10-31 — [GitHub API](https://api.github.com/repos/androidx/media). Docs: transcoding, trimming, cropping, custom effects; MediaCodec hardware encode/decode + OpenGL effects; Android 6.0+; multi-asset Composition and CompositionPlayer preview exist; "actively under development" — [Media3 Transformer](https://developer.android.com/media/media3/transformer).

**GPU / serverless**
- Modal GPU per-second rates (SECONDARY tracker citing Modal): L4 about $0.000222/s, A10 $0.000306/s, L40S $0.000542/s, H100 about $0.001097/s ($3.95/hr); region multipliers 1.15-1.75x — [computeprices H100](https://computeprices.com/providers/modal/gpus/h100), [usagepricing](https://www.usagepricing.com/blueprint/activity/modal-2026-10-24-region-surcharge-cut).

### Inferences
- For a 20 s Reel, the render step is pennies on any option: Remotion Lambda about $0.007 (20/60 x $0.021, plus S3) before license; Shotstack about $0.017-0.067 (20/60 x 5-20 c/min; unknown if billed per-second or rounded to minute); JSON2Video 20 credits, about $0.07 on Startup ($99.95/30,000 credits x 20); Creatomate about 10-12 credits per 1080x1920 20 s at 25-30 fps by the secondary formula, so roughly $0.10-0.30 depending on unverified plan price.
- Remotion license is the main commercial gotcha: if the company has 4+ employees, budget at least $100/month minimum plus $0.01/render (secondary figures); this is trivial per Reel but a fixed cost. FFmpeg (LGPL/GPL build considerations aside) has no per-render license.
- Recommended architecture (design inference, not sourced): store timeline as JSON with per-shot content hash (source, trim in/out, speed, crop, effect params). Render each shot to a normalized intermediate (e.g., 1080x1920, 30 fps, same codec/GOP) with FFmpeg or Remotion; cache by hash; feedback edits invalidate only changed shots; final step = concat/xfade + captions overlay + audio mix as one cheap pass. SaaS JSON APIs re-render the whole composition each call, so they cannot give per-shot caching, though at about 5-15 c/min that rarely matters for 20 s output. Revideo/Remotion are best if you want component-based captions/animations; plain FFmpeg is best for trims/concat/xfade/audio.
- Editly's JSON spec is conceptually the closest to the "timeline-as-JSON" idea but is stale; treat as design reference, not dependency.

### Gaps
- Remotion company license prices not verified on a primary page (embedded table unreadable).
- Creatomate dollar prices per tier not retrievable; Cloudinary per-second video rates and Bannerbear credits-per-video not retrieved.
- Not researched: Lottie (lottie-web/dotLottie runtime), iOS AVFoundation/AVMutableComposition, Etro vs Revideo benchmarks, Google Cloud Run GPU pricing, AWS Lambda FFmpeg limits, actual Lambda render speed for vertical 1080x1920 with video layers.
- Etro/Remotion GPU vs CPU rendering behavior (Remotion uses headless Chromium, CPU by default) not sourced.

## 2. Agentic video editing: projects, papers, design patterns, failures

### Takeaway
Working open-source agents (video-use, MCP wrappers) put the LLM on a text/transcript layer and have it emit an edit-decision list (EDL) that deterministic tools (ffmpeg) render, with a capped self-eval loop. Benchmarks in 2026 show frontier agents still resolve only about 27-30% of real editing tasks; failures are mostly taste/quality, not tool errors.

### Cited Findings
- browser-use/video-use: 30.3k stars, MIT, last push 2026-10-08. Pipeline: one ElevenLabs Scribe call per source gives word timestamps, diarization and audio events, packed into about 12 KB `takes_packed.md`; on-demand `timeline_view` PNG (filmstrip + waveform + word labels); LLM writes an EDL; ffmpeg renders; self-eval loop up to 3 fix-and-re-render cycles; README says the LLM "never watches the video"; overlays via HyperFrames/Remotion/Manim/PIL sub-agents; needs ffmpeg and ElevenLabs key; cloud version "coming" — [GitHub repo](https://github.com/browser-use/video-use), [GitHub API](https://api.github.com/repos/browser-use/video-use).
- Secondary write-ups rationale: naive frame-feeding (30,000 frames x 1,500 tokens = 45M tokens) vs transcript approach — [The Menon Lab](https://themenonlab.blog/blog/video-use-ai-video-editing-claude-code).
- Auto-Editor (non-LLM silence/motion cutting CLI): 5,694 stars, Unlicense, last push 2026-11-01 — [GitHub API](https://api.github.com/repos/WyattBlue/auto-editor).
- MCP servers: burningion/video-editing-mcp (wraps Video Jungle service) 295 stars, last push 2025-10-09 (about 13 months, STALE) — [GitHub API](https://api.github.com/repos/burningion/video-editing-mcp); DareDev256/fcpxml-mcp-server (natural language to Final Cut Pro XML, directory-reported 48 stars, MIT) and vedit-mcp (ffmpeg-based, 2025) — [directory listings](https://enterprisedna.co/directories/mcp/daredev256-fcpxml-mcp-server), [burningion listing](https://enterprisedna.co/directories/mcp/burningion-video-editing-mcp) (not verified at repo level).
- LAVE (UofT + Meta Reality Labs, IUI '24): plan-and-execute LLM agent, plan shown to user before execution; language descriptions of footage generated so the LLM can reason over video; 8-participant study — [project page](https://www.dgp.toronto.edu/~bryanw/lave/), [arXiv 2402.10294](https://arxiv.org/abs/2402.10294v1).
- EditDuet (2025): Editor + Critic agents over a non-linear editing timeline — [arXiv 2509.10761](https://arxiv.org/html/2509.10761v1).
- Aurora (arXiv 2605.18748): tool-using VLM agent + video diffusion transformer; AgentEdit-Bench; VLM judge score rises from 74.7 to 87.9 with the agent — [arXiv PDF](https://arxiv.org/pdf/2605.18748), [papers.cool](https://papers.cool/arxiv/2605.18748).
- VideoAgent (arXiv 2606.23327): multi-agent orchestration with 30+ editing agents and VideoEdit benchmark — [arXiv PDF](https://arxiv.org/pdf/2606.23327). HKUDS/VideoAgent repo has 1,993 stars, MIT, last push 2026-07-22 (not confirmed to be this paper's repo) — [GitHub API](https://api.github.com/repos/HKUDS/VideoAgent).
- AgenticVBench (arXiv 2605.27705): 100 post-production tasks from 20 industry experts; best agent stack "barely crosses 30%"; harness choice substantially changes scores and failure modes — [arXiv abs](https://arxiv.org/abs/2605.27705).
- Timeline-Bench (arXiv 2609.35143): 56 real editing tasks, 16 agents (frontier model + coding-agent harness like Codex/Claude Code/OpenCode); best resolves 15/56 (26.8%), average 14.0%; of 771 unresolved runs 562 failed only the quality test; authors attribute this to agents perceiving footage "through stills and transcripts"; humans preferred reference edit 83.5% — [arXiv abs](https://arxiv.org/abs/2609.35143).
- TimelineBench (NeurIPS 2026): 100 tasks where computer-use agents drive an open-source editor GUI via screenshots/mouse/keyboard — [NeurIPS page](https://neurips.cc/virtual/2026/166886) (via search snippet only).

### Inferences
- Pattern that works: LLM emits structured data (EDL/timeline JSON) over a compact text/representation of footage; deterministic renderer; bounded verify-and-fix loop; user-visible plan before execution (LAVE). This matches the "timeline JSON patched by feedback" architecture.
- What fails (per benchmarks): GUI/computer-use control; judging craft (pacing, taste) from stills and transcripts; unbounded loops. Keep LLM output schema-validated and edit-scoped (patch ops on shot IDs) rather than regenerating the full timeline. (Schema-patch point is design inference.)
- Silent/dialog-driven footage suits transcript-led editing; B-roll/silent product Reels (typical for generative fill) lack a transcript layer, so a vision/shot-description layer (LAVE-style captions or embeddings) is needed.

### Gaps
- No Hacker News threads were found via search; no first-hand failure post-mortems from video-use. Failure modes above come from benchmark papers, not repo issue trackers.
- ExpressEdit, Etro-style "text-based editing" tools (Descript etc.), and commercial agentic editors not researched. LAVE's own limitations section not read.
- Whether HKUDS/VideoAgent is the arXiv 2606.23327 code is unverified.

## 3. Captions / ASR (word-level timestamps, styling)

### Takeaway
Cost is negligible (cents per hour of audio, a fraction of a cent per Reel). For word-level timestamps use ElevenLabs Scribe v2 (what video-use uses), AssemblyAI, or Deepgram via API, or faster-whisper/WhisperX self-hosted (both MIT/BSD and actively maintained).

### Cited Findings
- ElevenLabs Scribe v2: $0.22/hour (official API pricing page) — [ElevenLabs API pricing](https://elevenlabs.io/pricing/api). Realtime $0.39/h (secondary) — [comparison](https://www.web3aiblog.com/blog/speech-to-text-models-compared-whisper-deepgram-assemblyai-elevenlabs-2026).
- AssemblyAI about $0.15/h (Universal-2) to $0.21/h (Universal-3.x Pro) batch; Deepgram Nova-3 about $0.26-0.46/h batch depending on source; one July 2026 blog ranks Scribe v2 at 2.2% WER vs AssemblyAI 3.1% and Deepgram 5.2% (directional, not independent) — [secondary roundup 1](https://www.web3aiblog.com/blog/speech-to-text-models-compared-whisper-deepgram-assemblyai-elevenlabs-2026), [Soniox comparison](https://soniox.com/compare/stt/pricing), [costbench](https://costbench.com/compare/assemblyai-vs-deepgram).
- faster-whisper: 26.4k stars, MIT, last push 2026-10-31 — [GitHub API](https://api.github.com/repos/SYSTRAN/faster-whisper). WhisperX (forced-alignment word timestamps + diarization): 25.0k stars, BSD-2-Clause, last push 2026-10-22 — [GitHub API](https://api.github.com/repos/m-bain/whisperX).
- Gemini image/TTS/music pricing is on the same Gemini API page (see sections 4-5).

### Inferences
- 20 s of audio x $0.22/h = about $0.0012 per Reel via Scribe. Self-hosting only pays off at high volume or for data-residency reasons.
- Pairing ASR word times with the render timeline gives karaoke-style captions as Remotion/Revideo components or ASS subtitles burned by FFmpeg.

### Gaps
- Caption-styling libraries (e.g., ASS/libass presets, Remotion caption packages) not researched or sourced.
- Deepgram and AssemblyAI official pricing pages not fetched; Gemini as an ASR not researched.

## 4. TTS / voiceover

### Takeaway
Voiceover for a 20 s Reel costs about $0.002-0.02 on any current API; ElevenLabs is priciest per character but is the quality benchmark; Gemini TTS is cheapest but its low rate is promotional through 2026.

### Cited Findings
- ElevenLabs TTS per 1K chars: Flash/Turbo $0.04; Multilingual v2 and v3 $0.08; "Commercial use licensing on Starter+ plans" — [ElevenLabs API pricing](https://elevenlabs.io/pricing/api). (A secondary source quotes $50 / $100 per 1M chars, which is inconsistent with the official $0.04 / $0.08 per 1K.)
- Gemini TTS (Gemini API pricing page): `gemini-3.8-flash-tts` $0.50/M text-in and $9.00/M audio-out (25 audio tokens/s; about $0.00225 per 10 s); flash-lite-tts $6.00/M audio out; those 3.8 TTS prices hold through 2026-12-31 and double from 2027-01-01 — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).
- OpenAI gpt-4o-mini-tts about $0.015/min (secondary estimate); tts-1 $15/M chars, tts-1-hd $30/M chars — [Fast.io TTS comparison](https://fast.io/resources/best-ai-text-to-speech-tools-2026/).
- Cartesia Sonic: no clear per-character rate found; claimed 40-90 ms time-to-first-audio — [futureagi](https://futureagi.com/blog/elevenlabs-vs-cartesia-tts-2026/).

### Inferences
- 20 s of speech is about 300 characters: ElevenLabs Flash about $0.012, Multilingual about $0.024, Gemini 3.8 flash TTS about $0.0045 (500 tokens x $9/M), OpenAI about $0.005.

### Gaps
- OpenAI, Cartesia, Google Cloud TTS official prices not fetched; voice cloning/licensing terms not compared.

## 5. Music (beat detection, licensed libraries, AI music, platform constraints)

### Takeaway
Beat tracking libraries are free and maintained (Beat This, librosa; Essentia is AGPL). For IG-bound Reels the cleanest path is either a licensed API (Epidemic Sound) or attaching platform audio at publish time via Instagram's Audio API; AI music is now licensed-but-restricted (ElevenLabs Music, Lyria cheap; Suno/Udio constrained, no public Suno API reported).

### Cited Findings
**Beat/downbeat**
- Beat This (CPJKU, ISMIR 2024 model): 461 stars, MIT, last push 2026-05-28 — [GitHub API](https://api.github.com/repos/CPJKU/beat_this). librosa: 8.75k stars, ISC, last push 2026-10-06 — [GitHub API](https://api.github.com/repos/librosa/librosa). Essentia: 3.8k stars, AGPL-3.0, last push 2026-10-22 — [GitHub API](https://api.github.com/repos/MTG/essentia). madmom not checked.

**Licensed libraries**
- Epidemic Sound API: 55,000+ tracks and 250,000 SFX; self-serve free tier with instant API key for prototyping ("clear limits" unspecified), no contract/credit card; licensed globally and forever, sublicensing to end users supported; "Soundtrack API" reads video pacing/mood and syncs music; "Create versions" recuts track to a set length keeping builds/drops; safelisting with YouTube/Instagram/TikTok/Facebook/Twitch; production pricing not published — [Epidemic Sound developers](https://www.epidemicsound.com/business/developers/). Epidemic Sound is suing Meta (Reels Remix / Original Audio), case still active in 2026 with motions pending — [Courthouse News filing](https://www.courthousenews.com/wp-content/uploads/2026/07/reels-remix.pdf), [DMN 2022](https://www.digitalmusicnews.com/2022/07/22/epidemic-sound-meta-infringement-suit/).
- Instagram Audio API (Meta): search/retrieve original sounds and licensed music (no keyword = trending), and attach via `audio_configuration` (`audio_id`, audio volume 1-100, original-video volume) when creating a Reel container; only audio cleared for third-party use is returned (differs from in-app library); cannot preview before publishing; requires Business/Creator account linked to a Facebook Page, `instagram_basic` + `instagram_content_publish`, Facebook Login or Unified Login (not Instagram Login); ads mode returns royalty-free Sound Collection tracks, limited release — [Instagram Audio API docs](https://developers.facebook.com/documentation/instagram-platform/content-publishing/audio-api).

**AI music**
- Google Lyria via Gemini API: `lyria-3.5` full song $0.08; `lyria-3-clip-preview` 30 s clip $0.04; `lyria-3-pro-preview` $0.08 per song — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).
- ElevenLabs Music: $0.15/minute (official pricing page); commercial use on Starter+ plans — [ElevenLabs API pricing](https://elevenlabs.io/pricing/api). ElevenLabs says trained on licensed data; film/TV uses need Enterprise (secondary) — [ElevenLabs Music API](https://elevenlabs.io/music-api), [docs](https://elevenlabs.io/docs/overview/capabilities/music).
- Suno: v6 model family launched Sept 2026, built with Warner, BMG and Believe licensing, older models retired; Pro/Premier include commercial rights; free tier non-commercial; downloads metered (free 7 lifetime; Pro 20/month per one headline); sources disagree on whether any public API exists (one says none as of Apr 2026, enterprise only); Suno has not disclosed v6 training catalogues; distributors (Spotify/DistroKid/CD Baby) screen AI music separately — [TNW on v6](https://thenextweb.com/news/suno-v6-warner-bmg-believe-licensed-models), [MBW on download caps](https://www.musicbusinessworldwide.com/suno-limits-subscribers-downloads-per-month/), [Suno commercial rules](https://sunowatermark.com/suno-commercial-use-rules/), [Dubspot licensing](https://blog.dubspot.com/ai-music-licensing-explained-2026).
- Udio: settled with Universal (Oct 2025) and Warner (Nov 2025), moving to licensed walled-garden; downloads disabled after settlement (one blog's characterization) — [MBW Universal-Udio](https://www.musicbusinessworldwide.com/universal-music-settles-udio-lawsuit-strikes-deal-for-licensed-ai-music-platform), [Decrypt](https://decrypt.co/349360/warner-music-moves-from-litigation-to-licensing-with-udio). Sony had not settled with either (as of the cited coverage); Sony ruling not confirmed — [Dubspot lawsuits](https://blog.dubspot.com/suno-udio-ai-music-lawsuits-2026).

### Inferences
- Cheapest compliant background music for a 20 s clip: Lyria clip ($0.04) or ElevenLabs Music ($0.05 for 20 s). Epidemic API likely requires an existing paid subscription ("works with your existing subscription") for production — price not published.
- Beat-synced cuts: run Beat This or librosa on the chosen track, snap shot boundaries to nearest beat/downbeat in the timeline JSON. Beat This is the more accurate modern model, librosa the lighter dependency (accuracy claim from training knowledge, not sourced here).
- Instagram publish-time audio attach means you can ship a silent/voiceover-only render and let IG add trending licensed audio, but only for Business/Creator accounts and without preview, so beat-sync to it is impossible unless you also download/analyze the track (not documented as possible).
- Essentia AGPL-3.0 means network-service use triggers source-disclosure obligations; avoid in a closed SaaS without a commercial license (legal inference).

### Gaps
- Soundstripe, Artlist, Pixabay music API terms, and Meta Sound Collection download terms for third-party apps not researched. Stable Audio licensing not researched. Madmom status unchecked. Suno official pricing/API pages not retrieved.

## 6. Generative models for missing shots / backgrounds (video, image, consistency, reframing)

### Takeaway
Generative fill is feasible but costs 10-100x the entire deterministic stack: about $0.05-0.60 per generated second. Sora's API is gone, Veo 3.1 preview endpoints were shut down on 2026-10-22 and replaced by Gemini Omni Flash, and open weights top out at Wan 2.2. For "adapt this similar clip with AI," the most suitable current API is Gemini Omni Flash's video-edit/extend and subject/first-last-frame modes, with hard input limits.

### Cited Findings
**Google**
- Gemini Omni Flash (`gemini-omni-1.1-flash`): text-to-video with default audio, image-to-video (one image), first/last-frame, subject reference (multiple images), video editing (multi-turn via `previous_interaction_id` or uploaded video), video extension (appends 3-10 s, up to 40 s total, end-only); 9:16 supported; resolutions 360p, 720p default, 1080p/4K upscaled; uploaded input to edit/extend must be 10 s or less; video references up to 3 clips of up to 3 s each (audio ignored); editing/extending uploaded video unavailable in EEA/Switzerland/UK; recognizable people and minors restricted; SynthID watermark on all output; no negative prompts/temperature — [Gemini Omni docs](https://ai.google.dev/gemini-api/docs/omni), [video docs](https://ai.google.dev/gemini-api/docs/video).
- Veo 3.1 preview model IDs (`veo-3.1-generate-preview`, fast, lite) "were shut down on October 22, 2026"; recommended replacement is Gemini Omni Flash; GA Veo available via "Gemini Enterprise Agent Platform" — [Gemini API video docs](https://ai.google.dev/gemini-api/docs/video).
- Omni Flash priced $17.50 per 1M video output tokens, about $0.10/s of 720p video (standard) — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).
- Veo 3.1 per-second prices (aggregator dated 2026-10-13, i.e., before the preview shutdown; may no longer apply to Gemini API): standard $0.40/s (720p/1080p), $0.60/s 4K; Fast $0.10/$0.12/$0.30; Lite $0.05/$0.08 — [BenchLM](https://benchlm.ai/md/media-pricing/veo.md). Not verified on Google's page (current pricing page lacks Veo).
- Nano Banana / Gemini image (output per image, standard tier): `gemini-nano-banana-2.1` about $0.034 (1K); `gemini-3.1-flash-image` $0.067 (1K), $0.101 (2K); `gemini-3.1-flash-lite-image` $0.034 (1K); `gemini-3-pro-image` $0.134 (1K/2K), $0.24 (4K); `gemini-2.5-flash-image` $0.039, deprecated, shutdown 2027-03-15; batch about half price — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).

**Other video APIs (all SECONDARY, vendor pages not retrieved; treat as ranges)**
- Runway Gen-4.5 about $0.12/s (12 credits at $0.01), Gen-4 Turbo about $0.05/s — [Costbench Runway](https://costbench.com/software/ai-media-apis/runway-api/), [CometAPI](https://www.cometapi.com/ai-video-api-pricing/). One aggregator says about $0.25/s (uncorroborated).
- Kling 3.0 about $0.08-0.17/s at 720p-1080p (one source up to $0.42/s); credit guide: 6 credits/s 720p no audio, 12 credits/s 1080p with audio, 30 credits/s 4K — [Costbench Kling](https://costbench.com/software/ai-media-apis/kling-api/calculator/), [CloudZero](https://www.cloudzero.com/blog/kling-ai-pricing/).
- Seedance 2.0: sources conflict on whether BytePlus ModelArk offers it officially (one August 2026 source says yes, another says not yet); estimated Fast about $0.09/s, Pro about $0.25/s; supports 9:16, up to 9 image refs, 3 video clips, 3 audio files, reference videos total 15 s or less (provider-dependent) — [Anikuku guide](https://anikuku.com/blog/seedance-2-api-pricing-guide-2026), [Artlist help](https://help.artlist.io/hc/en-us/articles/37430797266973-Seedance-2-0-Family), [Runway help](https://help.runwayml.com/hc/en-us/articles/50488490233363).
- Luma Ray 3 about $0.10-0.30/s (one guide); Sora 2 about $0.15/s and Pro $0.70/s (secondary) — [CometAPI](https://www.cometapi.com/ai-video-api-pricing/).
- Sora: OpenAI announced discontinuation 2026-03-24; app closed 2026-04-26; Videos API shut down 2026-09-24; no successor named on OpenAI platform (as of Aug 2026) — [The Decoder](https://the-decoder.com/openai-sets-two-stage-sora-shutdown-with-app-closing-april-2026-and-api-following-in-september/), [Make.com notice](https://help.make.com/openai-sora-and-video-modules-deprecation-by-september-24-2026).

**Open weights**
- Wan 2.2: Apache-2.0, 18.3k stars, last push 2026-09-21; Wan 2.1: Apache-2.0, 17.4k stars, last push 2026-03-05 — [Wan2.2 API](https://api.github.com/repos/Wan-Video/Wan2.2), [Wan2.1 API](https://api.github.com/repos/Wan-Video/Wan2.1). Wan 2.5/2.6/(2.7) reportedly API-only; sources conflict on 2.7 — [Runpod](https://www.runpod.io/articles/guides/wan-2-7-runpod), [HowAIWorks](https://howaiworks.ai/blog/alibaba-wan-open-weights-stopped-at-2-2), [LocalAIMaster](https://localaimaster.com/blog/wan-2-7-open-source).
- LTX-Video: Apache-2.0, 11.3k stars, last push 2026-01-05 (about 10 months) — [GitHub API](https://api.github.com/repos/Lightricks/LTX-Video). black-forest-labs/flux repo: last push 2025-07-31 (STALE), Apache-2.0 on the repo — [GitHub API](https://api.github.com/repos/black-forest-labs/flux).

**Reframing / smart crop**
- MediaPipe: 37.5k stars, Apache-2.0, last push 2026-10-31 — [GitHub API](https://api.github.com/repos/google-ai-edge/mediapipe). google/automl (a different repo) is archived — [GitHub API](https://api.github.com/repos/google/automl).

### Inferences
- A realistic "generative fill" pattern: (1) generate a still with Nano Banana (about $0.03-0.07) conditioned on brand/product refs, (2) animate via image-to-video or Omni Flash first/last-frame for 3-5 s, (3) drop into the same timeline slot as a normal shot. For "adapt a similar clip" use Omni Flash video-edit on a 10 s-or-less source clip (not available in EEA/CH/UK), or Seedance/Kling reference-video modes via third-party providers.
- Because API clips are short (about 4-10 s), keep generative shots for B-roll/transition fillers, not full 20 s sequences; plan 2-3 retries per kept shot (aggregators note retries/rejects dominate real cost).
- Veo 3.1 prices cited by aggregators should not be used in budgeting until confirmed on Google's Enterprise Agent Platform pricing, since the Gemini API Veo preview endpoints were shut down.

### Gaps
- Not researched: Luma/Pika/Hailuo official pricing pages, FLUX Kontext licensing and API price, GPT-image pricing, Seedream, subject/face consistency tools, virtual try-on, relighting, video inpainting/outpainting models, quality benchmarks, and typical generation latency. Official Kling and Runway pricing pages were not retrieved.
- Google Cloud TTS and Gemini Enterprise Agent Platform Veo GA pricing not retrieved.
- AutoFlip's current location/maintenance status not verified (only the mediapipe repo activity is).

## 7. Transitions / effects (gl-transitions, speed ramps, stabilization, auto-reframe)

### Takeaway
Open tooling exists and is maintained (gl-transitions, Gyroflow, MediaPipe); FFmpeg's built-in xfade/vidstab cover deterministic needs but I did not source them in this session.

### Cited Findings
- gl-transitions: 2,219 stars, last push 2026-11-01; GitHub reports license as NOASSERTION (per-transition licenses; check individually) — [GitHub API](https://api.github.com/repos/gl-transitions/gl-transitions).
- Gyroflow (gyro-based stabilization): 9.7k stars, GPL-3.0, last push 2026-11-01 — [GitHub API](https://api.github.com/repos/gyroflow/gyroflow).
- Media3 Transformer supports custom effects via OpenGL (see section 1) — [Media3 Transformer](https://developer.android.com/media/media3/transformer).

### Inferences
- Gyroflow's GPL-3.0 and need for gyro metadata make it unsuitable for user-uploaded generic footage in a SaaS; FFmpeg vidstab (also GPL) is the more practical deterministic option (licensing inference).
- Beat-synced cuts and speed ramps are expressible as timeline-JSON fields (cut times snapped to beats, `speed` curves) executed by FFmpeg `setpts`/`xfade` or Remotion interpolation (design inference).

### Gaps
- FFmpeg xfade/vidstab documentation, speed-ramp implementations, OpenCV/MediaPipe face-aware auto-reframe quality, Google AutoFlip status not fetched.

## 8. Cost per finished 20-second Reel

### Takeaway
Deterministic stack: about $0.02-0.15 per Reel. Adding generative fill for 8 s of AI footage adds about $0.4-2.5 depending on model and retries, i.e., generation dominates cost by an order of magnitude.

### Cited Findings (inputs used; see sections 1-6 for sources)
- Render: Remotion Lambda $0.021/min; Shotstack 5-20 c/min; JSON2Video 1 credit/s; Creatomate about 14 credits/min at 720p.
- ASR: Scribe $0.22/h. TTS: ElevenLabs Flash $0.04/1K chars; Gemini 3.8 flash TTS $9/M audio tokens at 25 tokens/s. Music: ElevenLabs $0.15/min; Lyria clip $0.04, full song $0.08.
- Image: Nano Banana about $0.034-0.067. Video: Omni Flash about $0.10/s 720p; Veo 3.1 Fast (aggregator) $0.10-0.12/s; Kling about $0.08-0.17/s; Runway Gen-4.5 about $0.12/s.

### Inferences (arithmetic on the above; estimates, not quotes)
| Item | Deterministic-only | With generative fill (8 s of AI footage, 2 shots) |
|---|---|---|
| Render (20 s) | $0.007 (Remotion Lambda) to $0.07 (SaaS) | same |
| ASR on voiceover | about $0.001 | same |
| TTS (about 300 chars) | $0.005-0.024 | same |
| Music (20 s) | $0.04-0.05 (Lyria / ElevenLabs) or $0 (platform audio via IG Audio API) | same |
| Stock/user footage | $0 (user-supplied) | $0 |
| Image gen for stills | $0 | about $0.07-0.13 (2 stills) |
| Video gen | $0 | $0.8-1.0 at about $0.10-0.12/s x 8 s; x2-3 for retries = $1.6-3.0; ranges $0.64-1.4 at Kling-class rates per attempt |
| Total | about $0.05-0.15 | about $1-3 typical (up to about $5 with Veo-standard-class $0.40/s) |
- LLM planning/verification calls (not priced here) would add roughly cents per Reel; not sourced.
- Fixed costs not included: Remotion company license minimum ($100/month, secondary) if used and 4+ employees; Epidemic Sound subscription; ElevenLabs Starter+ plan.

### Gaps
- LLM token cost for the planning/self-eval loop not estimated. Egress/storage not estimated. Actual retry/accept rates for generated shots not found.
