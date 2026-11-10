# Competitor landscape: AI-assisted short-form video (Reels/Shorts/TikTok) editing, as of 2026-11-02

Method note: about 40 web searches/fetches. Search-engine summaries were thin and many pricing pages are third-party aggregators that contradict each other, so every price below is "reported", not verified on the vendor's own checkout. Anything not directly fetched from a primary page is labelled. Gaps are listed at the end of each section. Items older than 12 months (before 2025-11) are flagged "[OLD]".

---

## 1. Per-competitor: what it does and how close it is to the idea (reference -> ShotSpec blueprint -> match user library -> ask for missing shots -> auto-edit -> chat edits)

### Takeaway
No single product found does the full loop. The closest overall is **invideo's agentic editor** (reference-video matching + footage search + chat/agent edits on an editable timeline), but it has no persistent cross-project library, no explicit "missing shot" request flow, and no ShotSpec-style pre-production output. The closest to the *blueprint + shootable shot list* half is **ViralClip** (a tiny, newly launched startup). CapCut, Instagram Edits and Google Photos cover template-slot filling and highlight reels, but not reference-to-blueprint extraction.

### Cited Findings

**Closest direct competitors (new "agentic" and "clone a reel" tools)**
- **invideo (agentic video editor).** Feature "Match an edit using reference videos": the agent studies a reference (upload or YouTube link; private/closed Drive links not supported) and recreates pacing, transitions, effects, text/title animation and sound design on your footage. You can point at specific timestamps or apply to the whole edit. Result is "creative direction", similar not identical, and fully editable on a timeline; revisions can be requested after generation. — [invideo reference page](https://invideo.io/make/style-and-motion-reference/)
- invideo's agent page: agents "watched the footage, not just the transcript"; a "Search" agent finds "people, actions, objects, camera angles" in your footage; work is assigned "in plain language"; everything lands on an editable timeline with undo/redo; manual editor is free, agents cost credits ("credits only when agents take a job"). — [invideo agentic editor page](https://invideo.io/make/agentic-video-editor/)
- invideo FAQ caveat: matching works best when your footage can support the reference style; a multi-location, complex-camera reference may not translate to one static recording. That is exactly the "missing shot" problem the idea solves. — [invideo FAQ](https://invideo.io/faq/can-an-ai-editing-agent-match-the-pacing-and-style-of-a-reference-video/) (found via search snippet; not separately fetched)
- invideo launch date: neither page gives one. A third-party aggregator mentions an "invideo v4 agent" handling up to 30 minutes per prompt but no dated announcement was found. — [aiproductivity.ai](https://aiproductivity.ai/pricing/invideo/) (low reliability)
- invideo pricing (third-party, conflicting): Plus about $17/mo (others $25-28); Max $50-85; Generative $170; Elite $900; free tier disputed. Agent usage is credit-metered. — [CostBench](https://costbench.com/software/ai-video-editing-saas/invideo-ai-edit/), [ToolRadar](https://toolradar.com/tools/invideo-ai/pricing), [Creatify](https://creatify.ai/blog/invideo-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay)
- **ViralClip (viralclip.app).** "Viral Video Cloner": paste a TikTok/Reels/Shorts link; it breaks down hook, pacing, shot list and captions, then rebuilds that structure around *your product*; choose how far it departs from the original, compare nine options, edit storyboard shot by shot before render. Also lip sync, motion transfer, TTS, product photos. Freemium, credit cost shown before render. Listing says launched 2026-08-19. Aimed at e-commerce/UGC ads and appears to *generate* footage with AI rather than match the user's real clips. — [SimilarLabs listing](https://similarlabs.com/zh/p/viralclip-viral-video-cloner-blueprint). Note: viralclip.app returned HTTP 410 Gone when I fetched it, so the site may be down or moved; the listing is the only source.
- **Virash** (Product Hunt, ~March 2026, maker blurb only): "AI-native viral reels agent", clone viral videos from a URL, fix weak hooks, remix high-performing keyframes; no timeline. No pricing/reviews found. — [Product Hunt maker profile](https://www.producthunt.com/@mangata), via search snippet
- **CloneViral** (analyses trending TikTok/YouTube videos, replicates style/pacing with your own content; reported $29/mo Creator, $89/mo Pro as of Oct 2025 [OLD-ish]) — [G2 listing](https://www.g2.com/sellers/cloneviral), pricing via [search snippet](https://www.trendingaitools.com/?p=35487)
- **Vireel** (Product Hunt, 2025-08-08, 552 upvotes, #2 Product of the Day [OLD, >12 months]): "publish-ready reels using dozens of viral formulas"; generative, formula-library based, not user-footage matching. — [hunted.space](https://hunted.space/product/cracked-ai/launches/vireel)
- **Higgsfield**: library of "viral presets" encoding narrative structure, pacing and camera logic; one-tap: pick preset + upload photo. Generative (photo -> stylised video), not an editor of real footage. OpenAI write-up dated Jan 2026. — [OpenAI on Higgsfield](https://openai.com/index/higgsfield), [Miracamp preset list](https://www.miracamp.com/learn/video-editing/new-higgsfield-viral-presets)
- **Reeroll** and **Kiki**: template-based chat editors on Product Hunt (pick a trending template, add assets, edit by typing). Kiki: free, 0 upvotes/1 comment, so negligible traction. Reeroll page had no data. — [Kiki](https://www.hunted.space/product/kiki-video-ai), [search listing](https://www.hunted.space/product/reeroll)
- **Mosaic (YC W25)**: browser node-canvas of editing "tiles" (Rough Cut, Montage, etc.), agents with visual+audio understanding, exports XML to Resolve/Premiere/FCP. Launch HN (~Nov 2025, 148 points). Founders said **style transfer from a reference video is planned** and that indexing/retrieval over ~1 TB of footage is *not yet supported*. Product Hunt launch 2026-03-02 (202 upvotes). Funding unverified (directory says ~$500K pre-seed). — [Launch HN](https://hn.svelte.dev/item/45980760), [Product Hunt/hunted](https://hunted.space/dashboard/mosaic-so), [funding snippet](https://www.sixtyfour.ai/yc-company-data/stillwind)
- **Tellers.ai**, **Tella**, **VEED AI Agent**: described as agentic/chat editing; VEED agent handles plain-language edit commands. Details not verified (VEED help URL 404'd). — [Tellers](https://feedbagel.com/post/tellersai-ai-agent-platform-for-automated-video-editing), [Tella](https://www.tella.com/edit-with-ai/agentic-video-editing.md)

**Template/consumer editors**
- **CapCut**: templates "automatically sync clips, music, and transitions" (CapCut article dated 2026-03-30); beat-synced templates; remix culture (creators swap own footage into viral templates). The official page names no "smart match" or media-search feature. Auto captions 130+ languages, TTS, avatars, AutoCut-style long-to-short (CapCut marketing pages; third-party claims for the 2026 "AI suite"). — [CapCut trends](https://www.capcut.com/help/latest-capcut-editing-trends), [BibiGPT summary (third-party, weak)](https://bibigpt.co/en/features/capcut-2026-ai-suite-explained). Template listings show "Remix" with clip count and aspect ratio. — [example template](https://www.capcut.com/template-detail/7641859347563171085)
- CapCut pricing: Pro reported $19.99/mo or $179.99/yr (US web), lower regional/web prices reported ($7.99-9.99); free tier with limits; web caps free users at 5 AI exports/day per one review. — [CapCut help (plans)](https://www.capcut.com/help/monthly-and-yearly-plans), [BigVU](https://www.bigvu.tv/blog/capcut-pricing-2026-free-vs-pro-included-alternatives), [Marc Andrews review](https://marcandrews.com/?p=3063)
- **Instagram Edits** (standalone app, launched ~April 2025 [OLD]): Jan 2026 update added links to IG accounts, 25 effects, storyboard multiple takes, and **10 personalised weekly clip ideas** based on your past Reels; no AI mentioned in that release. Later 2026 items from a SocialBee changelog (unverified): 15-minute export beta, colour tools, AI-assisted font style, lyric generation, video-effects search, templates, loudness matching. Free; Mosseri has said paid features may come to cover AI compute. — [Social Media Today, 2026-01-14](https://www.socialmediatoday.com/news/edits-gets-ig-links-weekly-ideas-and-new-video-effects-features/809644/), [SocialBee changelog](https://socialbee.com/blog/instagram-updates/), [Mosseri on paid features (2025)](https://www.lindseygamble.com/blog/instagrams-edits-app-will-likely-have-some-paid-features)
- **InShot**: mobile editor; Pro reported $3.99/mo, $14.99/yr, $34.99 lifetime (checked 2026-04-10 by a review site); sources conflict on whether it has real AI features. **VN**: free watermark-free editor, AI text-to-speech per a Splice roundup; nothing found on AI editing. — [Creator Stack](https://www.creatorstackclub.com/software/inshot), [Splice blog (vendor)](https://spliceapp.com/blog/which-apps-use-ai-features-in-2026-video-editing)
- **Splice**: mobile-first editor, free download with in-app purchases (vendor blog, May 2026). No AI-editing detail found. — [Splice blog](https://spliceapp.com/blog/best-iphone-apps-for-quick-video-editing/)
- **Wondershare Filmora** (v15 as of Apr 2026 per one source): AI captions, scene detection, text-based editing, AI Copilot, credit-based cloud AI; pricing reported ~$49.99/yr, ~$79.99 perpetual (conflicting). — [TechRadar review](https://techradar.com/computing/creative-software/wondershare-filmora-ai-video-editor-2026-review), [GeekChamp](https://geekchamp.com/wondershare-filmora-pricing-reviews-2026/)
- **Captions (Mirage)**: "AI Edit" accepts text commands (add B-roll, change mood), Text-to-Video, AI Twin/Actors, dubbing, denoise, eye contact; **in-app camera teleprompter** exists. AI Edit expanded to 16:9 and 10-minute videos in Feb 2026; new business styles May 2026. Mirage raised $75M in March 2026 (aggregator claim). Pricing: Free; ~$9.99 entry; Max $24.99 (or $29.99 per a Sept 2026 IAP listing); Frontier $69.99-279.99. — [eesel review (edited 2026-09-27)](https://www.eesel.ai/blog/captions-ai), [Hooked](https://www.hooked.so/compare/captions-ai-pricing), [Captions teleprompter help](https://captions.ai/help/guides/creators/camera-teleprompter)
- **Kapwing**: "Kai" AI chat agent on a timeline editor; May 2026 notes: Kai edits layers/filters/audio/background, can use >10 uploaded files as context; March 2026 "Editable Agent Plan". Release notes list **no** reference-video, template or media-search feature. — [Kapwing May 2026 notes](https://www.kapwing.com/help/kapwing-release-notes-may-2026/), [March 2026 notes](https://www.kapwing.com/help/release-notes-march-2026/)
- **Canva**: Magic Studio, Magic Switch (16:9 -> 9:16 resize), AI video generation capped around 4 s clips; Pro reported $15/mo ($120/yr); "Canva AI 2.0" chat assistant claim unverified. Strength is brand templates. — [eesel Canva AI pricing](https://eesel.ai/blog/canva-ai-pricing), [Morphed](https://morphed.app/blog/canva-ai-video-generator-pricing)
- **Adobe Premiere (mobile)**: free iPhone app launched 2025-09-30 [OLD], no watermark, 4K HDR export, generative features cost Firefly credits (Standard $9.99/mo 2,000 credits; Pro $19.99/mo 4,000; Premium $199.99/mo 50,000); Creative Cloud Pro $69.99/mo after promo. Desktop Generative Extend (Firefly Video Model) introduced Oct 2024 [OLD]. — [AppleInsider](https://appleinsider.com/articles/25/09/30/adobe-premiere-launches-on-iphone-free-to-download-now), [Adobe plans](https://www.adobe.com/creativecloud/plans.html?single_app=premiere), [BusinessWire 2024](https://www.businesswire.com/news/home/20241014405532/en/Adobe-Revolutionizes-Professional-Video-Editing-with-Premiere-Pro-Innovations-Powered-by-New-Firefly-Video-Model/). Adobe Express not researched.
- **Google Vids**: Workspace video tool with Gemini/Veo text-to-video; Veo 3.1 released Oct 2025 [OLD]; consumer Google AI Pro $19.99/mo and Ultra $249.99/mo (aggregators, conflicting). Not oriented to reels or reference matching. — [Veo pricing aggregator](https://deeka.ai/blog/veo-ai-in-2026-google-s-video-generator-explained-features-pricing-how-to-use-it), [Capterra Vids](https://capterra.com/p/10030512/Google-Vids/)
- **Google Photos**: Create tab (2025) with photo-to-video, Remix, collages, **highlight videos** where typed "place/person/date" makes Gemini pick shots with transitions and rhythm; **Video Remix** announced 2026-07-08 (Gemini Omni; relighting, background swap, art styles) for AI Plus/Pro/Ultra subscribers in the US and 13 other countries. Restyles clips; does not do reference-to-blueprint. — [TechCrunch 2026-07-08](https://techcrunch.com/2026/07/08/google-photos-adds-a-new-ai-video-remix-tool/), [Google blog (2025)](https://blog.google/products/photos/photo-to-video-remix-create-tab)
- **DaVinci Resolve 20** (May 2025 [OLD]): AI IntelliScript (timeline from script), AI Multicam SmartSwitch (speaker-based angles), AI-powered rough cut/audio generation. One commenter on HN expects Resolve to add Mosaic-like features natively. — [Larry Jordan](https://larryjordan.com/articles/ai-powered-features-in-davinci-resolve-20/), [Newsshooter](https://www.newsshooter.com/2025/05/27/davinci-resolve-20-final-release/). Resolve 21 mentioned in passing; not checked.
- **Opus Clip / Agent Opus**: ClipAnything (prompt-steerable moment finding), virality score; Agent Opus (Aug 2025 [OLD]) generates short videos from a topic. Pro reported ~$14.50-15/mo (300 credits); Agent Opus Free/$29/$129 per an index site. Long-to-short clipper, not reference matching. — [Quso review](https://quso.ai/blog/opus-clip-review) (competitor-written), [AI Agent Index](https://theaiagentindex.com/agents/opus-clip)
- **Descript (Underlord)**: transcript-based editing with AI agent; plans reported Hobbyist $16-24, Creator $24-35, Business $50-65; AI credits metered separately; public API in beta with MCP access in 2026 (aggregators). — [Sonix review](https://sonix.ai/resources/?p=3512), [Castmagic](https://www.castmagic.io/de/blog/descript-pricing)
- **Runway**: Aleph 2.0 video-to-video editing model plus Edit Studio, reportedly 2026 (release date disputed: May 21, June or July 29, 2026); API about $0.28/s; paid plan required. Generative restyle of existing footage; no library or blueprint. — [OpenRouter listing](https://openrouter.ai/runway/aleph-2), [Atlas Cloud](https://www.atlascloud.ai/zh-TW/blog/tips/runway-aleph)
- **Pika** (reported Basic free, Standard $10, Pro $35, Fancy $95), **HeyGen** (Creator $24-29/mo), **Synthesia** ($18-89/mo reported), **Hedra** (credit-based): generative/avatar tools, no editing of user libraries or reference-edit matching found. — [CostBench Pika vs HeyGen](https://costbench.com/compare/heygen-vs-pika/), [Creatify HeyGen vs Synthesia](https://creatify.ai/fr/blog/heygen-vs-synthesia-(2026)-pricing-avatars-and-which-one-fits-your-team)
- **Pictory** ($19/$39/$99 reported), **Lumen5** (free, $29, $79, $199 reported): script/blog-to-video with stock footage. **Vizard** (~$15 Pro reported), **Submagic**, **Gling** (silence/mistake cutting for talking video), **Quso.ai** (clips, scheduler, trend analysis): repurposing/captioning tools. — [Submagic vs Pictory (vendor)](https://www.submagic.co/alternatives/pictory-ai), [Toolradar Pictory vs Lumen5](https://toolradar.com/compare/pictory-vs-lumen5), [G2 Lumen5 vs Pictory](https://www.g2.com/compare/lumen5-vs-pictory-ai)
- **Apple Clips** discontinued (TechCrunch, Oct 2025). — [TechCrunch](https://techcrunch.com/2025/10/11/apple-says-goodbye-to-the-clips-app)
- **Magisto/Vimeo**: Vimeo-Magisto integration discontinued Dec 31 2024; Bending Spoons agreed to buy Vimeo for $1.38B (Sept 2025); layoffs Jan 2026, including most Israeli staff, which is where Magisto's engineering sat. No report that the app itself shut down. — [Magisto help](https://help.magisto.com/hc/en-us/articles/360031272952), [TechCrunch 2026-01-22](https://techcrunch.com/2026/01/22/vimeo-starts-layoffs-after-acquisition-by-bending-spoons), [Bloomberg](https://www.bloomberg.com/news/articles/2025-09-10/bending-spoons-to-buy-vimeo-in-1-38-billion-all-cash-deal)

### Inferences
- Treat invideo as the main threat to the "edit like this reference" claim. It already ships reference matching, in-footage search and agent chat edits; distinct from the idea mainly in lacking persistence, missing-shot planning and a mobile-first reels UX (inference from page text, not from testing the product).
- CapCut, Instagram Edits and Canva are the distribution incumbents; their templates solve "fill slots" but the template is authored by a human creator, not extracted from an arbitrary reference.
- Generative tools (Runway, Higgsfield, Pika, Veo, Hedra, HeyGen) substitute for *missing shots* by synthesising them, which is an alternative answer to "ask the user to record it".

### Gaps
- No hands-on testing of any product; all capability statements come from vendor pages or reviews.
- Not researched in depth: Quik/GoPro, Adobe Express, Vizard/Submagic/Gling/Quso/Pictory/Lumen5 current AI features, Hedra, Pika features, Apple Photos Memories, Synthesia features, VN features. Splice, InShot AI features are unclear.
- CapCut official pricing page and CapCut's latest (2026) feature announcements were not accessed directly.

---

## 2. Who already does: reference-to-template extraction, auto-match to slots, semantic library search, shot list / guided recording, style cloning

### Takeaway
Each piece exists somewhere, but in separate products: style cloning from a reference (invideo, ViralClip, CloneViral, Virash), natural-language footage search (invideo's Search agent, plus small tools like Memories.ai, Clipto, Framea, Video Atlas), shot-list planning (SimplistUGC), teleprompter recording (Captions and many apps). No product found combines all of them.

### Cited Findings
- **Reference-video-to-edit/style cloning**: invideo ("Match an edit using reference videos", undated) — [page](https://invideo.io/make/style-and-motion-reference/); ViralClip (listing date 2026-08-19; hook/pacing/shot list/captions breakdown) — [listing](https://similarlabs.com/zh/p/viralclip-viral-video-cloner-blueprint); CloneViral (reported Oct 2025) — [G2](https://www.g2.com/sellers/cloneviral); Virash (~March 2026) — [PH profile](https://www.producthunt.com/@mangata); Mosaic says it is planned — [Launch HN](https://hn.svelte.dev/item/45980760). Higgsfield uses preset formats rather than extracting from a user-supplied reference — [OpenAI](https://openai.com/index/higgsfield).
- **Template slot filling with your clips**: CapCut templates (clips, music and transitions synced; March 2026 article, feature itself long-standing) — [CapCut](https://www.capcut.com/help/latest-capcut-editing-trends); Instagram Edits has templates (listed in mid-2026 changelog, unverified) — [SocialBee](https://socialbee.com/blog/instagram-updates/); Kiki/Reeroll chat-on-template (tiny) — [Kiki](https://www.hunted.space/product/kiki-video-ai). I did not confirm that any of these *auto-assign* a user's library clips to template slots by content similarity; CapCut's page does not mention it.
- **Searchable media library (semantic/NL)**: invideo Search agent over *project* footage ("people, actions, objects, camera angles") — [page](https://invideo.io/make/agentic-video-editor/). Google Photos highlight videos choose shots by typed place/person/date — [Google blog](https://blog.google/products/photos/photo-to-video-remix-create-tab). Standalone search apps launched 2026: Framea (iOS, 2026-04-21), Clipto (2026-05-31, local), Video Atlas (Apple devices, local), Cerul (open source), Memories.ai (vendor blog Feb 2026) — [search roundup](https://memories.ai/blogs/The-End-of-Scrubbing-How-AI-Video-Analyzers-Find-Your-Highlights-in-Seconds), [Framea PH](https://www.producthunt.com/products/framea/launches/framea-2), [Clipto PH](https://www.producthunt.com/products/clipto-ai/launches/clipto), [Video Atlas](https://www.vincentchu.com/videoatlas.html). Mosaic's founders said ~1 TB indexed retrieval is not supported yet (Launch HN, ~Nov 2025). Persistence across projects in invideo was not documented.
- **Shot list / guided recording**: SimplistUGC (iOS): brief + duration (15/30/60 s) -> shot list with script prompts, each shot a checklist item while filming; $2.99/mo or $24.99/yr — [App Store](https://apps.apple.com/us/app/simplistugc/id6759472145). Teleprompter apps (Captions camera teleprompter, Prompty, GlideGear, etc.) guide *speech*, not shots — [Captions help](https://captions.ai/help/guides/creators/camera-teleprompter). ViralClip produces a shot list from a reference but renders with AI. No product found that diffs a reference blueprint against the user's library and requests only missing shots.
- **Instagram Edits Storyboard** (multiple takes per segment, Jan 2026) is manual planning, not AI shot-list generation — [Social Media Today](https://www.socialmediatoday.com/news/edits-gets-ig-links-weekly-ideas-and-new-video-effects-features/809644/).
- **Chat-based edits**: Kapwing Kai (May 2026), Captions AI Edit, VEED AI Agent, invideo agents, Canva AI (claimed), Descript Underlord — see section 1 sources.

### Inferences
- The unbundled components are individually cheap to replicate; invideo is the only one seen combining reference matching + footage search + agent edits, and it can plausibly add persistence or recording prompts.
- The "persistent visual memory across projects" claim appears under-served in editing products: library search exists mainly as separate local/indie tools or in Google Photos, not wired to reference-driven editing. This is an absence-of-evidence inference.

### Gaps
- Launch dates for invideo's reference-matching and Search agent not found.
- Whether CapCut/Edits templates auto-pick clips by content: not found.
- Whether invideo keeps an indexed library between projects: not found.
- Whether Captions or Google Photos have shot-list features beyond teleprompter: not found.

---

## 3. Startups / open source doing "copy this reel with my footage" or agentic (LLM-driven) editing

### Takeaway
There is a crowded, mostly tiny field. Open-source agentic editors are dominated by "LLM reads transcript, writes an edit decision list, FFmpeg renders" projects aimed at talking-head footage; none found does visual reference matching or library retrieval for reels.

### Cited Findings
- **browser-use/video-use**: MIT, 30.3k stars, 3.5k forks, 23 commits on main when fetched. Claude Code-driven; uses ElevenLabs Scribe transcripts (word-level) plus an on-demand filmstrip/waveform composite; "cuts come from speech boundaries and silence gaps"; pipeline Transcribe -> Pack -> LLM -> EDL -> Render -> Self-Eval; requires user strategy approval before cutting. Last-commit date not shown. — [GitHub](https://github.com/browser-use/video-use)
- **cut-as-code** (WhiteTowerAI, MIT, ~7 stars), **CutAgent** (DaKev, Python/FFmpeg EDL, PyPI 0.1.1), **premiere-agent** (Kemerd; LLM gets text descriptions, "never watches the video", exports Premiere XML), **OpenVids** (free open-source desktop editor with agent modes, v0.5.4), **Crayotter** (arXiv 2606.07636, multi-agent long-form editing). — [cut-as-code](https://github.com/WhiteTowerAI/cut-as-code), [CutAgent](https://pypi.org/project/cutagent/0.1.1/), [premiere-agent](https://github.com/Kemerd/premiere-agent), [OpenVids](https://toolradar.com/tools/openvids), [Crayotter](https://arxiv.org/pdf/2606.07636). Stats from search snippets/directories, unverified.
- **Mosaic (YC W25)** — see section 1. Only YC video-editing agent company found; planned reference style transfer.
- **Tellers.ai**, **Tella**, **Kapwing Kai**, **VEED Agent**, **invideo agents**, **Descript Underlord (with MCP API in 2026)** — commercial agentic editors. — [Tellers](https://feedbagel.com/post/tellersai-ai-agent-platform-for-automated-video-editing), [Tella](https://www.tella.com/edit-with-ai/agentic-video-editing.md)
- **"Clone a viral reel"** products: ViralClip (2026-08-19), Virash (Mar 2026), CloneViral (Oct 2025), ClipTrend.ai (turns viral TikTok/YouTube AI trends into one-click templates; weak traction), Vireel (Aug 2025), insMind video clone. — [ClipTrend](https://www.hunted.space/product/cliptrend-ai), [insMind](https://www.insmind.com/ai-video-generator/video-clone), plus links above. Most appear to generate AI footage or use the user's *product images*, not match a library of real user clips (inference from descriptions).
- An Intempt "video remix" recipe builds a branded reel from four reference clips (not a product launch). — [Intempt](https://intempt.com/recipes/video-remix)

### Inferences
- Builders can assemble a prototype quickly from these open components (VLM shot description -> EDL -> FFmpeg/Remotion), which lowers the barrier for competitors too.
- Traction is small for nearly all "clone viral" Product Hunt launches (Kiki 0 upvotes, ClipTrend 0 upvotes/#152), apart from Vireel (552) and Mosaic (202); this suggests demand exists but no breakout winner.

### Gaps
- Did not search X/Twitter, Hacker News beyond Mosaic, or Crunchbase/YC directory systematically; no complete YC batch scan. Other possible entrants (e.g., Twelve Labs consumer tools) not found.
- GitHub star counts for most repos not verified against live pages.

---

## 4. Pricing and business model (summary)

### Takeaway
The market splits into free-plus-subscription consumer editors (CapCut, InShot, Edits, Splice, VN), credit-metered AI SaaS (invideo, Captions, Descript, Runway, Higgsfield, Adobe Firefly credits), and bundle-with-subscription (Google Photos via Google AI plans, Canva Pro). Agentic/generative features are consistently gated or credit-metered because of compute cost.

### Cited Findings (reported, third-party, unverified on vendor pages)
- CapCut Pro: $19.99/mo or $179.99/yr (US web); lower web/regional prices reported — [BigVU](https://www.bigvu.tv/blog/capcut-pricing-2026-free-vs-pro-included-alternatives), [CapCut help](https://www.capcut.com/help/monthly-and-yearly-plans)
- Instagram Edits: free; paid AI features floated by Mosseri, none confirmed — [Lindsey Gamble](https://www.lindseygamble.com/blog/instagrams-edits-app-will-likely-have-some-paid-features)
- InShot Pro: $3.99/mo, $14.99/yr, $34.99 lifetime — [Creator Stack](https://www.creatorstackclub.com/software/inshot)
- Captions: ~$9.99 entry / $24.99-29.99 Max / $69.99+ Frontier; credit-based — [eesel](https://www.eesel.ai/blog/captions-ai), [Hooked](https://www.hooked.so/compare/captions-ai-pricing)
- invideo: ~$17-28 Plus up to $900 Elite; credits for agents — [CostBench](https://costbench.com/software/ai-video-editing-saas/invideo-ai-edit/)
- Opus Clip: ~$15/mo for 300 credits; Agent Opus $29/$129 — [AI Agent Index](https://theaiagentindex.com/agents/opus-clip)
- Descript: $16-35/mo (varies), separate AI-credit pool — [Sonix](https://sonix.ai/resources/?p=3512)
- Canva Pro: $15/mo ($120/yr) — [eesel](https://eesel.ai/blog/canva-ai-pricing)
- Adobe: Premiere iPhone free, generative via Firefly credits ($9.99-199.99/mo tiers) — [AppleInsider](https://appleinsider.com/articles/25/09/30/adobe-premiere-launches-on-iphone-free-to-download-now)
- Google: AI Plus/Pro/Ultra plans gate Photos Video Remix; AI Pro $19.99, Ultra $249.99 (aggregator) — [TechCrunch](https://techcrunch.com/2026/07/08/google-photos-adds-a-new-ai-video-remix-tool/)
- Filmora ~$49.99/yr; Pictory $19/$39/$99; Lumen5 free/$29/$79/$199; Pika $0/$10/$35/$95; HeyGen Creator $24-29; Runway Aleph $0.28/s API — links in section 1
- SimplistUGC: $2.99/mo or $24.99/yr — [App Store](https://apps.apple.com/us/app/simplistugc/id6759472145)

### Inferences
- Credit-metered generative/agent usage and $15-30/mo consumer price points are the norm; a library-indexing product has an additional storage and embedding cost to price in.

### Gaps
- No vendor-primary pricing pages were successfully read for most products; numbers conflict (e.g., Captions Max $24.99 vs $29.99; invideo tiers; Descript tiers; free-tier existence). Verify on vendor pages before quoting.
- Hedra, Synthesia, Vizard, Submagic, Gling, Quso, Quik/GoPro, VN prices not captured reliably.

---

## 5. Closest existing product to the full vision, and the real white space

### Takeaway
Closest: **invideo's agentic editor** (reference matching + footage-level search + agent/chat edits on an editable timeline). Closest on the *blueprint/shot-list* half: **ViralClip**. White space (inferred): a persistent, cross-project, personal visual memory that is queried against a reference-derived shot spec, with explicit exact/similar/missing classification and precise recording instructions for missing shots, in a mobile-first reels workflow.

### Cited Findings
- invideo already claims: reference matching, footage search by people/actions/objects/camera angles, plain-language agent edits, editable timeline — [invideo agent page](https://invideo.io/make/agentic-video-editor/), [reference page](https://invideo.io/make/style-and-motion-reference/)
- invideo itself notes reference styles may not translate when the user's footage can't support them (e.g., multi-location references) — [FAQ](https://invideo.io/faq/can-an-ai-editing-agent-match-the-pacing-and-style-of-a-reference-video/)
- ViralClip produces hook/pacing/shot-list breakdown and storyboard from a reference link, but rebuilds around the user's *product* with AI generation — [listing](https://similarlabs.com/zh/p/viralclip-viral-video-cloner-blueprint)
- Mosaic: library-scale retrieval not supported yet; style transfer from reference planned — [Launch HN](https://hn.svelte.dev/item/45980760)
- Google Photos can retrieve and assemble highlights from a personal library by typed query, but does no reference-based editing — [Google blog](https://blog.google/products/photos/photo-to-video-remix-create-tab)
- Guided shooting exists only as shot-list checklists (SimplistUGC) and teleprompters — [App Store](https://apps.apple.com/us/app/simplistugc/id6759472145)
- Platform risk: CapCut and Instagram Edits ship template and AI features rapidly (Edits: weekly personalised clip ideas from your past Reels, Jan 2026) — [Social Media Today](https://www.socialmediatoday.com/news/edits-gets-ig-links-weekly-ideas-and-new-video-effects-features/809644/)

### Inferences
- Remaining white space (not directly evidenced, based on absence in what I found): (1) persistent indexed personal library tied to editing; (2) gap analysis (exact/similar/missing) against a reference blueprint; (3) per-shot recording instructions for missing shots only; (4) real-footage-first rather than generative-first. Each is individually thin; the moat is the combination plus data accumulation in the library.
- Risks: invideo or CapCut could add a "missing shots" prompt cheaply; Google Photos/Apple already own the personal library and could bolt on reference editing; Instagram Edits has the user's Reels history and the reference-Reel context natively.

### Gaps
- Could not verify invideo's feature depth or recency (no dated launch, product not tested).
- No App Store/Play Store review analysis done (user pain points with templates, library search) — not covered.
- Apple Photos Memories, Quik/GoPro and Adobe Express status unchecked; they could narrow the white space.
