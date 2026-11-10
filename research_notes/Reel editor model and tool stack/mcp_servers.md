# MCP Servers for an AI Reel/Short-Form Video Editing Agent (as of 2026-11-04)

Method note: ~25 tool calls (web search + fetch). Star counts from third-party directories are flagged as such. Tool schemas for Canva and Figma were read directly from the MCP servers connected in this research session (cited as "session tool schema"; no public URL). Most vendor docs for Canva/Adobe/Blackmagic were not directly fetchable; gaps are listed.

---

## 1. Video / FFmpeg MCP servers (including the existing mcp-video dependency)

### Takeaway
`mcp-video` has been renamed to **Kinocut**; the PyPI `mcp-video` 1.6.20 is now only a compatibility installer, and the active package is `kinocut` (1.16.5, 2026-10-27, Apache-2.0, 243 stars). The product should migrate its pin to `kinocut`. The official Remotion docs MCP was shut down 2026-10-26 (replaced by Agent Skills). Other FFmpeg MCPs are small community projects.

### Cited Findings
- PyPI `mcp-video` latest = 1.6.20 (2026-10-27), described as "Compatibility installer for Kinocut, formerly mcp-video"; says "mcp-video is now Kinocut"; tells new users to `pip install kinocut`; Apache-2.0; single maintainer listed as "puenteworks" — [PyPI mcp-video](https://pypi.org/project/mcp-video/)
- Kinocut repo (KyaniteLabs/kinocut, formerly KyaniteLabs/mcp-video): 243 stars, 50 forks, 1,676 commits, v1.16.5 published 2026-10-27, Apache-2.0; page calls 1.16.5 a "publication checkpoint" and says further releases are "TBD" (i.e. future maintenance cadence unclear) — [GitHub KyaniteLabs/kinocut](https://github.com/KyaniteLabs/mcp-video)
- Kinocut surface: 205 MCP tools / 177 CLI commands with `KINOCUT_TOOLS=all`; default registration is a curated 20-tool core. Categories: core video editing (32), analysis (8), AI-assisted media (11), Hyperframes (18), visual effects (8), procedural audio (7), layout and motion (6), transitions (3), governed AI-video (4), agent workflow engine (4), cinematic creation (4), Revideo (4), repurposing (2), discovery (1). Named tools: `video_shorts` (one-call shorts), `video_doctor`, `video_intent`, `video_review_run`/`video_review_decide`, `video_workflow_*`, `video_ingest`, `video_preflight`, `video_verdict`, `search_tools` — [GitHub Kinocut](https://github.com/KyaniteLabs/mcp-video)
- Transport: local stdio via `uvx --from kinocut kino --mcp`; also Python client (`from kinocut import Client`) and `kino` CLI. Requires FFmpeg on PATH; Hyperframes tools need Node.js 22+ — [GitHub Kinocut](https://github.com/KyaniteLabs/mcp-video)
- Kinocut security posture: typed tools with preflight before FFmpeg runs; "Video Receipts" record provenance/hashes; overwrites need explicit `overwrite=true`; AI-video approval has no bypass flag; telemetry for optional model calls and Revideo/Hyperframes defaults off; page states controls are "not a network sandbox"; unsigned MCPB desktop package labelled "user-configured-local-access" and "not a sandbox" — [GitHub Kinocut](https://github.com/KyaniteLabs/mcp-video)
- History: earlier releases (to at least 1.3.x) lived under pastorsimon1798/mcp-video; 1.2.2 notes said 83 tools. A search snapshot showed ~19 stars at the KyaniteLabs/mcp-video URL (older snapshot) — [PyPI 1.2.2 / ecosyste.ms](https://awesome.ecosyste.ms/projects/github.com%2Fkyanitelabs%2Fmcp-video)
- **Remotion**: hosted Remotion MCP (`remotion-documentation`) shut down 2026-10-26. Reasons given: data could lag docs, Remotion paid token costs, installs were hard and agents did not invoke it reliably, duplicated `/remotion-docs` skill. Migration: `npx remotion skills add` — [Remotion docs](https://remotion.dev/docs/ai/mcp). Community Remotion MCPs exist (e.g. mcp-use/remotion-mcp-app; "Remotion Video MCP" on LobeHub) but are not official — [search result listing](https://github.com/mcp-use/remotion-mcp-app)
- **HyperFrames (HeyGen)**: open-source HTML-to-MP4 framework (Apache-2.0), launched mid-April 2026, agent integration is via installable **skills**, not a confirmed dedicated MCP; Node 22+ and FFmpeg; one directory claims 29k+ stars (secondary source, unverified) — [themenonlab blog](https://themenonlab.blog/blog/heygen-hyperframes-video-as-code); [noqta.tn](https://www.noqta.tn/en/blog/heygen-hyperframes-html-to-mp4-ai-agent-video-2026). Kinocut bundles 18 Hyperframes tools and 4 Revideo tools (see above).
- Revideo / Motion Canvas dedicated MCP: no standalone official MCP found; only Kinocut's 4 Revideo tools (above).

### Inferences
- The product already depends on the correct lineage; just rename the dependency (`kinocut`) and re-test, since `mcp-video` 1.6.x will not get new features. Check import path/API compatibility before migrating (the compatibility installer claims to keep existing installs working).
- Using Kinocut's Python `Client` (not MCP) inside FastAPI avoids the MCP-protocol/prompt-injection surface in the render path; the MCP interface is better for the developer's Claude Code workflow or an interactive revise agent.
- 205 tools overall is far too many to put in a runtime agent's context; the default curated 20-tool core (or `search_tools`) is the right mode.
- Remotion/HyperFrames are alternative render engines (React/HTML) rather than FFmpeg drivers; relevant only if templates need rich animated text. Skills, not MCP, are the 2026 integration pattern for these.

### Gaps
- Kinocut last-commit date and current issue count not shown on fetched page. Independent security audit of Kinocut: none found.
- No verified standalone "video-edit-mcp" / "mcp-ffmpeg-helper" entries were evaluated; search surfaced only Kinocut. Treat other FFmpeg MCP variants as unvetted.
- Revideo/Motion Canvas MCP: nothing standalone found.

---

## 2. Pro editor bridges (Resolve, Premiere/AE, CapCut, Blender, Final Cut)

### Takeaway
Only DaVinci Resolve (samuelgursky) and Blender have large, active, well-adopted MCPs; both are desktop-app bridges unsuitable for a headless server render path. CapCut/JianYing (VectCutAPI) is the only way to emit editable CapCut drafts. Premiere/AE MCPs are small, experimental, community projects. No Final Cut MCP was found.

### Cited Findings
- **DaVinci Resolve MCP (samuelgursky/davinci-resolve-mcp)**: 3.9k stars, 452 forks, 1,206 commits, MIT, version badge 4.18.5; 37 compound tools (default) or 390 granular tools (`--full`); 136 guarded workflow actions; needs Resolve 18.5+ on macOS/Windows/Linux with external scripting enabled; Studio supports scripting directly, free edition only via an in-app bridge ("supported-until-it-is-not tier"); Resolve 21.1 moved Python scripting to Studio and free 21.1 support unconfirmed; default stdio with no network listener; opt-in networked transport is loopback-only with per-launch bearer token; destructive writes honour `destructive.safe_mode` and audit log; macOS validated directly, Windows/Linux from user reports — [GitHub](https://github.com/samuelgursky/davinci-resolve-mcp). Conflict: a third-party directory listed ~1.4k stars and v2.60.0 (2026-07-06) — [dev.co](https://dev.co/ai/mcp/davinci-resolve-mcp); the direct GitHub fetch (3.9k, 4.18.5) is more current. A second project, tooflex/davinci-resolve-mcp, also exists (no stats found) — [GitHub](https://github.com/tooflex/davinci-resolve-mcp)
- **Premiere Pro / After Effects**: community-only. Candidates: Aodaruma/adobe-mcp-rs (Rust; AE has 9 tools; Premiere path experimental, UXP bridge plus CEP fallback), leancoderkavy/premiere-pro-mcp, nepfaff/premiere-pro-mcp (runs arbitrary JavaScript against the Premiere UXP API; needs Premiere 25.3.0+ and UXP Developer Tool), morim3/mcp_adobe_premiere (few stars), mikechambers/adb-mcp (Node proxy to UXP plugin; Photoshop and Premiere), hetpatel-11/Adobe_Premiere_Pro_MCP (older CEP) — [search results incl. GitHub/LobeHub listings](https://github.com/Aodaruma/adobe-mcp-rs); [LobeHub nepfaff](https://lobehub.com/zh-TW/mcp/nepfaff-premiere-pro-mcp); [awesome.ecosyste.ms adb-mcp](https://awesome.ecosyste.ms/projects/github.com%2Fmikechambers%2Fadb-mcp). No dedicated standalone AE MCP repo surfaced. Adobe first-party Premiere/AE MCP: not found.
- **CapCut / JianYing — VectCutAPI (sun-guannan)**: HTTP REST API (default port 9001, `capcut_server.py`) plus MCP server (`mcp_server.py`, stdio); Python 3.10+, CapCut Intl or Jianying installed, FFmpeg; MCP tools: create_draft, add_video, add_audio, add_image, add_text, add_subtitle, add_effect, add_sticker, add_video_keyframe, get_video_duration, save_draft; output is a `dfd_`-prefixed draft folder the user copies into the CapCut/Jianying drafts dir. Wrappers (e.g. goransmoljanovic015-cell/capcut-mcp-server on Glama) require running the VectCutAPI backend separately — [VectCutAPI wiki](https://github.com/sun-guannan/VectCutAPI/wiki); [Glama wrapper](https://glama.ai/mcp/servers/goransmoljanovic015-cell/capcut-mcp-server)
- **Blender MCP (ahujasid)**: renamed "MCP for Blender" (repo `ahujasid/mcp-for-blender`); ~32.4-32.7k stars, ~2.9k forks (aggregator figures; one wiki says 32,730 as of 2026-10-30); NVD lists a remotely exploitable injection in `input_image_url` (`src/blender_mcp/server.py`), CVE-2026-10661; wiki says 3 CVE records published 2026-06-02, a Poly Haven path-traversal fix in 1.6.5 (July 2026), telemetry moved to opt-in 2026-07-21; a scanning-vendor Reddit post flagged prompt-injection/exfil risk (community opinion, not an audit) — [NVD CVE-2026-10661](https://nvd.nist.gov/vuln/detail/cve-2026-10661); [aiwiki](https://aiwiki.ai/wiki/blender_mcp/raw); [ecosyste.ms](https://awesome.ecosyste.ms/projects/github.com%2Fahujasid%2Fblender-mcp). Blender socket addon exposes arbitrary Python execution by design (general known property; not directly verified in fetched sources).
- Final Cut Pro MCP: no source found.

### Inferences
- Resolve MCP is useful only if you want a pro "export-to-NLE" path or Resolve-based finishing/color on a desktop machine; it is not a good fit for a server-side FastAPI renderer (needs a licensed GUI app, Studio for stable scripting).
- VectCutAPI is the only route to give users an editable CapCut project (a differentiator for "open in CapCut"), but it's a draft emitter with version-fragile draft formats; treat as optional export target, not core renderer.
- Blender is relevant only for 3D text/motion; for 9:16 kinetic captions, HTML/Remotion-style rendering is lighter. CVE history makes it a dev-machine-only tool.

### Gaps
- GitHub stars/last-commit for VectCutAPI and all Adobe-bridge repos not verified (search snippets only).
- Whether Adobe ships an official Premiere/AE MCP in late 2026: not found.
- Final Cut: nothing found.

---

## 3. Media AI MCPs

### Takeaway
Vendor-hosted remote MCPs (ElevenLabs, Replicate, Hugging Face, TwelveLabs) are the trustworthy options; ElevenLabs' old local server is archived. fal, Runway, Luma, Kling, Gemini-video, Whisper, and stock-media MCPs are all community projects of unverified maintenance; for production code, call those APIs directly via SDK rather than via MCP.

### Cited Findings
- **ElevenLabs**: local `elevenlabs/elevenlabs-mcp` repo (MIT, 1.5k stars, 263 forks, 79 commits) is archived/read-only and "deprecated in favor of ElevenLabs' hosted MCP server"; tools named on page include `speech_to_text`, `isolate_audio`, `speech_to_speech`, `video_to_music`, `upload_music_for_inpainting` (plus TTS etc.); had path-boundary control `ELEVENLABS_MCP_BASE_PATH` (default `~/Desktop`) — [GitHub](https://github.com/elevenlabs/elevenlabs-mcp). Official changelog (2026-08-22) confirms retirement of local server and hosted server at `https://api.elevenlabs.io/v1/mcp` with OAuth, no API key or local install — [ElevenLabs changelog (nl)](https://elevenlabs.io/docs/nl/changelog/2026/8/22.md). Conflict: a directory still lists v0.10.0 (2026-06-19) of the local server as latest — [dev.co](https://dev.co/ai/mcp/elevenlabs-mcp); this predates the archive notice.
- **TwelveLabs**: official hosted remote HTTP server (branded "Jockey" endpoint) at `https://mcp.twelvelabs.io/jockey/mcp`, OAuth sign-in; manages collections of media (create, add media from URL, list), search and Q&A over video; individual tool names and license not stated in docs; added via `claude mcp add --transport http` — [TwelveLabs docs](https://docs.twelvelabs.io/docs/advanced/model-context-protocol); [TwelveLabs blog](https://twelvelabs.io/blog/twelve-labs-mcp-server). Community variants: npm `twelvelabs-mcp` (19 tools per an MCP Seoul talk), Vinkius (~18 tools), MCPBundles — [MCP Seoul 2026](https://mcpseoul2026.sched.com/event/2PYdY).
- **Replicate**: official MCP server (hosted `https://mcp.replicate.com/sse` per one directory, or local `replicate-mcp` npm; OAuth or API key); registered in official MCP Registry; metadata at `https://replicate.com/.well-known/mcp/server.json`; `--tools` flag selects standard tools (`all`) vs code mode (`code`); docs at replicate.com/docs/reference/mcp — [Replicate changelog](https://replicate.com/changelog/2026-02-10-mcp-server-auto-discovery); [developersdigest](https://www.developersdigest.tech/mcp-servers/replicate). deepfates/mcp-replicate is a separate, older community experiment.
- **fal.ai**: no official model-calling MCP found. Official docs offer a hosted *documentation* MCP at `https://docs.fal.ai/mcp`. Community: PyPI `fal-mcp-server` (raveenb; image/video/music/audio generation), `fal-ai-mcp-server`, mcp.so @am0y server — [fal docs](https://docs.fal.ai/model-apis/mcp); [PyPI fal-mcp-server](https://pypi.org/project/fal-mcp-server/1.16.1/); [mcp.so](https://mcp.so/servers/mcp-fal?tab=config)
- **Hugging Face**: official hosted MCP at `hf.co/mcp` (token header or `?login` OAuth); built-in `hf_fs` Hub tool, docs search, Jobs; community MCP-compatible Gradio Spaces can be added as callable tools (incl. dynamic runtime discovery); open-source `huggingface/hf-mcp-server` runs locally via npx/Docker — [HF docs](https://huggingface.co/docs/hub/en/agents-mcp); [GitHub hf-mcp-server](https://github.com/huggingface/hf-mcp-server). Spaces-as-tools executes third-party code: dynamic discovery widens the attack surface.
- **Runway / Luma / Kling**: no official MCP from any of the three found. Community: `video-generation-mcp` npm (Runway, Pika, Luma, Kling via PiAPI, MiniMax; Luma via Replicate), wheattoast11/mcp-video-gen (Runway + Luma), a Runway Gen-4/Aleph server, Krea.ai MCP (aggregator of Flux/Hailuo/Runway/Kling) — [LobeHub search](https://lobehub.com/mcp?q=runway); [pkgstats](https://www.pkgstats.com/pkg:video-generation-mcp)
- **Gemini video**: community only — ugarchance/mcp-gemini-video-understanding (npm, public YouTube URLs) and moe5445/gemini-video-mcp-server (Python; `analyze_youtube_video`, local files; default model "gemini-3-pro-preview", fps 10; free tier 8h/day of YouTube) — [LobeHub ugarchance](https://lobehub.com/mcp/ugarchance-mcp-gemini-video-understanding); [LobeHub moe5445](https://lobehub.com/bg/mcp/moe5445-gemini-video-mcp-server). No official Google video MCP found.
- **Whisper / transcription**: ramedina-ia/faster-whisper-mcp (local, MIT, faster-whisper + yt-dlp, word timestamps, SRT/VTT); bis-code groq-whisper-mcp (`transcribe_video`, word-level timestamps, paid Groq) — [Glama](https://glama.ai/mcp/servers/ramedina-ia/faster-whisper-mcp/tree); faster-whisper `word_timestamps=True` and WhisperX (alignment+diarization) are the underlying libraries — [mcp.directory/search summary](https://mcp.directory/skills/whisper-transcription)
- **Stock media**: Pexels MCPs: codeChap/mcp-server-pexels (Rust, stdio; search_videos, popular_videos, get_video, collections), developer-ishan/mcp-pexels (Node; free tier 200 req/hr, 20k/month), garylab/pexels-mcp-server (Python); jeanpfs/stock-images-mcp covers Pexels/Unsplash/Pixabay but appears photo-focused (video support unconfirmed). No dedicated Pixabay-only MCP; no Storyblocks MCP found in results — [GitHub codechap](https://github.com/codechap/mcp-server-pexels); [GitHub developer-ishan](https://github.com/developer-ishan/mcp-pexels); [GitHub garylab](https://github.com/garylab/pexels-mcp-server); [LobeHub jeanpfs](https://lobehub.com/mcp/jeanpfs-stock-images-mcp)
- **Music MCPs**: ElevenLabs hosted MCP (video_to_music etc. on the legacy server). No dedicated music-library (Epidemic/Artlist/Suno) MCP evaluated.

### Inferences
- For a runtime agent, a Python backend is better off calling fal/Replicate/ElevenLabs/Whisper via their SDKs; MCP adds token overhead (Remotion explicitly cited unreliable agent invocation and token cost as reasons to drop theirs). MCP adds value mainly for the developer's Claude Code to try models quickly (Replicate official, HF official, ElevenLabs hosted).
- Replicate's official MCP is the best single "access to many models" bridge (bg removal, upscaling, video gen) for dev exploration, given official status and registry listing.
- TwelveLabs MCP fits the "analyze reference Reel / search user clips" step, but it is a hosted indexing service (uploads media; cost and data-retention need review).

### Gaps
- Star counts / last commits for all community media MCPs not verified.
- TwelveLabs MCP license and exact tool list not published on fetched page.
- Replicate official tool names not listed on fetched changelog; hosted URL (SSE vs streamable HTTP) from a third-party directory only.
- ElevenLabs hosted-server tool list not fetched (docs returned 403).
- Storyblocks, Pixabay video, Suno/music-library MCPs: nothing found.

---

## 4. Social platform MCPs (download / publish / analytics) and ToS risk

### Takeaway
No single reputable server covers download+publish+analytics for IG/TikTok/YouTube. Available ones are small, unvalidated community projects or depend on paid third-party scrapers. Reference-Reel downloading in particular carries ToS/copyright risk and is better done via user upload.

### Cited Findings
- BilalTariq01/instagram-analytics-mcp: TypeScript, read-only, Instagram Graph API; unvalidated listing; Graph API limit 200 calls/hr per user token — [LobeHub](https://lobehub.com/mcp/bilaltariq01-instagram-analytics-mcp?activeTab=deployment)
- handoing/ig-download-mcp-server: single-tool Instagram video downloader (Node) — [Glama](https://glama.ai/mcp/servers/handoing/ig-download-mcp-server?locale=zh-CN)
- lupikovoleg/instagram-cli: Python analytics/download/MCP tools, appears to depend on paid HikerAPI — [LobeHub](https://lobehub.com/mcp/lupikovoleg-instagram-cli)
- @andrewlwn77/social-media-mcp: npm multi-platform downloader requiring a RapidAPI key — [pkgstats](https://www.pkgstats.com/pkg:@andrewlwn77/social-media-mcp)
- tokportal/tokportal-mcp: 91 tools for TikTok/IG/YouTube managed accounts, MIT, needs TokPortal credentials, listing showed 0 GitHub stars — [Enterprise DNA](https://enterprisedna.co/directories/mcp/tokportal-tokportal-mcp)
- QPost MCP: publish video/images to YouTube, TikTok, Instagram (hosted service) — [search result](https://enterprisedna.co/directories/mcp/tokportal-tokportal-mcp) (same results page; vendor not independently checked)
- Official platform paths (not MCP): Instagram Graph API and YouTube Data API are the sanctioned publish/analytics routes (general knowledge; not fetched this session).

### Inferences
- ToS: Downloaders for IG/TikTok generally rely on scraping or third-party scraper APIs (RapidAPI, HikerAPI), which typically violate platform terms and raise copyright issues if the downloaded reel is reused; the product should accept user-uploaded reference files or official-API/oEmbed metadata only. (Inference; ToS text not fetched.)
- Publishing MCPs would give a hosted third party OAuth tokens for user social accounts; high blast radius. Prefer official Graph/YouTube APIs inside the backend.

### Gaps
- No maintenance/last-commit verification for any of these; ToS text for Instagram/TikTok/YouTube not fetched.
- No official TikTok/Instagram/YouTube-owned MCP found.

---

## 5. Canva MCP and Figma MCP: can they produce or import reel templates?

### Takeaway
Both are connected hosted official servers. Canva's `create-video` is **generative AI video** (Seedance engine, 5-30 s, 9:16 or 16:9, consumes the user's AI limit), not a timeline/template editor; Canva can export designs as MP4 and has brand templates/autofill. Figma can read motion timelines (`get_motion_context`) and render a timeline node to MP4 (`export_video`); neither can ingest an existing Reel into an editable template.

### Cited Findings (all from the session's connected servers' tool schemas; no public URL)
- Canva `create-video`: "Produces a Canva video from a complete production specification"; requires a prior `get-video-production-guide` (guides for try-ons, unboxings, product demos, comparisons, showcases, ads); output engine enum = `seedance`, aspect 9:16 or 16:9, duration 5-30 s, resolution 480p/720p; storyboard up to 12 shots; needs explicit user approval each time and warns it may use a large part of the monthly "AI limit"; reference images are Canva asset IDs or generated; uploaded audio and real-person voice cloning unsupported; returns a job_id to poll — [session tool schema: mcp__claude_ai_Canva__create-video / get-video-production-guide]
- Canva `export-design`: export formats include pdf, png, jpg, gif, pptx, **mp4**, csv; MP4 requires a `quality` like `horizontal_1080p`; returns a download URL — [session tool schema: export-design]
- Canva `import-design-from-url`: converts a public HTTPS PDF/PPT/Word/Excel/webpage/HTML/Photoshop/Illustrator into a Canva design; `intended_design_type` enum includes `instagram_reel`, `mobile_video`, `video`, `your_story`; not for local/private files — [session tool schema: import-design-from-url]
- Canva also exposes brand-template tools: `create-design-from-brand-template`, `search-brand-templates`, `get-brand-template-dataset`, `create-brand-template-draft`, `publish-brand-template`, plus `resize-design`, `remove-background`, `generate-image`, `edit-design`, `import-claude-motion-from-url` (imports a Claude Motion MP4 into Canva) — [session tool list / schemas]
- Third-party docs for older/other Canva MCP integrations describe ~10-25 tools, template autofill needing Canva Enterprise (Workato), and MP4 export via export (Dust); none documented `create-video` — conflicting with the live schema, which shows it exists (tool lists are version-dependent) — [Workato](https://docs.workato.com/en/mcp/prebuilt-mcps/canva-mcp-server); [Dust](https://docs.dust.tt/docs/user-documentation/agents/tools/canva)
- Figma `export_video`: renders a top-level timeline frame to **MP4 only** (no GIF/animated SVG), server-side, returns presigned URL, async via jobId; fps 5-60; quality low/medium/high; constraint SCALE/WIDTH/HEIGHT up to 4096 px/dimension; TTL 30 s to 7 days; Slides slide also valid — [session tool schema: Figma export_video]
- Figma `get_motion_context`: keyframe tracks with easing, animated-node inventory, pre-computed CSS @keyframes and motion.dev snippets, `recursive` up to 500 nodes — [session tool schema: get_motion_context]; independent confirmation via Figma's implement-motion skill — [mcpservers.org](https://mcpservers.org/agent-skills/figma/mcp-server-guide/figma-implement-motion)
- HyperFrames' Figma skill uses `export_video` as fallback to bake untranslatable tracks (shader-driven, unsupported props, complex masks) into an MP4 clip; notes Figma's export flattens shaders to base colour — [Skillselion/HyperFrames figma skill](https://skillselion.com/skills/heygen-com/hyperframes/figma)
- Figma also exposes shader tools (`create_shader`, `get_shader`...) and `use_figma`, `generate_image`, `html_to_figma` — [session tool list]

### Inferences
- Reel template creation path with these MCPs: Figma motion (`get_motion_context` JSON of keyframes/easing/timing) is the closest thing to a machine-readable motion template that could map onto the product's template schema; Canva brand templates are static-ish layout data and their autofill route is gated (possibly Enterprise).
- Canva `create-video` cannot recreate a reference Reel or edit user footage; it generates new AI video from a spec. Useful only as a generative B-roll/filler source (quality, cost to user's AI limit).
- Neither tool analyzes an existing Reel into a template; that stays the product's own pipeline (scene detection, transcript, motion analysis).

### Gaps
- Canva autofill tool in this server (`autofill-design` is referenced but not confirmed present) and plan gating not verified.
- Whether Canva MP4 export is allowed/quality-limited by plan: not verified.
- Figma public docs for `export_video` not found; behaviour taken from tool schema.

---

## 6. Dev-workflow MCPs (brief)

### Takeaway
Playwright MCP (Microsoft), Chrome DevTools MCP (Google/ChromeDevTools) and Context7 (Upstash) are the main de-facto standards; the developer already has Chrome connected.

### Cited Findings
- Chrome DevTools MCP ~51.1k stars; Playwright MCP (Microsoft) ~36.8k (Devtk lists 32k+); Context7 (Upstash) ~54.7k — all third-party directory figures, conflicting/approximate — [Skillselion compare](https://skillselion.com/compare/mcp/ship/io.github.microsoft/playwright-mcp/vs/io.github.ChromeDevTools/chrome-devtools-mcp); [devtk.ai](https://devtk.ai/en/directory/mcp-servers/playwright/)
- Playwright MCP: Apache-2.0 (per directories), accessibility-snapshot-based (`browser_snapshot`) by default with optional vision mode; allowed/blocked origin flags are not a security boundary and do not apply to redirects — [ecosyste.ms](https://awesome.ecosyste.ms/projects/github.com%2Fmicrosoft%2Fplaywright-mcp); [github.com/mcp listing](https://github.com/mcp/microsoft/playwright-mcp)
- Context7: up-to-date version-specific library docs for coding agents (FFmpeg-python/FastAPI/React docs lookup) — [devtk.ai](https://devtk.ai/en/directory/mcp-servers/playwright/)
- SQLite MCP: not researched in this session.

### Inferences
- For a React review/editor UI: Playwright MCP for E2E flows (upload clip, chat revise, preview); Chrome DevTools MCP for performance/network/console debugging of video preview. The Claude-in-Chrome MCP already connected overlaps with these. Context7 helps with FFmpeg/FastAPI/React API accuracy. Rendered video verification still needs ffprobe/frame sampling in the product's own tests.

### Gaps
- Official repo star counts, last-commit dates, SQLite MCP status not verified.

---

## 7. Security: prompt injection and supply chain

### Takeaway
Community MCP servers are an inventory-able supply chain with documented real incidents (malicious Postmark clone, tool poisoning, CVEs in Blender MCP). Trust vendor-hosted official servers first; pin versions, run local servers without broad filesystem/network access, and never put untrusted servers on a path that handles user-uploaded media or social tokens.

### Cited Findings
- Malicious npm package impersonating Postmark MCP added a line in v1.0.16 that BCC'd outgoing email to an external address (reported September 2025; download counts vary 1,500/week to 1,643 total; Postmark disavowed it); one blog dates a fake Postmark server to January 2026 — unverified/conflicting — [dev.to state of MCP security](https://dev.to/luckypipewrench/the-state-of-mcp-security-2026-incidents-attack-patterns-and-defense-coverage-2h45); [HackerNoon](https://hackernoon.com/lite/mcp-servers-are-a-supply-chain-you-have-not-inventoried-yet); [toolradar](https://toolradar.com/blog/mcp-server-security-best-practices)
- Tool poisoning (hidden instructions in tool descriptions/schemas/outputs; Invariant Labs, April 2025), GitHub MCP issue-injection data leak (May 2025), "rug pull" description changes after approval — [glasp.ai](https://glasp.ai/articles/mcp-security-tool-poisoning-supply-chain); [dev.to](https://dev.to/luckypipewrench/the-state-of-mcp-security-2026-incidents-attack-patterns-and-defense-coverage-2h45)
- Mitigations recommended: hash-pin approved tool definitions, scan descriptions, avoid auto-approval for untrusted servers, verify provenance, monitor outbound traffic; a free-scanner test caught injected text but missed the BCC line — [devtoollab](https://devtoollab.com/blog/best-mcp-security-tools). Another source counts "30 CVEs in 60 days" in early 2026 (unverified blog) — [heyuan110](https://heyuan110.com/posts/ai/2026-03-10-mcp-security-2026)
- Blender MCP CVE record (injection via `input_image_url`) — [NVD](https://nvd.nist.gov/vuln/detail/cve-2026-10661)
- Resolve MCP: stdio default, loopback-only token-gated network mode, safe_mode and audit log — a good local-bridge security design — [GitHub](https://github.com/samuelgursky/davinci-resolve-mcp)
- Kinocut states its controls are not a network sandbox — [GitHub](https://github.com/KyaniteLabs/mcp-video)
- Replicate states the MCP Registry stores metadata only, not code, backed by Anthropic, GitHub, Microsoft (registry listing is not a code audit) — [Replicate changelog](https://replicate.com/changelog/2026-02-10-mcp-server-auto-discovery)

### Inferences
- Product-specific injection vectors: reference Reel/user clips supply text via captions, OCR, transcripts, filenames, metadata (ID3/EXIF), and downloaded page content; those flow into the agent's context and can contain instructions. Treat all media-derived text as untrusted data, keep tool allow-lists per step, and require confirmation for destructive/outbound actions.
- Trust tiers: (1) vendor-hosted official (ElevenLabs, Replicate, HF, TwelveLabs, Canva, Figma, Playwright/Microsoft, Chrome DevTools, Context7); (2) maintained open source with transparent security design (Kinocut, Resolve MCP) after pinning; (3) single-maintainer low-star listings (social scrapers, Pexels clones, Gemini-video, Runway/Luma/Kling wrappers, Adobe bridges): sandbox or avoid.

### Gaps
- Primary-source incident reports (Koi Security, Snyk, Invariant) were not fetched; blog accounts conflict on dates/counts.
- No independent audit of Kinocut, Resolve MCP, or any community MCP found.

---

## 8. Recommendation (shortlist)

### Takeaway
Runtime: keep FFmpeg via Kinocut (library/CLI, migrate off the `mcp-video` name), call media AI via SDKs; use MCP only for official hosted vendors if at all. Dev: Replicate/HF/ElevenLabs hosted MCPs for model exploration, Playwright + Chrome DevTools + Context7 for build/test. Avoid community social scrapers/publishers and unvetted video-gen wrappers.

### Cited Findings
(See sections above for sources.)

### Inferences
**Adopt - runtime (product agent)**
1. Kinocut (`pip install kinocut`; Python `Client`, or stdio MCP with the default 20-tool core) - replace `mcp-video` 1.6.x pin; verify API compatibility; pin version; set FFmpeg path; leave telemetry off; use preflight/`video_verdict`-style verification for the verify step.
2. ElevenLabs hosted MCP or SDK (speech-to-text with timestamps, audio isolation, TTS/music) - official, OAuth. For a backend, use the SDK with an API key instead.
3. TwelveLabs (SDK or hosted MCP) - optional, for reference-Reel analysis and clip search/matching; check data retention and cost.
4. Replicate / fal via SDK (not MCP) for background removal, upscaling, video gen; Whisper (faster-whisper/WhisperX library, not an MCP wrapper) for local word-level transcripts.

**Adopt - developer workflow (Claude Code)**
- Replicate official MCP, Hugging Face hosted MCP, ElevenLabs hosted MCP (model trials); Playwright MCP + Chrome DevTools MCP (UI tests/perf; already have Chrome); Context7 (docs); Figma MCP `get_motion_context`/`export_video` and Canva MCP (templates, brand assets, design references; Canva `create-video` only for generated B-roll experiments with user's AI limit in mind); Remotion Agent Skills (`npx remotion skills add`) and HyperFrames skills if exploring HTML/React rendering.

**Optional / situational**
- VectCutAPI (CapCut draft export), Resolve MCP (pro finishing on a dev machine), Pexels MCP (dev; use Pexels API directly in prod), Blender MCP (dev-only, patched version, isolated).

**Avoid / treat as untrusted**
- Social downloaders/publishers (ToS and credential risk), unofficial Runway/Luma/Kling multi-provider wrappers, small Adobe UXP bridges that execute arbitrary JS, the archived local `elevenlabs-mcp`, the shut-down Remotion docs MCP, community fal wrappers in production, any Blender MCP version before the CVE fixes, and Spaces-as-tools "dynamic discovery" on Hugging Face in an agent that touches user data.

### Gaps
- Costs, rate limits and data-retention terms per vendor not compared.
- No benchmark of agent reliability across tool counts; the Remotion shutdown rationale suggests MCP invocation reliability is a real concern but is one vendor's statement.
