# Reel editor stack and free tiers guide

This guide joins two earlier reports into one, written in plain language:

- `Reel editor model and tool stack.md`: which AI models, MCP servers and editing tools to use.
- `Reel editor stack free tiers.md`: what you can use for free while you build.

All facts come from public web pages read on 4 November 2026. Nothing here has been tested hands-on. Prices and free plans change often, so check a vendor's page before you depend on a number. Where a number is our own estimate or a guess, the text says so.

---

## 1. The short version

1. **Do not use one AI for everything.** Use small, exact tools to measure facts, such as where each cut is, what text is on screen, and where the beats are. Then use AI models to describe meaning and make plans. The best AI video model (Gemini) was 2 to 4 seconds off when it guessed where cuts are. A dedicated cut detector was about 1.8 seconds off and is far cheaper.
2. **The recommended stack:**
   - **Measurement tools:** TransNetV2 for cuts, PP-OCRv5 for on-screen text, OpenCV for camera motion, Beat This! for music beats, and WhisperX for spoken words.
   - **Gemini 3.8 Flash** describes each shot.
   - **Claude Sonnet 5.5** plans the edit, matches your clips and handles chat changes.
   - **FFmpeg** makes the final video. **HyperFrames** can be added later for fancy animated captions.
3. **Fix this now:** `mcp-video` has been renamed **Kinocut**. Change your `requirements.txt` to use `kinocut` and call it as a normal Python library.
4. **MCP servers are for you, not for the app.** Use them in Claude Code while you build. Keep them out of the app's video pipeline.
5. **License traps:** some popular tools cannot be used in a paid product, or they cost money once your company grows. Examples are Remotion, Ultralytics YOLO, RMBG-2.0 and CrisperWhisper. See section 10.
6. **Cost per reel (our estimate):** about **$0.15 to $0.30** for a normal reel. About **$1 to $3.50** if the reel needs two AI-generated filler shots.
7. **Free plans:** you can build almost the whole app for free. You need about **$10 once** for the Claude planner through OpenRouter. AI-generated filler shots have no free option.
8. **TwelveLabs free plan:** 3 GB of storage plus a monthly usage allowance whose size is not published. It stops hard when you hit the limit.
9. **Data warning:** Google may use anything you send through the free Gemini key to improve its products, and staff may read it. India gets no exemption. Only send test clips you own.
10. **Startup credits you can get without investors:** Cloudflare ($10k), AWS ($1k to $5k) and Microsoft ($1k to $5k, but reports of problems). Anthropic's startup program is closed.

---

## 2. Words you will see

| Word | Meaning |
|---|---|
| **Template / blueprint** | The recipe of a reference reel: how many shots, how long each is, where text appears, what style, where cuts land on the beat. |
| **LLM** | A text AI model, such as Claude or GPT. It reads and writes text and can call tools. |
| **VLM** | A vision-language model. It can look at images or video and describe them, such as Gemini. |
| **Embedding** | A list of numbers that captures what a clip is about, so you can search clips by meaning ("find a shot of someone walking"). |
| **OCR** | Reading text from an image, such as captions burned into a video. |
| **ASR** | Turning speech into text with word timings. |
| **Beat detection** | Finding the beats in music so cuts can land on them. |
| **Render** | Building the final video file. |
| **FFmpeg** | Free command-line tool that cuts, joins, colours and encodes video. |
| **libass / ASS** | A subtitle format and renderer. It lets FFmpeg draw styled captions with word-by-word timing. |
| **MCP server** | A plug-in that gives an AI agent new tools, for example "trim video" or "search Figma". |
| **API** | A web service your code calls, usually paid per use. |
| **Free tier** | A free monthly allowance on a paid service. |
| **Credits** | A one-time free balance (for example $200) to spend on a service. |
| **License** | The legal rules for using code or a model. "Apache-2.0", "MIT" and "BSD" are safe for a paid product. "AGPL", "GPL" and "non-commercial" can block you. |
| **Open weights** | A model you can download and run yourself. |
| **JSON schema** | A strict format the AI must follow, so your code can read its output without errors. |

---

## 3. How the app works, step by step

Your app has six steps. The table shows the best tool for each step and whether it is free.

