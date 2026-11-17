# Legal and terms-of-service position of building an AI training dataset from CapCut / JianYing templates, projects and exports

NOT LEGAL ADVICE. Research notes as of Nov 2026. Method caveats: the fetch tool truncates quotes to about 125 characters and sometimes summarises; where a quote below is marked "excerpt" it is a short verbatim fragment, everything else is paraphrase. Several primary texts could not be retrieved (JianYing Chinese agreement, EU Directive 2009/24/EC text, India Copyright Act s.52(1)(ab), Delhi HC judgment, Third Circuit docket). Those are listed under Gaps and any statement about them is labelled as model background knowledge, not verified.

## 1. What do the current CapCut ToS (Apr 2026), Materials License Agreement (Jan 2026) and JianYing agreement say (reverse engineering, automation/scraping, commercial use of materials, AI training, competing products, template ownership)?

### Takeaway
CapCut's ToS expressly bans reverse engineering and automated access to "the Services"; the Materials License bans reverse engineering of, and editing outside the Platform of, effects/fonts/stickers/music and bars spider/crawler/robot access. Neither document (as retrieved) has any clause on AI/ML training or competing products, so training-use is governed by the general restrictions plus copyright law, not a specific ban. JianYing's own agreement could not be retrieved.

### Cited Findings
- CapCut Terms of Service, "Last updated: April 15, 2026"; governed by laws of Singapore (subject to jurisdiction-specific terms). — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- ToS s.6 prohibited conduct, excerpt: "reverse engineer, disassemble, decompile, or create any derivative works based on, the Services". — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- ToS s.6 item 9, excerpt: "use automated scripts or other technologies to collect information from or otherwise interact with the Services". — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- ToS s.6 item 4, excerpt: "distribute, license, transfer, or sell, in whole or in part, any of the Services or any derivative works thereof"; other items bar bypassing access controls. — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- ToS: keyword check by the fetch found no occurrence of "artificial intelligence", "machine learning", "train", "scrape", "robot", "spider", "compete", "benchmark". "AI" appears only in the third-party AI services section ("Certain features of the Services are integrated with third-party AI technologies and APIs") and a bar on circumventing limits of any Services. — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- ToS s.10: "We don't own your User Content"; user grants CapCut and affiliates a "non-exclusive, royalty-free, transferable, sub-licensable" licence (reported as perpetual and worldwide). — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- ToS s.10 "Company Content" = "creative materials provided directly by CapCut"; user gets "non-exclusive, limited, non-transferable, non-sublicensable, revocable license"; commercial-use scope depends on product and is set by the Materials License Agreement; Pippit expressly permits commercial use. Third-party content such as "certain video templates provided by third parties": "Such third party content is not provided by us or endorsed by us"; limited licence, use at own risk. — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- CapCut Materials License Agreement, "Last Updated: January 22, 2026". Licence is "non-exclusive, non-transferable, non-sublicensable"; materials are either Non-commercial Use or Dual Use (limited commercial use as marked on the Platform); licence granted per exported content, with term and territory. — [Materials License](https://www.capcut.com/clause/materials-license-agreement)
- Materials License s.4 restrictions, excerpts: "edit or modify the Platform Materials or Music Materials incorporated in your content outside the Platform"; "reverse engineer, decompile, disassemble any Platform Materials or Music Materials or any source code included therein"; "use Platform Materials or Music Materials for any purpose or in any manner not expressly permitted under this Agreement". Access via "spider, web crawler, robot software" prohibited (paraphrased by fetcher). — [Materials License](https://www.capcut.com/clause/materials-license-agreement)
- Materials License s.2-3: content with any Non-commercial material is limited to personal non-commercial use; mixing Dual Use and Non-commercial material limits the result to non-commercial use. Music: Sounds "only for personal entertainment and non-commercial purposes"; "Commercial Sounds" only for Commercial Users on Permitted Platforms (CapCut, TikTok). — [Materials License](https://www.capcut.com/clause/materials-license-agreement)
- Materials License: CapCut owns Platform Materials (s.7); Third Party Materials not owned/controlled by CapCut and governed by separate terms (s.8). No clause found on ML training. — [Materials License](https://www.capcut.com/clause/materials-license-agreement)
- CapCut's own explainer says content such as a shared template "can't be fully recalled once others have reused or remixed it", and that other members may "adapt, modify" or create "derivative works" from shared templates; it does not mention AI training. — [CapCut explainer](https://www.capcut.com/resource/about-capcut-terms-of-service)
- June 2025 ToS update drew wide criticism for a broad perpetual, sublicensable licence over user content including drafts and templates (secondary commentary, with an interest in the controversy). — [Techloy](https://www.techloy.com/capcuts-latest-terms-of-service-raises-big-questions-about-content-ownership/); [Payhip blog](https://payhip.com/FlutterCreativeStudio/blog/archive/what-every-creator-should-know-about-capcut-s-2025-terms-update)
- rea-capcut README itself says "writing back to Jianying format is unsupported" and describes "Experimental Jianying import: converts basic clips from verified formats"; "Complex text styles, effects and keyframes may be lost". So the tool will not give a faithful effects-level label set. — [rea-capcut README](https://github.com/Xiangyu-CAS/rea-capcut)

### Inferences
- The ToS s.6 reverse-engineering and automated-access clauses are drafted against "the Services" (app/platform). Opening a draft with an open-source parser is arguably not reverse engineering by the team (the tool's author did that), but running scripts that "interact with the Services" (template fetching, bulk template opening via UI automation, cache scraping) squarely fits s.6 item 9. Note: ToS s.6 item 9 text "collect information from or otherwise interact with" is broad.
- The Materials License is the most dangerous document for this plan: effects, fonts, stickers and music inside a template are Platform Materials, licensed per exported content, mostly personal/non-commercial, and cannot be "edit[ed] or modif[ied] ... outside the Platform". Extracting their parameters or rendered looks into a commercial model's training set is a use "not expressly permitted".
- Absence of an AI-training clause is not permission; the default is that anything not granted is not licensed (licence is "limited" and "revocable").
- Mixing templates containing non-commercial materials makes the export non-commercial-use-only under s.2 of the Materials License. Training a commercial product on it is at least arguably "commercial".

### Gaps
- JianYing (剪映) Chinese user agreement and material-licence text not retrieved: jianying.com/agreement redirects to capcut.cn; a Chinese search returned no original text. Do not assume parity with CapCut. Must fetch and read in Chinese (or via Chinese counsel).
- Full verbatim text of ToS s.6 and Materials License s.4 (fetcher truncates quotes). Retrieve the pages directly and archive them (dated snapshot) before relying on them.
- CapCut template-creator/"template community guidelines" terms (separate creator terms) not found; no primary text on who owns a template design.
- Whether ToS has jurisdiction-specific terms for India (the ToS says Singapore law "subject to any jurisdiction-specific terms").

## 2. Template creators' rights: who owns a template's design, and what licence do users get?

### Takeaway
Creators keep ownership of their own content but grant CapCut a broad licence that explicitly contemplates other users adapting and remixing shared templates; CapCut disclaims endorsement of third-party templates. No primary text found that grants template users rights to use the template as AI training data, nor that grants the creator's underlying footage, music or effects rights.

### Cited Findings
- "We don't own your User Content" (ToS s.10); user grants CapCut a licence over it. — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- Other members may "adapt, modify" or make "derivative works" from shared templates. — [CapCut explainer](https://www.capcut.com/resource/about-capcut-terms-of-service)
- Third-party templates: "Such third party content is not provided by us or endorsed by us"; limited licence, own risk. — [CapCut ToS](https://www.capcut.com/clause/terms-of-service)
- CapCut help says templates with copyrighted audio can be muted and that the review team checks shared templates for copyright violations (platform policy, not a ruling on template copyright). — [CapCut help](https://www.capcut.com/help/no-sound-in-the-template-published)
- Music in built-in libraries can trigger copyright claims on other platforms. — [Foxi Music](https://www.foximusic.com/blog/royalty-free-music-capcut-licensing-guide/)
- AutoTransition (ECCV 2022) built its dataset from videos "extracted from the video editing template" on "online video editing platforms" (platform unnamed) and releases only links, not videos; its repo states no licence. — [AutoTransition repo](https://github.com/acherstyx/AutoTransition)

### Inferences
- A template bundles at least four rights layers: (1) the creator's arrangement (timing, transitions, text layout), (2) CapCut Platform Materials (effects, fonts, stickers), (3) licensed music, (4) sometimes the creator's placeholder footage. Each has a different owner; the ToS licence to "users of templates" does not clearly cover bulk extraction.
- The permissive-looking "remix" language concerns user-to-user use inside CapCut, not export to a third-party training set.
- AutoTransition's "links only" release suggests academics treat redistributing template-derived videos as sensitive; this is an inference about intent, the repo only says links are released.

### Gaps
- No primary CapCut creator/template terms located (the search returned commentary only). Need the in-app template-publishing terms.
- No case law found on ownership of a template as a whole.

## 3. Reverse engineering for interoperability: DMCA 1201(f), Sega/Connectix, EU Software Directive Art 6/8, India s.52(1)(ab), China; does a clean-room reimplementation stay legal and does a contract clause override?

### Takeaway
Statutory/case-law interoperability exceptions are narrow (they permit analysis to build an interoperable independent program, not to harvest the target's content), and in the US a contractual ban on reverse engineering can still bind (Bowers v. Baystate), whereas in the EU contrary clauses are void for the Art 6/5(3) acts. Even where the tool's creation is lawful, it says nothing about the legality of using CapCut-owned content or breaching ToS in your own use.

### Cited Findings
- 17 USC 1201(f)(1): a person "who has lawfully obtained the right to use a copy of a computer program" may circumvent an access control "for the sole purpose of identifying and analyzing those elements of the program" necessary for interoperability, only "to the extent any such acts of identification and analysis do not constitute infringement". (f)(2) allows developing means for that; (f)(3) lets those means/information be shared "solely to enable interoperability of an independently created program"; (f)(4) defines interoperability as "the ability of computer programs to exchange information" and mutually use it. — [17 USC ch.12 (copyright.gov)](https://www.copyright.gov/title17/92chap12.html)
- 1201(a)(1)(A), excerpt: "No person shall circumvent a technological measure that effectively controls access to a work protected under this title." — [17 USC ch.12](https://www.copyright.gov/title17/92chap12.html)
- Sega v. Accolade (9th Cir. 1992): "where disassembly is the only way to gain access to the ideas and functional elements embodied in a copyrighted computer program and where there is a legitimate reason for seeking such access, disassembly is a fair use". — [summary via search, FindLaw/OpenJurist listing](https://caselaw.findlaw.com/us-9th-circuit/1452245.html)
- Sony v. Connectix (9th Cir. 2000, 203 F.3d 596): intermediate copies made during reverse engineering of the Sony BIOS were fair use; copies were intermediate and no Sony code appeared in the final product. — [BitLaw](https://www.bitlaw.com/source/cases/copyright/Sony-Connectix.html)
- Bowers v. Baystate, 320 F.3d 1317 (Fed. Cir. 2003): 2-1 majority held the Copyright Act does not preempt a shrink-wrap clause barring reverse engineering; the ban was enforced even where the copying would otherwise be fair use; Supreme Court denied review. — [Wikipedia summary](https://en.wikipedia.org/wiki/Bowers_v._Baystate_Technologies,_Inc.); [WilmerHale](https://www.wilmerhale.com/en/insights/publications/shrink-wrap-licenses-and-reverse-engineering-april-16-2003)
- A UK commentary on IBM v LzLabs states that under the interoperability decompilation exception (CDPA s.50B, implementing Directive Art 6) contract terms cannot override it (search summary; full article not retrieved). — [RPC](https://www.rpclegal.com/thinking/tech/reverse-engineering-of-ibm-mainframe-software-in-breach-of-software-licence-ibm-v-lzlabs-part-1/)
- ippt.eu reproduces Directive 2009/24/EC Art 8 as "Any contractual provisions contrary to Article 6 or to the exceptions provided for in Article 5(2) and (3) shall be null and void" (search snippet; legislation.gov.uk header for Art 8 reads "Continued application of other legal provisions", so numbering/wording must be checked on EUR-Lex; in the codified 2009 text, "null and void" is, to my recollection, Art 8 para 2 / the former Art 9(1)). — [IPPT Art 8](https://www.ippt.eu/legal-texts/software-directive/article-8)
- rea-capcut README: "An independently implemented, open-source video editor", "Research is limited to authorized scope, without copying proprietary Jianying / CapCut code or assets", "The project uses REA to study Jianying's interface behavior and local project formats", "REA, Ghidra and Jianying are not runtime dependencies"; README does not use the term "clean-room"; Ghidra appears only in topic tags. — [rea-capcut README](https://github.com/Xiangyu-CAS/rea-capcut)

### Inferences
- US: 1201(f) only matters if there is an access-control circumvention; reading a plain JSON draft is not circumvention. If a given CapCut/JianYing version encrypts drafts (my recollection of community reports, not verified in this session), decrypting would implicate 1201(a), and 1201(f)(1) protects only analysis "for the sole purpose" of interoperability of an independently created program, not extracting content for a dataset.
- Sega/Connectix protect making intermediate copies to study functional elements, as fair use; they do not address training-data extraction or ToS breach by the person who did not do the RE.
- Bowers means that in the US, a ToS/EULA clause barring RE can create contract liability irrespective of copyright defences, if the clause is assented to (clickwrap) and enforceable. Whether CapCut's online ToS (Singapore law) would be enforced in a US or Indian court against a company is uncertain; Singapore/English-style law has no general "RE is overridden" rule outside the EU-derived UK s.50B.
- EU: Art 6 decompilation by a lawful user is allowed only if indispensable to obtain interoperability information, not previously readily available, and confined to the parts necessary; information may not be used for goals other than interoperability or to develop a substantially similar program (from model knowledge of the Directive, unverified here). Contrary contract terms are void for those acts.
- India: s.52(1)(ab) (from model knowledge, unverified here): permits a lawful possessor to do acts necessary to achieve interoperability of an independently created program; s.52(1)(aa)/(ac)/(ad) cover adaptation/observing/backup. No Indian case found; Indian courts have not tested interplay with contractual RE bans. Indian Contract Act s.27/s.28 arguments possible but speculative.
- China: not researched beyond noting JianYing is governed by PRC law; Regulation on Computer Software Protection permits study of ideas (from model knowledge, unverified). Treat as unknown.
- A "clean-room" claim: rea-capcut's README says research was "limited to authorized scope" and no copied code/assets, but it does not document a clean-room process (no separate spec/implementation teams), nor describe whether decompilation was done. Its legality is plausible but unproven; and it does not matter to our own obligations because we are users, not the implementer.

### Gaps
- Primary text of Directive 2009/24/EC Arts 5(3), 6, 8 (EUR-Lex/ippt/legislation.gov.uk fetches failed with empty/403).
- Primary text of India Copyright Act 1957 s.52(1)(aa)-(ad) (India Code returned 403).
- Primary text of the Sega, Connectix and Bowers opinions (only summaries retrieved).
- No Indian or Chinese case law found on contractual RE bans; no check on China's Software Protection Regulation.
- rea-capcut's "Draft interoperability" document (linked from README) not read; it may state exactly which formats are supported and how derived.

## 4. Does using rea-capcut change our obligations? Legality of the tool versus legality of what we do with CapCut content.

### Takeaway
No. rea-capcut is an MIT-licensed independent editor, and its own legal posture (if sound) covers only its authors' research and distribution. It does not license CapCut's materials, waive CapCut's ToS for us, or authorise reading data we obtained through ToS-breaching routes. "We can do anything with rea-capcut" is not supported.

### Cited Findings
- rea-capcut: "ReaCut is an independent project and is not affiliated with Jianying / CapCut"; "ReaCut's own source code is licensed under the MIT License"; bundled FFmpeg/x264 under GPL, Noto Sans SC under SIL OFL 1.1; "Use media you own or can redistribute." — [rea-capcut README](https://github.com/Xiangyu-CAS/rea-capcut)
- Jianying import is "experimental ... basic clips from verified formats"; "Complex text styles, effects and keyframes may be lost; writing back to Jianying format is unsupported." — [rea-capcut README](https://github.com/Xiangyu-CAS/rea-capcut)
- A directory listing (SkillsLLM) says it does not control the underlying repo; it calls the project early stage (v0.5.1). — [SkillsLLM](https://skillsllm.com/skill/rea-capcut)
- Related tools (pyJianYingDraft, capcut-cli, jianying-headless) generate/read draft JSON without being CapCut-licensed. — [search listing](https://docsearch.algolia.com/mcp/docs/repo/guanyixuan/pyjianyingdraft)

### Inferences
- Layering: (a) tool legality (author's RE; MIT licence) is the author's risk and sits under 1201(f)/Art 6-type analysis; (b) our use of CapCut app to open templates is governed by ToS/Materials License; (c) what we do with exported video and JSON (train a commercial model) is governed by copyright in the template arrangement and materials, the licence terms, and the AI-training law in section 5. rea-capcut touches only (a).
- The MIT licence on the tool's code also says nothing about the data files; the data's licence comes from CapCut and the template creator.
- The README itself says "Use media you own or can redistribute", which is the opposite of the "anything" claim.
- Practical warning: the tool is a young, third-party, single-maintainer project (v0.5.1); relying on it for a commercial labelling pipeline carries engineering and provenance risk.

### Gaps
- Could not verify rea-capcut's repo directly beyond the README summary (license file, issue tracker, any DMCA/takedown notice).
- No evidence found of any CapCut/ByteDance enforcement against RE tooling such as pyJianYingDraft or rea-capcut (absence of evidence, not of risk).

## 5. Copyright and AI training on others' videos/edits (India, US, EU); are editing styles/templates themselves copyrightable?

### Takeaway
Law on AI training is unsettled everywhere: India has an interim Delhi HC ruling favouring OpenAI and a DPIIT proposal for mandatory licensing with royalties; US district decisions lean fair use for lawfully acquired data but split on market harm and note Ross (non-generative, competing) went against the AI developer; EU has a TDM exception with opt-out and a pending CJEU case. A style or editing technique is likely unprotectable idea, but a specific template's concrete arrangement plus included materials may be protected. Contract/ToS breaches and unlawful acquisition are separate exposures that fair-use arguments do not cure.

### Cited Findings
- DPIIT working paper Part I (8 Dec 2025) recommends a "Hybrid Model" with a mandatory blanket licence for AI training, royalties payable "only upon commercialisation", set by government, administered by CRCAT; no opt-out; limited to lawfully accessed works and cannot bypass technological protection measures; Nasscom dissented in favour of a TDM exception with opt-out. It is a proposal, not law. — [Mondaq](https://www.mondaq.com/india/copyright/1718746/exploring-the-dpiits-working-paper-on-generative-ai-and-copyright); [Storyboard18](https://www.storyboard18.com/digital/dpiit-releases-working-paper-on-copyright-and-ai-proposes-hybrid-licensing-model-85551.htm)
- ANI v OpenAI (Delhi HC): on 24 July 2026 Justice Amit Bansal dismissed ANI's interim-injunction application, prima facie holding storage of ANI's works to train the model is protected under s.52(1)(a) (fair dealing); RAG outputs not substantially similar; findings do not bind the merits; jurisdiction in Delhi upheld. — [SpicyIP](https://spicyip.com/2026/07/training-chatgpt-on-copyrighted-works-prima-facie-protected-under-indian-copyright-act-delhi-high-court-refuses-interim-injunction-against-openai.html); [IPleaders](https://blog.ipleaders.in/ani-v-openai-ai-training-copyright-ruling/)
- Thomson Reuters v. Ross (D. Del. Feb 2025): fair use rejected for a non-generative competing legal-search tool; interlocutory appeal at the Third Circuit (no decision seen in results). — [OSU Libraries 2026 update](https://library.osu.edu/site/copyright/2026/03/20/fair-use-and-artificial-intelligence-2026-update/); [ABA Business Law Today](https://www.americanbar.org/groups/business_law/resources/business-law-today/2026-september/thomson-reuters-v-ross-one-year-later/) (page not directly fetched; via search summary)
- Bartz v. Anthropic (N.D. Cal. June 2025): training on lawfully acquired books fair use; later a reported $1.5bn settlement with final approval in July 2026 (liability for pirated library copies). Kadrey v. Meta (N.D. Cal. June 2025): summary judgment for Meta on that record, with the judge noting different market-harm evidence could change the result. — [White & Case](https://www.whitecase.com/insight-alert/two-california-district-judges-rule-using-books-train-ai-fair-use); [Global Legal Post](https://www.globallegalpost.com/news/anthropic-meta-fair-use-rulings-in-ai-training-expose-judicial-split-on-market-harms-1365503569)
- EU: Like Company v Google (CJEU C-250/25) first AI copyright reference; one report says the AG opinion was delivered 3 Nov 2026 and treated training as permitted under an exception (single secondary source, unverified; an AG opinion is not a judgment). Hamburg Regional Court (LAION, Sept 2024) dismissed a photographer's claim over dataset creation. — [Stephenson Harwood](https://www.stephensonharwood.com/insights/cjeu-to-rule-on-ai-and-copyright-in-a-landmark-case-against-google/); [IPStars](https://ipstars.com/NewsAndAnalysis/ai-chatbots-and-copyright-anticipating-the-ruling-in-cjeus-case-c-250-25-is-the/Index/10994)
- CapCut's own guide states that US courts generally treat style as closer to an idea than protected expression, but that style-driven output can infringe by reproducing recognisable protected expression; it suggests shot order, timing, overlays and caption styling may be where human authorship shows (self-interested secondary source). — [CapCut guide](https://www.capcut.com/create/ai-video-copyright-safe-workflows)

### Inferences
- Our model would learn the structure of editing (cut timing, transition type, text animation parameters) rather than reproduce a specific video. This favours the "idea/method/fact" and transformative arguments, but if the trained model can regurgitate a particular template (nearly identical timings, effects, text layouts), the output-similarity risk rises.
- The Ross reasoning matters: our model generates editing templates, i.e. products that could substitute for CapCut templates in the market; that looks more like Ross (competing) than like a general LLM. Market-harm factor risk is real for a "template-generating" product, in my assessment.
- Data legitimacy matters in all three regimes: DPIIT limits to "lawfully accessed" works; Bartz penalised pirated acquisition; EU TDM requires lawful access and respecting opt-outs (from model knowledge of Art 3/4 DSM, not verified here). Extraction from cache or by automation (ToS s.6 item 9) is a weak "lawful access" story. Using platform materials outside their licence undermines it.
- Jurisdiction: a team in India training in India is primarily under Indian law for copyright (interim ANI ruling favourable but not final; DPIIT licence proposal would add royalty obligations if enacted); selling in the US/EU exposes the product to those regimes for output-side claims, and the EU AI Act GPAI copyright-policy duties may apply to model providers (not researched).
- Template arrangements: a short template's sequence of cuts/effects is arguably thin; the originality in effect choice and arrangement could attract protection as a compilation/audiovisual work in a particular instance, but I found no case law (see Gaps). Strongest protectable elements are the creator's footage, music and distinctive text/graphic assets, not timing.

### Gaps
- No case law found on copyrightability or infringement of video-editing templates, transitions sequences or "editing style". Needs counsel / targeted research (US Copyright Office compendium on short audiovisual works, Indian case law on format rights).
- Third Circuit decision in Ross: not confirmed.
- EU AI Act Art 53 GPAI copyright-policy obligations and Art 4 DSM opt-out specifics: not researched; and whether a template-generating model counts as GPAI is unclear.
- Delhi HC judgment text not read; reporting is secondary and descriptions of reasoning differ.
- China AI-training/copyright rules (generative AI Interim Measures) not researched.

## 6. Practical risk ranking of data routes and mitigations

### Takeaway
Risk rises sharply as the data stops being yours: own footage and own edits (lowest) < synthetic data < carefully scoped licensed-template experiments < public research datasets (licence unclear) < extracting cached template packages < downloading creators' reels (highest). The "templates with own footage" route is lower than a scrape but still carries ToS and Materials-License exposure, so it needs written permission or a narrow use.

### Cited Findings
- Edit3K: paper says code and dataset released at github.com/GX77/Edit3K; about 3,094 editing components, 618,800 videos in six categories (effects, animation, transition, filter, sticker, text); raw materials from ImageNet / ImageNet-Vid. The repo shows an MIT licence for the code; the repo README states no licence for the dataset and does not say whether effects were rendered from a commercial editor. — [arXiv Edit3K](https://arxiv.org/html/2403.16048v2); [Edit3K repo](https://github.com/GX77/Edit3K)
- AutoTransition: videos "extracted from the video editing template" on online platforms; only links released; no licence stated for code or data; follow-up AutoTransition++ (6k videos with style categories) cited in V-Trans4Style. — [AutoTransition repo](https://github.com/acherstyx/AutoTransition); [arXiv V-Trans4Style](https://arxiv.org/abs/2501.07983v1)
- rea-capcut README advises "Use media you own or can redistribute." — [rea-capcut README](https://github.com/Xiangyu-CAS/rea-capcut)
- Materials License: non-commercial vs Dual Use materials, per-export licence; edits "outside the Platform" prohibited. — [Materials License](https://www.capcut.com/clause/materials-license-agreement)

### Inferences
Ranked by my assessment (1 = lowest risk):
1. Own footage edited by own team in CapCut: low. Remaining issues: use only Dual Use or no platform materials, or treat every exported video as non-commercial-licence-bound; the ToS/Materials License do not mention training. Safest if (a) team members are employees with IP assignment, (b) music is excluded or cleared, (c) you avoid Non-commercial-only effects, or (d) you obtain written confirmation from ByteDance.
2. Synthetic data from own renderer (own routes): lowest if renderer and parameters are your own; moderate if you seed distributions from copied template parameters (laundering risk). Rank this as 1-equal with route 1.
3. Templates with own footage: medium. You own the footage; the template arrangement and its built-in materials belong to others. The ToS s.6 prohibitions are triggered by automation and by RE, not by hand-use; the hazard is bulk, systematic copying of third-party template structures and training a competing model. Get a licence.
4. Public datasets (Edit3K, AutoTransition): medium-high and unclear. Edit3K code is MIT but dataset licence not stated in the README and upstream sources include ImageNet (research-only terms, unverified here); AutoTransition has no licence and its data originate from platform templates. Both are research artefacts; commercial use is unlicensed by default.
5. Extracting template packages from CapCut cache: high. Breaches ToS s.6 (bypass/automated access/RE), Materials License s.4 (editing/use outside Platform), potentially 1201(a) if access controls/encryption are circumvented, and is outside 1201(f)'s narrow interoperability purpose; weak "lawful access" story for AI-training exceptions.
6. Downloading creators' reels: highest. Third-party copyright (footage, music, creators' works) plus platform ToS of the hosting site; no licence; bears the full infringement risk and invites takedown, and extraction of editing parameters from finished video adds no protection.

Mitigations:
- Get written permission or a commercial data-licence from ByteDance/CapCut (or a partnership); failing that, ask counsel to review a narrow "own footage + own editing" corpus.
- Build primarily on route 1 and 2 data; use real templates only for structure inspiration, not bulk copying; keep a documented, dated provenance log per training sample (source, licence, who edited, which materials were used).
- Exclude music, non-commercial materials and any creator-supplied clips from the corpus; store only parameters you own (e.g. your own taxonomy of cut times, easing curves) and not CapCut's asset IDs or bitmaps.
- Do not use automated bulk scraping or decryption; keep dated snapshots of ToS/Materials License versions; re-check before each data-collection run since terms change (CapCut changed ToS in June 2025 and April 2026).
- Add output-side controls: similarity/regurgitation tests so generated templates do not replicate a specific third-party template; do not use CapCut's trade names or assets in the product.
- Choose the governing assumptions: Singapore law governs the ToS; seek counsel in Singapore/India, and in China for JianYing.
- If training for commercial release, watch the DPIIT hybrid licence (royalties on commercialisation) and Third Circuit/CJEU outcomes.

### Gaps
- Edit3K Hugging Face dataset card/licence not retrieved; ImageNet terms not verified.
- AutoTransition Hugging Face card/licence not retrieved.
- No evidence found on how ByteDance enforces its ToS against dataset builders (no lawsuits found); lack of precedent is not safety.
- The ranking is my judgment, not drawn from a source; counsel should validate.
