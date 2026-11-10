# Free compute, hosting, storage and startup credits for a solo India-based AI Reel Editor developer (as of 4 Nov 2026)

Method note: primary vendor pages were fetched where they rendered. Several Google, Kaggle and Microsoft pages did not render, so those rows rely on secondary sources and are flagged. WebFetch returns a model summary of each page, not raw text, so treat exact numbers as "as reported by fetch, 4 Nov 2026". Nothing was verified from inside India, so India availability is mostly a gap unless stated. Card = payment card required at signup.

## 1. Free GPU for the open models (API-callable vs notebook-only)

### Takeaway
No free GPU option is a production API. Only Modal ($30/month credit, code-first serverless) is genuinely callable from a FastAPI backend at zero cost. Colab and Kaggle are notebook-only (Kaggle can be driven via CLI and Colab via manual runs), and Hugging Face has restricted free Space creation to ZeroGPU Gradio only. SageMaker Studio Lab is closed. Lightning's free terms conflict between sources. For development, plan on Modal for API-style GPU calls plus Kaggle/Colab for batch runs.

### Cited Findings
Catalog (GPU / limits / card / commercial / fit):

| Service | Free allowance and GPU | Limits | Card | Callable from backend? | Fit for the reel workload |
|---|---|---|---|---|---|
| Modal Starter | "$30 / month free credits"; T4 $0.000164/s, L4 $0.000222/s, A10 $0.000306/s, L40S $0.000542/s, A100-40 $0.000583/s, A100-80 $0.000694/s | 3 seats, 100 containers, 10 GPU concurrency, 200 deployed apps, 1 day log retention; no custom domains | Page did not say | Yes (Python SDK, deploy functions and web endpoints) | Best fit: $30 of L4 is about 37 GPU-hours/month (my arithmetic: 30/0.000222/3600). Source: [Modal pricing](https://modal.com/pricing) (4 Nov 2026) |
| Kaggle Notebooks | Commonly reported about 30 GPU h/week (P100 or 2xT4); quota shown in account settings, NOT stated in Kaggle docs | 12 h sessions CPU/GPU (per one Sept 2026 review citing Kaggle docs; many guides say 9 h); quota counts session time, not utilisation; internet access reportedly needs phone verification | No | Notebook-only; kernels can be pushed/run via Kaggle CLI (from the model's general knowledge, page did not render) | Good for batch jobs (WhisperX, SigLIP 2 embeddings, Qwen3-VL captioning, FlashVSR trials) on T4/P100; not a live API. Sources: [gpuperhour 21 Sep 2026](https://gpuperhour.com/blog/free-cloud-gpus-and-credits); search summary of 2026 guides |
| Google Colab free | Variable GPU (T4 user-reported, not confirmed by Google) | Max 12 h runtime; limits "fluctuate" and are not published; idle timeouts; background execution only on paid plans | Page did not say | Notebook-only | Fine for interactive experiments. Colab FAQ does not address commercial use or India. [Colab FAQ](https://research.google.com/colaboratory/faq.html) |
| Hugging Face ZeroGPU | Free account: 5 min GPU/day (2 min unauthenticated); PRO 40 min/day; backing hardware now "RTX Pro 6000 Blackwell" (large = half, 48 GB; xlarge = full, 96 GB) | Gradio SDK only; default 60 s per call (extendable with duration=); PyTorch 2.8-2.13; no torch.compile; free accounts (verified email, older than 30 days) can host max 2 ZeroGPU Spaces | No (free) | Yes, a Gradio Space exposes an API (gradio_client). 5 min/day is a hard cap | Demo/prototyping of one model at a time; too small for pipelines. [HF ZeroGPU docs](https://huggingface.co/docs/hub/spaces-zerogpu) |
| Lightning AI free | Conflicting: pricing page says "Up to 30 starting credits" (FAQ: 5 on registration, 25 after adding a card, expire after 12 months), 2 concurrent GPUs, 50 GB storage, one free Studio needing restart every 4 h, "No credit card" on headline | T4 $0.55/h, L4 $0.79/h, A100-40 $2.19/h on page. A third-party page dated 21 Sep 2026 says the old 15-credit monthly refresh became a one-time grant | Headline says no, FAQ says card unlocks 25 credits | Studio is a cloud VM with SSH/VS Code, can run a server; not a serverless API | One-time about 30 credits is roughly 38 L4-hours; useful for one burst. [Lightning pricing](https://lightning.ai/pricing); [usagepricing change note](https://www.usagepricing.com/blueprint/activity/lightning-ai-2026-09-21-gpu-rate-card-reprice) (secondary) |
| Paperspace Gradient free | Free M4000 (8 GB VRAM, per secondary guide) | DigitalOcean docs list Free GPU (M4000) on Free plan; sessions 6 h blocks; 5 GB storage; notebooks public; a guide says card needed for verification. Other sites claim free GPU was removed, which conflicts with DO docs | Reportedly yes | Notebook-only | M4000 is too old/slow for most of the model list. [DO Paperspace pricing](https://docs.digitalocean.com/products/paperspace/pricing); [gpuperhour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) |
| SageMaker Studio Lab | CLOSED to new customers; existing users 4 h sessions, 4 h cap per 24 h | AWS plans no new features | n/a | n/a | Do not plan on it. [gpuperhour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) (Sept 2026) |
| Saturn Cloud | Allowance unclear: 2023 PR said 150 h/month, 2024 reviews say 10-30 h; aimultiple (2026) says no longer publishes figure | Unverified | Reportedly no | Notebook/Jupyter | Treat as unconfirmed. [PRNewswire 2023](https://prnewswire.com/news-releases/saturn-cloud-launches-new-tier-of-150-free-hours-for-data-professionals-301923769.html) |
| Google TPU Research Cloud | Free TPUs by application; participants expected to publish work and give feedback | Official GitHub repo archived 19 Apr 2026; no 2026 eligibility confirmed | n/a | TPU, not CUDA | Poor fit: these models are CUDA/PyTorch; research/publication obligation. [TRC GitHub](https://github.com/google-research/trc); search results |
| Camber (via GitHub Student Pack) | Student plan: 40 CPU h, 5 GPU h, 50 GB per month | Students only | n/a | n/a | Token amount. [GitHub Education pack](https://education.github.com/pack) |

- HF Spaces change to flag: the current Spaces overview states "Static Spaces are free for everyone. Gradio and Docker Spaces run on compute and require a paid plan to create: PRO for personal accounts", with the single exception of up to 2 ZeroGPU Gradio Spaces for free accounts. Free CPU Basic hardware (2 vCPU, 16 GB, 50 GB non-persistent disk) therefore needs a paid plan to create. Free hardware sleeps when unused. Community GPU grants can be requested from Space settings. — [HF Spaces overview](https://huggingface.co/docs/hub/spaces-overview) (fetched 4 Nov 2026; date of the policy change not found)
- Paid fallback pricing on HF: T4-small $0.40/h, L4 $0.80/h, L40S $1.80/h, A100-large $2.50/h. — [HF Spaces overview](https://huggingface.co/docs/hub/spaces-overview)
- Cheapest on-demand GPU market prices observed 4 Nov 2026: RTX 3090 $0.29/h, A100 $0.68/h, RTX 4090 $0.82/h, L4 $0.93/h (no T4 in stock) — [gpuperhour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- Modal credits from AWS/GCP/Azure cannot be applied to Modal usage. — [Modal pricing](https://modal.com/pricing)

### Inferences
- Modal's $30 monthly credit covers roughly 37 L4-hours or 15 A100-40-hours per month, enough for dev/test of every model in the list one at a time, but not for continuous serving. Use scale-to-zero functions only.
- Kaggle's about 30 h/week (about 130 h/month) is the largest free GPU pool, but it is notebook-only and quota behaviour is undocumented, so use it for offline batch jobs, not as a request-time dependency.
- For a request-time GPU API at zero cost, the only options are Modal credit and a 2-Space ZeroGPU quota (5 min/day), so the MVP should treat GPU steps as optional/async jobs.

### Gaps
- RunPod and Vast.ai signup credits were not searched successfully (search returned only Saturn). No sourced figure.
- Colab and Kaggle commercial-use terms were not found on the pages that rendered. Kaggle official docs page did not render; the weekly quota, 9 vs 12 h session and phone-verification claims are secondary.
- India availability of every service above: not stated on any fetched page. Colab free, Kaggle and Modal are generally reachable from India but this was not confirmed from a primary source.
- Whether Modal Starter requires a card: page did not say.

## 2. Local GPU option (6-8 GB RTX laptop or CPU-only), per model

### Takeaway
On Windows with 6-8 GB VRAM, TransNetV2, Beat This!, PP-OCRv5, SigLIP 2 and WhisperX (int8, smaller models) are realistic locally; BS-RoFormer separation works but is slow on CPU; Qwen3-VL-8B needs 4-bit quantisation and is tight on 8 GB; SAM 2 and FlashVSR are the least laptop-friendly. Sourcing for sizes is thin; many entries are gaps.

### Cited Findings
- WhisperX: faster-whisper backend "requires <8GB gpu memory for large-v2 with beam_size=5"; lower memory with batch size 4, smaller model, or int8; CPU-only supported via --device cpu --compute_type int8; BSD-2-Clause; diarisation uses pyannote model that needs an HF token and agreement. — [WhisperX README](https://github.com/m-bain/whisperX)
- Beat This!: main checkpoints about 78 MB, small checkpoints about 8.1 MB; uses GPU by default and falls back to CPU (--gpu=-1); MIT code and weights; no speed benchmarks or VRAM figures given. — [beat_this](https://github.com/CPJKU/beat_this)
- audio-separator (BS-RoFormer): CPU install supported; CLI default model is a BS-RoFormer ckpt; on Windows DirectML (AMD/Intel) RoFormer models "run on CPU automatically"; no VRAM figures; use --chunk_duration (300-600 s on limited memory); v0.47.0+ runs 4-6x more forward passes than 0.46.x, use --mdxc_overlap=2 to speed; MIT. NVIDIA CUDA 11.8/12.2 listed. — [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator)
- TransNetV2: MIT; PyTorch inference version released; no CPU/GPU speed or VRAM figures on the README (repo is small, F1 77.9 on ClipShots). — [TransNetV2](https://github.com/soCzech/TransNetV2)
- Qwen3-VL-8B: sources conflict. One Codersera guide says Q4_K_M GGUF is about 6.1 GB with 8 GB minimum, an updated version says 12 GB; Spheron estimates about 4.8 GB INT4 weights plus cache; an Unsloth mirror estimates about 7.3 GB. No official figure. — [Codersera](https://codersera.com/blog/qwen3-vl-4b-vs-qwen3-vl-8b-benchmarks-vram-guide/), [Spheron](https://www.spheron.network/tools/gpu-recommender/Qwen/Qwen3-VL-8B-Instruct/)
- SAM 2.1: tiny 38.9M (91.2 FPS on A100), small 46M, base+ 80.8M, large 224.4M (39.5 FPS); needs Python 3.10+, torch 2.5.1+; custom CUDA kernel build needs nvcc (optional, post-processing only); README recommends WSL Ubuntu on Windows; Apache 2.0; no VRAM figures. — [SAM 2](https://github.com/facebookresearch/sam2)
- FlashVSR: official repo tested only on A100/A800/H200; RTX 40/50 series "currently unknown"; no low-VRAM mode documented officially (third-party ComfyUI forks mention tiling); about 17 FPS at 768x1408 on A100; Apache-2.0. — [FlashVSR](https://github.com/OpenImagingLab/FlashVSR)

### Inferences
- Keep FlashVSR, SAM 2 (large) and Qwen3-VL-8B off the laptop critical path; run them on Modal/Kaggle. SAM 2 tiny/small and Qwen3-VL-8B 4-bit are the most plausible local candidates but need measurement on the actual card.
- Windows: SAM 2 and FlashVSR docs steer toward WSL/Linux. Plan on WSL2 for GPU model development, and on audio-separator + torch CUDA wheels for BS-RoFormer.

### Gaps
- No sourced VRAM/CPU data for PP-OCRv5, SigLIP 2 and RIFE; not researched. Model priors suggest SigLIP 2 base/so400m and PP-OCRv5 mobile run on CPU, and RIFE is light on 6 GB, but this is unverified.
- No source for SAM 2 / FlashVSR / TransNetV2 actual VRAM. Qwen3-VL-8B VRAM unresolved (6-12 GB range across sources).
- BS-RoFormer CPU timings: none published in README.

## 3. Free hosting for FastAPI + React + background jobs

### Takeaway
There is no good always-on free FastAPI+worker host in 2026. Oracle halved Always Free Arm (now 2 OCPU / 12 GB), Fly.io has no free tier, Render free web services sleep and have no workers, and HF Spaces now require PRO for Docker/Gradio. Best zero-cost combo: React on Cloudflare Pages (or Netlify/Vercel non-commercial), FastAPI on Oracle Always Free A1 or Google Cloud Run free tier, and heavy FFmpeg rendering on Oracle ARM or locally.

### Cited Findings
| Host | Free allowance | Limits | Card | Fit |
|---|---|---|---|---|
| Oracle Cloud Always Free | Ampere A1: 1,500 OCPU-h + 9,000 GB-h/month = "2 OCPUs and 12 GB" total; 200 GB block/boot; 10 TB/month outbound; Object Storage 20 GB (Always Free only) | CHANGED effective 15 Jun 2026 from 4 OCPU/24 GB (3,000/18,000) with no public announcement; instances above limit shut down until resized; idle reclamation if 95th pct CPU, network and memory (A1) all under 20% over 7 days; home region only; "out of host capacity" common | Oracle signup requires card (not on fetched page; widely known) | Best always-on option: 2 ARM cores run FFmpeg (libx264 CPU) slowly; good for API + SQLite + queue. Sources: [Oracle docs](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [InfoQ Jul 2026](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) |
| Oracle PAYG nuance | Support emails (reported 22 Jun 2026) say PAYG accounts may still use 4 OCPU/24 GB free; unofficial, docs say "All tenancies" get 1,500/9,000 | Get written confirmation | Yes | [InfoQ](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) |
| Google Cloud Run (free tier) | Per month, request-based billing: 2M requests, 180,000 vCPU-s, 360,000 GiB-s, 1 GB North America egress | Free Tier "has no end date" but Google can change with 30 days' notice; no GPUs in free tier; stateless | Card needed for the $300 trial and for billing accounts | Good for API; 180k vCPU-s = 50 vCPU-hours/month, so FFmpeg rendering burns it fast. [GCP free features](https://docs.cloud.google.com/free/docs/free-cloud-features) |
| Google Compute e2-micro | 1 VM (Oregon/Iowa/South Carolina), 30 GB-mo standard disk, 1 GB outbound | Too weak for FFmpeg | Yes | [GCP free features](https://docs.cloud.google.com/free/docs/free-cloud-features) |
| GCP $300 trial | $300 for 90 days; card required (hold of $0-1); GPUs cannot be added during the trial (per gpuperhour) | Never been a paying GCP customer | Yes | [GCP](https://docs.cloud.google.com/free/docs/free-cloud-features), [gpuperhour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) |
| AWS Free plan | $100 credits at signup plus up to $100 more by exploring services; account closes after 6 months or when credits run out; "30+ services always free within limits" | Card not mentioned on page; India not mentioned | Unconfirmed | [AWS Free](https://aws.amazon.com/free/) |
| Azure | $200 for up to 30 days; Azure for Students $100 for 12 months | GPU eligibility unknown | Yes for the $200 | [gpuperhour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) |
| Render | Free web service: 750 h/month, spins down after 15 min idle (about 1 min cold start), ephemeral disk, no persistent disk, SMTP blocked, no one-off jobs, no workers; Free Postgres 1 GB expires after 30 days (+14 days grace); Free Key Value in-memory; static sites free | Free instances can be suspended for high outbound traffic | Not stated | API only, OK for demo; DB must be external. [Render free docs](https://render.com/docs/free) |
| Railway | Free plan: $1 credit/month, 1 vCPU, 0.5 GB RAM, 0.5 GB volume; Trial: one-time $5; Hobby $5/month incl. $5 usage | Trial duration and card not stated on page; "Railway now requires a post-paid card for payments" | Likely | Too small for FFmpeg. [Railway plans](https://docs.railway.com/reference/pricing/plans) |
| Fly.io | NO free tier: "New organizations don't have a free tier"; $1 trial credit for 7 days, no card to start | Card needed after trial | After trial | Not free. [Fly pricing](https://docs.fly.io/about/pricing) |
| Koyeb | Pricing page shows no free instance; Pro $29/month incl. $10 compute; Postgres "Free 5h"; startup program "up to $30k" | Free instance status unconfirmed | n/a | [Koyeb pricing](https://www.koyeb.com/pricing) |
| Cloudflare Pages | Free: 500 builds/month, 1 concurrent build, 20-min build timeout, 20,000 files | Bandwidth and commercial terms not on page | No | Frontend host. [CF Pages limits](https://developers.cloudflare.com/pages/platform/limits/) |
| Vercel Hobby | 100 GB Fast Data Transfer, 1M function invocations, 4 h active CPU, 10 GB origin transfer | "Hobby teams are restricted to non-commercial personal use only" (financial gain of anyone involved counts) | No | Frontend OK for dev, not for commercial. [Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines) (updated 14 Sep 2026) |
| Netlify Free | "300 credit limit"; bandwidth 20 credits/GB; production deploy 15 credits | Commercial use and card not stated | n/a | Frontend. [Netlify pricing](https://www.netlify.com/pricing/) |
| Hugging Face Spaces (full app) | Static Spaces free; Docker/Gradio need PRO except 2 ZeroGPU Spaces; CPU Basic 2 vCPU/16 GB/50 GB ephemeral | Sleeps when idle; ports 80/443/8080 only | PRO is paid | Not free for a FastAPI Docker app any more. [HF Spaces](https://huggingface.co/docs/hub/spaces-overview) |

### Inferences
- FFmpeg fit: 2 Arm cores on Oracle will render roughly real-time-or-slower for 1080p H.264; fine for MVP/testing, not for concurrency. Cloud Run's 50 vCPU-hours/month would only cover a modest number of short renders.
- Oracle capacity: new accounts often cannot provision A1 ("out of host capacity" is documented), so budget time for retries or a different availability domain.
- Developing locally on Windows and only deploying the thin API to a free host keeps costs at zero; run render workers on the dev laptop or Oracle.

### Gaps
- Render/Railway/Netlify card requirements and India availability not stated on fetched pages.
- Cloudflare Workers/Containers free options (a possible FFmpeg runner) not researched.
- Whether Cloud Run free tier requires the account to upgrade out of the $300 trial: not confirmed.

## 4. Free storage, CDN and DB

### Takeaway
Cloudflare R2 (10 GB, zero egress) is the best fit for uploads and renders, with Backblaze B2 (10 GB free, free egress through Cloudflare/bunny) as a second. For DB, SQLite on the host volume suffices; Neon, Turso and Supabase are free fallbacks.

### Cited Findings
| Service | Free allowance | Limits | Card | Notes |
|---|---|---|---|---|
| Cloudflare R2 | 10 GB-months Standard, 1M Class A, 10M Class B ops per month, egress free | Card requirement not stated on pricing page (R2 normally needs a payment method on account; unverified) | ? | [R2 pricing](https://developers.cloudflare.com/r2/pricing/) |
| Backblaze B2 | First 10 GB free; $6.95/TB/month after; egress free up to 3x average stored, then $0.01/GB; unlimited free egress via Cloudflare, Fastly, bunny.net; Class A/B/C calls free | Class D $0.004 per 10k after 2,500/day | Not stated | [B2 pricing](https://www.backblaze.com/cloud-storage/pricing) |
| Supabase Free | 500 MB DB, 1 GB file storage, 5 GB egress (+5 GB cached), 50 MB max upload, 50,000 MAU, 2 active projects | Projects pause after 1 week inactivity | Not stated | 50 MB upload cap makes it unsuitable for video. [Supabase pricing](https://supabase.com/pricing) |
| Neon Free | 1 GB Postgres per project (20 GB across account), 100 CU-h/project/month, scale-to-zero after 5 min, 100 projects, 5 GB object storage per project | Permanent plan | No card | [Neon pricing](https://neon.com/pricing) |
| Turso Free | 100 DBs, 5 GB storage, 500M rows read, 10M rows written per month | PITR 1 day | No card | SQLite-compatible, closest to the SQLite plan. [Turso pricing](https://turso.tech/pricing) |
| Cloudinary Free | 25 credits/month (1 credit = 1 GB storage or bandwidth or transformations), 3 users | Video limits and commercial terms not stated | No card | [Cloudinary](https://cloudinary.com/pricing) |
| Bunny | 14-day free trial, no card; $1/month minimum; CDN $0.01/GB EU/NA, $0.03/GB Asia/Oceania | Storage and Stream rates not on page | No | Not free long-term. [bunny.net](https://www.bunny.net/pricing/) |
| GCP Cloud Storage | 5 GB (us-east1/west1/central1 only), 100 GB/month NA egress | US regions only | Card on billing account | [GCP free](https://docs.cloud.google.com/free/docs/free-cloud-features) |
| Oracle Object Storage | 20 GB (Always Free only) or 10 GB per class (trial/paid), 10 TB outbound | If trial ends over 20 GB, objects deleted | Yes | [Oracle docs](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) |

### Inferences
- A reel editor with a few raw clips plus renders can exceed 10 GB quickly; implement TTL cleanup (e.g., delete renders after 24-72 h) to stay inside R2/B2 free tiers.
- R2 plus Cloudflare for Startups credits (see 5) removes cost beyond 10 GB.

### Gaps
- R2 and B2 card-at-signup: not confirmed on the fetched pages. India region latency not researched.

## 5. Startup credit programs for an early solo founder in India

### Takeaway
Reachable without investors: Cloudflare for Startups Tier 3 ($10k, bootstrapped), AWS Activate Founders ($1,000 start, up to $5,000), Microsoft Azure startup offer ($1,000 then up to $5,000 after business verification), Google for Startups Start tier (up to $2,000, per secondary source), ElevenLabs grant, NVIDIA Inception (requires incorporation). Anthropic's offer is paused, OpenAI is VC-gated, Modal and fal are gated by funding/traction. IndiaAI needs DPIIT recognition plus revenue or funding.

### Cited Findings
| Program | Offer | Eligibility (as reported) | India | Status / flag |
|---|---|---|---|---|
| Cloudflare for Startups | Tier 3 $10k (bootstrapped/self-funded, under $1M raised), Tier 2 $100k (<$5M raised, affiliated partner), Tier 1 $350k ($5M+, affiliated partner). Workers AI capped $2,500 for Tier 3; R2 capped $10,000 all tiers | Valid for 1 year or until used; no extensions. Earlier $5k/$250k figures no longer listed | Not stated | [Cloudflare for Startups](https://www.cloudflare.com/forstartups/) |
| AWS Activate | Founders (self-funded): start with $1,000, up to $5,000; Portfolio up to $200k needs Activate Provider Org ID; AI Startups $200k+ invite-only | Pre-Series B, founded in last 10 years, AWS account on Paid plan, new to Activate credits; apply with AWS Builder ID; reply in 5-10 business days; also Kiro Startup Credits | Not stated | [AWS Activate](https://aws.amazon.com/startups/credits). Note: needs a Paid-plan AWS account (not the 6-month Free plan) |
| Google for Startups Cloud Program | Official AI page: Year 1 up to $250,000 including extra $150k for AI tier; year 2 adds 20% of usage up to $100k (total $350k); credits Google Cloud only. Start tier: up to $2,000 for 1 year, "Pre-funded; <5 years old" (dev.to guide, secondary); Scale pre-seed to Series A up to $200k; partner perks up to $10k for Anthropic and Fireworks | Official page describes AI program as for VC-funded AI startups; third-party sites conflict on whether bootstrapped can apply. Official apply/FAQ pages did not render | Not stated | [Google AI program page](https://cloud.google.com/startup/ai) (via search summary), [dev.to Google AI guide](https://dev.to/googleai/the-2026-ultimate-guide-to-google-for-startups-funding-accelerators-and-350k-in-credits-10ha) (secondary). Verify before relying |
| Microsoft for Startups | Azure startup offer: $1,000 immediately, up to $5,000 after business verification within 90 days; legal business entity with a software product; investor-network offer (up to $150,000 Azure) needs investor referral code | Q&A "AI answer" (May 2026); search results show May 2026 reports of founders blocked ("You're not eligible for an Azure free account"). Program referred to by moderator as "Microsoft for Startups Investor Offer (formerly Founders Hub)"; March 2026 trade news says open regardless of funding (conflict) | Not stated | [MS Q&A](https://learn.microsoft.com/en-us/answers/a/12780061); [Microsoft startups page](https://www.microsoft.com/en-us/startups) mentions max $150,000. Status uncertain; flagged changed in 2026 |
| NVIDIA Inception | Free membership; courses, hardware rebate pricing, cloud credits from NVIDIA/partners (amount not stated), VC network | Must be incorporated, under 10 years old, working website, clear NVIDIA-tech use case; excludes consulting, crypto, public cos., resellers; funding and revenue not required; solo founder seems to qualify | Regional site list includes India; contact inceptionprogram@nvidia.com | [NVIDIA Inception](https://www.nvidia.com/en-us/startups/) |
| Anthropic Claude for Startups | Discounts/credits up to $45,000 from partners (Startup Stack); VC-backed partner-network founders up to $100K API credits via VC; Oct 2026 expansion: free Claude Team year plus $1,000 API credits | PAUSED: program page says applications closed, cohort full; developersdigest.tech reports "over capacity" for new claims as of 11 Oct 2026; earlier open to bootstrapped/pre-seed | Page links to availability page; unspecified | [Claude startups](https://claude.com/programs/startups); [DevelopersDigest](https://www.developersdigest.tech/blog/claude-for-startups-offer-paused-capacity-what-to-do-2026) (secondary) |
| OpenAI | No public self-serve program found; credits via VC partners/accelerators; one blog lists Ramp route up to $2,500; YC batch tokens-for-equity deal reported May 2026 | All secondary and conflicting | Unknown | [fin.ai](https://fin.ai/learn/ai-credits-for-startups) (secondary). Treat as not available to bootstrapped solo founders |
| ElevenLabs Startup Grants | 12 months, 33 million credits (over 680 hours Conversational AI) | Official blog: startups under 25 employees anywhere in the world; enterprise customers excluded; badge required | Worldwide | [ElevenLabs blog](https://elevenlabs.io/blog/elevenlabs-startup-grants-just-got-bigger-now-12-months-and-over-680-hours-of-conversational-ai-audio) (via search summary). Relevant only if TTS/voice is used |
| TwelveLabs | No startup credits found; free tier reported 10 h of indexing; Ecosystem Partner Program (Apr 2026) is co-selling, not credits | Via AWS Activate credits it may be purchasable on Bedrock | n/a | [TwelveLabs pricing](https://www.twelvelabs.io/pricing-calculator) (secondary summary). Not a credits program |
| fal | Startup Program $1,000-$5,000 for teams with traction or VC; separate Builder Grant for earlier-stage | One program per company | Page header said "For teams in Europe & Asia" | [fal startups](https://fal.ai/startups) (via search summary) |
| Replicate | No official startup program page found; directory says $1k-$10k; "$500 free credits" marketing pages unverified | n/a | n/a | Unverified |
| Modal for Startups | "thousands of free GPU credits"; one-time per tier | Seed-Series A: raised any VC from Modal's partner network, or >$1M from any fund; academic grant up to $10k for grad students/labs | Not stated | [Modal startups](https://modal.com/startups); [Modal pricing](https://modal.com/pricing). Not reachable without VC |
| Koyeb | "up to $30k in credits" | Details not on page | n/a | [Koyeb](https://www.koyeb.com/pricing) |
| Startup India / DPIIT | Recognition unlocks IndiaAI startup route and other benefits | Needs incorporated Private Ltd, LLP or registered partnership (sole proprietorships ruled out per multiple 2026 guides); 10 years from incorporation; turnover cap reportedly raised to Rs 200 crore on 4 Feb 2026 (one source; another still says Rs 100 crore) | India | [Patron Accounting](https://www.patronaccounting.com/blog/what-is-startup-registration-guide-indian-businesses), [incorpx](https://www.incorpx.io/blog/dpiit-startup-recognition-2026-eligibility) (secondary; verify on startupindia.gov.in) |
| IndiaAI Compute Portal | Subsidised GPUs. Startups/MSMEs: DPIIT recognition, AI/ML experience and revenue Rs 50 lakh or funding Rs 100 lakh. Early-stage startups: 4 years AI/ML experience plus letter from IndiaAI CEO or JS-rank officer. Students: AI/ML project plus aligned academic profile. Requests under 5,000 GPU hours auto-approved; requests 1st-25th of month; approvals valid 30 days | Rate reported about Rs 65 per GPU-hour in a 2026 Lok Sabha reply (Business Standard), but other sources say Rs 100-150; official page lists no rates | India only | [IndiaAI compute portal](https://compute.indiaai.gov.in); [Business Standard 2026](https://business-standard.com/technology/artificial-intelligence/india-ai-compute-race-subsidised-gpu-capability-gap-126062900734_1.html). Not free: subsidised paid GPU |
| GitHub Student Developer Pack | Azure $100 credit (18+, 25+ services), Copilot Student, Namecheap .me + SSL for 1 year, Camber 5 GPU h/month | Verified students; the DigitalOcean credit cited in older guides did not appear | Not stated | [GitHub Education](https://education.github.com/pack); [gpuperhour](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) |

### Inferences
- A solo developer with no company can apply only to: GitHub Student Pack (if a student), Azure and AWS entry tiers (AWS asks for company description; Microsoft requires a legal business entity), ElevenLabs, and Cloudflare Tier 3. Incorporating a Private Ltd or LLP (and DPIIT recognition) opens NVIDIA Inception, IndiaAI and stronger AWS/Google/Cloudflare applications. That is a cost/time decision for the founder.
- Credits from AWS/GCP/Azure cannot be used on Modal, and Google credits cannot go to third parties, so credit stacking only helps if the stack actually runs on that cloud (e.g., Cloudflare credits for R2/Workers AI; AWS for Bedrock/EC2 GPU).
- Because Anthropic's program is paused and OpenAI credits are VC-gated, plan LLM spend on Google Gemini free API tier or Cloudflare Workers AI credits (not researched here).

### Gaps
- Google for Startups: official eligibility and Start-tier terms did not render; bootstrapped solo-founder eligibility is unresolved (sources conflict).
- Microsoft Founders Hub: current 2026 status unresolved (naming change, conflicting eligibility reports).
- No primary source on India eligibility for any non-Indian program; assume acceptable if incorporated, but verify.
- Replicate, fal exact terms; TwelveLabs credits; OpenAI primary page not read.
- Whether an unincorporated individual can apply to Cloudflare Tier 3 / AWS Founders: not stated.

## 6. Recommended zero-cost setup and application order

### Takeaway
Develop locally on Windows (FastAPI, SQLite, React dev server, FFmpeg, WSL2 for GPU models), use R2 free tier for files, Modal $30/month and Kaggle for GPU batches, and Oracle Always Free (2 OCPU/12 GB) or Cloud Run for a demo deployment. Apply first to programs that need no investors.

### Cited Findings (supporting each recommendation)
- Modal $30 monthly credit and prices: [Modal pricing](https://modal.com/pricing)
- R2 10 GB free, zero egress: [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- Oracle 2 OCPU/12 GB limits and idle reclamation: [Oracle docs](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- Cloudflare Pages free build limits: [CF Pages](https://developers.cloudflare.com/pages/platform/limits/)
- Neon/Turso free DB: [Neon](https://neon.com/pricing), [Turso](https://turso.tech/pricing)
- Vercel Hobby non-commercial restriction: [Vercel](https://vercel.com/docs/limits/fair-use-guidelines)

### Inferences (proposed plan; not a sourced fact)
1. Day 0 (no card or little cost): Local dev on Windows 11; React on Cloudflare Pages; Cloudflare R2 bucket for clips/renders (add TTL cleanup); Neon or Turso only if you outgrow SQLite on a host volume.
2. Day 0-1: Modal Starter account for GPU functions (WhisperX, SigLIP 2, Qwen3-VL, SAM 2, FlashVSR) with scale-to-zero. Keep a Kaggle account (phone-verified) for batch/benchmark runs.
3. Week 1: Oracle Cloud Always Free account and A1 VM (2 OCPU/12 GB), keep CPU above idle thresholds or accept reclamation; ask Oracle Support whether PAYG tenancies keep 4 OCPU/24 GB and save the response.
4. Week 1: Apply to Cloudflare for Startups Tier 3, AWS Activate Founders, Microsoft startup offer, ElevenLabs grant (if voice), GitHub Student Pack (if eligible).
5. After incorporation: DPIIT recognition, then NVIDIA Inception, Google for Startups Start/AI tier, IndiaAI compute request (auto-approval under 5,000 GPU-h).
6. Avoid for commercial: Vercel Hobby, Fly.io, Render free Postgres (30-day expiry), SageMaker Studio Lab (closed). Check Anthropic program page for reopened intake.

### Gaps
- No cost modelling of FFmpeg render throughput on 2 Arm cores; needs a benchmark.
- Whether Windows-native vs WSL2 is better for each model: not researched beyond SAM 2's README WSL recommendation.
