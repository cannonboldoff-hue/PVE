# Editing engines, interchange formats, FFmpeg ceiling, reframing and template representation for an AI Reel template editor (as of 2026-11-04)

Evidence note: GitHub stats come from api.github.com queried 2026-11-04 (primary). "Stale" = no push in 12+ months. Items marked "(training knowledge)" are not sourced in this session and the writer should treat them as lower confidence. Overlap with the earlier file (rendering_and_generation_tools.md: Remotion Lambda cost, SaaS render API prices, Editly/Revideo/MoviePy/Etro/Diffusion Studio stats, auto-editor, MediaPipe, gl-transitions stats) is not repeated except where it changes a conclusion.

## 1. Code-driven renderers: which is best for animated text, keyframed motion, transitions?

### Takeaway
Two things changed vs the earlier note. (1) HyperFrames (HeyGen, Apache-2.0, HTML/CSS/GSAP rendered by headless Chrome + FFmpeg, 78.8k stars, pushed today) is a license-clean Remotion-style engine and Kinocut already ships a Hyperframes tool set. (2) Remotion's company license is now confirmed from the primary FAQ ($100/month minimum for companies with 4+ people). For animated captions, keyframed motion and shader transitions the browser-rendering family (HyperFrames, Remotion) clearly beats FFmpeg-only and MoviePy; Revideo/Motion Canvas are better for explainer-style procedural animation than for video-clip templating.

