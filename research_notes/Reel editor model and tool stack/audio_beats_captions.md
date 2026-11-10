# Audio and Caption Layer for an AI Reel Template Editor (as of Nov 2026)

Scope note: builds on `AI reel editor competitor landscape/video_understanding_models.md`, which only says "librosa/madmom beat tracking vs cut times (not researched)" and "beat-sync detection tooling and OCR options not researched". Nothing here repeats that file. Research budget was ~15 tool calls, so many items are only partly verified; unverified background knowledge is kept out of "Cited Findings" and labelled in "Inferences" / "Gaps".

## 1. Beat / downbeat / tempo / structure detection (librosa vs madmom vs Beat This! vs allin1 vs essentia vs BeatNet)

### Takeaway
Beat This! (CPJKU, ISMIR 2024, MIT) is the best-documented modern beat+downbeat tracker: it needs no DBN post-processing, runs from `pip`, and beats prior SOTA F1 on most datasets, but its continuity scores are lower and it is weak on odd material (SMC F1 62.7). All-In-One (allin1, MIT) adds tempo plus intro/verse/chorus segments but is a Windows pain (NATTEN built from source, madmom from git). I found no head-to-head MIREX/GTZAN numbers for madmom, BeatNet, essentia or librosa vs Beat This! in this session.

