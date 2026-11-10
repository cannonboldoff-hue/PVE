# Generative and enhancement AI models for an AI Reel template editor (state as of 2026-11-04)

Scope note: builds on `AI reel editor competitor landscape/rendering_and_generation_tools.md` (not repeated: Gemini Omni Flash modes and limits, Sora shutdown, Veo 3.1 preview shutdown 2026-10-22, Wan 2.2 Apache-2.0, Remotion/Shotstack pricing, MediaPipe repo stats). Evidence tags: "primary" = vendor page, GitHub API/license file, or leaderboard fetched directly on 2026-11-04; "secondary" = blogs/aggregators (many are SEO/reseller pages that disagree). Items marked "training knowledge" are NOT sourced this session and sit only in Inferences/Gaps. Search/fetch was capped (~22 calls), so several niches (deep stabilizers, MUSIQ/FAST-VQA, YOLO/MediaPipe face tracking, neural LUT papers, Luma/Hailuo/Kling official pages) are thin; see Gaps in each section.

---

## 1. Video generation / gap filling: which model for a 3-6 s B-roll slot, and cost per second

### Takeaway
The closed-model quality frontier is now Seedance 2.5/2.0 (ByteDance), MiniMax H3, Wan 3.0 (API-only), Kling 3.0, and Gemini Omni Flash; Sora is dead and Veo 3.1 preview is replaced by Omni Flash. For a cheap 4-5 s vertical B-roll slot, the best quality-per-dollar API picks are MiniMax H3 (about $0.08/s at 768p per Artificial Analysis; $0.025-0.05/s on fal.ai) and Kling 3.0 via fal ($0.14/s); open weights (LTX-2.3, Wan 2.2, HunyuanVideo 1.5, MiniMax H3) are all license-encumbered or a generation behind, so API-first is the sane MVP path.