| Step | What happens | Best tool | Free? |
|---|---|---|---|
| 1. Get the reference | User gives a reference reel | A file the user uploads, with a "I have the rights" checkbox | Yes |
| 2. Find the cuts | Find where each shot starts and ends | TransNetV2 or AutoShot. PySceneDetect as backup | Yes, runs on your PC |
| 3. Read on-screen text | Find captions, their position and timing | PP-OCRv5 plus a tracker | Yes, runs on your PC |
| 4. Camera motion | Is it zooming, panning, shaking? | OpenCV maths. Ask the AI only if unsure | Yes |
| 5. Music beats | Where the beats and bars fall | Beat This! on the music-only track | Yes |
| 6. Spoken words | What is said and exactly when | WhisperX on the voice-only track | Yes |
| 7. Split voice and music | Separate the two so steps 5 and 6 work better | audio-separator (BS-RoFormer model) | Yes |
| 8. Describe each shot | Shot size, angle, subject, mood, transition, colour look | Gemini 3.8 Flash, given the cut list from step 2 | Free key for testing |
| 9. Search the user's clips | Find user clips that fit each slot | TwelveLabs Marengo 3.5 or Gemini Embedding 2 | Free tiers exist |
| 10. Plan the edit | Match clips to slots, write the template, handle chat changes | Claude Sonnet 5.5 via OpenRouter (Haiku 5.5 first, Opus 5.5 for hard cases) | No. About $10 for testing |
| 11. Render | Build the video | FFmpeg + libass, through Kinocut | Yes |
| 12. Check the result | Compare render to template, fix problems | Simple checks first, then Gemini as a judge | Mostly free |

**The key idea:** measuring tools produce the facts (steps 2 to 7). The AI only adds meaning (step 8) and makes decisions (step 10). Never let the AI decide where cuts are.

---

## 4. Why not just use one AI model for everything

AI video models are good at saying what is happening. They are bad at saying exactly when.

