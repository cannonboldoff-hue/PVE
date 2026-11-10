# Free tiers and credits for LLM/VLM APIs (AI Reel Editor dev, as of 2026-11-04)

Method note: ~28 tool calls. Primary pages read: Google pricing + terms, OpenRouter limits doc, HF pricing doc, Groq rate-limit doc, Alibaba Model Studio free-quota doc, claude.com startups page. Everything else is aggregator/search-snippet and is flagged "UNVERIFIED". Free tiers change monthly; no India-specific restriction was found on any page read, but no page affirmatively confirmed India availability either (except where noted). Earlier report (Reel editor model and tool stack.md) skimmed: picks are Gemini 3.8 Flash direct, Sonnet 5.5/Haiku 5.5 via OpenRouter, Gemini Embedding 2 / Marengo, Qwen3-VL fallback, GLM-5.1 / Qwen3.7 Plus budget. Its own advice: use paid tiers only in production because paid Gemini does not train on data.

## Q1. Google Gemini API free tier (AI Studio)

### Takeaway
Gemini 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite, 3 Flash Preview, Gemini Embedding 2 and Gemma 4 are "Free of charge" on the Standard tier; Gemini 4 Argon, 3.1 Pro Preview and Omni Flash are not free. Free-tier content is used to improve Google products (and human-reviewed); paid tier is not. This makes free tier fine for dev with throwaway/test clips but unsuitable for real user footage. Exact RPM/RPD numbers could not be confirmed from a primary page.

