# Free tiers, free credits and free plans for video/audio/media AI APIs (AI Reel Editor MVP, solo dev in India) - as of 2026-11-04

Method note: figures below were fetched on 2026-11-04 from the cited pages. "Primary" = vendor's own page/docs. "Third-party" = aggregator/blog, flagged inline. India availability: no vendor page checked stated an India restriction or an India-specific rule; I did not find India-specific statements anywhere (see Gaps in the last section). Card-required status is given only where the page says it.

## 1. Video understanding (TwelveLabs, Google Video Intelligence, AWS Rekognition, Azure Video Indexer, Memories.ai, VideoDB, Jina, Voyage)

### Takeaway
TwelveLabs Free is now a storage-capped plan (3 GB, "Basic" Workload, no overage) that auto-migrates existing free users on 2027-01-04, and the Workload size is not published on a primary page, so you cannot compute how many test videos it covers. The most generous video-specific free options are Memories.ai ($100 credit, no card), Azure Video Indexer trial (600 min web / 2,400 min API), Google Video Intelligence (1,000 min/month per feature, third-hand snippet of the official page), and Gemini API free tier (video input, but data used to improve Google products).

### Cited Findings

TwelveLabs
- Free plan: $0/month, "Explore and test our APIs"; 3 GB cumulative Managed Intelligence storage; "Basic" Workload allowance renewing monthly; "Basic" rate limit; shared environment; usage capped at plan limits. No overage: new Workload requests are blocked when the allowance runs out and new uploads are blocked when the storage allowance is reached - [TwelveLabs pricing (primary, fetched 2026-11-04)](https://www.twelvelabs.io/pricing)
- The primary pricing page gives no minutes/hours/credits number for the Free Workload, no model list, no card statement, no commercial-use terms - [TwelveLabs pricing](https://www.twelvelabs.io/pricing)
- Plan change timeline: new billing started 2026-10-15 (new users start on it; Free/Developer users may move early); Developer users must choose Plus or Pro by 2027-01-03; Free users move to the new Free plan on 2027-01-04; Developer users who do not choose move to Free - [TwelveLabs migration doc (primary)](https://docs.twelvelabs.io/v1.3/docs/get-started/plans-and-billing/migrate-to-new-billing.md)
- Legacy Free plan (accounts before 2026-10-15): 600-minute shared limit across indexing, analysis and segmentation; per-index 10 video hours and 100 videos; one entity collection of up to 15 entities; indexes expire 90 days after creation - [TwelveLabs migration doc (primary)](https://docs.twelvelabs.io/v1.3/docs/get-started/plans-and-billing/migrate-to-new-billing.md); the 90-day expiry on downgrade to Free is also in [Manage your plan (primary)](https://docs.twelvelabs.io/docs/get-started/manage-your-plan)
- After the move, "your plan's allowances apply instead of these limits" (i.e. the 600-min legacy cap is replaced by 3 GB/Basic Workload) - [migration doc](https://docs.twelvelabs.io/v1.3/docs/get-started/plans-and-billing/migrate-to-new-billing.md)
- Existing assets do not count toward Managed Intelligence storage until you enable storage accounting, which must be done before adding an asset to a Marengo-enabled index or knowledge store - [migration doc](https://docs.twelvelabs.io/v1.3/docs/get-started/plans-and-billing/migrate-to-new-billing.md)
- New-billing Free rate limits: Index 60 RPM / 3,000 RPD / 600 min per hour / 3,000 min per day; Upload 60 RPM; Search 600 RPM; Analyze 60 RPM, 1,000 RPD, 30,000 output TPM, 500,000 output tokens/day; Jockey Response 5 RPM / 15 RPD. Marengo 3.5 embeddings on Free: Video and Audio 25 RPM, 3,000 RPD (input 50M TPM / 500M TPD video); Image and Text 600 RPM - [TwelveLabs new-billing rate limits (primary)](https://docs.twelvelabs.io/v1.3/docs/get-started/plans-and-billing/rate-limits/new-billing.md)
- Legacy Free limits: Index capped 3,000 min/day and 600 min/hour; Marengo 3.0 video/audio 3,000 min/day; Developer Tier 1 (starts when you add a payment method) has the same limits as Free - [TwelveLabs legacy-billing rate limits (primary)](https://docs.twelvelabs.io/v1.3/docs/get-started/plans-and-billing/rate-limits/legacy-billing.md)
- Paid tiers: Plus $29/month ($290/yr) 50 GB, Medium Workload, no overage; Pro $99/month ($990/yr) 200 GB, High Workload, optional overage (storage $0.065/GB/month; Analyze $1.75/hour; Embed from $0.065 per 1M tokens; Search $4 per 1,000 queries) - [usagepricing.com (third-party tracker; says it captured the official page on 2026-10-15)](https://www.usagepricing.com/blueprint/activity/twelve-labs-2026-10-15-subscription-plans-replace-payg)
- Old pay-as-you-go Developer rates (no longer on pricing page): indexing $2.50/hour, Analyze $1.75/hour plus $7.50 per 1M output tokens, search $4/1,000 queries - [usagepricing.com (third-party)](https://www.usagepricing.com/blueprint/activity/twelve-labs-2026-10-15-subscription-plans-replace-payg)
- A May 2026 third-party listing described a free tier of "up to 600 minutes of indexing, 90 days retention" (matches the legacy plan; superseded by the 3 GB plan for new accounts) - [xpay.sh index (third-party)](https://www.xpay.sh/agent-ready-index/twelvelabs-io/)

Google Video Intelligence API
- Label detection for stored video is free for the first 1,000 minutes per month (the official table's free band runs to 1,001 min); partial minutes round up; older examples show $0.10/min after free; Google pricing guide also describes 1,000 free minutes of streamed video per month. I could not fetch the pricing tables directly (page rendered title only); these come from a search summary of the official page - [Google Video Intelligence pricing (primary, via search summary)](https://cloud.google.com/video-intelligence/pricing)

AWS Rekognition
- Legacy free tier (12 months from account creation): 1,000 images/month for Group 1 and Group 2 APIs, 60 minutes of stored video analysis per month (label, moderation, face detection/search, celebrity, text detection, person pathing), 1,000 face-vector objects. - [AWS Rekognition pricing (primary)](https://aws.amazon.com/rekognition/pricing/)
- New customers from 2025-07-15 can choose a free plan (6 months) or a paid plan, with up to $200 credits that must be used within 12 months; the page does not say if the 60 free video minutes apply under the credit-based plan. Stored-video label detection $0.10/min - [AWS Rekognition pricing](https://aws.amazon.com/rekognition/pricing/)

Azure Video Indexer
- Trial: up to 600 minutes free indexing via website, up to 2,400 minutes via API (product page); docs say 2,400 minutes via either website or API (conflict between Microsoft pages). Trial account may be deleted after 12 months of no use. Not available in Azure Government - [search summary of Microsoft Video Indexer pricing/docs (primary pages, unfetched)](https://azure.microsoft.com/pricing/details/video-indexer/) and [Microsoft Learn account types](https://learn.microsoft.com/azure/azure-video-indexer/accounts-overview)
- A Microsoft Q&A thread (community, unverified) claims trial accounts cannot issue Azure AD tokens needed for automation - [Q&A](https://learn.microsoft.com/en-us/answers/questions/5849365/issue-using-azure-ai-video-indexer-trial-with-powe)
- Microsoft notes Video Indexer feature "adjustments" due to Azure Media Services retirement; details not confirmed - [Learn account types](https://learn.microsoft.com/azure/azure-video-indexer/accounts-overview)

Memories.ai
- New developer/startup accounts get $100 free credits, no credit card required; console.memories.ai. Listed API rates: video embedding $0.12/min, index-to-search $15/1,000 min, storage $0.03/GB-month, Whisper transcription $3.60/hour, edit video $0.15/min, search $0.10/1,000. Rate limits/expiry not listed - [Memories.ai pricing (primary)](https://www.memories.ai/pricing)

VideoDB
- Pricing page mentions only "$20 of free credits" when you add VideoDB to Claude and try it on a video link; storage/minutes/card not stated. Free tier otherwise unconfirmed - [VideoDB pricing (primary)](https://videodb.io/pricing)

Jina embeddings
- New users get an auto-generated API key with free tokens (amount not stated on the page). Embeddings free-key rate limit 100 RPM / 100,000 TPM. Current multimodal models (text, image, audio, video, PDF): jina-embeddings-v5-omni-small/nano; jina-clip-v2 (text+image). CC BY-NC 4.0 weights need a commercial license for self-hosting (Elastic Jina On-Prem since 2026-08-10); using the hosted API does not require a separate license; jina-embeddings-v4 is Qwen Research License (non-commercial only) - [Jina embeddings page (primary)](https://jina.ai/embeddings/)

Voyage AI
- First 200M tokens free per account for voyage-4 family; 50M for older domain models. voyage-multimodal-3.5 and -3: 200M text tokens and 150B pixels free per account; each video frame counts as an image; paid $0.12/M text tokens, $0.60/B pixels - [Voyage pricing (primary)](https://docs.voyageai.com/docs/pricing)

Gemini API (relevant because the earlier report picked Gemini Flash for video analysis)
- Gemini 3.8 Flash Standard tier: input/output/caching "Free of charge" on the free tier, but free-tier data is "used to improve our products" (paid: no). Gemini 3.5 Flash-Lite and 3.1 Flash-Lite free incl. video input at text rate; Gemini 4 Argon and Gemini Omni Flash (video gen/edit) have no free tier; Batch/Flex not available free; 2.5 Pro/Flash deprecated, routed to newer models 2026-12-01; free-tier rate limits not shown on the page - [Gemini pricing (primary)](https://aistudio.google.com/docs/pricing)
- Earlier report notes that Gemini 3.8 Flash is $0.75/$3.75 per M tokens until 2026-12-31 and recommends paid tiers only for data-training reasons - from the local earlier report at `C:/Users/kiran/Desktop/PVE/reports/Reel editor model and tool stack.md`

### Inferences
- TwelveLabs Free (3 GB, hard stop, no overage) is enough to prototype the A/B arm on a handful of short reels, but 3 GB is storage not minutes, so a rough conversion (about 10-60 short 1080p reels depending on bitrate) is my estimate, not a vendor number.
- Free-tier rate limits (Index 3,000 min/day etc.) are not the blocker; the unpublished Workload size is.
- Free Gemini input is the cheapest video-analysis dev path, but real user/reference reels must not go through it (training on free-tier data).
- Memories.ai $100 would buy roughly 800 min of embedding at the listed $0.12/min (my arithmetic).

### Gaps
- Exact "Basic Workload" size for TwelveLabs Free; which models (Marengo 3.5, Pegasus 1.6) are enabled on Free; card requirement and commercial-use terms for Free - not on any fetched primary page.
- Google Video Intelligence per-feature free tiers - tables did not render; only search-summary evidence.
- Azure Video Indexer pricing page not fetched directly; conflict on 600 vs 2,400 minute split.
- VideoDB free tier beyond the $20 Claude promo; Memories.ai rate limits and credit expiry.
- Jina exact free token count.

## 2. Speech / ASR and TTS (Deepgram, AssemblyAI, ElevenLabs, Gladia, Speechmatics, Rev.ai, Groq, OpenAI)

### Takeaway
For transcription, Deepgram ($200, no card, no expiry) and Speechmatics ($100, no card) and Gladia (EUR 50, 1-year validity) give the largest no-cost headroom; AssemblyAI gives $50 no card. ElevenLabs Free is non-commercial with attribution and about 30 min of Scribe or about 10 min of TTS per month, so it is only a prototype tool.

### Cited Findings

| Service | Free allowance | Expiry/renewal | Card | Notes | Source |
|---|---|---|---|---|---|
| Deepgram | $200 credit on Pay-as-you-go | Does not expire | No | Nova-3 pre-recorded $0.0043/min mono, $0.0052 multi; streaming $0.0077/min; TTS Aura-2 $0.030/1k chars; PAYG 150 concurrent streams | [Deepgram pricing (primary)](https://deepgram.com/pricing) |
| AssemblyAI | $50 credit at signup | Expiry not stated | No | 5 new streams/min on free (100 on PAYG); Universal-3.5 Pro $0.21/hr, Universal-2 $0.15/hr; default model differs free vs paid, set `speech_models` explicitly | [AssemblyAI pricing (primary)](https://www.assemblyai.com/pricing) |
| ElevenLabs Free | 10,000 credits/month (about 10 min TTS at 1 credit/char; Scribe 330 credits/min = about 30 min/month); no rollover | Monthly | Not stated | About 2 concurrent requests; no commercial license (starts at Starter); instant voice cloning not on Free; API access on Free not stated on pricing page | [ElevenLabs pricing (primary)](https://elevenlabs.io/pricing) |
| ElevenLabs terms | "If you are on the free plan, you can use the content non-commercially with attribution"; paid plans grant commercial rights | - | - | Attribution wording not specified in docs; three custom voice slots via Voice Design on Free | [ElevenLabs billing docs (primary)](https://elevenlabs.io/docs/overview/administration/billing) |
| Gladia | EUR 50 free credits on Self-serve (about 312 hrs async Solaria-3, 185 hrs Solaria-1, 73 hrs real-time) | Valid one year | Not stated | 25 concurrent async, 30 real-time; no recurring free hours | [Gladia pricing (primary)](https://gladia.io/pricing) |
| Speechmatics | $100 free credits | Not stated; not stated whether recurring | No | Free: up to 2 concurrent real-time, 10 pre-recorded files/sec; Melia 1 $0.24/hr pre-recorded; Enhanced $0.75/hr; data location EU/US/AUS | [Speechmatics pricing (primary)](https://www.speechmatics.com/pricing) |
| Rev.ai | Free credits equal to 5 hours of Reverb ASR | Not stated | Not stated | Reverb English $0.20/hr; Whisper Large $0.005/min | [Rev.ai pricing (primary)](https://www.rev.ai/pricing) |
| Groq Whisper | Free tier exists (not verified); the doc table (labelled "Developer plan base limits") shows whisper-large-v3 / -turbo: 20 RPM, 2K requests/day, 7.2K audio-seconds/hour, 28.8K audio-seconds/day (= 8 hours/day) | Daily | Not stated | Free-plan numbers not separately shown; check account limits page | [Groq rate limits (primary)](https://console.groq.com/docs/rate-limits) |
| OpenAI | No free credits or free tier mentioned; whisper-1 $0.006/min; gpt-4o-transcribe $0.006/min; gpt-4o-mini-transcribe $0.003/min | - | - | - | [OpenAI pricing (primary)](https://developers.openai.com/api/docs/pricing) |

- Third-party search results conflict on ElevenLabs Free API access (most say a key can be generated on Free; one older source says no); not settled on a primary page - [Puter ElevenLabs API pricing (third-party)](https://developer.puter.com/tutorials/elevenlabs-api-pricing/)
- fal.ai Whisper not on its pricing page (see section 5) - [fal pricing](https://fal.ai/pricing)

### Inferences
- Deepgram $200 at $0.0043/min is about 46,500 minutes (about 775 hours) of pre-recorded English - my arithmetic from the cited price; far more than an MVP needs, and no card or expiry.
- Groq's 28.8K audio-seconds/day is 8 hours/day, ample for dev if the free plan matches the doc table.
- ElevenLabs Free cannot ship in a product (non-commercial + attribution); use it only to evaluate voice quality or use Deepgram Aura-2 TTS credits instead.

### Gaps
- Groq free-plan-specific limits and max file size; ElevenLabs Free API access and Scribe-on-Free confirmation; AssemblyAI credit expiry; Rev.ai expiry/card; Gladia/Speechmatics card requirement and commercial terms; self-hosted WhisperX has no API free tier question (not researched).

## 3. Music and sound (AudD, ACRCloud, Jamendo, Freesound, Pixabay music, YouTube Audio Library, Epidemic/Artlist, Mubert)

### Takeaway
Music ID has usable free trials (AudD 300 requests, ACRCloud no-card trial of unspecified size). For licensed music, only Epidemic Sound's free API tier is a clear self-serve evaluation path; Mubert API has no free tier (paid $49 trial); Jamendo/Freesound limits are generous but commercial terms must be checked.

### Cited Findings
- AudD: 300 free recognition requests for new accounts "where available"; no credit card needed per FAQ; file recognition $2-$5 per 1,000 requests; $5/month plan includes 1,000 requests; extra $5 per 1,000 - [AudD (primary)](https://audd.io/)
- ACRCloud: "Start Free Trial" with no credit card; trial length, request quota and pricing not stated on the pricing page - [ACRCloud pricing (primary)](https://www.acrcloud.com/pricing/)
- Jamendo API: needs a `client_id` from devportal.jamendo.com; new applications are read-only by default (write needs approval); contact Jamendo if you exceed 500,000 hits; high-consumption apps get reviewed, may get temporary limits, 7-day response window; non-commercial vs commercial terms are not on the docs page (see API Terms of Use) - [Jamendo authentication docs (primary)](https://developer.jamendo.com/v3.0/authentication). Earlier report states Jamendo's free tier is non-commercial - local earlier report, not independently verified here.
- Freesound API: 60 requests/minute and 2,000/day standard; 30/min and 500/day for original-quality downloads, uploads and writes; license/non-commercial terms not on this page (per-sound Creative Commons licenses; not verified) - [Freesound API overview (primary)](https://freesound.org/docs/api/overview.html)
- Pixabay (images, video, and music on the site): Content License lets you use content free; no attribution required; cannot be sold/redistributed standalone; no trademark/logo commercial use - [Pixabay license summary (primary)](https://pixabay.com/service/license-summary/). The Pixabay API docs list video and image endpoints but no music endpoint - [Pixabay API docs (primary)](https://pixabay.com/api/docs/)
- Epidemic Sound API: self-serve free tier with API key issued instantly, "no contract, no credit card," full catalog of music and SFX for prototyping/evaluation; limits not specified; production pricing not published; production access depends on a partnership agreement - [Epidemic Sound developers (primary)](https://www.epidemicsound.com/business/developers/), [Epidemic docs](https://developers.epidemicsound.com/docs/getting-started)
- Artlist: only a passing mention of an Artlist Music API; no access or pricing info found - [Epidemic/Storyblocks comparison search results](https://www.epidemicsound.com/blog/artlist-vs-epidemic-sound)
- Mubert API: official page lists a Trial Plan at $49/month (100 generations and 100 streaming minutes/month); no free API tier on the official page; third-party trackers conflict (a free Ambassador plan of 25 tracks/month is consumer, non-commercial, not API) - [Mubert API (primary)](https://mubert.com/api), [CostBench (third-party, unreliable)](https://costbench.com/software/ai-music-apis/mubert-api/free-plan/)
- YouTube Audio Library: not researched (no source fetched).

### Inferences
- AudD 300 requests + ACRCloud trial cover all MVP music-ID testing; one request per reference reel means 300 reels.
- For shipping with licensed music, Pixabay (no attribution, commercial OK) is the zero-cost safe default but has no music API endpoint, so it needs manual curation or scraping (check terms).

### Gaps
- ACRCloud trial size; Jamendo commercial terms; Freesound license terms; YouTube Audio Library; Artlist API; Epidemic free-tier limits.

## 4. Stock footage and images (Pexels, Pixabay, Unsplash, Coverr, Storyblocks)

### Takeaway
Pexels and Pixabay APIs are free with generous limits and commercial-OK licenses; Unsplash is images only; Coverr's API terms and Storyblocks API were not found.

### Cited Findings
- Pexels API: free; 200 requests/hour and 20,000/month by default; unlimited free on request if you meet API terms; must show a prominent link to Pexels and credit photographers when possible; may not replicate Pexels core functionality; video endpoints `/v1/videos/search`, `/v1/videos/popular` - [Pexels API docs (primary)](https://www.pexels.com/api/documentation/)
- Pexels license page fetch failed (HTTP 403), so the Pexels content license (commercial use, attribution) is unverified in these notes; the API docs only say all content is free of charge - [Pexels API docs](https://www.pexels.com/api/documentation/)
- Pixabay API: 100 requests per 60 seconds per key; responses must be cached 24 hours; no systematic mass downloads; permanent hotlinking not allowed (download first); video endpoint `GET /api/videos/`; attribution requested in return for free API - [Pixabay API docs (primary)](https://pixabay.com/api/docs/)
- Unsplash API: attribution to Unsplash and photographer with UTM links required; must hotlink `photo.urls`; must call `download_location` endpoint on use; demo/production rate limits not on the guidelines page (images only, no video) - [Unsplash API guidelines (primary)](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines)
- Coverr API page: terms for free, rate limit, license, attribution, approval not stated; notes a downloads quota - [Coverr API (primary)](https://www.coverr.co/api)
- Storyblocks: no API or free developer access found in search - [search results](https://www.storyblocks.com/resources/?p=35844)

### Inferences
- Pexels + Pixabay video endpoints are sufficient for B-roll fallback in dev and likely in production at MVP scale. Pexels' attribution/link requirement is for the API display, so a product UI needs a Pexels link.

### Gaps
- Pexels license text (403); Unsplash numeric limits; Coverr terms; Storyblocks.

## 5. Generative and enhancement (fal.ai, Replicate, Runway, Kling, Luma, MiniMax, PixVerse, Pika, Hugging Face, remove.bg, Photoroom, Clipdrop, Topaz)

### Takeaway
No major generative video API gives a large, verified, no-card free pool. fal.ai and Replicate free credits are unverified on primary pages, Runway/Luma/Kling APIs are pay-first, and Hugging Face ZeroGPU (5 free GPU min/day) is the only genuinely free GPU route. For background removal, Photoroom sandbox (1,000 watermarked calls/month) and remove.bg (50 calls/month) are usable.

### Cited Findings
fal.ai
- fal pricing page lists no free credits, free tier or card statement. Prices: Kling v3 Pro/Standard $0.14/s; Kling 2.5/2.6 Pro $0.07/s; MiniMax H3 Max $0.05/s, H3 Max Turbo $0.025/s; BiRefNet v2 listed $0 per compute second; SeedVR2 image upscale $0.001/MP; FILM $0.0013/s; no Hailuo or Whisper listed - [fal pricing (primary)](https://fal.ai/pricing)
- fal docs: new accounts start at 2 concurrent requests, rising to up to 40 with credit purchases; purchased credits expire 365 days after purchase; free credits/coupons expire between 1 week and 1 year; account locks below a lock threshold and API calls are rejected - [fal FAQ (primary)](https://fal.ai/docs/documentation/model-apis/faq.md)
- Signup credit amount: sources disagree ($1 no card; about $20 with business email; "promotional credits" unquantified); no official figure found - [yangmao.ai fal tracker, updated 2026-06-24 (third-party)](https://yangmao.ai/en/providers/fal/free-tier/); search summary of other third-party listings
- Separate grant programs exist (builder grant, startup program, agent-access) by application, listed at [fal builder grant](https://fal.ai/builder-grant) and [startup program](https://fal.ai/startup-program) (pages seen only in search results, terms unread)

Replicate
- Replicate billing docs: "You can run select models on Replicate for free, but after a bit you'll be asked to set up billing." No dollar free credit mentioned; some features need billing - [Replicate billing docs (primary)](https://replicate.com/docs/topics/billing)
- Replicate pricing page mentions no free credits, trial or card details; sample prices wan-2.1-i2v-480p $0.09 per second of output video, A100 80GB $0.0014/sec - [Replicate pricing (primary)](https://replicate.com/pricing)
- A "$500 free credits, no card" claim is a promo site, unverified and likely marketing - [getaiperks.com (third-party, treat as unreliable)](https://www.getaiperks.com/en/ai/free-replicate-credits)

Video generation APIs
- Runway API: credits $0.01 each; gen4_turbo 5 credits/s ($0.05/s); free credits not mentioned; the Runway web free plan (125 one-time credits, third-party) is not API - [Runway API pricing (primary)](https://docs.dev.runwayml.com/guides/pricing/), [Creatify (third-party)](https://creatify.ai/blog/runway-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay)
- Luma API: no free credits or trial on pricing page; Ray3.2 SDR 5s T2V/I2V $0.15 (540p), $0.30 (720p), $1.20 (1080p) - [Luma API pricing (primary)](https://lumalabs.ai/api/pricing)
- Kling API: no confirmed free API credits; third-party sources conflict (about $1 grant vs no free tier vs paid trial pack about $9.80 for 100 units); consumer app 66 credits/day is not API - [Atlas Cloud (third-party)](https://www.atlascloud.ai/blog/tips/kling-ai-api-pricing), [apis.io (third-party)](https://apis.io/plans/kling-ai/kling-ai-plans-pricing/)
- MiniMax/Hailuo, PixVerse, Pika free daily credits: not researched/no source fetched.

Hugging Face
- ZeroGPU daily GPU quota: unauthenticated 2 min, Free account 5 min, PRO 40 min; resets 24h after first use; free accounts (verified email, older than 30 days) may host up to 2 ZeroGPU Spaces; Gradio SDK only; RTX Pro 6000 Blackwell; PRO extra $1 per 10 min - [HF ZeroGPU docs (primary)](https://huggingface.co/docs/hub/spaces-zerogpu)
- Free Spaces hardware: CPU Basic (2 vCPU, 16 GB) free and ZeroGPU free; PRO includes $2/month inference credits; free-tier inference credit amount not stated - [HF pricing (primary)](https://huggingface.co/pricing)

Background removal and upscaling
- remove.bg API: first 50 API calls per month free; 50 MP output costs 1 credit; free resolution and commercial use not stated - [remove.bg API (primary)](https://www.remove.bg/api)
- Photoroom API: 1,000 sandbox calls/month on Image Editing API (watermarked results), plus 10 free production calls on Remove Background; no card for trial; about $20 for 1,000 images in an FAQ example - [Photoroom API pricing (primary)](https://www.photoroom.com/api/pricing)
- Clipdrop: "now part of Jasper"; no pricing, credits or commercial terms on its API page (remove background, upscale up to x16) - [Clipdrop APIs (primary)](https://clipdrop.co/apis)
- Topaz Video: no free trial mentioned on the fetched page; API is Enterprise "Contact sales"; local render unlimited on paid plans; cloud credits (25-600/month by plan) expire monthly; page truncated - [Topaz Video AI page (primary)](https://www.topazlabs.com/video-ai)

### Inferences
- With fal/Replicate free credits unverified, budget a small paid top-up for B-roll/upscale tests (e.g. a few dollars: 10 s of MiniMax H3 Max Turbo is about $0.25 and 10 s of Kling v3 about $1.40 from the listed per-second prices, my arithmetic).
- Self-hosted open models (BiRefNet, SeedVR2, FILM, RIFE) on a local/Colab GPU avoid the free-credit uncertainty; this is a design suggestion, not sourced.
- HF ZeroGPU's 5 min/day quota is for demos/small tests only and requires Gradio wrappers.

### Gaps
- Official fal.ai signup credit amount and card requirement; Replicate free-run count and whether a card is required for API calls; MiniMax, PixVerse, Pika, Luma API trial; Topaz free trial and watermark; Clipdrop/Jasper API pricing; remove.bg preview resolution and commercial rules.

## 6. OCR and vision (Google Cloud Vision, Azure AI Vision, OCR.space)

### Takeaway
All three give enough free OCR for template-text detection tests: Google 1,000 units/month, Azure F0 5,000 transactions/month (20/min), OCR.space 25,000 requests/month but limited to 1 MB images.

### Cited Findings
- Google Cloud Vision: first 1,000 units per feature per month free; TEXT_DETECTION and DOCUMENT_TEXT_DETECTION $1.50 per 1,000 for 1,001 to 5M; one unit = one feature on one image; some sources say new GCP customers also get $300 credit - [Vision pricing (primary; page fetch truncated, confirmed via search summary)](https://cloud.google.com/vision/pricing), [vantaige.io (third-party)](https://vantaige.io/blog/google-vision-ai-pricing-explained-alternatives-2026)
- Azure AI Vision F0: 5,000 transactions/month, 20/minute, per subscription; each feature requested counts as a transaction; S1 about $1 per 1,000 for tagging and $1.50 per 1,000 for OCR (from Microsoft Q&A/template, not the pricing page) - [Microsoft Q&A (primary-adjacent)](https://learn.microsoft.com/en-us/answers/questions/2155960/computer-vision-free-(f0)-limitations-(5-000-trans)
- OCR.space free API key: 25,000 requests/month (plus 1,000 Engine 3), 500 requests/day per IP, 1 MB max file, 3 PDF pages max, searchable PDF watermarked; PRO $30/month - [OCR.space API (primary)](https://ocr.space/ocrapi)

### Inferences
- OCR on extracted keyframes (sub-1 MB JPEG) fits all three; Google or Azure for quality, OCR.space for volume.

### Gaps
- Azure official pricing page returned 404; commercial-use terms of OCR.space free tier not stated.

## 7. Rendering services (Shotstack, Creatomate, JSON2Video, Remotion, Cloudinary, Mux)

### Takeaway
Rendering services' free tiers are small trials; since the MVP renders with FFmpeg, none is needed. Remotion is the only free-for-commercial option (up to 3 people), and Cloudinary/Mux free tiers are for hosting/delivery.

### Cited Findings
- Shotstack: 10 credits at signup valid 30 days, no card; pay-as-you-go 20 cents/minute, one credit = one minute; free sandbox mentioned without details; watermark/commercial terms not stated on the page. - [Shotstack pricing (primary)](https://shotstack.io/pricing/)
- Creatomate: 50 free credits, no time limit, no card; free renders are small previews up to 480 px; API on every plan (trial API confirmation not explicit); Essential $45/month 2,000 credits - [Creatomate pricing (primary)](https://creatomate.com/pricing)
- JSON2Video: 600 credits free, no card; 1 credit per second so about 10 min; free plans are watermarked; API on paid plans only per page - [JSON2Video pricing (primary)](https://json2video.com/pricing/)
- Remotion: free for individuals and companies up to 3 people, unlimited commercial use; 4+ people need a Company license ($0.01/render, $100/month minimum for Automators; $25/seat/month for Creators) - [Remotion license (primary)](https://www.remotion.pro/license). The earlier report cites additional restrictions (headcount counts the whole company; users may not upload their own Remotion projects for rendering) from the [Remotion FAQ](https://www.remotion.dev/docs/license/faq), not re-fetched here.
- Cloudinary Free: 25 monthly credits (1 credit = 1 GB storage or 1 GB bandwidth or 1,000 transformations), 3 users, no card; boosted video bandwidth paid only; video file-size/duration limits not stated - [Cloudinary pricing (primary)](https://cloudinary.com/pricing)
- Mux: 100,000 delivery minutes free every month, no card to start; 1080p basic on-demand encoding free; storage from $0.003/min/month; Pay-as-you-go includes $20 monthly credit; a 'Free plan' asset cap/watermark not stated on the page - [Mux pricing (primary)](https://www.mux.com/pricing)

### Inferences
- Skip paid render APIs: FFmpeg is already the renderer. Cloudinary/Mux are only useful for previews/hosting; both have no-card free allowances.

### Gaps
- Shotstack sandbox limits and watermark; Creatomate API on trial; Mux Free plan limits.

## 8. Verdict: which free tiers are enough to build the MVP end to end, and which are blockers

### Takeaway
Free is enough for analysis, transcription, OCR, stock footage, music ID and local FFmpeg rendering. It is not enough for generative B-roll, hosted upscaling and video-model testing, and not safe for production on Gemini free-tier or ElevenLabs Free.

### Cited Findings
- Enough, no card: Deepgram ($200, no expiry), AssemblyAI ($50), Speechmatics ($100), Memories.ai ($100), Pexels/Pixabay APIs, AudD (300 requests), Google Vision 1,000 units/month, Azure Vision F0 5,000/month, OCR.space 25,000/month - sources in sections 1 to 6.
- TwelveLabs Free is capped at 3 GB with hard stop and unspecified Workload; existing free users migrate 2027-01-04 - [TwelveLabs pricing](https://www.twelvelabs.io/pricing), [migration doc](https://docs.twelvelabs.io/v1.3/docs/get-started/plans-and-billing/migrate-to-new-billing.md)
- Blockers: no confirmed free credits on Runway/Luma/Kling APIs, Topaz (API Enterprise only), and fal.ai/Replicate (no primary-page amount) - sections 5.
- Non-commercial limits on free: ElevenLabs Free; Jamendo (earlier report, unverified); Jina CC BY-NC weights for self-hosting - sections 2, 3, 1.

### Inferences
- Recommended zero-spend dev stack: local FFmpeg render; Deepgram or Groq for ASR; Gemini free tier for dev-only video analysis with non-sensitive clips; TwelveLabs Free for the A/B arm; Google Vision or OCR.space for OCR; Pexels/Pixabay for B-roll; AudD for music ID; local open models or HF ZeroGPU for background removal/upscaling.
- Plan a small paid budget (about $10 to $20, my estimate) for fal.ai B-roll and upscale tests, since no free route is verified.

### Gaps
- India availability and India-payment issues (Indian cards, INR, GST, regional restrictions) were not found on any fetched page; verify at signup. Notably, the earlier report said MiniMax H3 weights exclude the US/EU/UK/South Korea (not India), but this is about weights not the API.
- No developer-forum evidence on real-world free-tier limits was gathered (time/tool budget).
- Mistaken or unverifiable items flagged above: fal.ai/Replicate credits (third-party), Kling API (third-party conflict), Mubert (aggregators conflict), Google Video Intelligence tables (search summary only).