On one public test ([TransVLM](https://chence17.github.io/TransVLM/), run by the test's own authors), these were the average errors when finding cuts:

| Tool | Average error |
|---|---|
| AutoShot | 1.78 s |
| TransNetV2 | 1.87 s |
| PySceneDetect | 1.93 s |
| Gemini 3 Pro | 2.18 s |
| Gemini 2.5 Pro | 3.62 s |
| Qwen3-VL-8B | 34.4 s |

Developers also report Gemini inventing timestamps that do not exist. The fix is simple:

1. Find cuts with TransNetV2.
2. Tell Gemini: "Describe shot 3, which runs from 2.40 s to 3.85 s."

Now Gemini cannot get the timing wrong, because you gave it the timing.

The exception is slow transitions such as dissolves. For those, send Gemini the 1 to 2 seconds around the cut, because the detectors miss them.

TransNetV2 has not been updated since December 2023, but it still works. PySceneDetect is actively maintained and is a good backup.

---

## 5. Which AI models to use

### Planner and chat: Claude Sonnet 5.5

This model reads the template, picks clips, writes the edit plan as strict JSON and handles "make the captions bigger" style chat.

| Model | Price per million tokens (in / out) | Use it for |
|---|---|---|
| Claude Haiku 5.5 | $0.10 / $0.50 | First try. Cheap. |
| Claude Sonnet 5.5 | $2 / $10 | Default. Good at tools and JSON. |
| Claude Opus 5.5 | $4 / $20 | Hard re-plans only. |
| GLM-5.1, Qwen3.7 Plus | Cheaper | Budget backup. |

Two public leaderboards disagree on which model is best at calling tools. Sonnet 5.5 is in the top three on one of them. Neither leaderboard tests JSON reliability directly. Source: [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).

### Shot description: Gemini 3.8 Flash

Gemini is the only big AI service that accepts video directly. Claude and OpenAI accept only images.

- **Price:** $0.75 / $3.75 per million tokens until 31 December 2026, then double.
- **Bigger model:** Gemini 4 Argon is better but costs $2 / $10, rising to $4 / $20 after 30 November 2026.
- **Size:** a 20 to 30 second reel is about 6,000 to 9,000 tokens.
- **How to call it:** call Google directly, not through OpenRouter. It is unclear whether OpenRouter passes video through correctly.

Source: [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing).

**Free option you can run yourself:** Qwen3-VL (Apache-2.0 license). It is weaker than Gemini, but you can run it on your own GPU.

**TwelveLabs Pegasus:** it can return a table of segments with start time, end time and labels, which is close to what you need. Nobody has compared it fairly against Gemini, so run it side by side as a test instead of making it the default.

### Clip search: Marengo 3.5 or Gemini Embedding 2

- **Marengo 3.5 (TwelveLabs):** use it if you keep a TwelveLabs plan.
- **Gemini Embedding 2:** otherwise use this. It handles video up to 120 seconds but ignores the sound.
- **SigLIP 2:** free, runs on your PC, and uses still frames only.

No one has tested these against each other on short clips. Build a small test of 50 searches over 200 clips before you pick one.

Embeddings are good for finding about 20 possible clips. Then ask an AI to pick the best one, because embeddings get confused by direction ("walking left" vs "walking right") and negation.

---

## 6. Audio and captions

**Order of steps:**

1. **Split voice from music** with audio-separator. Its BS-RoFormer model scores 12.9 on the standard quality measure, against 10.8 for the older Demucs.
2. **Find beats** in the music track with **Beat This!** (MIT license). It scores 97.5 out of 100 on dance music. It is weaker on hard music (62.7).
3. **Find words** in the voice track with **WhisperX** (BSD license). Plain Whisper timings can be off by several seconds. WhisperX fixes this.
4. **Snap cuts** to the nearest beat, within about 40 milliseconds.

**Word timing is good enough.** WhisperX is about 65 milliseconds off. One video frame at 30 fps is 33 milliseconds, so the error is about two frames. CrisperWhisper is more exact (30 ms) but cannot be used in a paid product.

**Captions burned into the reference:** if the reference has text on screen but nobody speaks it, use the OCR timing from step 3 instead.

**Music:**

- **Identify the track:** ShazamIO (free, but it is an unofficial copy of Shazam and sometimes confidently wrong) or AudD (paid backup).
- **Suggest legal music:** pick tracks with a similar speed and energy.
- **Never copy the reference's audio into the output.**

**Caption style:** write captions as ASS subtitles. ASS supports word-by-word highlight, outline, shadow and "pop" scaling, and FFmpeg draws them with libass.

**Loudness:** aim for **-14 LUFS** with peaks under **-1 dBTP**. This comes from creator guides, not official platform pages.

---

## 7. Making the video

### Keep FFmpeg as the main engine

FFmpeg does cutting, speed changes, colour (with a `.cube` colour file through `lut3d`), cropping, zoom, captions, transitions and the final encode. **About 90% of how "right" a reel feels comes from timing, framing, speed, colour and caption style, and FFmpeg can do all of these.** The 90% figure is our estimate.

**Known FFmpeg problems and fixes:**

| Problem | Fix |
|---|---|
| Zoom looks jittery | FFmpeg's `zoompan` moves in whole pixels. Scale the video up about 5 times first, then zoom, then scale down. |
| Transitions fail or use huge memory | Convert every clip to 1080x1920, a fixed 30 fps, and reset timestamps (`setpts=PTS-STARTPTS`) before using `xfade`. |
| Want fancy transitions | `xfade-easing` (MIT) adds about 120 transitions, but it is slow on normal FFmpeg. |

### Kinocut (formerly mcp-video)

- **What it is:** `mcp-video` 1.6.20 now only installs `kinocut==1.16.5`. Kinocut is Apache-2.0 (safe), wraps FFmpeg, and has safety checks and "Video Receipts" that record what was done.
- **What it lacks:** its transitions are limited to glitch, morph and pixelate. Its documentation does not mention speed ramps or zoom/pan. You will need to write your own functions for those.
- **Maintenance:** it calls version 1.16.5 a "publication checkpoint" and says future releases are "TBD", so it may stop being updated.

**To do:** change `requirements.txt` from `mcp-video` to `kinocut`, call its Python `Client`, and check your existing imports still work.

### Add HyperFrames later, for fancy captions

HyperFrames (by HeyGen, Apache-2.0, free) builds animation from web code (HTML, CSS and animation libraries) and turns it into video. Use it only for see-through overlays, such as bouncy captions and shader transitions, and lay them on top in FFmpeg. Not yet confirmed: whether it works on Windows and whether it can export a see-through background. Test both first.

**Why not Remotion?** Remotion is good, but it is free only for companies of up to 3 people. After that it costs at least $100 a month plus $0.01 per render ([Remotion FAQ](https://www.remotion.dev/docs/license/faq)).

### Other helper tools (all safe licenses)

| Job | Tool |
|---|---|
| Match colour to reference | Compare colours, build a `.cube` file with colour-science, apply with `lut3d` |
| Crop wide video to vertical | Find the subject with MediaPipe or SAM 2, then smooth the crop movement |
| Stabilise shaky footage | FFmpeg vidstab |
| Slow motion | Practical-RIFE |
| Upscale low-res clips | FlashVSR (about 41 s for a 10 s clip) |
| Cut out the background | BiRefNet |

Google's old auto-crop tool (AutoFlip) stopped being supported in March 2023.

### How to store a template

No public standard for reel templates exists. Use your own strict JSON format with:

- the shot list (slots with roles),
- motion keyframes,
- a fixed list of allowed transitions,
- text items with a preset name and word timings,
- colour as a `.cube` file,
- the beat grid,
- a confidence score for each field.

A fixed list of options makes the AI's output easy to check and easy to patch.

---

## 8. Checking the result

No published paper does exactly what your app does, so this design is a recommendation, not a proven recipe. Run checks from cheapest to most expensive and stop at the first failure.

| Layer | What it checks | Cost |
|---|---|---|
| 0. Plan check | Clip IDs exist, trims are in range, text is inside the safe area, cuts are on beats | Free, no rendering |
| 1. File check | Resolution, fps, black frames, frozen frames, silence, loudness (FFmpeg filters) | Free |
| 2. Structure check | Do cuts match the template? Does pacing match? Do captions match in text, position and timing? Does colour match? | Free, no AI |
| 3. Clip fit | Does each clip fit its slot's meaning? (SigLIP 2) | Free |
| 4. AI judge | Gemini compares reference and render side by side | Small cost |

**AI judges are biased.**

- **Order bias:** one 2026 study found the judge favours whichever video is shown first, by about 18 points. Show the pair in both orders and mark disagreements as "unsure".
- **Repeat runs:** the same judge agreed with itself only 83 to 87% of the time.

**Fix loop:**

1. Turn each problem into a small JSON change.
2. Always keep the best version so far.
3. Stop after 2 or 3 rounds, or when the score stops improving.

The 2 to 3 rounds limit is our recommendation.

Even the best AI video-editing agent tested in 2026 solved only about 27 to 30% of real editing tasks. This is why the cheap exact checks matter.

---

## 9. MCP servers

An MCP server gives an AI agent extra tools. There are two places they could go.

### In your app: none

Do not put MCP servers in the app's video pipeline.

- **Cost and speed:** they add token cost and slow things down.
- **Security:** they create a security hole. Captions, transcripts and file names in a user's video can contain hidden instructions that trick the AI ("prompt injection").

Instead, call each service with its normal Python library: Kinocut `Client`, Gemini, OpenRouter, TwelveLabs, ElevenLabs and fal.

If you later want the chat agent to use Kinocut through MCP, give it only the default 20 tools and ask the user before anything destructive.

### In Claude Code while you build: yes

| MCP / tool | Why |
|---|---|
| Context7 | Up-to-date docs for FFmpeg, FastAPI and React |
| Playwright MCP | Automated tests of your web app (upload, chat, preview) |
| Chrome DevTools MCP | Debug the preview's speed |
| Replicate, Hugging Face (official hosted) | Try models quickly. Turn off Hugging Face's automatic Space discovery. |
| ElevenLabs (official hosted) | Voice tests. The old local version is archived. |
| TwelveLabs (official hosted) | Video tests |
| Remotion / HyperFrames "skills" | Replace the Remotion docs MCP, which shut down on 26 October 2026 |
| Figma, Canva | Reference only. Neither can turn a reel into a template. |

**Optional:** DaVinci Resolve MCP (needs Resolve installed) and VectCutAPI (exports CapCut projects).

**Avoid:**

- Instagram and TikTok downloader or poster MCPs: they break platform rules and are unvetted.
- Unofficial Runway, Luma and Kling wrappers.
- Adobe bridges that run any code.
- The archived ElevenLabs local server.
- Blender MCP, except on a separate test machine, because it has had security bugs.

Known MCP attacks include a fake Postmark MCP package that stole emails, and "tool poisoning". Trust official vendor servers first.

---

## 10. License traps

A license can stop you selling your product. These are the risky ones.

| Group | Tools | Problem |
|---|---|---|
| Company size | Remotion | Free up to 3 people. After that, at least $100/month plus $0.01 per render. |
| Copyleft ("share your code") | Ultralytics YOLO, Essentia, Video2X (AGPL); Gyroflow, Etro, Robust Video Matting (GPL) | AGPL can force you to publish your whole app's code. Avoid. |
| Non-commercial only | CrisperWhisper, MatAnyone, RMBG-2.0, DOVER, Q-Align, GIMM-VFI, XTTS v2, F5-TTS, InsightFace models | Cannot be used in a paid product. |
| Country or revenue limits | MiniMax H3 open model (not for US, EU, UK, South Korea), HunyuanVideo 1.5 (not for EU, UK, South Korea), LTX-2.3 (reported limit of $10M yearly revenue) | Use their hosted API instead, or avoid. |
| Unclear | SAM 3 | Says nothing about commercial use. Use SAM 2 (Apache-2.0). |

**Platform rules:**

- **Reel links:** downloading reels from a link on your server goes against Instagram and YouTube rules. Ask users to upload the file instead.
- **Faces:** do not identify people by face, because it is high legal risk. Only detect and count faces.

**Data rules:**

- Use paid AI tiers for real user footage. Paid Gemini does not train on your data.
- Ask TwelveLabs for a written data agreement, because its privacy policy and terms conflict.

**Safe list:** Kinocut, HyperFrames, SAM 2, MediaPipe, FlashVSR, OpenTimelineIO, colour-science, Beat This!, audio-separator, PySceneDetect, BiRefNet, Practical-RIFE, TransNetV2 and WhisperX.

This is not legal advice.

---

## 11. Cost per reel

These are our estimates from vendor price lists. Nothing was measured.

| Part | Cost |
|---|---|
| Analyse the reference (Gemini Flash + free local tools) | $0.03 to $0.06 |
| Plan and match clips (Sonnet) | about $0.05 (about $0.002 with Haiku) |
| Check the render | about $0.03 |
| 2 or 3 chat changes | about $0.05 |
| Speech, render, music | $0.01 to $0.10 |
| **Normal reel total** | **$0.15 to $0.30** (or $0.08 to $0.12 if Haiku and Flash-Lite do most work) |
| Two 4-second AI-generated filler shots | about $1 (MiniMax H3) to $2.50 (Kling v3) |
| Indexing the user's clip library (once per hour of footage) | $0.76 to $2.84 |
| Monthly fixed costs | TwelveLabs $29 or $99 if kept, Remotion $100 if used |

**AI-generated filler shots** (for slots the user did not film), with fal.ai prices:

- MiniMax H3 Max Turbo: $0.025 per second.
- Kling v3: $0.14 per second.
- Seedance 2.5: the top quality, but about 4 to 7 times worse value for money.
- Sora: its API shut down on 24 September 2026.

**Biggest unknowns:** how many "thinking" tokens the planner uses, and how often generated shots need a retry.

---

## 12. Free plans you can build on

### AI models

| Service | What is free | Catch |
|---|---|---|
| **Gemini API** | Gemini 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, Embedding 2 (accepts video). No card needed. | Google may use your data to improve its products, and staff may read it. India gets no exemption. Exact limits are visible only inside AI Studio. Gemini 4 Argon is not free. |
| **OpenRouter free models** | 20 requests a minute, 50 a day, or 1,000 a day after you buy $10 of credit | No free Claude. No confirmed free video model. |
| **Groq** | Text models (30 a minute, 1,000 a day) and Whisper speech-to-text (8 hours of audio a day) | No vision models. These numbers may be for a paid plan. |
| **Alibaba Qwen** | About 1 million tokens per model for 90 days | Qwen vision models are no longer free for new users (since 29 October 2026). |
| **Hugging Face** | Nothing for free accounts | PRO costs $2 a month. |
| **Anthropic** | No free API credit | Startup program is closed. |

Not confirmed (from blogs only): NVIDIA build.nvidia.com (about 1,000 credits), Z.ai GLM Flash models (may need a Chinese phone number), Mistral, Cerebras, Cloudflare Workers AI, and OpenAI's "share your data for free tokens" program.

### Video understanding

| Service | What is free |
|---|---|
| **TwelveLabs (new Free plan)** | 3 GB of storage plus a "Basic" monthly usage allowance whose size is not published. It stops when you hit the limit, with no extra charges. Limits: 3,000 indexing minutes a day, 1,000 analysis requests a day, 25 embedding requests a minute. |
| **TwelveLabs (old Free plan)** | 600 minutes in total. Indexes expire after 90 days. Old accounts move to the new plans on 4 January 2027. If you are on the Developer plan, pick Plus ($29, 50 GB) or Pro ($99, 200 GB) by 3 January 2027, or you drop to Free. |
| **Memories.ai** | $100 credit, no card (about 830 minutes of embedding) |
| **Azure Video Indexer** | 600 minutes on the website, or 2,400 through the API (Microsoft pages disagree) |
| **Google Video Intelligence** | 1,000 minutes a month (seen in a search summary only) |
| **AWS Rekognition** | 60 minutes a month, or up to $200 credit for new accounts |
| **Voyage multimodal** | 200 million text tokens and 150 billion pixels |

Source: [TwelveLabs pricing](https://www.twelvelabs.io/pricing). Our guess is that 3 GB holds 10 to 60 test reels, depending on file size.

### Speech, text reading, music, stock footage

| Service | What is free | Card? |
|---|---|---|
| **Deepgram** | $200 credit, never expires (about 46,500 minutes) | No |
| **Speechmatics** | $100 credit | No |
| **AssemblyAI** | $50 credit | No |
| **Gladia** | €50, valid 1 year | Not stated |
| **ElevenLabs Free** | 10,000 credits a month (about 30 min of speech-to-text or 10 min of voice) | Not for paid products. Needs attribution. |
| **Google Vision OCR** | 1,000 a month | Billing account needed |
| **Azure AI Vision** | 5,000 a month | Not stated |
| **OCR.space** | 25,000 a month (1 MB file limit) | No |
| **AudD** (music ID) | 300 requests | No |
| **Pexels** (stock video) | 20,000 requests a month | No. Must link back to Pexels. |
| **Pixabay** (stock video) | 100 requests a minute | No. Has no music in the API. |
| **Epidemic Sound** | Free test key | Paid deal needed for real use |

### AI generation and editing

There is **no reliable free option**.

- **fal.ai:** shows no free credit on its own page. Blogs say $1 to $20.
- **Replicate:** some models are free for a short while before billing is needed.
- **Runway, Luma, Kling:** no free API credit found.

Small free items: remove.bg (50 a month) and Photoroom (1,000 watermarked test calls a month).

Online render services (Shotstack, Creatomate, JSON2Video) are not needed, because FFmpeg runs on your own computer.

---

## 13. Free computers and hosting

### GPUs (for running AI models)

| Service | What is free | Can your app call it? |
|---|---|---|
| **Modal** | $30 a month (about 37 hours on an L4 GPU) | **Yes.** It is the only free GPU your backend can call. |
| **Kaggle** | About 30 GPU hours a week (reported, not on Kaggle's own page) | No, notebooks only. Good for batch jobs. |
| **Google Colab** | Variable, unpublished limits, 12-hour sessions | No, notebooks only. |
| **Hugging Face ZeroGPU** | 5 GPU minutes a day | Only through Gradio demos |
| **SageMaker Studio Lab** | Closed to new users | - |

**What runs on your own PC:**

- **WhisperX:** less than 8 GB of GPU memory, or the CPU.
- **Beat This!:** a 78 MB model that can use the CPU.
- **audio-separator:** works on the CPU.
- **Qwen3-VL-8B:** about 6 GB at reduced quality. Sources say 4.8 to 12 GB.
- **SAM 2:** prefers WSL on Windows.
- **FlashVSR:** tested only on big data-centre GPUs, so run it on Modal.

### Hosting the app

| Service | Free? | Problem |
|---|---|---|
| Oracle Always Free | 2 CPU cores, 12 GB RAM (cut from 4 and 24 on 15 June 2026) | Card needed. Often "out of capacity". Idle servers get reclaimed. |
| Google Cloud Run | About 50 CPU hours a month | FFmpeg would use it up fast. No GPU. |
| Render | Free web service | Sleeps after 15 minutes. No background workers. Free database deleted after 30 days. |
| Railway | $1 a month credit | Tiny |
| Fly.io | No free tier | - |
| Vercel Hobby | Free | Not allowed for commercial use |
| Hugging Face Spaces | Docker and Gradio now need PRO | - |

**Storage and database:**

- **Cloudflare R2:** 10 GB and free downloads. Delete renders after 1 to 3 days to stay under the limit.
- **Backblaze B2:** 10 GB.
- **Neon:** free Postgres, no card.
- **Turso:** 5 GB.
- **Cloudflare Pages:** free frontend hosting.
- **Supabase:** not suitable, because uploads are capped at 50 MB.

**Bottom line:** build and run on your own Windows PC. Treat any free host as a demo only.

---

## 14. Startup credits

| Program | Offer | Who can get it | Notes |
|---|---|---|---|
| **Cloudflare for Startups** | $10,000 (Tier 3) | Self-funded, under $1M raised | Biggest offer you can get without investors. Pays for storage and Cloudflare AI, not Gemini or Claude. |
| **AWS Activate Founders** | $1,000, up to $5,000 | No big funding round yet (pre-Series B). Needs a paid AWS account. | Reply in 5 to 10 business days |
| **Microsoft for Startups** | $1,000, up to $5,000 | Needs a registered business | May 2026 reports of founders blocked |
| **ElevenLabs grants** | 12 months of credits | Under 25 staff, worldwide | Only useful if you add voice |
| **NVIDIA Inception** | Free membership, some cloud credits | Must be a registered company | India included |
| **Google for Startups** | Up to $2,000 (Start tier, from a blog) | Unclear for self-funded founders | Official page did not load |
| **Anthropic** | Up to $45,000 in partner offers | **Closed** | Do not plan on it |
| **OpenAI, Modal, fal** | Credits | Need investor backing or traction | Not reachable yet |
| **IndiaAI compute** | Cheap GPUs (about ₹65 to ₹150 an hour), not free | Needs DPIIT recognition plus revenue or funding | India only |

**Students:** the GitHub Student Pack includes $100 of Azure credit.

**Registering a company:** it unlocks more programs (DPIIT, NVIDIA Inception, IndiaAI and bigger Google, AWS and Cloudflare tiers). DPIIT needs a Private Limited company, an LLP or a partnership. A sole proprietorship does not qualify.

---

## 15. Your zero-cost development setup

**Rule:** the code is the same in development and production. Only the keys, model names and connection strings change, set in your `.env` file.

| Part | Development (free) | Production (paid) | What changes |
|---|---|---|---|
| Shot description and judge | Gemini key from a **separate Google project with no billing**, `gemini-3.8-flash` | Billed project, same model | Key only |
| Clip search | Gemini Embedding 2 free, SigLIP 2 on your PC | Billed project | Key only |
| Planner and chat | OpenRouter: free models for wiring, a few cents of Haiku 5.5 for real tests | Sonnet 5.5 and Haiku 5.5 | Model name only |
| TwelveLabs | Free plan | Plus or Pro | Plan only |
| Speech-to-text | WhisperX on your PC, Deepgram $200 credit | Deepgram or ElevenLabs Scribe | One setting |
| On-screen text | PP-OCRv5 on your PC | Same | Nothing |
| Rendering | FFmpeg + libass + Kinocut on your PC | Same on a server | Nothing |
| GPU jobs | Modal ($30/month), Kaggle, Qwen3-VL in Ollama or LM Studio | Paid Modal | Settings only |
| Storage and database | R2 with auto-delete after 1 to 3 days, SQLite or Neon | Paid R2, Postgres | Connection string |
| Website | Your PC, Cloudflare Pages, Oracle for a demo | A paid host | Where you deploy |

**Three habits to build in from day one:**

1. **Cache** every AI answer by a fingerprint of the input, so you do not burn free daily limits while testing.
2. **Save test recordings** of AI answers so unit tests run without calling the AI.
3. **Retry** when the AI returns bad JSON or a "too many requests" error. Free tiers trigger these often.

**Two warnings:**

- **Google billing:** never link billing to the free Google project. That turns the whole project into a paid one.
- **User footage:** never send real user videos or other people's reels through the free Gemini key.

Free models may follow JSON rules less strictly than paid ones. Run the same test set on both before trusting results.

---

## 16. What to do, in order

### Part A: sign up (week 1)

1. **Today, instant and no card:**
   - A Gemini key in a new Google project.
   - Deepgram.
   - Modal.
   - Cloudflare (Pages and R2).
   - Pexels and Pixabay keys.
   - AudD.
   - Kaggle (needs phone verification).
   - Note any service that refuses Indian phone numbers or cards. That result changes this plan more than any price.
2. **TwelveLabs:** decide before 3 January 2027 whether to stay on Free or pay for Plus or Pro.
3. **OpenRouter:** add $10 once. It pays for the Claude tests and raises the free-model limit to 1,000 requests a day.
4. **Slower applications:**
   - Oracle Always Free: keep retrying if it says out of capacity.
   - Cloudflare for Startups Tier 3.
   - AWS Activate Founders.
   - Microsoft for Startups: check eligibility first.
   - ElevenLabs grant: only if you need voice.
5. **Later, after registering a company:** DPIIT, NVIDIA Inception, Google for Startups and IndiaAI.
6. **Skip:** Vercel Hobby, Fly.io and Render's free database.

### Part B: build (in this order)

1. **Make a test set first.**
   - Hand-label 10 reference reels: their cuts, text, motion and style.
   - Make 20 audio clips with hand-tapped beats and checked word times.
   - Make a set of 50 searches over 200 clips.

   No public test measures how well any tool recreates a reel template, so this test set is how you choose tools.
2. **Fix the renderer.**
   - Switch `mcp-video` to `kinocut` and use its Python `Client`.
   - Convert all clips to the same size and frame rate.
   - Add ASS caption presets.
   - Add the free file checks: black frames, frozen frames and loudness.
3. **Change the analysis.** Find cuts first (TransNetV2 or PySceneDetect), then read text (PP-OCRv5), measure motion (OpenCV) and have Gemini describe each known shot. Keep TwelveLabs as a side-by-side test and for clip search.
4. **Lock the template format** and move planning and chat to Sonnet 5.5 with strict JSON, retries and the "keep the best version, max 2 to 3 rounds" loop.
5. **Add the quality tools:**
   - colour matching with a `.cube` file,
   - vertical auto-crop,
   - smooth zoom and speed ramps,
   - voice and music split,
   - beat snapping,
   - loudness at -14 LUFS.
6. **Add the full check layers** (sections 8, layers 2 to 4). Test them on reference and render pairs that a person has marked "same template" or "not".
7. **Add HyperFrames** for animated captions, after you confirm it works on Windows and exports see-through video.
8. **Only if users ask for them:**
   - AI filler shots (fal.ai with MiniMax H3),
   - stabilisation,
   - upscaling,
   - slow motion,
   - CapCut project export.

**Leave out for now:** face matching and pasting reel links.

---

## 17. Things still not checked

Check these before you rely on them.

**India and payment:** no page confirmed that any of these services work from India, accept Indian cards or handle GST. Nothing was tested from India.

**AI models:**

- **Gemini:** no official video test results for Gemini 4 or 3.8 Flash. Gemini's exact free limits can only be seen after logging in to AI Studio.
- **JSON reliability:** no data for any model.
- **Cut-detection numbers:** they come from the test's own authors.
- **Caption fonts:** no tool for recognising caption fonts was found. Plan to pick the closest from a list of licensed fonts.
- **Camera motion:** Gemini and TwelveLabs have no proven accuracy for it.
- **OpenRouter:** the current free-model list could not be fetched. To get it, run `curl https://openrouter.ai/api/v1/models` and filter for zero price.

**Audio:**

- **Unverified licenses:** madmom, Essentia, MERT, CLAP, faster-whisper and Parakeet. Demucs's maintenance status is also unconfirmed.
- **Platform specs:** no official loudness or "safe area" numbers from Instagram, TikTok or YouTube. Make them settings you can change.

**Rendering:**

- **HyperFrames:** not tested on Windows. See-through export not confirmed.
- **Kinocut:** missing zoom and speed ramp is based only on its documentation. Not installed on Windows.
- **Recipes:** several FFmpeg recipes come from general knowledge, not the official docs.

**Free tiers:**

- **TwelveLabs:** the size of the "Basic" allowance and which models are on Free are unpublished.
- **Other limits:** fal.ai's signup credit, Modal's card requirement, Kaggle's weekly hours, and the Microsoft and Google startup rules are all unconfirmed.
- **Oracle:** whether old accounts keep 4 cores and 24 GB has been reported only in support emails.

**Legal:** the readings here are not legal advice. LTX and MiniMax license texts were not fully read.

---

## 18. Main sources

- Cut detection test: [TransVLM](https://chence17.github.io/TransVLM/)
- Gemini: [pricing](https://ai.google.dev/gemini-api/docs/pricing), [video docs](https://ai.google.dev/gemini-api/docs/video-understanding), [terms](https://aistudio.google.com/docs/terms)
- Claude: [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [Claude for Startups](https://claude.com/programs/startups)
- OpenRouter: [rate limits](https://openrouter.ai/docs/api-reference/limits)
- TwelveLabs: [pricing](https://www.twelvelabs.io/pricing), [migration](https://docs.twelvelabs.io/v1.3/docs/get-started/plans-and-billing/migrate-to-new-billing.md)
- Kinocut: [GitHub](https://github.com/KyaniteLabs/kinocut), [PyPI mcp-video](https://pypi.org/project/mcp-video/)
- HyperFrames: [GitHub](https://github.com/heygen-com/hyperframes)
- Remotion: [license FAQ](https://www.remotion.dev/docs/license/faq)
- Audio: [Beat This!](https://github.com/CPJKU/beat_this), [WhisperX](https://github.com/m-bain/whisperX), [audio-separator](https://github.com/nomadkaraoke/python-audio-separator)
- Video generation prices: [fal pricing](https://fal.ai/pricing), [Artificial Analysis](https://artificialanalysis.ai/video/leaderboard/image-to-video)
- Self-correcting editors: [EditDuet](https://arxiv.org/html/2509.10761v1), [AVE-Agent](https://arxiv.org/html/2607.24821v1)
- Free tiers: [Deepgram](https://deepgram.com/pricing), [Memories.ai](https://www.memories.ai/pricing), [Modal](https://modal.com/pricing), [Cloudflare R2](https://developers.cloudflare.com/r2/pricing/), [Oracle free tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- Startup credits: [Cloudflare](https://www.cloudflare.com/forstartups/), [AWS Activate](https://aws.amazon.com/startups/credits), [NVIDIA Inception](https://www.nvidia.com/en-us/startups/)

Full source lists are in the two original reports in this folder.
