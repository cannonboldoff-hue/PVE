# CapCut / JianYing template-to-(video, project file) workflow at ~800 reels

Scope note: as of Nov 2026. Most sources are community or third-party tool docs; official CapCut help pages are marked "OFFICIAL". Where a claim is from a single secondary source it is flagged. I did not research ways to break encryption of protected template drafts (legal/ToS risk, and a search for it was declined by the search tool); only what tools openly document is reported.

## 1. How do templates work (desktop vs mobile vs JianYing)? Does using one yield a normal editable draft with the full edit in draft_content.json, or a locked package?

### Takeaway
The trending-template library is a mobile feature; CapCut desktop (Win/Mac) officially has no access to the community/TikTok template library (only a few official templates), and a template applied on mobile is a replace-your-clips editing mode, not a normal draft. Template drafts are locked unless the creator enabled paid unlock ("Edit More"), and even then the creator's media stays protected. JianYing similarly separates 模板 (locked, apply-only) from 剪辑 (editable) drafts. So "use trending template, then read the full edit from the project file" is not a reliable path.

### Cited Findings
- OFFICIAL (CapCut help): on Desktop (Windows/macOS) "The desktop version does not support accessing the CapCut template library"; only a few official offline templates, no TikTok/mobile templates, no community gallery, no copying/sharing template links. You replace placeholder media and export via File > Export. Mobile has full template support (Template tab > Use template > pick media > Preview > Edit to replace/crop > Export). Web has only a limited official set, no trending/community templates. — [How to Use and Export Templates in CapCut?](https://www.capcut.com/help/use-and-export-templates-in-capcut)
- OFFICIAL, CONFLICTING: a help page dated Jan 12, 2026 gives desktop steps "Templates tab > Browse/search > Use Template > opens in the desktop editor; edit stickers, text, and music", and says "Templates can be edited, but the creator's original media (video/photos) may be protected." — [How to Use Templates in CapCut?](https://www.capcut.com/help/use-template). This contradicts the narrower statement above; I could not reconcile which is current. A search summary also noted a March 2026 help page describing a desktop Templates home tab with featured/trending templates (unconfirmed by me; I only fetched the other pages).
- OFFICIAL (Mar 25, 2026): "Some templates are designed for mobile only and won't open on the desktop version"; fix is to update desktop, or "Open the template on your phone and export, then continue editing on PC if needed." — [Why Can't I Open a Template in CapCut on PC?](https://www.capcut.com/help/open-a-template-in-capcut-pc)
- OFFICIAL: Template monetization lets a user "pay a one-time fee to unlock a template's draft and customize it freely"; subscribers can use "Edit More" on paid templates. Customizable: stickers, font styles, music; "the original creator's media is protected". If the creator has not enabled monetization, users cannot edit the draft. Only the CapCut App is named for the creator flow. — [What Is Template Monetization in CapCut?](https://www.capcut.com/help/what-is-template-monetization)
- OFFICIAL: the desktop app has no interface to mark clips as replaceable when creating a template; workaround is to finalize on desktop, export the video, and re-import into the mobile app or web editor. — [How to Set Replaceable Material Clips in CapCut?](https://www.capcut.com/help/how-to-set-replaceable-material-clips) (as summarized by search; page not fetched directly)
- Mobile-to-desktop sync: per a search summary of CapCut help, project files sync via cloud but some visual elements depend on mobile-only rendering engines. Treat as unverified (summary only). Source list: [CapCut Template PC: Desktop Workflow and Limits](https://www.nemovideo.com/blog/ai-video-workflows/capcut-template-pc-workflow-limits) is a third-party SEO page; low reliability.
- Community (CapCut-skill doc): "Projects downloaded from CapCut's template library have encrypted draft_info.json files" (described as base64 plus proprietary ByteDance encryption) and "cannot be modified"; only locally created projects can be read/written. Single secondary source, no CapCut version given. — [capcut-editor skill (duckyman-ai)](https://www.skills.sh/duckyman-ai/agent-skills/capcut-editor)
- JianYing mobile (community, May 2022, old): under 本地草稿 there are 剪辑 / 模板 / 图文 / 脚本 sub-menus. 模板 drafts (from 剪同款) can only be applied, not modified; paying (about 6 yuan in the example) unlocks them and moves them to 剪辑. Only 剪辑 drafts sync phone<->PC via 剪映云; downloading a 模板 draft on PC gave "not supported". — [Toutiao article](https://www.toutiao.com/zixun/7503702163357452322/). Old (2022); current behaviour not re-verified.
- JianYing PC (community CSDN): templates exist as draft folders; copy into the "JianyingPro Drafts" folder and they appear in local drafts where you can replace materials. Templates made on the phone app may not play correctly or lose elements on PC; phone app cannot import templates directly but can receive them via JianYing cloud. The page shares templates via netdisk links (provenance unclear; not an official channel). — [CSDN tutorial](https://adg.csdn.net/694cf2ac5b9f5f31781a9dbc.html)
- The JianYing PC "unfold template" button I was asked about: I found no official documentation of an "edit template"/"convert template to project"/"unlock" action beyond the paid unlock/Edit More above. A compound-clip "解除复合片段" (Shift+Alt+G) exists on JianYing PC but that is for user-made compound clips, not template unlocking — [Bilibili opus](https://www.bilibili.com/opus/913745521937481736) (via search summary).

### Inferences
- For community/trending templates, the exported mp4 is obtainable, but the exact edit labels are generally not: the template stays a locked template draft (encrypted per one source), and the creator's media is protected even after unlock.
- Mobile app drafts are not stored as an accessible draft_content.json (see Q2/Q3), so the mobile template path gives video-only output unless you do your own labeling.

### Gaps
- No primary source on the internal template package format, cache location, or file types (searches returned only generic CapCut cache paths, e.g. `%LocalAppData%\CapCut\User Data\Cache`, per [blog.usro.net](https://blog.usro.net/2025/08/capcut-folders-cache-mac-and-pc-paths/), which is a third-party blog and does not mention templates).
- Could not confirm whether the current desktop "Templates tab" (Jan/Mar 2026 help pages) exposes trending/TikTok templates, or whether those open as locked templates.
- Could not confirm a current in-app "edit template / unlock" flow on CapCut desktop or JianYing PC.

## 2. Is CapCut International draft_content.json plain JSON in current desktop versions? JianYing 6+ encryption: versions and workarounds

### Takeaway
JianYing 6.0+ encrypts the draft (community consensus: pyJianYingDraft, capcut-cli). CapCut International is reported plain JSON for user-created projects in versions 8.x through 9.x by tool authors who tested fixtures, but there are conflicting reports of encrypted/mirrored files, especially for template-library downloads, and the main timeline file moves around between versions (draft_content.json vs draft_info.json vs template-2.tmp vs Timelines/<id>/draft_info.json).

### Cited Findings
- JianYing 6.0+ stores the draft as an "AES-encrypted binary payload instead of plaintext JSON"; "CapCut International is **not** encrypted — only JianYing." Maintainer chose "detect, do not decrypt"; suggested options: pin JianYing to 5.9.x with auto-update blocked, use CapCut International, or see community references (pyJianYingDraft #142, duoec/duo-video). — [capcut-cli docs: jianying-encryption](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md)
- pyJianYingDraft docs: "剪映6+版本对draft_content.json文件进行了加密, 故(模板)功能仅支持剪映5.9及以下"; generation of drafts supports 5+ — [PyPI pyjianyingdraft](https://pypi.org/project/pyjianyingdraft/), [Gitee mirror](https://gitee.com/lettfc/pyJianYingDraft). The current GitHub README softens this: in new versions draft_content.json "往往不是可直接读取的明文 JSON" (often not directly readable plain JSON); template loading is OK on 5.9 and "partial" on 10.8, needing `DraftFolder(..., fallback_loader=...)` — [GuanYixuan/pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)
- capcut-cli compatibility table: CapCut 8.x desktop (Win/Mac) plain JSON, 9 fixtures (mac 8.2.0; Windows 8.5.0, 8.6.0); CapCut 7.x and earlier presumed plain, untested; CapCut 9.x+ presumed plain, untested; JianYing 5.x presumed plain; JianYing 6.x+ encrypted, "We will not ship a decryption layer"; CapCut Mobile uses a different storage layout, "draft_content.json is not the source of truth" — [COMPATIBILITY.md (capcut-cli-david 2.5.0)](https://cdn.jsdelivr.net/npm/capcut-cli-david@2.5.0/COMPATIBILITY.md)
- Which file holds the timeline varies: CapCut 8.7+ "readable template-2.tmp / draft_meta_info.json timelines take precedence"; CapCut 9.2.8-beta4 (macOS) reads `Timelines/<main_timeline_id>/draft_info.json` (root files are "legacy mirrors", so root-only writes do not reach the app); CapCut 9.0.0 (Windows) project can be plaintext draft_content.json with the app encrypting legacy mirrors on close; CapCut 10.x Mac primary file "reported" as draft_info.json with no fixture. Write guard refuses beyond 9.x. — [capcut-cli version-support.md](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/version-support.md). This is the likeliest explanation of "reports conflict on 10.x": the file you read may be a stale/legacy mirror or a different filename.
- pyCapCut (CapCut-international port of pyJianYingDraft): plaintext template loading validated on CapCut 8.2.0; other features' versions listed 9.5.0.4050; "Automated export is currently unsupported" — [PyPI pycapcut](https://pypi.org/project/pycapcut/)
- Community report that CapCut projects were plain JSON in early 2025 (asking whether only the free version is encrypted); the repo owner mentioned announced encryption "starting April 2024" for some builds — [emosheeep/capcut-export issue #3](https://github.com/emosheeep/capcut-export/issues/3). Anecdotal, unresolved.
- JianYing 9.1.0 (Sep 2025): after saving a draft as a preset ("保存为我的预设"), the preset folder contains an unencrypted draft_content.json that can be edited — [pyJianYingDraft issue #142](https://github.com/GuanYixuan/pyJianYingDraft/issues/142). The only comment points to an external online decryption site (unverified). Issue open, no maintainer reply visible.
- JianYing "invalid file name" nuance: writing pre-6.0 name `draft_content.json` into a JianYing 11.4 draft triggers "草稿内容已损坏"; app-authored name since 6.0 is `draft_info.json` — [capcut-cli jianying-encryption](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md)
- JianYing version numbering for 6.x+ in sources: 6.8 (last with working batch export), 7+ (export controls hidden), 9.1.0, 9.6.0 (duo-video validated), 10.8, 11.4.0 — see Q5.

### Inferences
- For the CapCut Intl desktop, plan on: locally created or programmatically generated drafts are readable as JSON in 8.x-9.x; verify per-install by checking which of draft_content.json / draft_info.json / template-2.tmp / Timelines/*/draft_info.json parses. Pin a CapCut desktop version and disable auto-update.
- JianYing 5.9 pinning is a workaround only for reading, and 5.9 lacks some newer effects/transitions library content.

### Gaps
- No primary-source (ByteDance) statement on encryption in any version.
- No confirmation for CapCut Intl 10.x (Windows or Mac); capcut-cli lists it as "reported, no fixture".
- Exact CapCut version at which template-library downloads become encrypted is not documented; only one secondary source asserts it.
- pyJianYingDraft #142's real discussion on the algorithm was not accessible; I did not pursue decryption.

## 3. Where to discover trending templates at scale; can IDs/links be listed programmatically?

### Takeaway
There is a public CapCut web gallery with template detail pages and usage counts, plus app share links; no documented official API to list templates. Third-party scraper actors exist but claims are unverified and scraping may breach ToS. TikTok template links open in the mobile app only.

### Cited Findings
- URL patterns (third-party guide): web gallery capcut.com/template, categories capcut.com/template/{category}, single template capcut.com/template-detail/{name}/{id}, app share links capcut.com/t/{code}; TikTok template links only work in the mobile app; some templates region-limited — [hooked.so guide](https://www.hooked.so/capcut-templates). Secondary source.
- CapCut explore pages list templates with usage counts (e.g. "152.8K"), no ID API documented — [CapCut explore example](https://www.capcut.com/zh-hk/explore/%E5%89%AA%E6%98%A0%E7%AF%80%E5%A5%8F%E6%A8%A1%E6%9D%BF/7513135763627935745)
- Third-party Apify actors claim to return template titles/authors/usage counts/covers from template URLs — [logiover/capcut-templates-downloader](https://apify.com/logiover/capcut-templates-downloader), [scrapers-hub/capcut-video-downloader](https://apify.com/scrapers-hub/capcut-video-downloader). Unverified; sample outputs look illustrative.
- The only "Template API" hit is CapCut Commerce Pro marketing, no endpoint docs — [commercepro.capcut.com](https://commercepro.capcut.com/templates/template-api)
- OFFICIAL: desktop has no template discovery or link sharing; web has only limited official templates, "no trending or community templates"; full TikTok-integrated experience is mobile only — [How to Use and Export Templates](https://www.capcut.com/help/use-and-export-templates-in-capcut)
- JianYing: I found no source on programmatically listing JianYing 模板 IDs; community "template drafts" circulate as folders on netdisks ([CSDN](https://adg.csdn.net/694cf2ac5b9f5f31781a9dbc.html)), which raises licensing/provenance issues.
- CapCut terms: coverage focuses on the June 2025 ownership/licence update; I could not retrieve the "You may not" list to confirm an automated-access ban — [Dreamina/CapCut ToS](https://dreamina.capcut.com/clause/terms-of-service). One VectCutAPI-related source claims CapCut terms ban scripted access (secondary, unverified).

### Inferences
- Discovery at scale is feasible only via web scraping of public gallery pages or manual curation; that path gives preview videos and usage counts but not edit data. Template creators' rights apply to the template itself.

### Gaps
- No verified count of templates, no official list endpoint, no verified ToS clause on scraping.
- No verified source for JianYing template listing pages.

## 4. Can template -> draft -> export be automated? Tools, MCP servers, throughput per person-hour

### Takeaway
No official CapCut API. Community tools automate (a) draft generation (pyJianYingDraft, pyCapCut, VectCutAPI/CapCutAPI, CapCut Mate), (b) JianYing Windows UI batch export (works only up to JianYing 6.8), and (c) Android template use via ADB (capcut-auto). I found no measured throughput numbers anywhere.

### Cited Findings
- VectCutAPI (formerly CapCutAPI; Apache-2.0): Flask/HTTP + MCP server over pyJianYingDraft; `save_draft` produces a `dfd_` folder to copy into the CapCut/JianYing drafts dir; needs Python 3.10+, FFmpeg, CapCut/JianYing desktop; profiles `capcut_legacy`, `jianying_legacy`, `jianying_pro_10`; MCP editing agent, web client and cloud rendering are not open source — [sun-guannan/VectCutAPI](https://github.com/sun-guannan/VectCutAPI)
- CapCut Mate (Hommy-master): FastAPI + uiautomation; create_draft, add materials, keyframes, text animations; `gen_video` / `gen_video_status` for async rendering (cloud rendering / Electron client); no throughput or version support stated — [Hommy-master/capcut-mate](https://github.com/Hommy-master/capcut-mate)
- pyJianYingDraft batch export: `JianyingController.export_draft()`, Windows-only via uiautomation, works on JianYing 6.8 and below; 7+ hides required controls; resolution/framerate settable only on 6.8 and below; needs export permission (VIP/active subscription) or may loop forever. Linux/macOS: generation + template mode only; drafts must be exported on Windows JianYing — [GuanYixuan/pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)
- pyCapCut: "Automated export is currently unsupported"; open generated drafts in CapCut for Windows and export manually — [PyPI pycapcut](https://pypi.org/project/pycapcut/)
- capcut-auto: drives CapCut on multiple Android devices over ADB + uiautomator2, opens CapCut from template links; aimed at TikTok posting rather than data collection — [nedsion/capcut-auto](https://github.com/nedsion/capcut-auto)
- Third-party Chinese batch-export tool (魔晶软件) exports drafts from the JianYing draft grid; marketing pages, "强力导出" mode deletes drafts after export; Windows only; exported drafts need the same JianYing version — via [CSDN](https://adg.csdn.net/695234175b9f5f31781b3070.html) (search summary; low reliability).
- Other CapCut MCP servers exist (e.g. [Atx-Guy/capcut-mcp-server](https://github.com/Atx-Guy/capcut-mcp-server)), most wrap draft generation, not template use.
- CapCut-cli (CLI for reading/writing CapCut drafts; "detect, do not decrypt") — [renezander030/capcut-cli](https://github.com/renezander030/capcut-cli)

### Inferences
- No source documents unattended template-use automation on desktop; mobile ADB automation of "use template -> select clips -> export" is plausible (capcut-auto shows the pattern) but captures only the exported video, not exact labels.
- Throughput: no sourced figure. My rough estimate (not sourced, treat as guess): manual template-apply on mobile ~10-20 reels/person-hour, which makes 800 reels around 40-80 person-hours with no ground-truth labels; scripted draft generation plus UI export is limited by export time per reel (minutes each) rather than human time, but depends on pinning JianYing <=6.8 on Windows.

### Gaps
- No benchmarks, rate limits or success rates for any tool.
- No documentation that ADB template automation survives CapCut mobile updates or login/paywall changes.

## 5. Alternative: generate drafts programmatically with real CapCut effects/transitions and render in CapCut itself; is batch export possible?

### Takeaway
Yes for generation, partially for batch rendering. pyJianYingDraft/pyCapCut/VectCutAPI/CapCut Mate generate drafts using the app's real effect/transition/animation resource enums, and the exact label metadata is known by construction. Batch export is automated only on Windows JianYing <=6.8 (pyJianYingDraft); CapCut Intl needs manual or custom UI automation; cloud render options exist but are closed or paid.

### Cited Findings
- pyJianYingDraft supports local media with time control, constant speed only (no speed curves), keyframes, masks, chroma keying, background fill, blend modes; segment effects, filters, standalone effect/filter tracks; text styling, animations, bubbles, flower text, SRT import; transitions; enums `IntroType/OutroType/GroupAnimationType`, `TextIntro/TextOutro/TextLoopAnim`, `VideoSceneEffectType`, `VideoCharacterEffectType`, `FilterType`; `from_name()` fuzzy-matches names — [GuanYixuan/pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)
- Draft generation supports JianYing 5+; new-version drafts generate and most editing works (tested to 10.8); license-gated assets (VIP) may block export — same source.
- duo-video (Java SDK) generates JianYing drafts, reports 6,000+ official text-animation templates and validation on JianYing 9.6.0; generated drafts are offline with embedded resources — [CSDN article](https://damodev.csdn.net/6a43478610ee7a33f284794d.html)
- VectCutAPI/CapCut Mate: output `draft_profile` for CapCut vs JianYing layouts; Cloud render not open source (see Q4).
- Generated drafts require the app to open them; the capcut-cli note on write guards says root-only writes may not reach the app in CapCut 9.2.8-beta4 (Timelines/<id>/draft_info.json is read), so generation tools must target the right layout for the pinned version — [version-support.md](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/version-support.md)

### Inferences
- Data-quality tradeoff: programmatic drafts give exact labels but look synthetic (random effect combos) unless the generator is tuned to imitate real trending reel grammar; template-based reels look real but labels are lost. A hybrid: use trending-template reels as style references (video only) to author a generator whose parameter distribution matches them, then render the generator's drafts.
- Pin versions: JianYing 6.8 on Windows for auto-export (but its effect library is older); CapCut Intl 8.x for readable plaintext (but no auto-export).

### Gaps
- No verified end-to-end report of 800+ batch renders on CapCut Intl.
- Not verified whether effects/transitions requiring downloads (cloud resources) render correctly offline in batch.

## 6. What metadata does a draft contain that maps to our label fields?

### Takeaway
A readable draft is rich enough to label cuts, canvas/layout, text content and animations, effects, filters, transitions, keyframes and speed, via ID/name references into `materials`; the details live in capcut-cli's draft-schema docs and pyJianYingDraft enums.

### Cited Findings
- Top-level draft_content.json: `id`, `name`, `version` (e.g. 360000), `new_version` (e.g. "167.0.0"), `draft_type`, `duration`/times in microseconds, `fps`, `canvas_config` (`ratio`,`width`,`height`,`background`), `materials`, `tracks`, `keyframe_graph_list`; segments have `material_id`, `target_timerange` (start,duration), `render_index`, `clip`, `uniform_scale`, `common_keyframes`, `extra_material_refs` (slot index 2 polymorphic: transitions or common_mask) — [draft-schema 00-overview](https://cdn.jsdelivr.net/npm/capcut-cli-david@1.14.1/docs/draft-schema/00-overview.md)
- Version differences: CapCut UI 169.x stores transitions in the outgoing segment's `extra_material_refs[2]`; text animations via `material_animations` (cutcli: text only; CapCut UI: text and sticker); effects via `materials.video_effects[]` on an `effect` track (cutcli) vs filters via `materials.effects[]` on a `filter` track (CapCut UI); keyframes via `common_keyframes` and `keyframe_graph_list[]` — [05-version-differences](https://cdn.jsdelivr.net/npm/capcut-cli-david@2.5.0/docs/draft-schema/05-version-differences.md)
- Materials reachable via segments include speeds (one-to-one with the owning segment), canvases, texts, videos, audios — [00-overview](https://cdn.jsdelivr.net/npm/capcut-cli-david@1.14.1/docs/draft-schema/00-overview.md). The overview does not define transition/animation/effect field lists (covered in files 01/02/04 I did not retrieve).
- pyJianYingDraft: speed is constant only (no speed curve generation); text keyframes limited to position and size; template mode exposes `inspect_material` metadata extraction when the draft is readable.

### Inferences
- Likely mapping (from the schema notes, not verified against a fixture): cuts = adjacent video-segment `target_timerange`s; transitions = materials.transitions via extra_material_refs; text animations = material_animations (in/out/loop); effects = video_effects/effects with resource names; speed = materials.speeds linked to segments; camera/motion = keyframes plus clip transform; layout = canvas_config and clip transform; colour = filters/effects and adjust materials.
- Names in the draft are often resource IDs plus display names; a name-mapping table per app version will be needed, and CapCut Intl and JianYing use different effect libraries.

### Gaps
- Did not retrieve the per-material field docs (01-tracks-and-segments, 02-materials, 04-effects-filters-stickers) or inspect a real fixture.
- Speed curve (variable speed) storage not confirmed.
- Whether a template-derived draft would expose effect names is unconfirmed because template drafts are reported locked/encrypted.

## 7. Practical recommendations at ~800 reels (synthesis of the above; flagged as inference)

### Takeaway
Template-based collection looks like the weakest route for exact labels; programmatic generation on a pinned app version is the most reliable for exact labels. A small number of manually produced reels in the app (own edits, readable draft) could serve as a validation set.

### Cited Findings
- See Q1 (locked/protected templates), Q2 (encryption/version drift), Q4/Q5 (tool support). No additional sources.

### Inferences
- Route A (exact labels): generate drafts with pyCapCut (CapCut Intl 8.x plaintext) or pyJianYingDraft (JianYing 5.9-6.8 on Windows) and render with the app; for JianYing <=6.8 export can be scripted (`export_draft`), for CapCut Intl export would need custom UI automation or manual export.
- Route B (looks real, no labels): collect trending-template reels on a phone and rely on our own labeling pipeline; no edit file access.
- Route C (hybrid): use trending templates to define the style distribution, then render generated drafts; keep ~50-100 hand-made reels as a realism check.
- Check licensing: template creator rights, CapCut ToS on automation/scraping, and export watermark/VIP asset gating before committing to scale.

### Gaps
- No empirical test performed; all feasibility judgements rest on community docs.
- I did not install CapCut or inspect real drafts.