### Cited Findings
**Quality ranking (Artificial Analysis AA-Video-I2V v2.1 "overall", fetched 2026-11-04; Elo anchored so Kling 3.0 1080p Pro = 1000; "price/min" is AA's cost at benchmark settings)**
- 1 Dreamina Seedance 2.5 Elo 1159, closed, $34.12/min (Jul 2026); 2 Utopai X 1149, no API; 3 Seedance 2.0 1135, $22.45/min (Mar 2026); 4 MiniMax H3 (768p) 1130, open weights, $4.80/min (Jul 2026); 5 HeyGen Video 1 1123, $2.40/min; 6 Hyperflow H3 1121, open weights, $9.00/min; 7 P-Video-2-Pro 1118, $5.70/min; 8 MiniMax H3 Max 1116, $9.60/min; 9 Wan 3.0 1112, closed, $12.00/min (Aug 2026); 10 Agnes-Video-2.5 1104, $2.40/min; 11 FLUX 3 1070, $17.40/min; 12 FLUX 3 Max 1068, $4.35/min; 13 Grok Imagine Video 1.5 1049, $15.00/min; 14 Gemini Omni Flash 1.1 1043, $9.12/min (Aug 2026); 15 HappyHorse-1.1 1038, $10.80/min; 17-18 Kling 3.0 Omni/Kling 3.0 1080p Pro 1002/1000, $8.40-10.08/min (Feb 2026); 20 PixVerse V6 958, $6.90/min. Only MiniMax H3 (768p) and Hyperflow H3 show Hugging Face links in the top 20. The page does not state per-row audio status or licenses — [Artificial Analysis I2V leaderboard](https://artificialanalysis.ai/video/leaderboard/image-to-video).
- Conflicting snapshot: an earlier/other AA view had Gemini Omni Flash at the top of the no-audio I2V board (Elo 1365), MiniMax H3 second (1346), Seedance 2.0 720p third (1337) (different Elo scale/board version). AA runs four boards (T2V/I2V x audio/silent); rankings differ by board — [search summary of AA pages](https://artificialanalysis.ai/video/leaderboard/image-to-video).

**Official/first-party per-second prices (invideo roundup of vendor rate cards, dated 2026-08-06; secondary aggregator citing primary rate cards)**
- Veo 3.1 $0.40/s (720-1080p), $0.60/s 4K; Veo 3.1 Fast $0.10/$0.12/$0.30; Veo 3.1 Lite $0.05/$0.08 (all with audio) — cites Google Gemini API pricing; note prior notes say the Gemini API Veo preview IDs were shut down 2026-10-22, so these may be stale.
- Sora 2 $0.10-0.70/s; API sunset 2026-09-24 (dead).
- Kling 3.0 Turbo ¥0.8/s (about $0.11) at 720p; MiniMax-H3 (Hailuo) $0.13/s at 2K with native stereo audio; HappyHorse ¥0.9-1.6/s; Grok Imagine Video 1.0 $0.05/s, 1.5 $0.08/s; P-Video (Pruna) $0.02-0.04/s.
- LTX-2.3 first-party: Fast $0.06/s (1080p), $0.12 (1440p), $0.24 (4K); Pro $0.08/$0.16/$0.32; Retake/extend/audio-to-video $0.10/s; Reframe $0.10-0.20/s; HDR beta $0.20-0.40/s. Up to 4K/50fps; about 10 s per generation (no official max published); portrait supported (9:16 not named) — [invideo pricing](https://invideo.io/blog/ai-video-model-pricing), [invideo LTX page](https://invideo.io/blog/ltx-ai-video-generator/).
- Seedance 2.x is token-billed: BytePlus $7.00/M tokens (no video input) / $4.30/M (with video input) at 720p; Volcano ¥28/M with video input; "planning estimate" about $0.14/s (derived, not a price) — [invideo](https://invideo.io/blog/ai-video-model-pricing).
- Runway API (primary, $0.01/credit): Gen-4.5 12 credits/s ($0.12/s); Gen-4 Turbo 5 ($0.05/s); Aleph 2.0 28 credits/s ($0.28/s, 56-credit minimum per generation); Act-Two 5; Veo 3.1 40 w/ audio ($0.40/s), Veo 3.1 Fast 15 w/ audio ($0.15/s) — [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/).

**fal.ai per-second prices (primary, fetched 2026-11-04)**
- MiniMax H3 Max (T2V/I2V/reference-to-video) $0.05/s; H3 Max Turbo $0.025/s; Kling 2.5 Turbo Pro and 2.6 Pro $0.07/s; Kling v3 Pro/Standard I2V/T2V $0.14/s; Kling O3 (I2V, reference-to-video, and video-to-video edit) $0.14/s; Grok Imagine Video $0.05/s and "v1.5 I2V" $0.01/s; PixVerse V6 (I2V, T2V, Extend) $0.005/s; FLUX 3 Max video $0.085/s. Seedance 2.x and Wan 3.0 not on that page — [fal.ai pricing](https://fal.ai/pricing). A reseller analysis claims Seedance 2.0/2.0 Fast/2.5 cost 82-114% more on fal than on BytePlus ModelArk — [AtlasCloud via search](https://www.atlascloud.ai/blog/guides/cheapest-api-provider-seedance-2-kling-wan) (reseller, interested party).
- Replicate (primary): billed by GPU-second (T4 $0.000225/s, L40S $0.000975/s, A100-80GB $0.0014/s, H100 $0.001525/s) or per output; listed video examples wavespeedai/wan-2.1-i2v-480p $0.09/s, 720p $0.25/s — [Replicate pricing](https://replicate.com/pricing).

**Open weights (licenses verified from repo LICENSE files via GitHub API, 2026-11-04)**
- Wan 2.2: Apache-2.0, 18.4k stars, last push 2026-09-21 — [GitHub](https://github.com/Wan-Video/Wan2.2). Wan 2.5/2.6/2.7/3.0 reported API-only (secondary, internally inconsistent; one page claims 2.7 Apache-2.0 and is flagged wrong by others); AA lists Wan 3.0 as closed — [HowAIWorks](https://howaiworks.ai/alibaba-wan-open-weights-stopped-at-2-2/), [AA](https://artificialanalysis.ai/video/leaderboard/image-to-video).
- LTX-2 repo (inference + LoRA trainer code): Apache-2.0, 10.1k stars, pushed 2026-11-04; weights (LTX-2 / LTX-2.3 22B full and distilled) are under the LTX-2 Community License Agreement (dated 2026-01-05), reported free for academic use and companies under $10M ARR, paid agreement above; one aggregator says "Apache 2.0" for the weights and conflicts with the license file — [GitHub](https://github.com/Lightricks/LTX-2), [search summary](https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE) (HF license page itself returned 404 to my fetch; threshold figure is secondary). Newer LTX-2.5 is described by a review dated Sep 2026 — [layer3labs](https://www.layer3labs.io/guides/ltx-2-5-explained) (unread).
- MiniMax H3 weights on HF (MiniMaxAI/MiniMax-H3): "MiniMax H3 Community License" reportedly excludes the US, EU, UK and South Korea from the licensed territory, requires prominent "MiniMax H3" display, needs written authorization above $20M annual revenue, and bars using outputs to train other models; only H3-Base is open, preprocessing and 2K regeneration stay hosted; MiniMax tightened M2.7 terms after release — [NYU Shanghai summary](https://rits.shanghai.nyu.edu/ai/minimax-ships-h3-weights-with-the-us-and-eu-excluded/), [DEV summary](https://dev.to/routeai_official/minimax-h3-is-open-weight-now-heres-whats-actually-downloadable-vs-api-only-441k) (secondary; license text not read).
- HunyuanVideo 1.5 (released 2025-11-21): Tencent Hunyuan Community License; first line of the license: "does not apply in the European Union, United Kingdom and South Korea"; GitHub reports NOASSERTION; 4.6k stars — [license file via GitHub API](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5). HunyuanVideo (v1) repo 12.7k stars, pushed 2026-10-08, NOASSERTION.
- CogVideoX/CogVideo: Apache-2.0 on repo, 13.2k stars, last push 2025-11-04 (about 12 months, effectively stale) — [GitHub](https://github.com/zai-org/CogVideo). Mochi 1: Apache-2.0, 3.8k stars, pushed 2026-10-22 — [GitHub](https://github.com/genmoai/mochi). (Repo licenses; per-weight license on HF not checked.)

### Inferences
- Cost for one kept 4 s 9:16 B-roll shot (before retries): MiniMax H3 Max Turbo on fal $0.10; H3 Max $0.20; Kling v3 on fal $0.56; Runway Gen-4 Turbo $0.20; Gen-4.5 $0.48; Omni Flash about $0.40-0.60 (AA $9.12/min = $0.15/s); Seedance 2.5 about $2.30 at AA's $34.12/min. Plan 2-3 attempts per kept shot. Quality-per-dollar knee is MiniMax H3 / Kling 3.0 / Gemini Omni Flash; Seedance 2.5 is #1 in quality but 4-7x cost.
- "Match a reference shot" is best done by I2V from a reference frame (or the user's nearest clip frame) plus a motion prompt, using Nano Banana-class image edit for the start frame (see section 8). Reference-to-video endpoints (H3 Max reference-to-video, Kling O3 reference-to-video, Grok reference-to-video, Seedance multi-ref) are the closest to subject-consistent fill.
- Open weights are not a good MVP default: LTX-2.3 needs a revenue-threshold check and serious VRAM (22B; distilled 8-step build exists), MiniMax H3 and Hunyuan exclude the EU/UK (and US for H3) from the licensed territory, Wan 2.2 is clean Apache-2.0 but a generation behind AA's top models. Wan 2.2 is the only clean-license option; LTX-2.3 is the only one with fast, 9:16-capable, extend/retake tooling.
- Treat all fal-vs-vendor price gaps (Seedance, Kling 3.0 at $0.029/s per one June review vs $0.14/s on fal's page) as noise; use fal's page as the integration price.

### Gaps
- Kling, Luma Ray 3, Hailuo, Seedance official pricing pages not fetched. Luma Ray API price conflicting in secondary sources ($0.08/s Ray-2 vs $0.32/M pixels).
- No generation latency numbers (typically tens of seconds to minutes; not sourced). No sourced comparison of "reference-matching" fidelity. PixVerse V6 at $0.005/s and Grok 1.5 at $0.01/s on fal look anomalously cheap — could be promo or per-unit display error; verify before relying.
- Veo GA pricing on "Gemini Enterprise Agent Platform" not found.
- Whether MiniMax H3's AA price ($4.80/min = $0.08/s) refers to the open Base model hosted by MiniMax or the Max tier is unclear.

---

## 2. Video-to-video restyling / editing for look matching

### Takeaway
Hosted V2V exists at three tiers: Runway Aleph 2.0 ($0.28/s, 56-credit minimum, priciest), Kling O3 Edit ($0.14/s on fal), and open Wan VACE (Apache-2.0, on fal; per-second price not found). V2V is overkill for plain color matching (use an LUT, section 6); use it only for restyling, object removal, or background replacement.

### Cited Findings
- Runway Aleph 2.0: 28 credits/s with a 56-credit minimum per generation ($0.28/s, minimum $0.56) — [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/); OpenRouter lists $0.28/s also — [search summary](https://openrouter.ai/compare/kwaivgi/kling-v3.0-pro/runway/aleph-2).
- Kling O3 "Edit Video" Pro and Standard: $0.14/s on fal (`fal-ai/kling-video/o3/{pro,standard}/video-to-video/edit`) — [fal.ai pricing](https://fal.ai/pricing).
- Wan VACE (ali-vilab/VACE): Apache-2.0, 4.0k stars, last push 2025-10-17 (about 12.5 months; stale) — [GitHub](https://github.com/ali-vilab/VACE). fal hosts `wan-vace-14b` variants (e.g. pose); no price retrieved — [fal model page](https://fal.ai/models/fal-ai/wan-vace-14b/pose).
- Luma Modify Video: described as restyling/re-texturing while preserving motion, clips up to about 10 s; no reliable price found. One source says Ray3 Modify is 3x cheaper per second than earlier Ray, no absolute figure — [Atlabs comparison](https://www.atlabs.ai/blog/runway-aleph-vs-luma-modify-video), [search summary](https://www.atlabs.ai/blog/runway-aleph-vs-luma-modify-video) (secondary).
- Gemini Omni Flash video edit: input must be 10 s or less, unavailable in EEA/CH/UK for uploaded video (from prior notes) — [Gemini Omni docs](https://ai.google.dev/gemini-api/docs/omni).
- LTX-2.3 "Clean Plate" IC-LoRA removes people/vehicles from footage without a mask; Retake $0.10/s — [invideo LTX](https://invideo.io/blog/ltx-ai-video-generator/).

### Inferences
- For "match the reference look" the correct escalation is: LUT/histogram transfer (free, deterministic) -> only if the reference has a stylized, non-grade look (film grain, glow, stylization) consider Kling O3 Edit ($0.14/s, about $0.70 per 5 s clip) as the cheapest hosted V2V on a single aggregator. Aleph at $0.28/s is 2x the cost with no sourced quality advantage here.
- V2V changes pixels non-deterministically, may drift identity/text/logos, and bills per attempt; keep it off the default render path.

### Gaps
- No benchmark comparing Aleph vs Kling O3 Edit vs Luma Modify vs VACE. VACE fal price missing. Luma API official price not found.

---

## 3. Upscaling, restoration, denoise

### Takeaway
Best open model for "low-res phone footage -> crisp 1080p" is FlashVSR (Apache-2.0, fastest, repo active) with SeedVR2 (Apache-2.0 family) as the higher-quality-but-slower option; Topaz is the commercial default (about $0.06-0.18/s via resellers; official developer pricing not retrieved). Real-ESRGAN is permissive but unmaintained since Aug 2024. Video2X is AGPL (a wrapper; avoid in closed SaaS).

### Cited Findings
- FlashVSR (OpenImagingLab): Apache-2.0, 1,960 stars, pushed 2026-10-16 — [GitHub](https://github.com/OpenImagingLab/FlashVSR). SeedVR (ByteDance-Seed/SeedVR, includes SeedVR2): Apache-2.0, 1,436 stars, last push 2026-01-27 — [GitHub](https://github.com/ByteDance-Seed/SeedVR).
- Speed on 10 s 720p clips (ComfyUI docs): FlashVSR about 41 s to 1080p, about 52 s to 4K (hardware not stated); SeedVR2 about 312 s to 1080p on an RTX 5090; Topaz Astra about 374 s to 1080p, about 560 s to 4K. Quality notes: SeedVR2 "most accurate and consistent realism", FlashVSR "fastest, conservative", Topaz Astra Creative good for repairing AI video — [ComfyUI video upscale docs](https://docs.comfy.org/tutorials/utility/video-upscale.md). A Topaz forum user measured SeedVR2 1.02 fps vs FlashVSR 1.12 fps and preferred SeedVR2 for faces — [Topaz community](https://community.topazlabs.com/t/sls-vs-slm-vs-seedvr2-vs-flashvsr-comparison/98005/1). Claims that open models beat Topaz come from interested parties (SECourses, Upsampler) — no independent benchmark found.
- Hosted: fal SeedVR2 image upscale $0.001/MP (video endpoint price not listed) — [fal.ai pricing](https://fal.ai/pricing); Runway's Magnific Video Upscaler Creative $0.007/frame at 720p/1k, $0.009 at 2k, $0.012 at 4k (about $0.21/s at 30 fps for 720p) — [Runway pricing](https://docs.dev.runwayml.com/guides/pricing/); both FlashVSR and SeedVR2 are on WaveSpeed API per ComfyUI docs.
- Topaz Video API via resellers (all secondary, conflicting): about $0.055-0.088/s (EvoLink), $0.06/s flat (Unifically), $0.125/s input (Segmind), $0.080/s 1K and $0.175/s 4K at 24 fps (Runware quote), credits 15-120/s by tier (BudgetPixel; 20 s / 100 MB input cap); Wireflow: basic about 4 credits/s, precision about 10, generative/Starlight about 41 at $0.01/credit — [search results](https://www.wireflow.ai/blog/topaz-upscale-api). Topaz desktop is $299 perpetual or $12.99/month (secondary) — [upsampler summary](https://upsampler.com/blog/seedvr-vs-flashvsr-ai-video-super-resolution-2026).
- Real-ESRGAN: BSD-3-Clause, 37.4k stars, last push 2024-08-06 (stale) — [GitHub](https://github.com/xinntao/Real-ESRGAN). Video2X: AGPL-3.0, 22.6k stars, pushed 2026-03-07 — [GitHub](https://github.com/k4yt3x/video2x).

### Inferences
- A 5 s clip upscaled: Topaz via reseller about $0.30-0.90; Magnific via Runway about $1.05 (150 frames x $0.007); self-hosted FlashVSR about 20-25 s of GPU per 5 s clip at 720p->1080p (scaled from ComfyUI timing), i.e. cents on L40S ($0.000975/s on Replicate).
- Reels are 1080x1920; most phone footage already is 1080p, so upscaling matters mainly for old/zoomed crops (e.g. digital zoom for tracked punch-ins) and generated clips (many APIs output 720p). Gate it: run only when source shorter side < target.
- Denoise: no dedicated model researched; FlashVSR/SeedVR2 do restoration jointly. FFmpeg `hqdn3d`/`nlmeans` are the zero-cost baseline (training knowledge, not sourced).

### Gaps
- No official Topaz developer pricing; FlashVSR/SeedVR2 VRAM and weights licenses on HF not checked (repo code is Apache-2.0). No independent perceptual benchmark (e.g. DOVER/MUSIQ scores) comparing them. SeedVR2-on-fal video price missing. Denoise-only models (e.g. VRT/BasicVSR++) not researched.

---

## 4. Frame interpolation / slow motion

### Takeaway
Use Practical-RIFE (MIT, active 2026) for 2x-4x slow motion; FILM on fal ($0.0013/s) is the zero-ops hosted option, but the Google FILM repo is archived. GIMM-VFI is non-commercial. FFmpeg `minterpolate` is a fallback only for tiny motion.

### Cited Findings
- Practical-RIFE (hzwer): MIT, 1,036 stars, last push 2026-08-27 — [GitHub](https://github.com/hzwer/Practical-RIFE); original RIFE (ECCV 2022): MIT, 5.7k stars, pushed 2025-09-10 — [GitHub](https://github.com/hzwer/ECCV2022-RIFE). Latest listed model in the README snapshot is v4.20 (2024-07-24) with a v4.25 mirrored on HF under MIT — [HF mirror](https://huggingface.co/gpanaretou/practical-rife-interpolation), [GitHub](https://github.com/hzwer/Practical-RIFE).
- GIMM-VFI: S-Lab License 1.0 — "Redistribution and use for non-commercial purpose" only; 409 stars, last push 2025-06-05 — [license via GitHub API](https://github.com/GSeanCDAT/GIMM-VFI).
- Google FILM (frame-interpolation): Apache-2.0, 3.2k stars, ARCHIVED, last push 2024-08-10 — [GitHub](https://github.com/google-research/frame-interpolation). Hosted FILM on fal: $0.0013/s — [fal.ai pricing](https://fal.ai/pricing).
- Runway "Enhance Frame Rate": 1 credit per 2 s input ($0.005/s) — [Runway pricing](https://docs.dev.runwayml.com/guides/pricing/).

### Inferences
- Slow-mo 2x on a 3 s 30 fps clip with Practical-RIFE is seconds on any modern GPU (RIFE is a light model; training-knowledge, not benchmarked here). Hosted FILM costs under a cent per clip; Runway Enhance Frame Rate costs about $0.015 per 3 s clip. Hosted FILM and Runway are the lowest integration effort.
- FFmpeg `minterpolate` (motion-compensated, `mi_mode=mci`) ghosts/warps on fast motion and occlusions (training knowledge); acceptable for 1.25-1.5x ramps, not 4x slow-mo. Source-faster-than-needed footage (60/120 fps) needs no interpolation, only `setpts`.
- Reel speed ramps need only interpolate the slowed section, then cache that shot.

### Gaps
- No sourced quality benchmark (PSNR/LPIPS/user study) for RIFE v4.x vs FILM vs GIMM-VFI; no sourced minterpolate evaluation; no GPU timings.

---

## 5. Stabilization

### Takeaway
For generic user clips the practical choice is FFmpeg vidstab two-pass (cheap, CPU, deterministic) with a crop/zoom penalty; Gyroflow needs gyro metadata and is GPL-3.0. Deep stabilizers were not evidenced this session.

### Cited Findings
- vid.stab (library behind FFmpeg `vidstabdetect`/`vidstabtransform`): 985 stars, last push 2026-08-14; GitHub license NOASSERTION (historically GPL-2.0+; not verified in text) — [GitHub](https://github.com/georgmartius/vid.stab).
- Gyroflow: GPL-3.0, 9.7k stars, pushed 2026-11-04 — [GitHub](https://github.com/gyroflow/gyroflow). Prior notes flagged it as needing gyro metadata.

### Inferences
- Pipeline: `vidstabdetect` -> `vidstabtransform` with `smoothing` about 15-30 and `zoom`/`optzoom`, then a 9:16 crop; trigger only when a shake metric (global-motion jitter from detect pass) exceeds a threshold (training knowledge on filter options; not verified here since the local machine has no ffmpeg).
- vidstab (GPL) in FFmpeg is only an issue if you distribute an FFmpeg binary built with `--enable-libvidstab --enable-gpl`; running it as a server-side tool is fine for non-distributed SaaS (legal inference, not advice).
- Gyroflow is relevant only if you accept GoPro/Insta360/phone-with-gyro files; skip for MVP.

### Gaps
- No deep-learning stabilizer (DUT, FuSta, etc.) researched or licensed; no vidstab quality evaluation; FFmpeg `deshake`/`libopencv` not compared; vid.stab license text unread.

---

## 6. Segmentation, matting, tracking, reframing

### Takeaway
Pick SAM 2 (Apache-2.0) as the license-safe promptable video segmenter, BiRefNet (MIT) for per-frame subject cutouts, and Ultralytics-free tracking (ByteTrack MIT or Roboflow trackers) to avoid AGPL. MatAnyone and RMBG-2.0 are NON-commercial; Robust Video Matting is GPL-3.0 and stale; SAM 3 has a custom royalty-free license without an explicit commercial grant or ban.

### Cited Findings
- SAM 2: Apache-2.0, 20.1k stars, last push 2026-05-30 — [GitHub](https://github.com/facebookresearch/sam2).
- SAM 3 (released 2025-11-19): custom "SAM License", 12.2k stars, pushed 2026-10-23; grants "non-exclusive, worldwide, non-transferable and royalty-free limited license"; does not mention commercial use either way; bars reverse engineering and military/ITAR/weapons uses; license terminates if you sue Meta over IP; indemnify Meta; Meta may modify terms (continued use = acceptance); redistribution must carry the agreement — [LICENSE via GitHub API](https://github.com/facebookresearch/sam3), [license summary](https://github.com/facebookresearch/sam3/blob/main/LICENSE). Hosted: fal SAM 3 image $0.005/unit — [fal.ai pricing](https://fal.ai/pricing). Text-prompt "detect, segment, track" across video — [Roboflow](https://roboflow.com/blog/what-is-sam3), [InfoQ](https://www.infoq.com/news/2025/11/meta-sam3) (secondary).
- BiRefNet: MIT, 4.4k stars, pushed 2026-10-25 — [GitHub](https://github.com/zhengpeng7/BiRefNet); fal hosted `fal-ai/birefnet/v2` listed at "$0/compute second" (page oddity) — [fal.ai pricing](https://fal.ai/pricing).
- RMBG-2.0 (BRIA, built on BiRefNet): CC BY-NC 4.0; commercial use needs a BRIA agreement; fal-hosted `fal-ai/bria/background/remove` $0.018/generation — [BRIA GitHub](https://github.com/Bria-AI/RMBG-2.0), [fal.ai pricing](https://fal.ai/pricing).
- MatAnyone (video matting): NTU "S-Lab License 1.0" = non-commercial only (commercial requires contacting authors); 1.6k stars, last push 2026-03-04; needs a first-frame mask (e.g. from SAM 2), outputs foreground + alpha video; MatAnyone 2 is a separate repo (license not checked) — [GitHub](https://github.com/pq-yang/MatAnyone), [LICENSE raw](https://raw.githubusercontent.com/pq-yang/MatAnyone/main/LICENSE).
- Robust Video Matting: GPL-3.0, 9.6k stars, last push 2024-04-02 (stale) — [GitHub](https://github.com/PeterL1n/RobustVideoMatting).
- Hosted video background removal: `veed/video-background-removal/fast` $0.008 per 30 frames on fal (about $0.008/s at 30 fps) — [fal.ai pricing](https://fal.ai/pricing).
- Tracking: Ultralytics (YOLO11/12): AGPL-3.0, 63.1k stars, pushed 2026-11-04 — [GitHub](https://github.com/ultralytics/ultralytics); ByteTrack: MIT, 6.8k stars, last push 2024-06-19 (stale but stable) — [GitHub](https://github.com/ifzhang/ByteTrack). MediaPipe: Apache-2.0, 37.5k stars, active (from prior notes).

### Inferences
- Auto-reframe / text-follow recipe: detect subject box per sampled frame (MediaPipe face/pose detector Apache-2.0, or SAM 2 box prompt) -> smooth the center path with a Kalman/One-Euro filter -> emit crop-window keyframes in the timeline JSON -> FFmpeg `crop` with expression or per-segment sendcmd; text-follow reuses the same path. SAM 2 gives mask-centroid tracking without a detector; ByteTrack adds multi-person identity.
- Commercial-safe background removal: BiRefNet (MIT) per frame + temporal smoothing, or hosted fal video-BG-removal (about 4 cents per 5 s). Use MatAnyone only after obtaining a commercial license from the authors; RMBG-2.0 only with a BRIA license.
- YOLO11/12 via Ultralytics is AGPL-3.0: network use triggers source-disclosure obligations unless an Enterprise license is bought (legal inference; the AGPL text is well known, the Ultralytics enterprise offer was not fetched). Prefer MediaPipe or an Apache-2.0/MIT detector (e.g., RT-DETR/YOLOX — not verified here).
- SAM 3's license is ambiguous on commercial use (silence, not a ban) and includes indemnification/termination clauses; SAM 2 is the zero-risk choice for the MVP, upgrade to SAM 3 after counsel review for text-prompted ("the guitar") segmentation.

### Gaps
- MediaPipe face/pose tracking quality and speed not sourced; YOLO11/12 vs RT-DETR licensing alternatives not researched; BiRefNet video temporal consistency not evaluated; MatAnyone 2 license unverified; SAM 2 / SAM 3 speed (fps on A10/L4) not sourced.

---

## 7. Color grade matching (reference -> target)

### Takeaway
Do this deterministically: estimate a global color mapping from reference frame(s) to target (Reinhard/histogram/OT in Lab or a fitted 3D LUT), export a `.cube`, apply with FFmpeg `lut3d`. Open tools exist for LUT estimation but no sourced neural-preset option with a commercial license was found.

### Cited Findings
- ColorMatch3D (TomArrow): creates a `.cube` 3D LUT matching colors of a reference image with a different grading — [GitHub](https://github.com/TomArrow/ColorMatch3D) (license not checked).
- lut-estimator (PyPI, MIT): estimates a 3D LUT from before/after image pairs, writes `.cube`; limited to global RGB-to-RGB transforms, needs a pair — [PyPI](https://pypi.org/project/lut-estimator/0.1.0/).
- colour-science (`colour`): BSD-3-Clause, 2.7k stars, pushed 2026-11-03 — [GitHub](https://github.com/colour-science/colour).
- OpenColorIO `ociolutimage` converts LUT <-> image — [manpage](https://manpages.ubuntu.com/manpages/noble/man1/ociolutimage.1.html).

### Inferences
- Without paired data, the standard approach (training knowledge, not sourced): convert both frames to Lab/OKLab, match mean/std (Reinhard) or per-channel CDF (histogram match) or sliced optimal transport on a pixel subset, bake the result into a 33^3 LUT by evaluating on a regular grid, save `.cube`, apply with `ffmpeg -vf lut3d=file.cube` (or `colorchannelmixer`/`curves` for simple cases). Per-shot, applied after exposure normalization; blend LUT strength (e.g. 0.6-1.0) to avoid skin-tone damage. Cost: CPU only, milliseconds per frame; no license issues with NumPy/OpenCV/colour (BSD).
- Reference-match risk: reference frames contain different content (e.g. blue sky vs indoor); match on matched-semantic regions (or via SAM masks) or use few-parameter transforms (exposure, white balance, contrast curve, saturation) fitted robustly. This is a design inference.
- NeuralPreset / image-adaptive 3D LUT (AdaInt etc.): not fetched; assume research code with non-commercial or unclear terms until checked.

### Gaps
- No sourced evaluation of any method; NeuralPreset, AdaInt, SA-3DLUT repos and licenses not retrieved; FFmpeg `lut3d` documentation not fetched (local machine has no ffmpeg; ffmpeg.org fetch failed in shell). ColorMatch3D license unverified.

---

## 8. Aesthetic / quality scoring to pick the best take

### Takeaway
The well-known video quality models (DOVER, Q-Align) are non-commercial (S-Lab license). For commercial scoring use LAION's improved-aesthetic-predictor (Apache-2.0, CLIP-based, frame-level) plus cheap heuristics (sharpness/Laplacian variance, exposure, motion stability); or an LLM/VLM rubric call.

### Cited Findings
- DOVER (VQAssessment): S-Lab License 1.0 non-commercial; 538 stars, last push 2024-08-12 — [license via GitHub API](https://github.com/VQAssessment/DOVER).
- Q-Align (Q-Future): same S-Lab non-commercial license; 632 stars, last push 2026-06-24 — [GitHub](https://github.com/Q-Future/Q-Align).
- LAION improved-aesthetic-predictor: Apache-2.0, 1.3k stars, last push 2024-07-01 (stable, stale) — [GitHub](https://github.com/christophschuhmann/improved-aesthetic-predictor).

### Inferences
- Take selection score = weighted sum of: LAION aesthetic on 3-5 sampled frames (CLIP ViT-L embeddings are open), blur (variance of Laplacian), exposure/clipping histogram, shake (vidstab detect transform magnitude), face-visible/centered (MediaPipe), plus a relevance score (CLIP similarity to the slot's shot description). FAST-VQA and MUSIQ were not checked (MUSIQ's official TF code is Apache-2.0 per training knowledge; unverified).
- An alternative is a single Gemini Flash call with a rubric over 4 frames (costs cents; relevance is the main benefit); not priced here.

### Gaps
- FAST-VQA and MUSIQ licenses, speed, and correlation with human MOS not retrieved; no sourced evidence that LAION aesthetic scores correlate with Reel engagement.

---

## 9. Aggregator APIs as a single integration point

### Takeaway
fal.ai is the best single integration: it lists Kling 3/O3 (including V2V edit and reference-to-video), MiniMax H3, Grok Imagine, PixVerse V6, FLUX 3, Nano Banana family, Seedream, BiRefNet, Bria RMBG, SeedVR2, SAM 3, FILM, and video background removal, with transparent per-unit prices. Replicate is GPU-second priced and better for custom open models; Runway's API is vertically integrated (Gen-4.5, Aleph, Veo, Magnific, frame-rate).

### Cited Findings
- fal.ai prices (see sections 1-3, 6): image — Nano Banana $0.0398/image, Nano Banana 2 $0.08, Nano Banana Pro $0.15, Seedream 4.5 $0.04, FLUX 2 $0.012/MP, FLUX.1 schnell $0.003/MP, GPT Image 2 and Nano Banana 2.1 listed "$1/unit" (unit undefined), Seedream 5.0 Pro $0.0675/unit — [fal.ai pricing](https://fal.ai/pricing).
- fal bills video models per second or per video depending on model; third-party pages disagree with each other on many rates, so fal's own page is authoritative — [search summary](https://fal.ai/pricing).
- Replicate: pay per second of GPU (L40S $0.000975/s, H100 $0.001525/s), private models billed for idle time; Wan 2.1 I2V 720p $0.25/s — [Replicate pricing](https://replicate.com/pricing).
- Runway: $0.01/credit; Veo 3.1 hosted in the Runway API; Magnific upscale, Enhance Frame Rate — [Runway pricing](https://docs.dev.runwayml.com/guides/pricing/).
- Together AI and Runware: not retrieved except a Runware Topaz quote ($0.080/s 1K, $0.175/s 4K) from a blog.

### Inferences
- Python integration effort: `fal_client.subscribe("fal-ai/kling-video/v3/pro/image-to-video", arguments={...})` style call per model (training knowledge on client API shape; not verified this session) — one SDK, uniform queue/webhook pattern, so a `generate_clip(provider_model, ref_image, prompt, seconds)` adapter plus a cache keyed by hash is a day of work. Gemini (Omni Flash, Nano Banana) and Runway need their own SDKs; Seedance 2.5 and Wan 3.0 are not on fal's price page (BytePlus ModelArk, Alibaba Model Studio, or resellers like Atlas Cloud).
- Reseller aggregators (AtlasCloud, WaveSpeed, EvoLink, Segmind, Unifically) are mostly SEO-heavy; their prices are not trustworthy for planning.

### Gaps
- Together AI and Runware model coverage/prices not fetched. fal's rate limits, concurrency caps, SLAs, and data retention/commercial-use terms not checked. Whether fal's Kling/MiniMax endpoints carry output licensing indemnity is unknown. Replicate's per-model video prices beyond Wan 2.1 not fetched.

---

## 10. Recommended combination (quality per dollar, low integration effort)

### Takeaway
Run a deterministic-first pipeline and use models only to fill gaps: FFmpeg + vidstab + LUT for shake and grade, SAM 2 + MediaPipe + BiRefNet for tracking/cutouts, Practical-RIFE or hosted FILM for slow-mo, FlashVSR for upscaling, and fal.ai for generation (Nano Banana -> MiniMax H3 / Kling 3.0 I2V). Avoid S-Lab/CC-BY-NC/AGPL components.

### Cited Findings
(Evidence is in sections 1-9; the picks are synthesis.)

### Inferences (design recommendation; not sourced as a whole)
| Job | Pick (MVP) | Upgrade | Why / cost | Avoid |
|---|---|---|---|---|
| Missing-shot B-roll | fal `minimax/h3-max-turbo/image-to-video` ($0.025/s) or `h3-max` ($0.05/s) from a Nano Banana start frame ($0.04/img) | Kling v3 Pro $0.14/s; Seedance 2.5 via BytePlus for hero shots; Gemini Omni Flash for extend/edit | 4 s about $0.10-0.56 plus retries; AA Elo 1130 for H3 vs 1000 Kling 3.0 baseline | Sora (dead), Veo preview IDs, open-weight Hunyuan/MiniMax in EU/UK/US |
| Restyle / object removal | Kling O3 Edit $0.14/s | Runway Aleph $0.28/s; Wan VACE self-host (Apache-2.0) | only when LUT is insufficient | default V2V |
| Upscale | FlashVSR self-hosted (Apache-2.0) | SeedVR2 for faces; Topaz API $0.06-0.18/s | gate by source resolution | Real-ESRGAN (stale), Video2X (AGPL) |
| Slow-mo | Practical-RIFE (MIT) | hosted FILM $0.0013/s | seconds per clip | GIMM-VFI (non-commercial) |
| Stabilize | FFmpeg vidstab two-pass | Gyroflow when gyro data exists (GPL-3.0) | CPU, free | deep stabilizers (unevaluated) |
| Segmentation/tracking | SAM 2 (Apache-2.0) + MediaPipe + ByteTrack (MIT) | SAM 3 after legal review | free; produces crop-keyframes for reframe and text-follow | Ultralytics YOLO (AGPL) unless licensed |
| Matting / green-screen | BiRefNet (MIT) per frame, or fal video BG removal about $0.008/s | MatAnyone after commercial license | about $0.04 per 5 s hosted | RMBG-2.0 / MatAnyone / RVM (GPL) without license |
| Color match | Lab/histogram/OT fit -> `.cube` -> FFmpeg `lut3d` | per-region (SAM-masked) matching | CPU only | non-commercial neural LUT code |
| Take scoring | LAION aesthetic + heuristics + CLIP relevance (+ VLM rubric) | Gemini rubric call | cents | DOVER, Q-Align (non-commercial) |
| Integration | fal client for all hosted models behind one `generate()` adapter with content-hash cache | add BytePlus/Alibaba direct for Seedance/Wan 3 | one key, uniform pricing | multiple reseller accounts |

- Budget for a Reel with two generated 4 s fills (H3 Max, one retry each): about $0.8-1.0 plus $0.08-0.16 for stills; swapping to Kling v3 raises it to about $2.2-2.5. Everything else in the table is under $0.10 per Reel.
- Order of operations per shot: trim -> stabilize (if needed) -> upscale (if needed) -> reframe via tracked crop -> color LUT -> speed/interpolation -> encode intermediate. Generated clips skip stabilization.

### Gaps
- No empirical test of this stack was run; all model-quality statements for non-generation tasks (RIFE vs minterpolate, vidstab, LUT quality) rely on general knowledge, not measurement. The user's actual GPU/hosting constraints are unknown, which decides self-host vs hosted for FlashVSR/RIFE/SAM 2.
- Legal items (SAM License, LTX Community License revenue threshold, MiniMax/Hunyuan territory clauses, AGPL exposure) need counsel review before shipping; I read the SAM 3, S-Lab, and Hunyuan license text from GitHub but not the LTX or MiniMax license text.