### Cited Findings
**Repo vitals (GitHub API, 2026-11-04)**
- Remotion: 70,692 stars, license NOASSERTION (custom), pushed 2026-11-04 — [API](https://api.github.com/repos/remotion-dev/remotion)
- HyperFrames (heygen-com): 78,792 stars, Apache-2.0, pushed 2026-11-04 — [API](https://api.github.com/repos/heygen-com/hyperframes)
- Motion Canvas: 19,688 stars, MIT, pushed 2026-07-02 — [API](https://api.github.com/repos/motion-canvas/motion-canvas)
- Revideo (midrender): 4,176 stars, MIT, pushed 2026-07-15 — [API](https://api.github.com/repos/midrender/revideo)
- MoviePy: 15,109 stars, MIT, GitHub push 2026-08-26, but latest PyPI release is 2.2.1 uploaded 2025-05-21 — [API](https://api.github.com/repos/Zulko/moviepy), [PyPI](https://pypi.org/pypi/moviepy/json)
- Editly: 5,579 stars, MIT, last push 2025-05-12 (STALE ~18 months) — [API](https://api.github.com/repos/mifi/editly)
- FFCreator (tnfe): 3,164 stars, MIT, last push 2024-12-19 (STALE ~23 months) — [API](https://api.github.com/repos/tnfe/FFCreator)
- VidPy (antiboredom; Python wrapper over melt): 132 stars, GPL-3.0, last push 2023-10-12 (STALE, effectively dead) — [API](https://api.github.com/repos/antiboredom/vidpy)
- Etro: 1,154 stars, GPL-3.0, pushed 2026-10-24 — [API](https://api.github.com/repos/etro-js/etro)
- Diffusion Studio core: 1,252 stars, MPL-2.0, last push 2025-11-18 (borderline stale) — [API](https://api.github.com/repos/diffusionstudio/core)
- Twick (React video-editor SDK): 546 stars, license NOASSERTION, pushed 2026-06-04 — [API](https://api.github.com/repos/ncounterspecialist/twick)
- The twickdev, ffcreator and vidpy org-slug guesses returned 404; the correct slugs are those listed above.

**HyperFrames (new, most relevant)**
- Composition is an HTML file; timing via data attributes (`data-start`, `data-duration`, `data-track-index`); animation via GSAP, CSS animations, Lottie, Three.js, Anime.js, WAAPI or a custom frame adapter; no React, no bundler; renderer seeks each frame in headless Chrome (Puppeteer) and encodes with FFmpeg; runs locally, in Docker or on AWS Lambda; catalog has reusable blocks for transitions, overlays, captions, charts, maps incl. WebGL shader transitions (`@hyperframes/shader-transitions`); states "same input, same frames, same output"; Node 22+ and FFmpeg required; Apache-2.0 with no per-render fees; used in production at HeyGen; README admits Remotion Lambda is the more mature cloud renderer; Windows desktop app offered but CLI-on-Windows not explicitly confirmed; no benchmarks or Python integration documented — [HyperFrames README](https://github.com/heygen-com/hyperframes)

**Remotion**
- Primary license FAQ: free for individuals, teams of up to 3 people, eligible non-profits and evaluators; headcount is total company headcount (a 20-person company with one Remotion user still needs a license). Creators plan $25/month per person who writes Remotion code (including via agentic coding tools). Automators plan $0.01 per successful render with $100/month minimum (applies to automated pipelines, prompt-to-video tools, SaaS render APIs, Player embeds). Enterprise has $500 minimum. If both plans are active, $100/month minimum. Letting users generate personalized videos from your template is allowed; letting users upload their own Remotion projects for rendering is not. Remotion 5.0 will make render telemetry mandatory for Automators customers (monthly verifiable render report otherwise); the server-side renderer has no automatic telemetry today — [Remotion license FAQ](https://www.remotion.dev/docs/license/faq)
- This confirms the previously secondary-only figures ($0.01/render, $100/month minimum). A pkgpulse article claims tiers by ARR ($0 / $50 / $200 per month) which contradicts the primary FAQ and also says "21K+ stars" (actual 70.7k); treat that article as unreliable — [pkgpulse](https://www.pkgpulse.com/guides/remotion-vs-motion-canvas-vs-revideo-programmatic-video-2026)
- Animation model: frame-based declarative React (`interpolate`, `spring`, `useCurrentFrame`, `Sequence`/`Series`); any CSS/SVG/web font text; no built-in transition API shown in that article (Remotion has a separate `@remotion/transitions` package, training knowledge) — [pkgpulse](https://www.pkgpulse.com/guides/remotion-vs-motion-canvas-vs-revideo-programmatic-video-2026)
- Remotion client-side rendering (`@remotion/web-renderer`, `renderMediaOnWeb`) is experimental alpha, encodes via WebCodecs with Mediabunny, needs Chrome 94+/Firefox 130+/Safari 26+, supports fewer codecs than Lambda (no ProRes), expect breaking changes; Remotion deprecated Media Parser (2026-02-01) and sponsors Mediabunny at $1000/month — [Remotion client-side rendering docs](https://remotion.dev/docs/client-side-rendering/), [search summary](https://www.remotion.dev/docs/web-renderer/)

**Motion Canvas / Revideo**
- Motion Canvas: generator-function (`yield*`) tweens on canvas nodes, MIT; Revideo forks it, adds headless rendering/audio/library-first API (hosted business at re.video); `Txt` node has no arbitrary HTML/CSS; neither has a transition API (hand-built from tweens); no caption feature — [pkgpulse](https://www.pkgpulse.com/guides/remotion-vs-motion-canvas-vs-revideo-programmatic-video-2026) (generic article; claims about speed unevidenced). Some blogs wrongly say Revideo forks Remotion; most sources say Motion Canvas — [search summary](https://www.remotion.dev/docs/compare/motion-canvas)

**MoviePy 2.x**
- v2.0 had major breaking changes; Python 3.9+; Windows/macOS/Linux; README says it is "slower than using ffmpeg directly due to heavier data import/export operations" because frames go through numpy — [MoviePy README](https://github.com/Zulko/moviepy)

**WebCodecs tools**
- Mediabunny: JS library for read/write/convert media in browser via WebCodecs (transmux, transcode, resize, rotate, trim); benchmarks are vendor-reported — [Mediabunny](https://mediabunny.dev/guide/introduction), [GitHub](https://github.com/Vanilagy/mediabunny)
- Diffusion Studio v3 removed FFmpeg and runs on WebCodecs in browser (see earlier note); WebCodecs tools require a browser runtime (headless Chrome w/ GPU for server use), so offer no server-render advantage over HyperFrames/Remotion for a Python backend.

**Shotstack-like JSON-to-video (schema reference)**
- Shotstack Edit JSON docs include: Rich Text (animated text with gradients, shadows, effects), Rich Captions (word-level animations, karaoke, generated from audio/video clip via `alias://`), Aliases, Animations, Merge fields, Templates, positioning/offset/fit/scale, SVG and HTML5 assets, chromakey and luma mattes; OpenAPI spec at `https://shotstack.io/docs/api/api.edit.json` — [Shotstack docs index](https://shotstack.io/docs/guide/llms.txt). Transition/effect/keyframe details not retrieved. Shotstack and JSON2Video are hosted APIs (not self-hostable engines; prices in the earlier file).

### Inferences
- Ranking for "animated text + keyframed motion + transitions" fidelity (design judgement): HyperFrames ≈ Remotion (full CSS/SVG/GSAP/Lottie/shader power, browser text rendering matches what designers see) > Revideo/Motion Canvas (procedural, good for vector-style but weak for clip-based templates) > FFmpeg+libass (strong for caption styling and basic zoom, weak for per-word spring animations and arbitrary easing) > MoviePy (numpy frame pipeline, slow, text via Pillow, no real easing/keyframe system; training knowledge on Pillow).
- Python/Windows integration: both HyperFrames and Remotion are Node processes. From FastAPI call them as subprocess/CLI with a JSON props file. Windows works for Node+Chrome in general but only the HyperFrames Windows desktop app is explicitly documented; test CLI on Windows. Kinocut already wraps Hyperframes (Node 22+), so the integration path partly exists.
- License: HyperFrames (Apache-2.0) avoids Remotion's $100/month floor and the Remotion 5.0 mandatory telemetry for Automators. For a multi-person company running a Reel SaaS the license is the main reason to prefer HyperFrames. A solo/≤3-person team can use Remotion free, but the threshold will be crossed on hiring.
- Editly (stale, JSON spec) and FFCreator (stale, Node/FFmpeg+canvas), VidPy (dead, GPL), Etro (GPL, browser) should not be adopted; Twick/Diffusion Studio are editor UIs/browser engines, not server renderers.
- Because HyperFrames is Chrome-based, video decode inside the page (many video layers at 1080x1920) is the cost driver; both HyperFrames and Remotion docs warn about or omit data here (the earlier note says embedded videos raise Remotion Lambda cost significantly). Hybrid approach: pre-render the video track with FFmpeg and use the browser engine only for transparent overlays (captions/stickers/shapes), then composite with FFmpeg (design inference).

### Gaps
- No independent benchmark of HyperFrames vs Remotion render time for 1080x1920 with video layers; HyperFrames Windows CLI, release cadence/version numbers and GPU use not confirmed.
- Remotion `@remotion/transitions` and caption packages not fetched.
- Shotstack transition/effect/keyframe JSON details not retrieved; JSON2Video schema not retrieved; Creatomate template JSON not retrieved.
- Revideo/Motion Canvas headless-render quality and speed unverified (only generic blog).

## 2. Timeline/interchange formats: OTIO, MLT, GES, Olive, Kdenlive/Shotcut, CapCut drafts

### Takeaway
OTIO is the right neutral cut/transition skeleton but is cut-level only (no text animation, keyframes, color grade); MLT XML is the only open format that natively holds filters, keyframes, transitions and renders headlessly, but integrating melt from Python on Windows is awkward. CapCut/Jianying draft JSON is the closest "viral template" native format and can be generated programmatically (pyJianYingDraft, VectCutAPI), with real version-compatibility limits.

### Cited Findings
- OpenTimelineIO: 2,056 stars, Apache-2.0, pushed 2026-10-31; PyPI version 0.18.1 (2025-11-09) — [API](https://api.github.com/repos/AcademySoftwareFoundation/OpenTimelineIO), [PyPI](https://pypi.org/pypi/OpenTimelineIO/json)
- OTIO core ships only native formats (`.otio` JSON, `.otiod`, `.otioz`); FCP XML, AAF, CMX3600 EDL etc. come from the separate OpenTimelineIO-Plugins package maintained at varying levels by the community; adapters are Python plugins. A (v0.16.0) feature matrix shows EDL lacks multiple video tracks/nesting and FCP7 XML and FCP X lack transitions; Premiere interchange is via FCP7 XML (older wiki); CMX3600 adapter carries ASC_CDL color metadata; no Resolve-specific adapter found — [OTIO adapter docs](https://opentimelineio.readthedocs.io/en/latest/tutorials/adapters.html), [v0.16 feature matrix](https://github.com/AcademySoftwareFoundation/OpenTimelineIO/blob/v0.16.0/docs/tutorials/feature-matrix.rst)
- MLT: 1,870 stars, LGPL-2.1, pushed 2026-10-29. Shotcut 15,597 stars GPL-3.0 pushed 2026-11-04; Kdenlive 6,046 stars GPL-3.0 pushed 2026-11-04 — [MLT API](https://api.github.com/repos/mltframework/mlt), [Shotcut](https://api.github.com/repos/mltframework/shotcut), [Kdenlive](https://api.github.com/repos/KDE/kdenlive)
- melt: multitrack command-line editor; filters per clip/track with in/out; `-mix` luma/mix transitions between adjacent clips; xml consumer serializes MLT XML; "melt" was built as a test tool for MLT; filters applying to every output frame across tracks are not supported in one command; copyright Meltytech 2008-2026 — [melt docs](https://www.mltframework.org/docs/melt/)
- GStreamer Editing Services repo on GitHub (a mirror) shows last push 2018-09-01 and 46 stars — the mirror is stale; the real GES lives in the GStreamer GitLab monorepo (not checked) — [API](https://api.github.com/repos/GStreamer/gst-editing-services)
- Olive: 9,148 stars, GPL-3.0, last push 2024-12-05 (STALE ~11 months at the very edge; project in long rewrite) — [API](https://api.github.com/repos/olive-editor/olive)
- pyJianYingDraft: 4,810 stars, Apache-2.0, pushed 2026-10-14, PyPI 0.3.1. Supports keyframes (video/sticker/text position and size, and audio volume; NOT effect/filter parameters), transitions, text intro/outro/loop animations, filters, effects, constant speed only (no curve speed), loading an existing `draft_content.json` as a template and replacing materials/text. Auto-export only on Windows with Jianying 6.8 and below (drives the GUI via mouse; needs an account with export permission). On newer Jianying (10.8) draft_content.json is often not plain JSON, so templates need a `fallback_loader`; a CapCut version is "in development in a separate repo" — [pyJianYingDraft README](https://github.com/GuanYixuan/pyJianYingDraft), [API](https://api.github.com/repos/GuanYixuan/pyJianYingDraft)
- VectCutAPI: 2,357 stars, Apache-2.0, pushed 2026-10-24. HTTP (port 9001) + MCP server generating CapCut/Jianying drafts (`draft_profile`: `capcut_legacy`, `jianying_legacy`, `jianying_pro_10`); supports video clips, transitions, effects, audio, images with animation/masks/filters, multi-style text with animations, SRT import, stickers, keyframes with easing (`add_video_keyframe` for scale/alpha etc.). Cloud rendering, web client and editing agent are "not open-sourced yet", so there is no local final render — [VectCutAPI README](https://github.com/sun-guannan/VectCutAPI), [API](https://api.github.com/repos/sun-guannan/VectCutAPI)
- Public data on CapCut templates: AutoTransition (arXiv 2207.13479) collected transitions from publicly available editing-software templates (~30k training / 5k test videos, 118,984 transitions, labeled category + start/end) and notes templates fix shot count, length, music, transitions, animation, camera movement; Edit3K (arXiv 2403.16048) catalogs six component types (video effects, animations, transitions, filters, stickers, text) — [AutoTransition](https://arxiv.org/abs/2207.13479), [Edit3K](https://arxiv.org/pdf/2403.16048). Anatomy of Video Editing (arXiv 2207.09812) is movie shot assembly, not short-form — [ar5iv](https://ar5iv.labs.arxiv.org/html/2207.09812). Search found no dedicated, openly downloadable "viral Reel/TikTok template" dataset.

### Inferences
- OTIO is useful only as the structural spine (tracks, clips, source ranges, markers for beats, transitions with in/out offsets). Put speed ramps, zoom/pan keyframes, text style and color grade into OTIO `metadata` namespaces (custom schema); no stock editor will read them, so interchange to Premiere/Resolve will carry cuts and transitions only (FCP7 XML/EDL limits above). Do not expect OTIO to give "export to Premiere with the effects."
- CapCut draft output is a delivery feature (user finishes in CapCut) rather than the render backend: no local render from VectCutAPI, constant-speed only in pyJianYingDraft, and Jianying version churn (encrypted drafts, export <=6.8). For an MVP, treat draft export as an optional later add-on.
- MLT is technically capable (keyframed filters, luma/composite transitions, text filters, timeremap; the last three are training knowledge, the melt docs page did not cover them), but Python bindings are thin/awkward and VidPy's death shows the wrapper layer is not maintained. Windows packaging is via Shotcut builds. Complexity is higher than staying on FFmpeg, so skip unless you want Kdenlive/Shotcut export.
- No usable public dataset of Reel templates exists, so template extraction must be done by your own analyzer (shot detection + OCR + motion estimation) on reference Reels.

### Gaps
- Did not verify the current GStreamer GES upstream (GitLab) maintenance, MLT Python binding status, MLT XML schema detail, Kdenlive/Shotcut project file keyframe format, or Windows melt packaging.
- CapCut (international) draft format compatibility with current CapCut desktop versions not verified; the separate CapCut repo for pyJianYingDraft not located.
- OTIO-Plugins latest release/maintenance not checked (only core 0.18.1 on PyPI).

## 3. FFmpeg capability ceiling and known pitfalls

### Takeaway
FFmpeg alone reaches the quality ceiling for cuts, speed, LUT color grading, xfade transitions and caption burn-in, if inputs are normalized and the zoom path is done at supersampled resolution. Its real limits are (a) smooth subpixel zoom/pan, (b) animated per-word text, (c) arbitrary shader transitions without a custom build, and (d) filter-graph complexity and memory with many chained xfades.

### Cited Findings
- zoompan jitter: it works in whole-pixel steps, so upscale the input (e.g. `scale=8000:-1` or ~5x lanczos) before zoompan, keep zoom increments small and consistent, use higher frame rate for long pans, and pad the image before panning; an FFmpeg trac ticket (#4298) and a 2020 devel patch "fix shaking when zooming" document the stutter in zoompan itself, so upscaling does not remove every case; upscaling only the zoom segment shifts position when switching to a static hold, and matching it with a lanczos scale raised render time from about 6 s to 30 s in one report; the `kenner` CLI wraps zoompan with auto-upscale and linear interpolation — [Bannerbear](https://www.bannerbear.com/blog/how-to-do-a-ken-burns-style-effect-with-ffmpeg), [KDE forum](https://discuss.kde.org/t/transform-on-zoomed-portait-4-3-image-results-in-jumpy-jittery-unsmooth-motion/26299), [mko.re](https://mko.re/blog/ken-burns-ffmpeg/), [FFmpeg-devel patch](https://lists.ffmpeg.org/pipermail/ffmpeg-devel/2020-February/257073.html), [r/ffmpeg](https://r.enesgenc.dev/r/ffmpeg/comments/1l7wta8/how_to_prevent_image_shift_when_transitioning), [kenner](https://github.com/wltechblog/kenner)
- xfade input hygiene: maintainers state cross-fading cannot work reliably if fps is variable or differs between inputs and PTS gaps matter, so normalize fps and timebase on every input before xfade; a 2024 devel patch reworked the timebase check (current behavior unconfirmed); a user reported 27 GB memory use from audio shorter than trimmed video (audio buffering) — [FFmpeg-devel 2020](https://ffmpeg.org/pipermail/ffmpeg-devel/2020-August/267707.html), [FFmpeg-devel 2024](https://ffmpeg.org/pipermail/ffmpeg-devel/2024-January/319288.html), [ffmpeg-user 27 GB](https://ffmpeg.org/pipermail/ffmpeg-user/2023-May/056381.html)
- xfade-easing (scriptituk, MIT, 565 commits, CLI v3.6.6): 58 xfade transitions (56 as expressions on vanilla FFmpeg), ~64 ported GL transitions, CSS easings (`cubic-bezier`, `linear()`, `steps()`) and Penner easings; easings can also drive zoompan and drawtext. Two modes: custom-patched FFmpeg (patches vf_xfade.c; fast, ~1 s for SD) vs expression mode on vanilla FFmpeg (needs `-filter_complex_threads 1`, slow: many GL expressions about 30 s for SD on an old Intel Mac, some far longer, e.g. `gl_powerKaleido`, `gl_LinearBlur`). Overshooting easings (`elastic`, `back`) can cause unpredictable behavior/access violations; Windows performance not measured; CLI is Bash 4 + gawk — [xfade-easing](https://github.com/scriptituk/xfade-easing)
- ffmpeg-gl-transition (transitive-bullshit): MIT, 721 stars, last push 2024-07-23 (STALE ~16 months), no license metadata on GitHub API; needs a custom FFmpeg build from source with `--enable-opengl`, GLEW, glfw, EGL/GLX; EGL eases headless use (else Xvfb); no Windows-specific steps; both inputs must be same size; README itself points to ffmpeg-concat as an easier option — [repo](https://github.com/transitive-bullshit/ffmpeg-gl-transition), [API](https://api.github.com/repos/transitive-bullshit/ffmpeg-gl-transition)
- gl-transitions collection: 2,225 stars, NOASSERTION (per-transition licenses), pushed 2026-11-04 — [API](https://api.github.com/repos/gl-transitions/gl-transitions)
- lut3d supports nearest, trilinear and tetrahedral interpolation (tetrahedral default, per source code); libplacebo filter can apply custom 3D LUTs and shaders on Vulkan-capable GPUs; a 2022 thread suggests gyan.dev Windows builds with Vulkan/libplacebo (check current build flags) — [vf_lut3d.c mirror](https://git.kx.studio/falkTX/FFmpeg/src/commit/2d96c945312d3f62e3f872bfb51a593afb40e09a/libavfilter/vf_lut3d.c), [ffmpeg-user 2022](https://ffmpeg.org/pipermail/ffmpeg-user/2022-May/054856.html)
- ffmpeg-python wrapper: 11,012 stars, Apache-2.0, last push 2024-08-04 (STALE; build filtergraphs yourself or via kinocut) — [API](https://api.github.com/repos/kkroening/ffmpeg-python)
- The full ffmpeg-filters.html (591k chars) could not be paged into xfade/minterpolate sections within the call budget; the FFmpeg wiki Xfade page was unreachable (connection refused).

### Inferences (training knowledge unless otherwise stated; verify before relying)
- Frame-accurate cutting: put `-ss` after `-i` (or use `trim`/`atrim` in filtergraph) and re-encode; input-seek with stream copy lands on keyframes. Always set constant frame rate (`fps=30`) and `setpts=PTS-STARTPTS` per clip before xfade/concat.
- Speed ramps: `setpts` with an expression gives stepwise or interpolated speed; smoothness needs frame blending (`minterpolate`/`framerate`) which introduces artifacts on fast motion (warping, ghosting) and is slow; audio needs matching `atempo` segments (atempo range 0.5-2.0 per instance, chain for more). Practical approach: split into constant-speed segments with short eased segments, and render source at 60 fps when possible.
- Better zoom/pan than zoompan: `crop` accepts per-frame expressions in `x`/`y` (using `t`/`n`) but `w`/`h` are fixed at init, so for zoom use `scale=...:eval=frame` (time-varying size) followed by `crop`, or `overlay` with time expressions, on a 2-4x upscaled stream then scale down; or `sendcmd`; or render the camera move in the browser layer (verify these filter semantics on your FFmpeg build). Easing curves can come from xfade-easing expressions.
- Text: libass (ASS) handles outline/shadow/karaoke `\k` tags, simple fades `\fad`, moves `\move`, and transforms `\t` (scale/color animation over time) — enough for most caption presets; it cannot do springs/bounce physics, per-glyph 3D, gradient text or emoji layout as in CapCut/Instagram; those need the browser layer. Variable-width/emoji font fallback is a common libass fidelity gap.
- Color: for reproducing a reference grade, estimate a 3D LUT from reference vs neutral frames (histogram matching/grading net) and apply with lut3d (tetrahedral); libplacebo only if a Vulkan GPU is guaranteed.
- Vanilla FFmpeg + xfade expressions is portable to Windows but slow for exotic GL-style transitions; the custom patched build and ffmpeg-gl-transition both require maintaining your own FFmpeg binary — high cost for little benefit versus doing the 3-5 signature transitions (whip, zoom-punch, glitch, flash, swipe) in the browser layer or as precomputed overlay clips.

### Gaps
- xfade full transition list, offset semantics, lut3d/libplacebo/minterpolate official documentation text not retrieved (see above); no sourced quantitative quality comparison of minterpolate vs framerate blending, or measured zoompan-vs-crop smoothness.
- Windows performance of expression-mode xfade-easing unmeasured by author.

## 4. Auto-editing and analysis tools, including Kinocut / mcp-video

### Takeaway
mcp-video is now just a compatibility installer for Kinocut (Apache-2.0, 243 stars, very active). Kinocut is a broad FFmpeg wrapper plus Hyperframes and Revideo tool sets with guardrails and quality checks, but it explicitly does not list speed ramps or zoom/pan, and its transitions are limited to glitch/morph/pixelate, so recreating a reference template needs extra render code on top.

### Cited Findings
- mcp-video on PyPI is version 1.6.20 and only a "Compatibility installer for Kinocut, formerly mcp-video", pinning `kinocut==1.16.5` plus extras; kinocut on PyPI is 1.16.5 ("Trusted, guardrailed video editing for AI agents. FFmpeg, Hyperframes, repurposing tools, Python client, CLI, and MCP server") — [mcp-video PyPI JSON](https://pypi.org/pypi/mcp-video/json), [kinocut PyPI JSON](https://pypi.org/pypi/kinocut/json)
- Kinocut GitHub: KyaniteLabs/kinocut, Apache-2.0, 243 stars, pushed 2026-11-03 — [API](https://api.github.com/repos/KyaniteLabs/kinocut). README (1.16.5, published 2026-10-27): 205 MCP tools / 177 CLI commands with `KINOCUT_TOOLS=all` (default curated 20-tool core); transitions: 3 tools (glitch, morph, pixelate); text: add text, subtitles, animated text, burned-in captions, watermarks; 8 visual effects (vignette, glow, noise, scanlines, chromatic aberration, luma key, mask, shape mask); layered compositing with blend modes; color grading only as still/plate tools (`still-match`, `still-grade` with optional LUT); speed ramp and zoom/pan not mentioned; audio normalization/mixing/ducking, stem separation, Whisper transcription, silence removal; FFmpeg core + Hyperframes (Node 22+) tool set + 4 Revideo local-render tools; preflight guardrails, `video_quality_check`, release_checkpoint, quality compare, "Video Receipts" with hashes; known limits: composite output is video-only, several mask/blend deferrals, "generative plans are non-executable", trusted execution kernel not running, not production-proven for every use, human inspection recommended. Release cadence: 1.12-1.16.5 between 2026-08-07 and 2026-10-27 — [Kinocut README](https://github.com/KyaniteLabs/kinocut)
- Hyperframes inside Kinocut is a direct bridge to the HTML motion-graphics layer (see section 1).
- PySceneDetect: 5,364 stars, BSD-3-Clause, pushed 2026-11-02; PyPI 0.7.2 uploaded 2026-10-12 — [API](https://api.github.com/repos/Breakthrough/PySceneDetect), [PyPI](https://pypi.org/pypi/scenedetect/json)
- TransNetV2: 1,075 stars, MIT, last push 2023-12-04 (STALE ~23 months; weights still usable, no maintenance) — [API](https://api.github.com/repos/soCzech/TransNetV2)
- auto-editor: 5,769 stars, Unlicense, pushed 2026-11-02; PyPI latest 29.3.1 uploaded 2025-11-04 (repo ahead of PyPI) — [API](https://api.github.com/repos/WyattBlue/auto-editor), [PyPI](https://pypi.org/pypi/auto-editor/json). It targets silence/motion cuts, not template recreation.
- LosslessCut: 45,710 stars, GPL-2.0, pushed 2026-11-03 (manual lossless cutting GUI; not a library) — [API](https://api.github.com/repos/mifi/lossless-cut)

### Inferences
- Keep Kinocut/mcp-video as the agent-facing guardrails and verification layer (its quality checks and receipts map to your "verify the output" step) but do not rely on it for template-specific motion; add your own render functions behind the same interface.
- For shot-boundary detection of the reference Reel use PySceneDetect (maintained, includes content/adaptive detectors) and fall back to a TransNetV2 pass for dissolves/whips (stale but works; PySceneDetect's hard-cut detectors miss gradual transitions: training knowledge).
- The 1.x version numbers and rapid release cadence (~weekly) mean pin versions and expect API churn.

### Gaps
- Did not verify Kinocut zoom/pan or speed ramp absence in code (README-only); did not test Windows install; Kinocut issue tracker and adoption not reviewed. Descript-like open tools (text-based editing) not researched.

## 5. Auto-reframe to 9:16

### Takeaway
Google AutoFlip is a MediaPipe legacy solution with support ended 2023-03-01 and no successor. Current open options are YOLO+tracker+smoothing pipelines (several small GitHub projects, mixed licenses) or a roll-your-own MediaPipe/YOLO detect, Kalman/EMA smoothing, per-shot crop path rendered with FFmpeg.

### Cited Findings
- MediaPipe legacy solutions incl. AutoFlip: "support ended" 2023-03-01, code and binaries still distributed as-is, no replacement listed — [Google MediaPipe solutions guide](https://developers.google.com/edge/mediapipe/solutions/guide), [search summary](https://developers.google.cn/mediapipe/solutions). Not verified whether AutoFlip code is still in the repo tree. MediaPipe repo itself: 37,549 stars, Apache-2.0, pushed 2026-11-04 (google-ai-edge/mediapipe) — [API](https://api.github.com/repos/google-ai-edge/mediapipe)
- PyAutoFlip (PyPI): a port of AutoFlip with detection and saliency (UNISAL + face detection) methods, per-scene motion classification (stationary/panning/tracking) with trajectory smoothing — [PyPI](https://pypi.org/project/pyautoflip/) (license/activity unchecked)
- Auto Vertical Reframe (verthor, KazKozDev): Python CLI combining segmentation, face/pose cues, saliency, tracking continuity, scene detection; Ultralytics YOLOv11 + ByteTrack — [repo](https://github.com/KazKozDev/auto-vertical-reframe)
- OpenSource Clipping: detection every 0.25 s by default, deadzone plus smoothing camera follow, YOLO option, static-crop mode; outputs 9:16, 1:1, 3:4, 4:5 — [wiki](https://github.com/NaufalRizqullah/opensource-clipping/wiki/Face-Tracking-and-Auto-Framing)
- halid96/reframe: 16:9/square to 9:16 tool, AGPL-3.0 (copyleft for network services) — [repo](https://github.com/halid96/reframe)
- Ultralytics (YOLO): 63,123 stars, AGPL-3.0, pushed 2026-11-04 — [API](https://api.github.com/repos/ultralytics/ultralytics). SAM2: 20,100 stars, Apache-2.0, last push 2026-05-30 — [API](https://api.github.com/repos/facebookresearch/sam2). OpenCV: 91,450 stars, Apache-2.0 — [API](https://api.github.com/repos/opencv/opencv)

### Inferences
- License trap: Ultralytics YOLO is AGPL-3.0 (commercial license needed for closed SaaS); MediaPipe (Apache-2.0) face/object/pose tasks, or RT-DETR/YOLO variants under permissive licenses, avoid that. SAM2 (Apache-2.0) is useful for refining a subject mask but is heavy for per-frame cropping.
- Recipe: per shot, detect subject boxes at ~4-8 Hz, pick primary subject (face/saliency), smooth with deadzone + EMA/Kalman, clamp to frame, emit a keyframed crop path (x,y,scale) into the template JSON, and render the crop via FFmpeg crop expressions (or supersampled zoom). Re-framing the user's clips is needed anyway because user footage rarely has the reference's framing (design inference).

### Gaps
- Licenses, activity and quality of PyAutoFlip, verthor, OpenSource Clipping not checked at repo level; no head-to-head quality evaluation; AutoFlip's in-repo status unverified.

## 6. Template representation schema

### Takeaway
No public standard captures a Reel template with high fidelity. Best-supported design: a custom JSON "template + style layers" schema whose cut skeleton is OTIO-compatible, with explicit keyframe tracks, text/caption style presets and grade/LUT references, rendered by a two-layer backend; use CapCut draft/Shotstack/Remotion props only as export or reference targets.

### Cited Findings
- Real templates in editing software bundle: number of shots, video length, music, transitions, animations, camera movement; public research annotates transition category and start/end times — [AutoTransition](https://arxiv.org/abs/2207.13479)
- Component taxonomy used in research: video effects, animations, transitions, filters, stickers, text — [Edit3K](https://arxiv.org/pdf/2403.16048)
- Hosted JSON schemas to borrow vocabulary from: Shotstack (timeline > tracks > clips, rich text, rich captions with word-level animation and `alias://` links, merge fields, templates, luma mattes) — [Shotstack docs](https://shotstack.io/docs/guide/llms.txt); OpenAPI at `https://shotstack.io/docs/api/api.edit.json`
- CapCut/Jianying draft JSON (via pyJianYingDraft/VectCutAPI) represents tracks, segments, materials, keyframes (position/scale/alpha/volume), transitions, text animations, filters, effects; template mode swaps materials/text in an existing draft — [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft), [VectCutAPI](https://github.com/sun-guannan/VectCutAPI)
- HyperFrames compositions are HTML with `data-start`/`data-duration`/`data-track-index` — natively a timeline-in-HTML — [HyperFrames](https://github.com/heygen-com/hyperframes); Remotion templates are React components with typed props (generating personalized videos from your template is license-permitted) — [Remotion FAQ](https://www.remotion.dev/docs/license/faq)

### Inferences (proposed schema; design, not sourced)
- Layers: (1) `structure`: tracks and shots as OTIO-style `source_range` / `transition` objects with duration in frames at a fixed fps (30), shot slots with role tags (hook, product, b-roll) and constraints for what user clip fits (min duration, orientation, subject type); (2) `motion`: per-shot keyframe tracks `{property, keyframes:[{t, value, easing:cubic-bezier}]}` for scale/x/y/rotation, plus `speed_curve` points; (3) `transitions`: `{type, duration, easing, params}` from a closed vocabulary mapped to xfade names and to HyperFrames/shader equivalents; (4) `text`: items with content slots, font id, style preset (fill, stroke, shadow, gradient), box, animation preset id (in/out/loop), word-level timing source (ASR); (5) `grade`: LUT file ref plus exposure/contrast/saturation params; (6) `audio`: music track, beat grid (times), ducking; (7) `sync`: beat markers each cut snaps to; (8) `provenance`: reference-extraction confidence per field, enabling the verifier to compare.
- Keep it closed and enumerated (presets by id) rather than free-form, so LLM output is schema-validatable and patchable (fits the earlier note's schema-patch design) and each field has a defined renderer: FFmpeg for structure/speed/grade/simple zoom/ASS captions; browser layer for animated overlays and complex transitions.
- Exports: OTIO (cuts, transitions, markers; pushes FCP7 XML/EDL for Premiere/Resolve with the limits above); CapCut draft via VectCutAPI/pyJianYingDraft (optional, version-fragile); Remotion/HyperFrames props are just a rendering of the same schema.

### Gaps
- No openly licensed dataset of real Reel/TikTok templates found; Edit3K/AutoTransition dataset availability and license not checked; the CapCut draft JSON field-level schema not retrieved; Shotstack and JSON2Video exact schemas not retrieved.

## 7. Recommended combination (highest quality, low complexity)

### Takeaway
Do not stay FFmpeg-only if animated captions and punchy transitions are core to "fidelity"; add one browser-based motion-graphics layer, and make it HyperFrames first (Apache-2.0, already integrated in Kinocut), with Remotion as the fallback if you want its mature Lambda/Player ecosystem and accept the license. Keep FFmpeg as the base compositor, cutter, color-grade and final encoder.

### Cited Findings
- (Evidence is in sections 1-5.) Key supports: Kinocut = FFmpeg + Hyperframes + guardrails, Apache-2.0, weekly releases ([Kinocut](https://github.com/KyaniteLabs/kinocut)); HyperFrames Apache-2.0, frame-deterministic, shader transitions + captions blocks ([HyperFrames](https://github.com/heygen-com/hyperframes)); Remotion license floor for companies ([FAQ](https://www.remotion.dev/docs/license/faq)); zoompan/xfade pitfalls ([sources above]); AutoFlip ended ([Google](https://developers.google.com/edge/mediapipe/solutions/guide)).

### Inferences
- Pipeline: (a) analyze reference: PySceneDetect (+ TransNetV2 for soft transitions) for shots; OCR/ASR for text and timing; optical-flow or feature tracking for zoom/pan per shot; librosa/Beat This for beat grid; palette/LUT estimation for grade; (b) write template JSON (section 6); (c) per-shot: reframe (YOLO/MediaPipe path) then FFmpeg render of trimmed, speed-ramped, supersampled-zoom, graded shot to normalized 1080x1920/30fps; (d) overlay layer: HyperFrames renders transparent captions/stickers/shape animations (alpha video, e.g. WebM/ProRes 4444 or PNG sequence; transparent export support in HyperFrames not verified); (e) FFmpeg xfade (normalized inputs, closed vocabulary of ~6 transitions; shader-style ones via HyperFrames shader-transitions blocks or xfade-easing expressions) + overlay + audio mix + libx264 encode; (f) verify with Kinocut quality checks plus own frame-diff vs template expectations (shot boundary times, text presence via OCR, beat alignment error).
- Cost/complexity discipline: ~90% of fidelity comes from correct timing, framing, speed ramp, grade and caption style, all achievable in FFmpeg+ASS. The browser layer adds the last mile (kinetic captions, spring pops, shader/whip transitions). If MVP time is tight, ship FFmpeg+ASS first, then add HyperFrames for caption presets only.
- Avoid: Editly/FFCreator/VidPy (stale), Etro/Gyroflow/Ultralytics-in-SaaS (GPL/AGPL), MoviePy as the main engine (slow numpy pipeline), custom FFmpeg builds with ffmpeg-gl-transition (stale, build burden), CapCut-draft as the primary render path (no local renderer, version fragility), WebCodecs-only tools (browser-bound).

### Gaps
- No end-to-end test of this stack was done; Windows behavior of HyperFrames CLI, transparent-overlay export, and render speed for 1080x1920 are the top verification items before committing.
- Several FFmpeg claims in section 3 Inferences are training knowledge and should be checked against ffmpeg.org docs.