### Cited Findings
- Beat This! repo: MIT license for code and weights (some training files carry other licences), 466 stars, 245 commits; outputs beats AND downbeats; `pip install beat-this` (needs PyTorch >=2, tqdm, einops, soxr, rotary-embedding-torch); CLI `beat_this audio -o out.beats`; Python `File2Beats(checkpoint_path="final0", device="cuda", dbn=False)`; `--gpu=-1` forces CPU; `--float16` may speed up; ffmpeg only needed for non-wav input; no Windows-specific guidance. Last-commit date not visible on the page. — [CPJKU/beat_this](https://github.com/CPJKU/beat_this)
- Beat This! paper abstract: drops the DBN post-processor, uses a shift-tolerant loss and conv+transformer architecture; "surpasses the current state of the art in F1" but "scores lower on continuity metrics" and still fails on difficult/underrepresented genres. — [arXiv 2407.21658](https://arxiv.org/abs/2407.21658)
- Beat This! 8-fold CV F1 (beat / downbeat, %): Ballroom 97.5/95.3, Beatles 94.5/88.8, Hainsworth 91.9/80.0, Harmonix 95.8/90.7, RWC Pop 96.1/93.7, SMC 62.7/n.a. (annotated beats only). Compared against Hung et al. (SpecTNT) only, e.g. Hainsworth beat 87.7, SMC 60.5. — [arXiv 2407.21658 HTML](https://arxiv.org/html/2407.21658)
- GTZAN test: Beat This! main F1 89.1 beat / 78.3 downbeat (CMLt 79.8, AMLt 89.8); Hung et al. 88.7 / 75.6 (CMLt 81.2, AMLt 92.0); small model 88.8 / 77.2. Params: main ~20M, small ~2M, Hung ~4M. Paper has no madmom/BeatNet/allin1 comparison and no inference speed. — [arXiv 2407.21658 HTML](https://arxiv.org/html/2407.21658)
- Beat This! default DBN parameters (optional add-on) are madmom's defaults; madmom's DBN is not part of the default pipeline. — [PyPI beat-this](https://pypi.org/project/beat-this/)
- 2026 failure-mode study: on SMC (8-fold) Beat This! F=0.627, CMLt=0.514, AMLt=0.610; routing Beat This! output through madmom's DBN lowers F-measure on many tracks; setting DBN min/max BPM to ground truth helps CMLt but not F; a per-track tuned DBN reached F=0.642 (oracle, not deployable). — [arXiv 2605.12287](https://arxiv.org/html/2605.12287)
- All-In-One (allin1): MIT, 878 stars, only 38 commits (low activity); predicts BPM, beats, downbeats, functional segment boundaries and labels (intro/verse/chorus/bridge/outro); trained on Harmonix Set with 8-fold CV (paper arXiv 2307.16425); speed: 10 songs / 33 min in 73 s on an RTX 4090; dependencies: PyTorch, NATTEN (must be built from source on Windows with git/make/ninja), madmom installed from GitHub, Demucs used internally, FFmpeg optional. No accuracy numbers on the README. — [mir-aidj/all-in-one](https://github.com/mir-aidj/all-in-one)

### Inferences
- For a reel (15-60 s, pop/EDM/trending-audio, often with voice-over on top) the right call is: Beat This! (CPU is fine for short clips) as the primary beat/downbeat source, run on the isolated music stem (section 3) rather than the mixed track. Keep librosa for cheap onset/RMS/spectral-flux features and for cut-to-beat snapping math.
- allin1 structure labels are trained on full songs (Harmonix); on 15-60 s clips with a drop, section labels will be coarse. Cheaper alternative for "where is the drop": onset-strength/RMS envelope change-points from librosa. Treat allin1 as optional because of the NATTEN/madmom install on Windows.
- Beat This! weak spots (SMC 62.7, RWC Classical 77.1) are not reel-typical; expect ~90+ F1 on beat-driven pop/EDM, but verify on 20 real reels with hand-tapped beats.
- Use tempo-doubling/half ambiguity checks: beats from Beat This! are frame-wise; derive BPM from median IBI and snap cut times to the nearest beat within a tolerance (e.g. +/-40 ms) rather than trusting absolute alignment.

### Gaps
- No verified MIREX or GTZAN F-measure for madmom, BeatNet, essentia (RhythmExtractor2013 / BeatTrackerMultiFeature) or librosa.beat_track; none of these repos was fetched, so licences/maintenance status are unverified here. From background (unverified this session): madmom code is BSD but its models are CC BY-NC-SA (non-commercial) and the project has seen little maintenance; essentia is AGPLv3 (commercial licence available); BeatNet is CC-BY 4.0 with a modern-numpy/Windows install history; librosa is ISC and well maintained but its beat tracker is a classic dynamic-programming method that is clearly less accurate than neural trackers. Verify each before choosing.
- Beat This! last-commit date and Windows-specific install experience not found.
- No source comparing allin1 vs Beat This! accuracy directly.

## 2. Speech transcription with word-level timestamps (WhisperX, faster-whisper, whisper-timestamped, Parakeet/Canary, Distil-Whisper, CrisperWhisper, stable-ts; Deepgram, AssemblyAI, ElevenLabs Scribe, Gemini)

### Takeaway
No independent benchmark exists comparing word-timing error across all of these. The only hard timing numbers found are vendor-run: CrisperWhisper claims 29.6 ms mean word-boundary error vs WhisperX 64.8 ms on TIMIT (but CrisperWhisper weights are non-commercial). For a product, WhisperX (BSD-2, wav2vec2 forced alignment) is the safe open default, and ElevenLabs Scribe v2 / Deepgram Nova-3 / AssemblyAI are the API options; you must run your own timing test against a hand-labelled or forced-aligned reference.

### Cited Findings
- WhisperX: BSD-2-Clause, 25.1k stars, 179 open issues; batched inference "70x realtime with large-v2"; alignment via language-specific wav2vec2 models, up to 30-100x faster alignment with Numba; plain Whisper timestamps "can be inaccurate by several seconds"; faster-whisper backend needs <8 GB GPU for large-v2; diarization via pyannote needs an HF token; known limits: tokens outside the alignment dictionary (e.g. "£13.60") cannot be aligned, overlapping speech handled poorly; Windows GPU needs CUDA toolkit 12.8, and "may also need ffmpeg, rust". — [m-bain/whisperX](https://github.com/m-bain/whisperX)
- CrisperWhisper 2.0: MIT inference code but weights are non-commercial research licence (commercial licence from Nyra required; Pro models commercial-only); 1.5k stars; vendor benchmark: mean word-boundary error 29.6 ms vs WhisperX 64.8 ms on TIMIT read speech, 41 ms on conversational speech (no WhisperX figure given); verbatim by default (keeps fillers, stutters). Vendor disfluency-F1 table: CrisperWhisper 2.0 Pro 93.5, 2.0 87.8, ElevenLabs Scribe v2 79.2, AssemblyAI Universal-3 Pro 30.5. All vendor-run. — [nyrahealth/CrisperWhisper](https://github.com/nyrahealth/CrisperWhisper)
- An aggregator ranks ElevenLabs Scribe v2 highest among services returning native per-word timestamps; AssemblyAI Universal-3 Pro, Deepgram Nova-3 and Speechmatics also emit them; the ranking follows overall accuracy, "timestamp granularity isn't independently benchmarked". Deepgram's WER claims are on its own test set. — [web3aiblog comparison](https://www.web3aiblog.com/blog/speech-to-text-models-compared-whisper-deepgram-assemblyai-elevenlabs-2026)
- Parakeet TDT: no word-timestamp accuracy figure found. A dataset paper (Granary) reports TDT-decoder timestamps give high-quality segment-level alignment while Whisper segment timestamps were weak at word alignment. — [arXiv 2505.13404](https://arxiv.org/pdf/2505.13404)
- Edinburgh paper evaluates a Whisper attention-based aligner against WhisperX and CrisperWhisper at 20-100 ms tolerances, using MFA-style references; alignments were close to MFA. — [arXiv 2509.09987](https://arxiv.org/html/2509.09987v1)
- Montreal Forced Aligner is the common reference for measuring word-timing error; forced alignment (known transcript, find times) differs from recogniser-native timestamps. — [Soniox wiki](https://soniox.com/wiki/timestamps-forced-alignment)
- API batch prices per audio hour (sources conflict, third-party aggregators): ElevenLabs Scribe v2 ~$0.22 (realtime ~$0.39); Deepgram Nova-3 ~$0.26 (another source ~$0.46; Soniox page $0.39 multilingual); AssemblyAI Universal-3.5 Pro ~$0.21 (Soniox page $0.33), diarization/prompting extra. — [CometAPI/aggregator search results](https://www.cometapi.com/es/best-speech-to-text-apis/), [Soniox pricing comparison](https://soniox.com/compare/stt/pricing)
- Scribe v2 lists word-level timestamps, diarization and audio tagging. — same aggregator results as above; AssemblyAI compare page: [assemblyai.com/compare/scribe-v2-vs-assemblyai](https://www.assemblyai.com/compare/scribe-v2-vs-assemblyai) (vendor)

### Inferences
- Reel speech is short (<60 s), noisy, music-over-voice, slang, code-switching. Run ASR on the separated vocal stem (section 3) to cut hallucinations and improve timing; keep a VAD gate.
- Practical pipeline: transcribe (faster-whisper large-v3 or an API) -> force-align with WhisperX/wav2vec2 (or MFA) -> snap word boundaries to nearest 10 ms frame. For karaoke highlight, 30-60 ms error is below perceptual threshold at 30 fps (one frame = 33 ms), so WhisperX-level accuracy is probably sufficient; the vendor 29.6 vs 64.8 ms gap is likely invisible in captions.
- Because the system "recreates" a reference reel, the reference captions may be burned-in text, not speech. Then OCR + frame timing (video-side), not ASR, is the ground truth for caption timing; keep both paths.
- Commercial-safe default: WhisperX/faster-whisper (open) with an API fallback (Scribe v2 or Deepgram) for hard audio. Avoid CrisperWhisper weights unless licensed.

### Gaps
- Licence/maintenance for faster-whisper (background: MIT, CTranslate2-based), whisper-timestamped (background: AGPL-3.0), stable-ts (background: MIT), Distil-Whisper (background: English-only, MIT), Parakeet TDT 0.6B v3 / Canary (background: CC-BY-4.0 NVIDIA) were not verified this session.
- Gemini word-level timestamp accuracy and pricing: not researched (earlier notes cover Gemini for video understanding only). Background: LLM-generated timestamps are typically coarser than forced alignment; treat as unverified.
- No independent word-boundary benchmark across APIs; Deepgram/AssemblyAI/ElevenLabs timing accuracy numbers not found.
- Exact WhisperX last release date not visible on the fetched page.

## 3. Source separation (Demucs/HTDemucs, BS-RoFormer, MDX, audio-separator)

### Takeaway
`python-audio-separator` (MIT, 1.5k stars) is the one-stop wrapper: it runs BS-RoFormer / Mel-Band RoFormer / MDX / VR / Demucs models. Reported SDR: BS-RoFormer vocals 12.9 vs htdemucs_ft 10.8 and htdemucs 10.0, so RoFormer wins for vocals/instrumental splits. On Windows use CUDA (NVIDIA); DirectML falls back to CPU for RoFormer.

### Cited Findings
- python-audio-separator: MIT, 1.5k stars, 390 commits; wraps MDX (.onnx), VR (.pth), Demucs (.yaml), MDXC/RoFormer (.ckpt); `pip install "audio-separator[gpu]"` (CUDA 11.8 / 12.2), `[cpu]`, `[dml]`; DirectML: MDX/VR GPU-accelerated, RoFormer (incl. default bs_roformer) runs on CPU, Demucs unsupported; CLI `audio-separator in.wav --model_filename model_bs_roformer_ep_317_sdr_12.9755.ckpt`; models auto-download. Listed SDRs: bs_roformer_ep_317 vocals 12.9 / instrumental 17.0; vocals_mel_band_roformer 12.6; melband_roformer_big_beta4 12.5; htdemucs_ft vocals 10.8 (drums 10.1, bass 11.9); htdemucs vocals 10.0. — [nomadkaraoke/python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator)
- Community benchmark (unverified against original): HTDemucs ~1.3 dB below BS-RoFormer on average (SDX23); BS-RoFormer ~1.5-3x real time vs ~4-6x for default HTDemucs on its test hardware; htdemucs_ft closes most gap at ~4x inference time. — [dev.to benchmark](https://dev.to/codesugar_lin_037a57b06a4/htdemucs-vs-bs-roformer-vs-spleeter-a-2026-audio-source-separation-benchmark-2ll8)
- Mel-Band RoFormer paper (music source separation): [arXiv 2310.01809](https://arxiv.org/html/2310.01809v1).

### Inferences
- Separate once, early: vocals -> ASR/forced alignment; instrumental -> beat tracking, music ID, CLAP/MERT embeddings, "which part is music vs SFX".
- Two-stem (vocal/instrumental) is all the pipeline needs; skip 4-stem. Use a RoFormer vocal model (about 12.5-13 SDR) for quality and `htdemucs` only if install risk matters.
- Cost per reel is small (short clips); GPU optional but RoFormer on CPU will be slow (minutes per minute of audio is plausible, not measured).
- Check licences of the specific checkpoint (community UVR checkpoints have mixed/unclear licences) before shipping commercially.

### Gaps
- Demucs repo status: background says facebookresearch/demucs was archived in early 2025 with the author's fork continuing; not verified this session. Treat as potentially stale.
- Checkpoint licences for BS-RoFormer (viperx) / Mel-Band (KimberleyJensen) weights not verified.
- Real-time-factor on CPU/GPU for 30 s clips not measured.

## 4. Music identification and similar-track matching (ShazamIO, Chromaprint/AcoustID, AudD; CLAP/MERT; royalty-free APIs)

### Takeaway
Identification of the exact track in a reference reel: ShazamIO (MIT, unofficial/reverse-engineered, 12 s window) is the free first try; AudD/ACRCloud are paid commercial fallbacks. "Find a similar royalty-free track" is not solved by fingerprinting, it needs embeddings (CLAP/MERT, not researched this session) plus a catalogue with API (Epidemic Sound partner API; Jamendo for CC music).

### Cited Findings
- ShazamIO: MIT, ~1.0k stars, 502 commits; "reverse engineered Shazam API" (asyncio/aiohttp); recognises from file/path/bytes; signature uses a 12 s window (from 15 s "Shazam finds nothing at all"); warns Shazam "sometimes answers with a confident match for the wrong track"; `max_skew` rejects some false matches but also rejects sped-up/slowed/pitch-shifted audio (off by default); Python 3.10+ vs 3.11+ stated inconsistently; text search goes via iTunes index. No legal/ToS section. — [shazamio/ShazamIO](https://github.com/shazamio/ShazamIO)
- AudD: 300 free recognition requests at signup; streaming pricing $45/stream/month on AudD DB, $25 with own content; enterprise endpoint handles files of any length. — [AudD](https://audd.io/) (via search summary of third-party aggregators)
- ACRCloud: usage-based pricing not public (console login), 14-day free trial. — [ACRCloud docs](https://docs.acrcloud.com/tutorials/recognize-music)
- Epidemic Sound Partner API: gated by partnership agreement; self-serve free key for prototyping; catalogue search by mood/genre/keyword with metadata, previews, download URLs; third-party wrapper mentions similar-track / semantic search. — [Epidemic Sound developers](https://www.epidemicsound.com/business/developers/), [free API blog](https://www.epidemicsound.com/blog/free-api/), [docs](https://developers.epidemicsound.com/docs/)
- Jamendo: CC-licensed catalogue, REST API, non-commercial apps up to 35,000 requests/month with client ID; commercial use needs separate licensing. — [FreeAPIHub Jamendo](https://freeapihub.com/apis/jamendo-api) (aggregator)
- Pixabay Music: no API documentation found; website says free for personal and commercial use without attribution (aggregator description). — search result only; no primary link.

### Inferences
- Trending-audio reality: most Reels use platform-licensed popular tracks or original audio; a royalty-free replacement is a legal necessity for non-platform use, not just a similarity problem. Output to the user: "identified track: X (Shazam), suggested licensed alternatives: top-k by embedding similarity of tempo/energy/mood".
- Chromaprint/AcoustID matches identical recordings against MusicBrainz and will fail when voice-over, speed change or heavy mixing is present; run it on the separated instrumental stem if used at all.
- Matching recipe: tempo (Beat This!) + key + energy curve filter, then CLAP (LAION-CLAP, text+audio) or MERT cosine ranking over the licensed catalogue; precompute catalogue embeddings once.
- ShazamIO is a scrape of a private API: fine for MVP, risky for production (ToS, breakage). Budget for AudD/ACRCloud.

### Gaps
- CLAP / MERT model cards, licences (background, unverified: LAION-CLAP Apache-2.0; MERT weights CC-BY-NC-4.0, so non-commercial) and any benchmark on music-similarity retrieval were not researched.
- Chromaprint/AcoustID licence (background: LGPL; AcoustID web service has non-commercial free tier) not verified.
- Whether any royalty-free API (Epidemic, Artlist, Pond5, Jamendo, Pixabay) supports BPM filtering or audio-similarity queries: not confirmed.
- ShazamIO last-commit date and Windows behaviour: not found. Reliability on reel audio (music under voice): no data.

## 5. Caption rendering and styling for viral-style captions (libass/ASS, pycaps, captacity, Remotion, font ID)

### Takeaway
Only pycaps was verified: MIT, CSS-styled word-state animations (`.word-being-narrated`), emoji and sound-effect insertion, but it is alpha (230 stars), renders via Playwright/Chromium by default and is not on PyPI. For the existing FFmpeg+libass stack, ASS karaoke tags are the lowest-effort route to word-by-word highlight and pop effects; Remotion caption templates are the higher-fidelity alternative. Font identification from a frame was not researched.

### Cited Findings
- pycaps (francozanardi): MIT, 230 stars, 52 forks, 208 commits, alpha, installs from GitHub (a PyPI fork `pycaps-ai` exists); templates + CSS styling incl. state selectors like `.word-being-narrated`; word tagging via regex/word lists/AI; built-in animations (fade, pop, slide) and effects (typewriting, emoji insertion, sound effects); default `CssSubtitleRenderer` needs Playwright + Chromium; optional `PictexSubtitleRenderer` without a browser supports only a CSS subset and differs visually, especially shadows; uses Whisper or faster-whisper; Python 3.10-3.12, FFmpeg on PATH; no Windows statement. — [francozanardi/pycaps](https://github.com/francozanardi/pycaps), [PyPI pycaps-ai](https://pypi.org/project/pycaps-ai/)
- wordcaps: separate Whisper-based tool with word-highlight style and CLI. — [PyPI wordcaps](https://pypi.org/project/wordcaps/)
- Tutorial on content-aware animated subtitles with pycaps. — [DEV Community](https://dev.to/francozanardi/how-to-create-content-aware-animated-subtitles-with-python-24dn)

### Inferences
- libass route (from standard ASS spec knowledge, not sourced this session): per-word timing with `{\k}`/`{\kf}` karaoke tags or one Dialogue event per word-state; pop/bounce via `{\t(start,end,\fscx120\fscy120)}` with a decaying scale, stroke via `\bord` + `\3c`, shadow via `\shad` + `\4c`, highlight colour via `\1c`/`\2c`, position via `\an`/`\pos`; emoji need a font fallback or separate PNG overlays because libass does not render colour emoji reliably. Validate each of these in a small test render.
- Recommended: generate ASS from (word, start, end, style-preset) records; one preset per reference style (font, size, primary/outline/shadow colours, outline width, alignment, highlight colour, pop scale). Keep pycaps only if CSS-level effects (rounded boxes, gradients) are needed; the Chromium dependency and alpha status make it heavy for the backend.
- Style extraction from reference: sample caption pixels for fill/stroke colours via OCR box + colour clustering; estimate font size from text-box height; match font from a candidate list of popular reel fonts (Montserrat ExtraBold, Anton, Bebas Neue, Poppins, Komika etc.) by rendering and comparing, rather than a trained WhatTheFont model.

### Gaps
- Captacity, auto-subtitle, Remotion caption templates/`@remotion/captions`, Submagic-style open clones: not fetched; licences/status unknown.
- Open font-identification models (WhatTheFont-like; e.g. DeepFont-style or CLIP-based font retrieval): not researched; no verified open model.
- libass limits (blur edge, per-glyph animation, colour emoji) not verified against docs.
- Reproduction fidelity numbers (SSIM/visual match vs reference) not available.

## 6. Voiceover / TTS (briefly)

### Takeaway
Commercially safe open options are Kokoro-82M (Apache-2.0, CPU-capable) and Chatterbox (MIT, voice cloning, ~8-10 GB GPU suggested); XTTS v2 and F5-TTS official weights are non-commercial. ElevenLabs is the API option (pricing not researched).

### Cited Findings
- XTTS v2: weights under Coqui Public Model License (non-commercial), Coqui shut down Jan 2024; code MPL-2.0. — [localaimaster XTTS licence](https://localaimaster.com/blog/xtts-coqui-commercial-license)
- F5-TTS: code MIT, official weights CC-BY-NC-4.0. — [aivideosensei comparison](https://aivideosensei.com/compare/kokoro-vs-chatterbox-vs-xtts), [HF discussion](https://huggingface.co/SWivid/F5-TTS/discussions/7)
- Kokoro-82M Apache-2.0, runs on CPU; Chatterbox MIT with cloning, needs GPU (~8-10 GB). Blog-level sourcing; model repos not checked. — [localaimaster best local TTS](https://localaimaster.com/blog/best-local-tts-models), [nerdynav](https://nerdynav.com/open-source-ai-voice)

### Inferences
- Voice cloning of a person's voice triggers the AI-label/consent issues already noted in `legal_platform_privacy.md`; default to stock voices.

### Gaps
- ElevenLabs TTS pricing/latency, Chatterbox/Kokoro quality benchmarks (MOS), and word-timestamp output from TTS engines: not researched. (ElevenLabs API returns character-level alignment per background knowledge, unverified.)

## 7. Loudness and mixing for Reels (LUFS, ducking, loudnorm)

### Takeaway
Most secondary sources say target about -14 LUFS integrated with -1 dBTP true-peak ceiling for Reels/TikTok/Shorts; no official platform doc was found, and one outlier recommends -10 to -12 LUFS.

### Cited Findings
- Consensus -14 LUFS / -1 dBTP; platforms normalise down but (for YouTube) do not boost quieter audio; some suggest -15 LUFS to avoid platform compression; outlier -10 to -12 LUFS at -1.5 dBTP for mobile. All third-party. — [Opus Pro blog](https://opus.pro/blog/best-loudness-normalizers), [dev.to LUFS -14 standard](https://dev.to/arthurvalle1_a2586dd2b4bc/mastering-for-reels-tiktok-and-youtube-shorts-the-lufs-14-standard-2ck5), [OpenClip](https://openclip.app/learn/audio-normalization)

### Inferences
- FFmpeg recipe (standard FFmpeg filter usage, not sourced this session; test before shipping): two-pass `loudnorm=I=-14:TP=-1.0:LRA=11` with measured values on the final mix; music ducking with `[music][voice]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=300` then `amix`; music bed around -18 to -22 LUFS under speech, voice around -14 LUFS after loudnorm. Normalise the final mix once, not the stems separately.
- When the user wants to preserve reference music loudness character, match integrated LUFS and crest factor of the reference rather than a flat -14.

### Gaps
- No official Instagram/TikTok/YouTube specification found; platform behaviour (normalising vs not) unconfirmed for Instagram and TikTok.
- FFmpeg `loudnorm`/`sidechaincompress` parameters not verified against FFmpeg docs this session.

## 8. Recommended combination for highest quality

### Takeaway
Separate first, then analyse each stem: audio-separator (BS-RoFormer vocal model) -> Beat This! on the music stem + librosa features -> ASR (faster-whisper/API) on the vocal stem + WhisperX forced alignment -> ASS captions rendered by existing libass -> FFmpeg mix with sidechain ducking and two-pass loudnorm at about -14 LUFS / -1 dBTP.

### Cited Findings
- Components and licences as cited above: Beat This! MIT, WhisperX BSD-2-Clause, python-audio-separator MIT, ShazamIO MIT, pycaps MIT, Kokoro Apache-2.0 / Chatterbox MIT (blog-level).

### Inferences
- Pipeline: (1) ffmpeg extract audio -> (2) audio-separator vocals/instrumental -> (3a) Beat This! beats+downbeats on instrumental, BPM from median IBI; librosa onset envelope for drop/energy curve; (3b) ASR on vocals -> WhisperX alignment -> word list with start/end; if the reference has no speech, OCR the burned-in captions and time them from frames; (4) ShazamIO on the instrumental/full mix (12 s windows at several offsets, vote), AudD fallback; embeddings (CLAP) for licensed alternatives; (5) caption style record -> ASS; (6) cut-to-beat snapping, ducking, loudnorm.
- Integration effort on Windows (my estimate, not measured): audio-separator, Beat This!, WhisperX = pip + CUDA setup, hours; allin1 = NATTEN source build, days; pycaps = Playwright/Chromium, hours but heavy; ShazamIO = pip, minutes.
- Build a 20-reel evaluation set (hand-tapped beats, hand-checked word times) before trusting any of the above; the key accuracy numbers here are either academic datasets unlike reels or vendor-run.

### Gaps
- Items marked unverified in sections 1-7 (madmom/essentia/BeatNet details, Demucs archive status, CLAP/MERT licences, Gemini timestamp quality, font ID models, Remotion captions, official platform loudness specs) should be checked before they enter the final report.
