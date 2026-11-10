# Legal, platform-policy and privacy constraints for a reel-analysis + face-recognition photo/video app (as of 2026-11-02)

Not legal advice. Research session had a search-tool rate limit and some sites unreachable (TikTok, Illinois ILGA); many findings rest on law-firm/secondary sources and are flagged. Founder location (India) is unconfirmed.

## 1. Reference ingestion (Instagram / TikTok / YouTube links)

### Takeaway
Official APIs do NOT permit fetching/storing the media of third-party Reels/Shorts for analysis: Instagram oEmbed is embed-only, YouTube API terms ban downloading/caching and scraping, and TikTok ToS bans automated extraction. Safest design: analyze only a file/screen-recording the user supplies (or analyze via embed-only display), and have the user attest they have the right to use it. Server-side link download (yt-dlp-style) is a ToS breach on all three platforms, and on YouTube also arguably circumvention.

### Cited Findings
- Instagram oEmbed returns only embed HTML plus basic metadata (no media file/video URL). Docs say it is "only meant to be used for embedding Instagram content in websites and apps"; using metadata/content for other purposes incl. analytics, extracting, or persisting is prohibited. Supports /reel/ URLs; private, age-restricted, embed-disabled accounts unsupported; 1,000 req/hour. — [Meta oEmbed docs](https://developers.facebook.com/docs/instagram-platform/oembed)
- YouTube API Services Developer Policies: may not "download, import, back up, cache, or store copies" of YouTube audiovisual content without written approval (III.E.1); may not separate/isolate audio or video components (III.I.7-9); may not scrape or obtain scraped YouTube data (III.E.6); may not use technology other than the API to access API data incl. audiovisual content; non-authorized API data stored max 30 days; delete user-authorized data within 7 days of user request. — [YouTube API Developer Policies](https://developers.google.com/youtube/terms/developer-policies)
- YouTube Terms of Service: bars accessing/reproducing/downloading content except as the Service authorizes or with written permission; bars circumventing features that restrict copying; bars accessing by automated means (robots, scrapers) except search engines obeying robots.txt. — [YouTube ToS](https://www.youtube.com/t/terms)
- TikTok ToS (secondary source quoting it): prohibits extracting data by any automated system/bot without written approval; source gives ToS date as July 15, 2026 while another monitoring site gives May 5, 2026 (date unclear; US-entity term). TikTok Research API limited to approved academic researchers at non-profit institutions in supported regions (US, EEA, UK, Switzerland, Brazil per one source); Research Tools ToS effective Oct 25, 2024. Not verified against TikTok's own pages (site unreachable). — [ConductAtlas on TikTok ToS](https://conductatlas.com/platform/tiktok/tiktok-terms-of-service/prohibition-on-scraping-and-data-extraction/); [webscraping.ai FAQ](https://webscraping.ai/faq/tiktok-scraping/can-i-scrape-tiktok-data-for-academic-research-purposes) (vendor with commercial interest)
- Precedent Meta v. Bright Data (N.D. Cal., Judge Chen, Jan 23 2024): summary judgment for Bright Data on breach of contract; Facebook/Instagram terms "only prohibit logged-in scraping, and not logged-off scraping"; no evidence of logged-in scraping; Meta later dismissed its remaining claim, waiving appeal. Limited: concerns logged-off public data and contract claims only, not copyright, not logged-in access, and is a district court ruling. — [Quinn Emanuel alert](https://www.quinnemanuel.com/the-firm/news-events/client-alert-what-does-the-meta-v-bright-data-summary-judgment-ruling-mean-for-web-scraping/); [MediaPost on abandonment](https://www.mediapost.com/publications/article/393996/meta-abandons-lawsuit-against-bright-data-over-scr.html); [Eric Goldman blog](https://blog.ericgoldman.org/archives/2024/01/game-on-bright-data-scores-major-victory-in-web-scraping-dispute-with-meta-guest-blog-post.htm)
- Competitors: Opus Clip reportedly accepts YouTube, Twitch, Zoom, Loom, Riverside links (third-party reviews); Submagic's own comparison page claims built-in downloaders for YouTube/TikTok etc. and says Opus lacks them (vendor marketing, unverified). No official terms/help pages retrieved for CapCut, Edits, Captions, Opus Clip, Submagic. — [Submagic vs Opus page](https://www.submagic.co/alternative/opus-pro); [Vantaige on Opus Clip](https://vantaige.io/ai-tool/opus-clip)

### Inferences
- Bright Data reasoning is thin cover: it addressed only logged-off scraping contract claims; YouTube's ToS/dev policy and TikTok's ToS are separate contracts and YouTube's anti-circumvention language adds a DMCA 1201-style theory (inference, not verified in case law here).
- Founder-facing safe tiers: (1) user-uploaded file/screen recording, analyzed ephemerally; (2) share-sheet receiving a user-owned file; (3) oEmbed/embed for display only, with no analysis of media; (4) link-paste fetching = high risk. A user-initiated device-side download is lower platform-risk than server-side scraping but still a user ToS breach (inference).
- Competitors that accept YouTube links tend to do so for the user's own/licensed videos (inference); their actual terms were not verified.

### Gaps
- Official Instagram Terms scraping clause (page fetch returned only a heading), Meta Platform Terms, TikTok official ToS/Display API/Content Posting API terms: not retrieved.
- Official CapCut/Edits/Captions/Opus/Submagic terms on link ingestion: not retrieved.
- Other precedents (hiQ v. LinkedIn, X Corp v. Bright Data, Meta v. voyager/other scrapers 2025-26): not researched; no 2025-26 scraping rulings checked.

## 2. Copyright and music

### Takeaway
Structural elements (pacing, shot list, format) are generally idea/style rather than protected expression in US doctrine, but I found no case law on video-structure replication in this session; risk rises with reproducing distinctive creative selection, original audio, text, or footage. Music is the bigger practical risk: business/commercial accounts on Instagram are restricted to Meta's Sound Collection or separately licensed tracks.

### Cited Findings
- US Copyright Office Part 3 (pre-publication, May 9, 2025): compiling training datasets "clearly implicates the right of reproduction"; many training acts may be prima facie infringing unless fair use applies; status uncertain as no final report after Register Perlmutter's removal. — [ppc.land](https://ppc.land/us-copyright-office-releases-major-ai-training-report-amid-intensifying-copyright-debate/); [babl.ai](https://babl.ai/u-s-copyright-office-releases-pre-publication-report-on-ai-training-and-copyright-law/)
- Bartz v. Anthropic (Alsup, June 23 2025): training fair use, but pirated central library not excused. Kadrey v. Meta (Chhabria, June 25 2025): fair use on that record because plaintiffs failed to show market harm; judge said result could differ with better record. — [Jackson Walker](https://www.jw.com/news/insights-kadrey-meta-bartz-anthropic-ai-copyright/); [Sterne Kessler](https://www.sternekessler.com/news-insights/insights/ai-ip-year-in-review-the-market-harm-dilemma-what-bartz-and-kadrey-reveal-about-fair-use%CA%BCs-future-in-generative-ai/)
- EU has a TDM exception allowing training on publicly available works subject to opt-out (per the Part 3 report coverage). — [babl.ai](https://babl.ai/u-s-copyright-office-releases-pre-publication-report-on-ai-training-and-copyright-law/)
- Instagram: accounts without access to the licensed music library may use Meta's Sound Collection (14,000+ royalty-free tracks, stated usable commercially, incl. ads); other sources say Meta's label deals cover only personal non-commercial use of the main library, and warn of muted audio, blocked posts, reduced reach, and German warning-letter waves for business accounts. Sources conflict on whether Sound Collection audio can be reused off-Meta. — [Instagram Help](https://help.instagram.com/ipad-app/402084904469945); [Osborne Clarke](https://www.osborneclarke.com/insights/use-music-social-media-platforms-what-businesses-and-creators-need-know-about-usage); [Third Chair](https://usethirdchair.com/blog/instagram-sound-library-rules-for-creators-and-brands)

### Inferences
- Analyzing a user-supplied reel to extract timing/shot-type metadata is an internal-analysis use; main exposure is the copy made for analysis (reproduction), not the output. Fair use/TDM arguments apply but are fact-specific; Kadrey stresses market harm, which is weak for a non-substitutive structural template (inference).
- Do not carry over the reference reel's audio into output; offer licensed/library audio or user's own.
- Because the app is B2C creator-facing, many users will be on business/creator accounts: audio guidance should be per-account-type (inference).

### Gaps
- No case law found on style vs expression for video structure/format (e.g., Cheney Bros./Feist doctrine, format cases); none retrieved.
- Japan Art. 30-4 text not retrieved; India's copyright law/TDM position (Copyright Act 1957, ANI v. OpenAI Delhi HC) not researched.
- TikTok Commercial Music Library, YouTube Audio Library terms not retrieved.

## 3. AI-generated content labelling, provenance, deepfake/digital-replica law

### Takeaway
EU AI Act Art. 50 applies since 2 Aug 2026 (machine-readable marking grace to 2 Dec 2026 for pre-existing systems). India's IT Rules amendment (in force 20 Feb 2026) mandates labels for synthetic audio-visual content. California's AI Transparency Act became operative 2 Aug 2026 (per secondary sources). NO FAKES Act not law. All three platforms require self-disclosure for realistic AI content and read C2PA.

### Cited Findings
- EU Digital Omnibus on AI = Regulation (EU) 2026/1744, in force 27 July 2026 (per Goodwin): Art. 50 obligations generally apply from 2 Aug 2026; Art. 50(2) marking grace until 2 Dec 2026 for generative systems already on market before 2 Aug 2026; Annex III high-risk delayed to 2 Dec 2027, Annex I to 2 Aug 2028; new Art. 5 ban on nudification/CSAM systems from 2 Dec 2026; Commission transparency guidelines adopted 20 July 2026; Art. 50 fines up to EUR 15M / 3% turnover, new prohibitions EUR 35M / 7%. Other secondary sources give differing adoption dates (EP 16 June, Council 29 June 2026). — [Goodwin](https://www.goodwinlaw.com/en/insights/publications/2026/08/alerts-technology-dpc-eu-ai-act-transparency-obligations-now-in-force); [Usercentrics](https://usercentrics.com/knowledge-hub/eu-ai-act-high-risk-delay-article-50-transparency-consent/); [Winston Taylor](https://www.winstontaylor.com/insights/ai-act-rules-on-high-risk-ai-delayed-as-ai-digital-omnibus-agreed)
- Art. 50 content: providers must mark synthetic outputs machine-readably; deployers must disclose deepfakes of real persons/places/events (Goodwin; sub-paragraph numbering not given there). — [Goodwin](https://www.goodwinlaw.com/en/insights/publications/2026/08/alerts-technology-dpc-eu-ai-act-transparency-obligations-now-in-force)
- India: MeitY notified IT Rules amendment on "synthetically generated information" Feb 10, 2026 (G.S.R. 120(E)), effective Feb 20, 2026; labelling of audio/visual SGI, user declarations and verification for significant social media intermediaries, provenance metadata, shortened takedown timelines (3 hours for some content per Hogan Lovells headline). A later follow-up amendment reported but unconfirmed. — [Hogan Lovells](https://www.hoganlovells.com/en/publications/india-introduces-mandatory-labelling-for-ai-and-3hour-takedown-for-illegal-content); [S.S. Rana](https://ssrana.in/articles/india-tightens-oversight-on-ai-generated-content-under-it-rules/); [Freshfields](https://technologyquotient.freshfields.com/post/102mjwn/india-targets-deepfakes-and-ai-generated-content-key-changes-under-meitys-2026)
- California AI Transparency Act (SB 942) operative date moved by AB 853 (signed Oct 13, 2025) from Jan 1 2026 to Aug 2 2026; later phases for large platforms (Jan 1 2027) and capture-device makers (2028). — [Orrick](https://infobytes.orrick.com/2025-10-17/california-delays-its-ai-transparency-act-and-passes-new-content-laws/); [Troutman](https://www.troutmanprivacy.com/2025/10/california-ai-transparency-act-amendments-signed-into-law/)
- NO FAKES Act: reintroduced May 20, 2026 (S.4591 / H.R.8915); Senate Judiciary advanced it unanimously June 18, 2026; 2026 version adds DMCA-style counter-notice; Daily Journal headline Oct 7, 2026 says "dead for now as Cruz objects to unanimous consent request" (headline only). Not law. — [Manatt](https://manatt.com/insights/newsletters/client-alert/congress-reintroduces-the-no-fakes-act-what-s-new-in-the-2026-bill); [Sen. Blackburn](https://www.blackburn.senate.gov/2026/6/blackburn-coons-bipartisan-bill-to-protect-individuals-and-creators-from-deepfakes-passes-senate-judiciary-committee); [Daily Journal](https://www.dailyjournal.com/article/395055-no-fakes-act-dead-for-now-as-cruz-objects-to-unanimous-consent-request)
- Platform labels (secondary sources): YouTube altered/synthetic disclosure (policy March 2024; permanent label for content with C2PA fully-generative metadata); Meta "AI info" label (renamed July 2024) driven by C2PA/IPTC signals; TikTok requires labelling realistic AI content and reads C2PA. Dates conflict across sources. — [Billo](https://billo.app/blog/ai-labeling/); [Influencer Marketing Hub](https://influencermarketinghub.com/ai-disclosure-rules/)

### Inferences
- If the app generates/alters people's faces or voices (replicas), it is likely a "provider" for Art. 50(2) and users are "deployers" for 50(4) when serving EU users; embed C2PA/watermark in exports (inference, matches Art. 50 design).
- If app only edits user's real footage (cuts, captions, reorder), AI-label duty is lighter, but any face/voice synthesis, lip-sync, or generated B-roll triggers labelling. Draw that product line deliberately.
- India SGI rules mainly bind intermediaries but create downstream pressure and likely app-level expectations; confirm applicability from the gazette text.

### Gaps
- Tennessee ELVIS Act (effective July 1, 2024) and other state digital-replica laws (CA AB 2602/1836, NY, etc.): search returned nothing; unverified, no source.
- Primary text of Art. 50 and EUR-Lex Regulation 2026/1744 not fetched; date discrepancies between sources unresolved.
- Official Meta/TikTok/YouTube policy pages not fetched.

## 4. Biometric / privacy law

### Takeaway
Face recognition on stored personal media = highest-risk component: BIPA (private right of action), Texas CUBI (AG enforcement with billion-dollar settlements), GDPR Art. 9 and India DPDP (core duties from May 2027). Third-party faces in user footage is the hard design problem; consider not doing identity matching at all (face detection/clustering on-device, no templates stored server-side).

### Cited Findings
- BIPA: 2024 amendment (Public Act 103-0769, effective Aug 2, 2024) limits damages to one recovery per person ($1,000 negligent / $5,000 intentional); Seventh Circuit in Clay v. Union Pacific (Apr 1, 2026) held it applies retroactively. — [Sidley](https://datamatters.sidley.com/2026/04/08/seventh-circuit-limits-potential-damages-under-bipa-holds-2024-amendment-applies-retroactively/); [Polsinelli](https://www.polsinelli.com/privacy-litigation/publications/bipa-amendment-limiting-damages-applies-retroactively)
- Clearview BIPA class settlement approved Mar 20, 2025 (23% equity stake, est. ~$51.75M). — [Darrow](https://www.darrow.ai/news/a-first-in-bipa-litigation-class-members-receive-equity-in-clearview-ai)
- Texas AG: Meta $1.4B (July 2024, first CUBI suit); Google $1.375B (announced May 9, 2025 per Haynes Boone; one source gives Oct 31, 2025, conflict); CUBI penalties up to $25,000 per violation. — [Linklaters](https://techinsights.linklaters.com/post/102kb5i/the-price-of-privacy-compliance-what-googles-texas-settlement-signals-for-big-t); [Haynes Boone](https://www.haynesboone.com/news/articles/newman-in-cybersecurity-law-report-on-texas-ags-billion-dollar-settlement); [CSLR](https://www.cslawreport.com/21169961/texas-ags-billiondollar-settlement-with-google-highlights-biometric-data-use-compliance-considerations.thtml)
- Dutch DPA fined Clearview EUR 30.5M (Sept 2024) for GDPR violations (no legal basis for scraped faces); warned Dutch users of Clearview may be fined; up to EUR 5.1M extra penalty; Clearview disputes enforceability. — [Pinsent Masons](https://pinsentmasons.com/out-law/news/dutch-pa-fines-facial-recognition-company-gdpr-breach); [Infosecurity](https://infosecurity-magazine.com/news/clearview-ai-fined-30m-netherlands)
- India DPDP Rules 2025 notified Nov 13, 2025 (Gazette Nov 14): Board provisions immediate; Consent Manager registration (Rule 4) from ~Nov 2026; bulk incl. notice/consent (Rules 3, 5-16, 22, 23) from ~13 May 2027 (some sources say 14 May); ambiguity noted by commentators. DPDP has no separate "sensitive/biometric" category in the sources retrieved (not confirmed). — [JSA Prism](https://www.jsalaw.com/wp-content/uploads/2025/11/JSA-Prism-InfoTech-November-2025-DPDP-Rules.Final_.pdf); [Hogan Lovells](https://ca.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-); [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/)

### Inferences
- A solo/early startup storing face embeddings of US users in Illinois/Texas faces statutory exposure; BIPA's per-person cap reduces but doesn't remove class risk (written policy, retention schedule, written release before collection are core BIPA requirements from my background knowledge; statute text not retrieved).
- Photos include bystanders: app can't obtain their consent; mitigation = no identity matching of non-users, cluster-only local processing, user-labelled "people" only with user's own attestation, short retention, deletion on account close (design inference).
- Because DPDP core duties start ~May 2027, an India launch in 2026-27 has a runway but should be built DPDP-ready (notice, purposes, deletion, breach duties).

### Gaps
- Not retrieved: BIPA statute text, Washington My Health My Data / RCW 19.375, GDPR Art. 9/35 regulator guidance, UK ICO guidance, CCPA/CPRA "sensitive PI" and ADMT regs, Meta $650M BIPA settlement, Google Photos/Shutterfly BIPA matters, Meta FTC 2019/2024, EDPB opinions.
- DPDP: children's data (18+ verifiable parental consent) and significant data fiduciary DPIA obligations not verified here; cross-border transfer rules not checked.

## 5. App store policies

### Takeaway
Apple (since Nov 2025 revision) requires disclosure and explicit permission before sharing personal data with third-party AI; account deletion in-app is mandatory. Google Play has an AI-Generated Content policy requiring in-app reporting/flagging and tight rules on non-consensual intimate/deepfake content.

### Cited Findings
- Apple guideline 5.1.2(i) updated Nov 2025: must disclose and obtain explicit permission before sharing personal data with third parties "including with third-party AI"; developers report rejections under 5.1.1(i)/5.1.2(i); a privacy-policy line alone reportedly insufficient (secondary). — [TechCrunch](https://techcrunch.com/2025/11/13/apples-new-app-review-guidelines-clamp-down-on-apps-sharing-personal-data-with-third-party-ai); [Apple dev forum](https://developer.apple.com/forums/thread/816140)
- Apple 5.1.1(v): apps supporting account creation must allow initiating account deletion in-app (since June 30, 2022). — [Apple App Review Help](https://developer.apple.com/help/app-review/guideline-reference/5-1-1-account-deletion)
- Google Play AI-Generated Content policy: covers content generated from text/voice/image prompts; generative AI apps need in-app flag/report mechanism; additional review for broad photo/video permissions (2023 announcement); Aug 25, 2026 Android Developers Blog guidance on preventing non-consensual intimate content. — [Google Play policy](https://support.google.com/googleplay/android-developer/answer/14094294); [Android Developers Blog](https://android-developers.googleblog.com/2026/08/ensuring-safety-genai-preventing-non-consensual-intimate-content.html); [TechCrunch 2024](https://techcrunch.com/2024/06/06/google-play-cracks-down-on-ai-apps-after-circulation-of-apps-for-making-deepfake-nudes)

### Inferences
- Sending users' photos/videos to Gemini/OpenAI/TwelveLabs needs a just-in-time consent screen naming the AI vendor (Apple), plus privacy nutrition label/Data Safety disclosures for photos/videos, face data (Apple lists "Face"? not verified).
- Use PHPicker/limited photo access rather than full-library access to ease review (inference).

### Gaps
- Primary Apple guidelines page, Apple privacy label categories, Google Play Photo/Video Permissions policy 2026 text, Google Play account-deletion/Data Safety requirements, UGC requirements (Apple 1.2): not retrieved.

## 6. Vendor terms for user-video upload

### Takeaway
Paid API tiers of Gemini and OpenAI do not train on your data by default and log for abuse monitoring (OpenAI up to 30 days; Gemini limited period); true zero retention needs OpenAI approval or Vertex AI. Free Gemini tier can use data for training (not in EEA/UK/CH per secondary source). TwelveLabs terms are less clear; get contract terms.

### Cited Findings
- Gemini API: for Paid Services, Google does not use prompts/files/responses to improve products; logs prompts/responses for limited period solely for Prohibited Use Policy violations; guaranteed ZDR/enterprise DPA -> use Vertex AI; Files API files persist until deleted/expiry; implicit caching 24h TTL in RAM; page silent on regional processing. — [Gemini API ZDR doc](https://ai.google.dev/gemini-api/docs/zdr.md.txt)
- Secondary: unpaid Gemini tier data may be used for training with human review, except EEA/CH/UK; older source cited 55-day abuse-log retention (2024; unverified now). — [Simon Willison](https://simonwillison.net/2024/Nov/19/preview-gemini/); [DevelopersDigest](https://www.developersdigest.tech/models/data-retention/google)
- OpenAI API: no training unless opted in; abuse logs up to 30 days; ZDR requires approval, and files/vector stores/etc. not ZDR-eligible; data residency incl. India, EU, UK, etc., but in-region processing only US/EU/UAE; images/files CSAM-scanned and retained if flagged even under ZDR. — [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
- TwelveLabs: Enterprise ToS say customer data used only to provide/maintain service, usage data shared only de-identified/aggregated; TechCrunch (2024) reports models trained on public-domain/licensed data, not customer data (press statement). A third-party site claims free indexes expire after 90 days (unverified). Privacy policy dated April 2023 says it uses customer data to run and improve services. — [TwelveLabs ToS](https://www.twelvelabs.io/tos); [TwelveLabs privacy](https://twelvelabs.io/privacy); [TechCrunch](https://techcrunch.com/2024/12/12/twelve-labs-is-building-ai-that-can-analyze-and-search-through-videos/)

### Inferences
- Use paid tiers only; for face-containing content prefer Vertex AI (Gemini) or approved ZDR; confirm EU/India residency by contract. The "improve services" language in TwelveLabs' privacy policy conflicts with a no-training reading; get written DPA (inference).
- Embeddings (vector DB) of faces/voices may themselves be biometric identifiers/personal data; where stored matters (inference).

### Gaps
- Runway terms/data usage: not retrieved. Gemini Vertex regional processing/ZDR specifics, current Gemini abuse-log retention days, TwelveLabs retention/indexing deletion API terms, Anthropic: not verified.