### Cited Findings
- Pricing page "Free tier" column (read 2026-11-04): Gemini 3.8 Flash "Free of charge"; 3.6 Flash "Free of charge"; 3.5 Flash-Lite "Free of charge" (text/image/video/audio input); 3.1 Flash-Lite "Free of charge" (text/image/video); 3 Flash Preview "Free of charge" (text/image/video); Gemini Embedding 2 "Free of charge" with video input (priced per frame on paid); Gemini Embedding (text) free; Gemma 4 free; 2.5 Flash / 2.5 Flash-Lite free — [Gemini pricing](https://aistudio.google.com/docs/pricing) (ai.google.dev/gemini-api/docs/pricing 301-redirects here)
- NOT free: Gemini 4 Argon ("Not available"), Gemini 3.1 Pro Preview ("Not available"), Gemini Omni Flash ("Not available"), Nano Banana variants, Lyria. Gemini 3.8 Flash shows "Not available" on Batch and Flex tabs (free only on Standard/Priority tab as displayed) — [Gemini pricing](https://aistudio.google.com/docs/pricing)
- "Used to improve our products": Yes on free tier, No on paid tier for every free-eligible model listed — [Gemini pricing](https://aistudio.google.com/docs/pricing)
- Terms: unpaid services content may be used to "provide, improve, and develop" Google products and ML; human reviewers may read it; "Do not submit sensitive, confidential, or personal information to the Unpaid Services." Paid: Google "doesn't use your prompts... or responses to improve our products" (still logged briefly for policy-violation detection) — [Gemini API terms](https://aistudio.google.com/docs/terms) (ai.google.dev/gemini-api/terms redirects here)
- EEA/Switzerland/UK: paid-service data protections also apply to unpaid quota and AI Studio, but "You may use only Paid Services when making API Clients available to users" there — [Gemini API terms](https://aistudio.google.com/docs/terms). India is not in this carve-out, so India-based free use falls under the "used for training" regime.
- Commercial use: terms describe the services as for "professional or business purposes" and not consumer use; no explicit ban on commercial use of free tier found. Must be 18+. Access only "within an available region" — [Gemini API terms](https://aistudio.google.com/docs/terms). The terms summary did not list India either way.
- Rate-limit doc: limits are per project (not per key); daily quotas reset at midnight Pacific; Free tier needs an "Active project or free trial" and "some projects need verification"; per-model numbers are only shown inside AI Studio; preview/experimental models have tighter limits; billing activation moves project to Tier 1+ — [Rate limits](https://aistudio.google.com/docs/rate-limits)
- Third-party figures (UNVERIFIED, dates vary): OpenRouter's own blog (updated 2026-09-24) summarises Gemini free as 5-15 RPM, 20-1,500 RPD, up to 1M context, "data training: Yes (outside EU/UK/EEA)" — [OpenRouter blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/). Another snippet says Pro models were removed from free tier in April 2026 and 2.5 Flash free was 10 RPM/250 RPD in Jan 2026 — [search snippets](https://tinkerllm.com/blog/gemini-api-free-tier-limits-rate-quotas/).
- 2.5 Pro and 2.5 Flash are deprecated and requests route to newer models from 2026-12-01 — [Gemini pricing](https://aistudio.google.com/docs/pricing)
- Forum reply (not formal terms): once a billing account is linked to a project, all usage is paid-tier and not used for training — [Google AI forum](https://discuss.ai.google.dev/t/clarification-on-gemini-api-free-tier-vs-paid-tier-after-billing-activation/96995)
- Caveat from Simon Willison (2024): AI Studio UI itself is treated as "free" for data-use purposes even on a billed account — [Willison](https://simonwillison.net/2024/Oct/17/gemini-terms-of-service)

### Inferences
- Dev flow: use a free-tier key from a separate non-billing project for Gemini 3.8 Flash / 3.5 Flash-Lite video description of your own or licensed test clips; keep prod on a billed project. Same SDK and model IDs, so no code change.
- Gemini Embedding 2 being free makes the whole embeddings pipeline testable at $0 (rate limits unknown).
- Free-tier throughput (likely tens to low hundreds of requests/day for Flash class) is enough to build and unit-test, not to batch-index a footage library.
- Don't upload user footage or third-party Reels to the free key; per Google's terms human reviewers may read it.

### Gaps
- Exact per-model RPM/TPM/RPD for 3.8 Flash, 3.5 Flash-Lite, Embedding 2 on free tier: only visible inside AI Studio (login-gated); no primary page captured them.
- Whether India accounts get the free tier for all models (e.g., some free models were restricted by country in the past): not confirmed on any page.
- Whether free tier has a video-length / Files API storage cap different from paid: not checked.

## Q2. OpenRouter `:free` models

### Takeaway
OpenRouter free models are capped at 20 RPM and 50 req/day (1,000/day after buying at least $10 credits all-time). The free catalog churns; I could not retrieve a reliable current list with modality/tool/schema flags, and no confirmed free video-capable model was found beyond a single stale third-party mention.

### Cited Findings
- Official limits: free (`:free`) models 20 RPM at both tiers; 50 RPD if purchased credits < 10, 1,000 RPD if >= 10; tier depends on all-time credits purchased; negative balance can break even free models; BYOK and exempt accounts not subject; 429 on platform limits; `GET /api/v1/key` shows `free_model_daily_requests` — [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- `openrouter/free` router picks a random free model, filtering for needed features (image understanding, tool calling, structured outputs named; video not mentioned) — [Free router docs](https://www.openrouter.ai/docs/guides/routing/routers/free-router.md)
- A third-party tracker (data last updated 2026-05-14, stale) listed NVIDIA Nemotron Nano 12B 2 VL (free) as built for video understanding, Gemma 4 31B (free) as text+image only, Owl Alpha as tool-use capable — [aimcp tracker](https://www.aimcp.info/openrouter-models). UNVERIFIED and likely out of date.
- Live models page with a max-price-0 filter showed only one fully free model ("Stealth: Crouton Alpha", 1.05M context, modalities not specified) at fetch time; the page seemed partial — [OpenRouter models](https://openrouter.ai/models?max_price=0&order=top-weekly)
- OpenRouter's own blog (2026-09-24) says 20+ free models, no card, "data training: No" — but data policy actually depends on each underlying provider; see model page. — [OpenRouter blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/)
- Earlier report: video via OpenRouter is contested; only a GLM row listed video; Gemini should go direct to Google. Claude Sonnet/Haiku 5.5 have no `:free` variants (not found; paid only).

### Inferences
- Use OpenRouter free only for exercising the OpenRouter code path (client, error handling, 429 retry) with some free tool-calling model; it cannot validate Sonnet 5.5 behaviour.
- Top up $10 once if you want 1,000 RPD on free models; it also pays for a few hundred Haiku 5.5 test calls ($0.10/$0.50 per M).
- Free models providers may log/train on prompts (provider-specific; not verified). Treat as test-data-only.

### Gaps
- Current list of `:free` models with `input_modalities` and `supported_parameters` (tools, structured_outputs): API endpoint fetch returned no `:free` entries and no modalities fields; models page filter incomplete. Run `curl https://openrouter.ai/api/v1/models` locally and filter `pricing.prompt == "0"` with `architecture.input_modalities` to get the live list.
- Any free model that accepts video input: unconfirmed.
- Per-model privacy/training policy on free routes: not checked.

## Q3. Anthropic credits and Claude Code free options

### Takeaway
No standing free API credits for individual developers found. Claude for Startups is VC-partner/cohort based and applications are currently closed. A solo India dev should plan on small paid Haiku 5.5 / Sonnet 5.5 top-ups (via OpenRouter) rather than free credits.

### Cited Findings
- Claude for Startups page: for "early-stage founders building on Claude"; members get offers worth "up to $45,000" from partner companies (discounts/credits redeemed in Console, not necessarily Anthropic API credits); VC-backed founders via partner network "may be eligible to receive up to $100K in additional API credits, claimed through your VC"; applications currently closed (subscribe to newsletter); page silent on solo founders without VC and on individual-developer free credits — [Claude for Startups](https://claude.com/programs/startups)
- News reports of 2026-10-06 expansion (SF Tech Week): $1,000 Claude API credits, free year of Claude Team for 5 seats, up to $45,000 third-party discounts; $1,000 applies only to first-party API via Console; one Korean article mentions 6-month expiry — [Android Headlines](https://androidheadlines.com/2026/10/anthropic-expands-claude-startups-program.html), [LetsDataScience](https://letsdatascience.com/news/anthropic-expands-claude-startups-program-with-credits-and-m-b5cab676). Secondary sources; the official page did not show these.
- Aggregator credit figures ($5K to $100K, 12-month validity, VC requirement) conflict and are unverified — [guptadeepak](https://guptadeepak.com/anthropic-claude-for-startups-the-complete-guide-to-credits-tiers-and-eligibility-2026/)
- Claude Code free options: not researched on a primary page (see Gaps).

### Inferences
- Pre-revenue solo dev in India: application route is closed and probably VC-gated; don't budget on it. Check the newsletter.
- Cheapest Anthropic-quality test path: Haiku 5.5 ($0.10/$0.50 per M per earlier report) — tens of thousands of test calls for a few dollars.

### Gaps
- Claude Code free tier / free Claude plan access to Claude Code in 2026: not researched.
- Whether a $1,000 credit exists for non-VC startups and its application path/expiry: only secondary sources.
- Anthropic educational / research credit programs: not checked.

## Q4. Other free LLM/VLM providers

### Takeaway
Best free options for this project: Google AI Studio (video-capable), Alibaba Model Studio Singapore (1M tokens/model, 90 days, but Qwen-VL/Qwen3-VL excluded for new users since 2026-10-29), Z.ai GLM Flash free models (incl. GLM-4.6V-Flash vision, UNVERIFIED), NVIDIA build.nvidia.com (~40 RPM, dev only), Groq (text only, 1,000 RPD). HF gives free users nothing. Most other figures below come from aggregators and are flagged.

### Cited Findings (catalog)
| Provider | Free? | Limits | Models / capability | Training / commercial | Source |
|---|---|---|---|---|---|
| Hugging Face Inference Providers | No credits for free users (buy credits); PRO $2.00/month | PRO and Team/Ent ($2/seat) only; HF passes through provider price, no markup; credits not applied for custom provider keys | 200+ models via router.huggingface.co/v1 (OpenAI-compatible) | not covered | [HF pricing](https://huggingface.co/docs/inference-providers/pricing) |
| Groq | Yes (no card per aggregator) | Doc table is "Developer plan base limits": gpt-oss-120b/20b 30 RPM, 1K RPD, 8K TPM, 200K TPD; qwen/qwen3.8-27b same; whisper 20 RPM/2K RPD; free-plan numbers not separately shown | No vision models and no Llama 4 in table; text/tool models only | OpenRouter blog says no training (UNVERIFIED); no region info on page | [Groq limits](https://console.groq.com/docs/rate-limits), [OR blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) |
| Alibaba Model Studio (Qwen) | Yes, new users, Singapore region only | ~1,000,000 tokens per model ("typically"), input+output combined pool, 90 days from latest of activation/model release/approval; no second grant for new account; real-time inference only (not batch) | Since 2026-10-29 new users no longer get quota for qwen-vl-max/plus/ocr or qwen3-vl models; qwen3.8-max eligibility unconfirmed; non-VL Qwen text models may still have quota | data-use terms not checked | [Alibaba free quota](https://www.alibabacloud.com/help/en/model-studio/new-free-quota.md) |
| NVIDIA build.nvidia.com / NIM | Yes via NVIDIA Developer Program | ~40 RPM (community-reported, not an SLA); ~1,000 credits (reported, expandable to 5,000; UNVERIFIED); dev/test use, not production per forum posters; base URL integrate.api.nvidia.com/v1 | Nemotron, Llama and other hosted models; VLMs available (Nemotron Nano VL is on the list per OpenRouter tracker) | Not for production (forum claim) | [NVIDIA forum](https://forums.developer.nvidia.com/t/is-nim-free/369368), [fremodel](https://fremodel.pages.dev/providers/nvidia-nim) (UNVERIFIED) |
| Mistral La Plateforme | Yes, "Experiment"/Free mode | Limits only shown in Admin Console; ~1B tokens/month is third-party figure (UNVERIFIED) | Codestral, Small, Large listed by OR blog | OR blog: training "Yes (Experiment tier)" — UNVERIFIED | [BenchLM](https://benchlm.ai/md/free-tier/mistral.md), [OR blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) |
| Cerebras | Yes | ~30 RPM, ~1M tokens/day, ~8K context cap on free (aggregators, model list changed) | Llama 3.3 70B and others | no training (OR blog, UNVERIFIED) | [OR blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) |
| Cloudflare Workers AI | Yes | ~10,000 Neurons/day (aggregators); context 2K-8K | 20+ models | no training (UNVERIFIED) | [OR blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) |
| GitHub Models | CONFLICT | Aggregators: 10-15 RPM, 50-1,000 RPD; one Czech article says GitHub ended the service 2026-07-30 | — | — | [OR blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/); contradicted by [365tipu](https://365tipu.cz/?p=63889) (single source) |
| Z.ai (Zhipu GLM) | Yes: GLM-4.7-Flash, GLM-4.5-Flash (text), GLM-4.6V-Flash (vision) listed free | 1 concurrent request for 4.5-Flash and possible Chinese phone number needed to register (both UNVERIFIED) | OpenAI-compatible base https://api.z.ai/api/paas/v4 | not checked | [LiteLLM Z.ai](https://docs.litellm.ai/docs/providers/zai), [Puter](https://developer.puter.com/ai/z-ai/glm-4.5-flash/) |
| Moonshot (Kimi) | Conflict: no standing API free tier (July 2026 guide) vs. ¥15 signup credit / $5 top-up coupon (June 2026 tracker) | — | Kimi K2.6 `:free`-style routes exist on third-party hosts | not checked | [yangmao tracker](https://yangmao-ai.pages.dev/en/providers/kimi/free-api/), [DEV](https://dev.to/preecha/how-to-use-kimi-k26-for-free-23h1) (aggregators) |
| OpenAI | Data-sharing program: free daily tokens in exchange for training use; amounts conflict (250K/day vs up to 11M/day); automatic signup credit no longer reliable | opt-in, org-specific; startup credits and researcher ($1,000) programs exist | GPT models | Training on your data by design | [Codex OSS fund](https://codex.danielvaughan.com/2026/03/31/codex-open-source-fund), [OpenAI forum](https://community.openai.com/t/api-data-sharing-free-credits-not-working/1250558) (UNVERIFIED amounts) |
| Together AI, SambaNova, DeepSeek, xAI | Not retrieved | — | — | — | OR blog lists trial credits for SambaNova, DeepSeek, Fireworks, Baseten, Nebius, AI21 but no amounts captured |

### Inferences
- Only Google (Gemini 3.x Flash / Flash-Lite) combines free + native video input + JSON schema; every other free source here is text/image at best.
- Qwen-VL via Alibaba free quota is effectively closed to new accounts; for Qwen3-VL testing go local or via paid HF/OpenRouter/NVIDIA.
- Free tiers that train on data (Gemini, Mistral Experiment, OpenAI data sharing) should receive only synthetic or licensed test clips.
- For "commercial use": none of the primary pages read banned commercial use on the free tier; NVIDIA reportedly limits free use to development/test.

### Gaps
- DeepSeek, xAI, Together AI, SambaNova credit amounts/expiry: not retrieved.
- Primary pages for Cerebras, Cloudflare, Mistral, GitHub Models, NVIDIA terms: not fetched; GitHub Models' alleged 2026-07-30 shutdown unresolved.
- India registration restrictions (phone verification, region blocks) for Z.ai, Moonshot, Alibaba, NVIDIA: not found.
- Per-provider training policies on free tiers (except Google): unverified.

## Q5. Local / self-hosted route

### Takeaway
Qwen3-VL-8B runs on a consumer GPU: roughly 6-8 GB VRAM at Q4_K_M for short context; video with many frames needs more KV cache. Third-party estimates vary (4.8 GB INT4 up to a 12 GB outlier).

### Cited Findings
- Qwen3-VL-8B VRAM at 8K context incl. overhead: Q4_K_M ~6 GB, Q5_K_M ~7 GB, Q8_0 ~10 GB, FP16 ~16 GB — [bestllmfor](https://bestllmfor.com/catalog/qwen3-vl-8b/)
- Spheron (vLLM-style): ~4.8 GB INT4, ~9.6 GB INT8, ~19 GB FP16 — [Spheron](https://www.spheron.network/tools/gpu-recommender/Qwen/Qwen3-VL-8B-Instruct/)
- Codersera: Q4_K_M GGUF ~6.1 GB; 8 GB minimum, 12-16 GB comfortable — [Codersera](https://codersera.com/blog/qwen3-vl-4b-vs-qwen3-vl-8b-benchmarks-vram-guide/)
- Hostinger general Ollama guide: 7-8B models at Q4_K_M, 8K ctx need ~6-7 GB — [Hostinger](https://www.hostinger.com/tutorials/?p=156543)
- Earlier report: Qwen3-VL-8B scored 34.4 s absolute boundary error on TransVLM; Qwen3-VL is Apache-2.0; 24 GB GPU hosts the 8B (inference).

### Inferences
- 8 GB GPU: Qwen3-VL-8B Q4 with short clips (few frames); 12-16 GB comfortable; use Qwen3-VL-4B on 6 GB. Ollama and LM Studio expose OpenAI-compatible endpoints, so the same client code works.
- Local VLM is a plumbing test and fallback, not a quality stand-in for Gemini on timing/semantics.

### Gaps
- Official Ollama library entry/size for qwen3-vl and whether Ollama/LM Studio accepts raw video (vs. frame lists): not verified.
- User's actual GPU is unknown.
- Claude Code / local-model routing not researched.

## Q6. Recommended free dev setup mirroring the paid stack

### Takeaway
Use OpenAI-compatible/provider-native clients behind two config switches (base URL + model ID) and keep the same JSON schemas; free tiers for each layer, paid keys only in prod env.

### Cited Findings
(Constructed from findings above; no separate sources.)

### Inferences
- Video description layer: Google Gemini API free key (separate non-billing project), model `gemini-3.8-flash` or `3.5-flash-lite`; same SDK as prod, prod flips to a billed project (paid = no training). Test with your own/licensed clips only.
- Embeddings: Gemini Embedding 2 free key; same code in prod.
- Planner/chat: OpenRouter client; dev uses a free tool-calling model or `openrouter/free` (20 RPM, 50/day, or 1,000/day after $10 top-up) plus pennies of Haiku 5.5 to exercise real Anthropic json_schema/tool behaviour; prod changes only model IDs to Sonnet 5.5 / Haiku 5.5. Use env vars `LLM_BASE_URL`, `LLM_MODEL`, `VLM_MODEL`.
- Offline fallback: Ollama / LM Studio serving Qwen3-VL-8B (Q4) on OpenAI-compatible localhost endpoint for CI and no-network runs.
- Budget LLM trials: Z.ai GLM Flash free models (verify), Groq gpt-oss/Qwen text for fast schema tests, NVIDIA build for ~40 RPM Nemotron/Qwen-class tests (dev only).
- Cache all model responses by content hash during dev so the 50 RPD / free RPD caps are not hit while iterating; record fixtures for unit tests.
- Add schema-validate-and-retry and 429 backoff from day one; free-tier limits will trigger them.
- Before prod: flip Gemini to a billed project, and don't let any free-tier key touch real user footage.

### Gaps
- No measurement that free-tier models behave identically to prod ones for JSON-schema strictness; run the same eval set on both before trusting dev results.
- Total $ for a dev month of Haiku 5.5 test calls was not computed (see earlier report for prices).
