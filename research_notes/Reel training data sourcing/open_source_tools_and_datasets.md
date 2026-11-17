# Open-source tools and public datasets for (reel video, exact edit-structure label) training pairs

Research date: 2026-11-15. Scope: beyond REA, rea-capcut and FilmCraft. Facts carry a source link. Inferences are in separate sections. Repo "last push" dates and licence tags come from the GitHub REST API (`api.github.com/repos/<owner>/<repo>`) queried on 2026-11-15. A licence tag on a repo covers code, not necessarily data.

## Key question 1: Which tools can turn a CapCut/JianYing project into a machine-readable timeline with transitions, text animations and effects intact?

### Takeaway
The only reliable route found is that a plaintext draft is itself the timeline. That means CapCut International drafts and JianYing 5.9.x or earlier drafts, where `draft_content.json` is readable JSON. Documented schema: capcut-cli's `docs/draft-schema` (MIT). No tool found converts a draft to OTIO, FCPXML or EDL while keeping transitions, text animation and effects. OTIO has no effect or text model, and capcut-cli's OTIO export drops text tracks by default. Most of the active "CapCut API" projects are writers, not parsers. JianYing 6.0+ drafts are AES-encrypted, and no maintained open decryptor was found.

### Cited Findings

#### A1. Tool-by-tool (Part A)

**pyJianYingDraft (GuanYixuan)**
- Python library to generate and export JianYing drafts. Licence Apache-2.0, about 4.9k stars, 735 forks. Latest push 2026-10-14 (GitHub API). — [GitHub README](https://github.com/GuanYixuan/pyJianYingDraft)
- Compatibility tables cover JianYing 5.9 and 10.8. Batch export (UI automation) works only up to JianYing 6.8 and only on Windows. Linux/macOS can generate drafts and use template mode but cannot auto-export. — [README](https://github.com/GuanYixuan/pyJianYingDraft)
- Features listed: video trim, speed, keyframes, masks, chroma key, blend modes; text styling and animations, SRT import; effects, filters, transitions; per-track effects and filters. — [README](https://github.com/GuanYixuan/pyJianYingDraft)
- Read side is "template mode". It loads an existing `draft_content.json`, then replaces materials or text, or imports tracks. It also extracts resource IDs for stickers, text bubbles and flower text. Imported template tracks cannot have transitions, effects or segments added to them. Newer JianYing `draft_content.json` is often not plaintext, and template features then need a custom `fallback_loader`. — [README](https://github.com/GuanYixuan/pyJianYingDraft)
- It is a writer first. Template mode is a replace/import tool, not a general draft-to-timeline parser (the README describes no full-timeline dump API; stated gap, see below).

**pyCapCut (GuanYixuan)**
- Sibling project for CapCut International. About 752 stars, 34 commits, no releases listed. Last push 2026-10-16. GitHub API returns no licence tag, and the README gave none, so licence is unknown. — [GitHub README](https://github.com/GuanYixuan/pyCapCut)
- README "verified version" column mostly lists CapCut 8.2.0 or 9.5.0.4050. Automatic export is not supported. Template mode needs a plaintext `draft_content.json`. The README announces a breaking 0.1.0 and says to pin `pycapcut==0.0.4` for current behaviour. — [README](https://github.com/GuanYixuan/pyCapCut)

**VectCutAPI (formerly CapCutAPI, sun-guannan)**
- Python HTTP server (port 9001) plus MCP server that generates new drafts via pyJianYingDraft. Apache-2.0. About 2.4k stars. Last push 2026-11-07. Cloud render code is not open-sourced. — [GitHub](https://github.com/sun-guannan/VectCutAPI); [search summary](https://docsearch.algolia.com/mcp/docs/repo/sun-guannan/vectcutapi)
- README lists transitions, effects, text animation, keyframes with easing. Output templates chosen by `draft_profile`: `capcut_legacy`, `jianying_legacy`, `jianying_pro_10`. The README does not describe reading existing drafts. Needs Python 3.10+, FFmpeg, and the desktop app. — [README](https://github.com/sun-guannan/VectCutAPI)
- Several forks and MCP wrappers share the name (huscpro, tginart, ashreo CapCutAPI; Atx-Guy/capcut-mcp-server needs VectCutAPI running). I only saw them in search hits. — [search results](https://github.com/Atx-Guy/capcut-mcp-server)

**capcut-cli (renezander030)**
- Zero-service CLI that reads and writes `draft_content.json` directly, for CapCut and JianYing (`--jianying` flag). MIT. About 1.2k stars, 307 commits. Last push 2026-11-15. Latest release 0.34.0 dated 2026-11-14. — [GitHub](https://github.com/renezander030/capcut-cli); [CHANGELOG](https://raw.githubusercontent.com/renezander030/capcut-cli/master/CHANGELOG.md)
- Commands include `info`, `tracks`, `segments`, `texts`, `lint`, plus add/edit commands for transitions, masks, text/image animations, easing; `detect-scenes`, `detect-silence`; `render` (an ffmpeg proxy preview). Effects commands are limited to `sfx`, `chroma`, `matting`. — [README](https://github.com/renezander030/capcut-cli)
- Version matrix: CapCut 6.2.8 is fixture-tested. 8.7.0 has a storage-shape fixture. 7.9/8.4.0/9.x are reported, not fixture-tested. CapCut 10.x is write-guarded (reports say new builds reject tool-written drafts). JianYing 5.9.x is community-reported compatible. JianYing 6.0+ is the "encrypted-draft era": `capcut decrypt` detects encryption but does not decrypt. — [version-support.md](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/version-support.md)
- Encryption doc: JianYing 6.0+ stores `draft_content.json` as an AES-encrypted binary payload; CapCut International is not encrypted (single source, the same project). Alternatives given: pin JianYing 5.9.x, use CapCut International, or see community references (pyJianYingDraft issue #142, duoec/duo-video), which are out of scope for the tool. — [jianying-encryption.md](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md)
- Writing is not blocked by encryption. JianYing 9.0.0 (Windows) accepted a tool-written plaintext draft and then re-encrypted it on close. JianYing 11.4.0 (macOS) upgrades plaintext drafts in place. — [version-support.md](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/version-support.md)
- OTIO: CHANGELOG 0.22.0 says OTIO has no title/subtitle schema, so the export dropped every text track. Text is skipped and reported by default. With `--captions markers`, captions become OTIO markers. The changelog gave no statement on transitions, effects or keyframes in the export. — [CHANGELOG](https://raw.githubusercontent.com/renezander030/capcut-cli/master/CHANGELOG.md) (I read only the first 100k of about 209k characters)
- Draft schema docs (the best public one found): `00-overview` through `05-version-differences`, covering tracks/segments, materials, keyframes and animations, effects/filters/stickers/transitions/masks, and CapCut 167 vs 169 and JianYing differences. In this schema a transition is a reference on the outgoing segment of an A to B pair, in `extra_material_refs[2]` (a slot shared with `common_mask`). Speed is a peripheral material attached via `extra_material_refs`. Keyframes sit in `keyframe_graph_list` and in segment `common_keyframes`. Text styling is embedded escaped JSON. Text in/out animation durations must fit inside the segment. — [schema overview](https://cdn.jsdelivr.net/npm/capcut-cli-david@1.14.1/docs/draft-schema/00-overview.md) (read via a fork's npm copy; the upstream docs folder is at [github.com/renezander030/capcut-cli/docs/draft-schema](https://github.com/renezander030/capcut-cli))
- A fork, capcut-cli-david, states JianYing 6+ is unsupported because the on-disk file is encrypted. — [fork compatibility doc](https://cdn.jsdelivr.net/npm/capcut-cli-david@1.14.1/COMPATIBILITY.md)

**capcut-mate (Hommy-master)**
- FastAPI JianYing draft automation service with a desktop client. Apache-2.0. About 2.2k stars, 703 commits, no releases listed. Last push 2026-11-14. — [GitHub](https://github.com/Hommy-master/capcut-mate)
- Adds videos, audio, images, stickers, subtitles, effects, masks, keyframes, text styles and animations. Has `create_draft`, `save_draft`, async `gen_video` (cloud render). The README does not list supported app versions. `get_draft` returns "draft file list and detailed information"; whether it parses arbitrary local drafts is not stated. — [README](https://github.com/Hommy-master/capcut-mate); [third-party API summary](https://developer.aliyun.com/article/1739963)

**ffcine-import (Rust crate)**
- Reads CapCut/JianYing drafts from `draft_content.json` or `draft_info.json`. Apache-2.0. Version 0.4.0 listed 2026-11-07. It refuses encrypted drafts (JianYing >5.9). There is no official spec, so its structure follows pyJianYingDraft and pyCapCut. The page does not say whether transitions, effects or text are parsed. — [docs.rs](https://docs.rs/ffcine-import)

**jianying-headless (mcncarl)**
- Source-available controller that builds JianYing drafts from a JSON plan and then drives the desktop app's local render to export an MP4. Pinned to Apple Silicon macOS 26+ and JianYing Pro 11.4.2. Non-commercial licence, commercial use needs written authorisation. Source is a news article dated 2026-09-18. The GitHub API returned "Not Found" for `mcncarl/jianying-headless` on 2026-11-15, so the repo may be renamed, private or removed. Treat as unverified. — [article](https://hermes-ai.net/news/jianying-headless-lets-coding-agents-build-editable-video-drafts-from-json/)

**OpenCut (OpenCut-app/OpenCut)**
- Free open-source editor billed as a CapCut alternative. MIT. About 98.4k stars. Last push 2026-09-24. The README says it is being rewritten and recommends `opencut-classic`. It states nothing about project file format or timeline export. — [GitHub](https://github.com/OpenCut-app/OpenCut)

**Older/other**
- JianYingDraft.PY (older PyPI package, forked from an unmaintained project) and notinmood/JianyingDraft.PY exist. — [PyPI](https://pypi.org/project/JianYingDraft.PY/0.1.1); [search summary](https://github.com/GuanYixuan/pyJianYingDraft)
- JianYing MCP server (hey-jian-wei/jianying-mcp) lists pyJianYingDraft as its main dependency. I saw it only as a search hit. — [listing](https://claudemarketplaces.com/mcp/hey-jian-wei/jianying-mcp)

#### A2. Open timeline interchange (Part C, partial)
- OpenTimelineIO feature matrix (v0.16.0 docs): adapters listed are OTIO, EDL, FCP7 XML, FCP X, AAF, RV, ALE, GStreamer. Transitions are supported in OTIO, EDL, AAF, GStreamer. Audio/video effects are supported only by GStreamer. Linear speed effects: OTIO, EDL (AAF read-only). "Fancy" speed effects: none. Markers broadly supported. Kdenlive is not in this matrix. — [OTIO feature matrix v0.16.0](https://github.com/AcademySoftwareFoundation/OpenTimelineIO/blob/v0.16.0/docs/tutorials/feature-matrix.rst)
- A search found no dedicated OTIO adapter for CapCut/JianYing in either direction. The only tie-in found is capcut-cli's export command. A Kdenlive OTIO adapter appears as a proposed KDE work item. — [KDE work item](https://invent.kde.org/multimedia/kdenlive/-/work_items/1916)
- A third-party blog claims there is no official CapCut editing/render API and that CapCut's terms ban automated scripts. — [wireflow blog](https://www.wireflow.ai/blog/capcut-api) (secondary; verify against CapCut's terms, not checked)

### Inferences
- For a ground-truth label per rendered reel, the cleanest pipeline is: author or collect plaintext drafts (CapCut International or JianYing 5.9), parse them with a custom reader built on the capcut-cli schema docs, then export the video from the app. Labels come straight from `transitions`, `video_effects`, `animations`, `common_keyframes` and `speed` materials. We would need to write the draft-to-our-JSON mapper; no tool does it.
- pyJianYingDraft, VectCutAPI and capcut-mate are best used as synthetic draft generators (Part A generation question), not as parsers. VectCutAPI and capcut-mate output depends on the installed app version and on effect-resource IDs that the app must be able to download. pyJianYingDraft notes that effect download can time out (README).
- Real "trending" reels from public CapCut templates usually are not available as drafts. Our own template-based pipeline would need the creators' drafts or the cloud-template payloads. This is a different problem from tool choice (not researched; see Gaps).
- OTIO is a poor target for our labels because its schema has no effects, text or keyframes. A custom JSON derived from the draft schema is the better label format. OTIO would only help for cut times and speed.
- Because encrypted JianYing 6+ drafts are unreadable, Chinese-market creator drafts mostly cannot be parsed. This favours CapCut International or JianYing 5.9 as the label source.

### Gaps
- Whether capcut-cli's OTIO export keeps transitions or effects: the changelog slice I read (first 100k of about 209k characters) does not say, and the README/docs page for `export-timeline` was not fetched.
- Whether pyJianYingDraft, pyCapCut or capcut-mate can dump a full parsed timeline (all tracks, transitions, effects) from an arbitrary draft, as opposed to template-mode replacement: not shown in any page read.
- The schema docs were read only at the overview level. I did not read `03-keyframes-and-animations.md` or `04-effects-filters-stickers.md`, so exact JSON keys for text in/out animation, effect IDs and filter names are not captured here.
- pyCapCut's licence: no licence tag and none in the README snapshot. Check the repo's LICENSE file.
- Reports that CapCut 10.x rejects tool-written drafts come from capcut-cli's own write guard. Not independently verified.
- Any working open-source JianYing 6+ decryptor: none found; capcut-cli points to pyJianYingDraft issue #142 and duoec/duo-video, which I did not open.
- Not researched: Kdenlive/MLT XML, Shotcut, OpenShot, Blender VSE, DaVinci Resolve (.drp, FCPXML), Rust/Go parsers other than ffcine-import, and any current OTIO plugin package.

## Key question 2: Which public datasets can we use right now, under what licence, and for which of our tracks?

### Takeaway
No public dataset gives full reel-level edit labels (cuts + transitions + text + effects + speed + camera + layout + grade). Edit3K (components, synthetic, gated) and AutoTransition (transitions, template-sourced, cc-by-4.0 tag) are the closest and both are derived from editing templates. The rest are single-track resources: shot boundaries (SHOT/AutoShot, ClipShots), cut types (MovieCuts, AVE), and QA-style editing-understanding benchmarks (VEU-Bench, VEBench). Most dataset licences are unstated; repo MIT tags and arXiv CC BY cover code/paper, not videos.

### Cited Findings

#### B1. Datasets that are close to our task

**Edit3K (ByteDance and UCAS, arXiv 2403.16048)**
- 618,800 rendered videos, 3,094 components, six types: video effect (888 comps, 177.6k videos), animation (176; 35.2k), transition (204; 40.8k), filter (228; 45.6k), sticker (1,000; 200k), text (598; 119.6k). 200 videos per component. — [arXiv v2](https://arxiv.org/html/2403.16048v2)
- Construction: components came from "a pre-defined set of editing components" in the free tool CapCut (paper does not say built-in library vs JianYing). Each video applies exactly one component to two source items drawn at random from ImageNet and ImageNet-VID (images or videos), each slot 2 s. For transitions, the transition lasts 2 s between the slots and each slot is shortened to 1 s. For other types the component spans both slots (about 4 s). — [arXiv v2](https://arxiv.org/html/2403.16048v2)
- Entirely synthetic. The label of each video is the single component applied. No reel-level or multi-edit annotations. — [arXiv v2](https://arxiv.org/html/2403.16048v2)
- Availability: the GitHub repo (MIT, 5 stars, last push 2025-02-25) has `edit_3k.json` and `edit_id2type.json` and points to Hugging Face `Gstar666/Edit3K`. The HF card lists 100K-1M size category, total 1.74 TB, no licence tag, and the dataset is gated (login and accept conditions). — [GitHub](https://github.com/GX77/Edit3K); [HF card](https://huggingface.co/datasets/Gstar666/Edit3K)
- The paper states no dataset licence. Source footage is ImageNet, which has its own terms. — [arXiv v2](https://arxiv.org/html/2403.16048v2)

**AutoTransition (ECCV 2022, arXiv 2207.13479)**
- 34,998 videos (29,998 train, 5,000 test), about 138.8k valid transitions; train 118,984 and test 19,869 transitions; about 3.97 transitions per video; average length about 15.8 s. — [arXiv](https://arxiv.org/html/2207.13479)
- Source: "publicly available video templates on editing softwares", collected from "online video platforms". The paper names neither the app nor the platform. Filtering: videos at most 60 s, filtered by likes and usage counts, videos with no transitions dropped, top 30 transition categories kept, each video must have more than two distinct transition types, no transition used more than six times. Each template provides a transition's category and its start and end time. Only the rendered output videos are available, not the original raw shots. — [arXiv](https://arxiv.org/html/2207.13479)
- Release: Hugging Face `yaojie-shen/AutoTransition`, tag cc-by-4.0, no gating notice, 52.9 GB, README empty, viewer fails. Files: `template_download.tar.gz.00` to `.12` (twelve parts of 4 GiB plus a 1.3 GB tail) and `transition_annotation_en_url_fixed.json` (55 MB). There is no file named `annotation.json`. — [HF card](https://huggingface.co/datasets/yaojie-shen/AutoTransition); [HF file tree](https://huggingface.co/api/datasets/yaojie-shen/AutoTransition/tree/main)
- The repo moved. `github.com/acherstyx/AutoTransition` returns "Moved Permanently" in the API and search mirrors show owner Yaojie-Shen. The README (as fetched) states no dataset size, annotation format or licence. — [GitHub (acherstyx path)](https://github.com/acherstyx/AutoTransition)
- Paper text notes only user-study footage came from copyright-free sources; the paper has no ethics or consent statement for template content. — [arXiv](https://arxiv.org/html/2207.13479)

**AutoCut (CVPR 2026, arXiv 2603.28366)**
- Advertisement-video editing with RVQ tokens; tasks are clip selection/ordering, script generation and music selection, with a production pipeline that assembles long-form video. Claims a large-scale ad dataset. Abstract gives no size, annotation or licence. Code link per a search summary: `github.com/AdAutoCut/Autocut`; the GitHub API shows 4 stars, last push 2026-06-07, no licence tag. Output granularity is clip level. — [arXiv abs](https://arxiv.org/abs/2603.28366); [search summary](https://qinsz01.github.io/qsz_academic/publication/2026-03-30-AutoCut); [GitHub API](https://github.com/AdAutoCut/Autocut)
- Not a fit for our label schema (no effects/transitions/text in the abstract).

**VEU-Bench (CVPR 2025, arXiv 2504.17828)**
- About 30,000 videos, 49,536 QA samples (45,154 train, 4,382 test; training set called VEU-50K). 10 dimensions, 19 tasks: intra-frame (shot size, angle, location, subject, type, colour), intra-shot (shot motion, speed), inter-shot (cut type, transition). — [arXiv](https://arxiv.org/html/2504.17828v1)
- Clips come from AVE, MovieCuts and AutoTransition. Labels come mostly from those sources plus HSV thresholds (colour) and ffmpeg (speed variants), with Gemini-1.5-pro filtering. Released models: Oscars. Project page `labazh.github.io/VEU-Bench.github.io`. No dataset licence stated. — [arXiv](https://arxiv.org/html/2504.17828v1)
- This means it is a re-labelling of other datasets as QA, not new edit annotations. The authors report a fine-tuned Vid-LLM ("Oscars") that beats open-source Vid-LLMs by over 28.3% accuracy on it, so it is a possible recipe for QA-style auxiliary training and evals (base model not checked). — [CVPR open access](https://openaccess.thecvf.com/content/CVPR2025/html/Li_VEU-Bench_Towards_Comprehensive_Understanding_of_Video_Editing_CVPR_2025_paper.html)

**VEBench (arXiv 2605.03276, May 2026)**
- 3.9K edited videos (257 hours), 3,080 human-verified QA pairs. TechRec: 885 videos with seven techniques (L-cut, J-cut, jump cut, smash cut, cutaway, invisible cut, match cut) and every transition timestamp annotated with three rounds of QA. OpSim: 783 reference and 2,217 candidate videos. Videos sourced from YouTube searches. Abstract text says "77 editing techniques" while the body describes seven; conflicting within the paper. No release link or dataset licence stated, only a project site `vebench.github.io`. — [arXiv abs](https://arxiv.org/abs/2605.03276); [arXiv HTML](https://arxiv.org/html/2605.03276)

#### B2. Shot-boundary and cut datasets

**SHOT / AutoShot (CVPRW 2023, arXiv 2304.06116)**
- 853 short videos with 11,606 shot annotations; test set of 200 videos with 2,716 boundary labels. Label file `kuaishou_v2.txt` (start and end frame of each shot per line). Videos on Google Drive and Baidu Pan. Repo MIT, 267 stars, last push 2023-04-18. No dataset licence stated. The README does not say whether cut vs gradual types are distinguished. The platform is not named in the README; the filename hints Kuaishou (inference). — [GitHub](https://github.com/wentaozhu/AutoShot); [CVPRW paper](https://openaccess.thecvf.com/content/CVPR2023W/NAS/html/Zhu_AutoShot_A_Short_Video_Dataset_and_State-of-the-Art_Shot_Boundary_Detection_CVPRW_2023_paper.html)
- Paper claims the only prior public short-video set (SVD) targets near-duplicate retrieval. — [CVPRW search summary](https://arxiv.org/abs/2304.06116v1)

**ClipShots (ACCV 2018, arXiv 1808.04234)**
- 4,039 online videos, each 1 to 20 min, with 128,636 cuts and 38,120 gradual transitions (dissolve, fade in/out, sliding in/out), double-annotated. Repo MIT, 129 stars, last push 2021-11-09. Videos on Baidu Pan and Google Drive. Licence of the videos not stated. — [arXiv](https://arxiv.org/pdf/1808.04234); [GitHub](https://github.com/Tangshitao/ClipShots)

**MovieCuts (ECCV 2022)** — 173,967 clips, ten cut types (expert-defined), best model 47.7 mAP. Repo `PardoAlejo/MovieCuts` MIT, last push 2025-04-17. Movie content, so video rights are third-party. — [arXiv listing](https://huggingface.co/papers/2109.05569); [GitHub API](https://github.com/PardoAlejo/MovieCuts)

**AVE, "The Anatomy of Video Editing" (ECCV 2022, arXiv 2207.09812)** — 5,591 movie scenes, 196,176 shots, more than 1.5M cinematography labels. Clips come from the MovieClips YouTube channel and users download them with yt-dlp. Authors state they do not own the clips. Repo `dawitmureja/AVE`, no licence tag, last push 2022-11-28. — [search summary of paper and repo](https://github.com/dawitmureja/AVE)

#### B3. Other datasets found
- RAI and BBC shot-boundary sets appear only as AutoShot generalisation benchmarks. Nothing else found about them. — [CVPRW search summary](https://arxiv.org/abs/2304.06116v1)
- Text in video: BOVText (bilingual, open-world video text; paper CC BY 4.0, code and data on GitHub; IEEE DataPort entry blank) and DSText V2 (140 clips, 7 scenarios; built partly on BOVText and RoadText-1k, so source licences stack). Neither is reel overlay text with animation labels. Dataset licences are not stated in the pages read. — [DSText V2](https://arxiv.org/abs/2312.01938v1); [BOVText](https://arxiv.org/abs/2112.04888)
- EditVerse and EditVerseBench (ICLR 2026) are generative video-editing, not edit-structure annotation. The benchmark has 100 stock videos, an `adobe-research-license`, and source videos cannot be redistributed. Not a fit. — [EditVerse arXiv](https://arxiv.org/pdf/2509.20360); [HF benchmark](https://huggingface.co/datasets/sooyek/EditVerseBench/blob/main/README.md)
- Other 2026 benchmarks (names only, not opened): TimelineBench (NeurIPS 2026, 100 agent editing tasks scored on project-state changes), Timeline-Bench (aggregator summary only, arXiv ID `2609.35143` unverified), AgenticVBench (2605.27705), CutVerse (2605.19484), CineBench (2604.10456), CoVEBench (2606). They evaluate agents or generative editing, not reel-to-labels recognition. — [search results](https://neurips.cc/virtual/2026/166886)

#### B4. Summary table (track fit)
| Dataset | Labels | Size | Licence status | Tracks it can feed |
|---|---|---|---|---|
| Edit3K | one component per video (effect, animation, transition, filter, sticker, text) | 618.8k videos, 1.74 TB | repo MIT; dataset no licence, HF gated | effect/transition/filter/text-style appearance; pretraining only, clips are 4 s and not reel-like |
| AutoTransition | transition type + start/end per template video | 34,998 videos, 138.8k transitions, 52.9 GB | HF tag cc-by-4.0; underlying templates third-party | transition track (30 classes) |
| SHOT / AutoShot | shot boundaries | 853 videos, 11.6k shots | repo MIT; data licence unstated | cut track on short video |
| ClipShots | cuts + gradual types | 4,039 videos | repo MIT; video rights unstated | cut and dissolve/fade track |
| MovieCuts, AVE | cut type, cinematography | 174k clips; 196k shots | repo MIT / none; movie clips third-party | cut-type, shot size/angle/motion; film domain, not reels |
| VEU-Bench | QA over cut, transition, speed, motion, colour | 49.5k QA | unstated | eval and auxiliary QA |
| VEBench | editing technique QA | 3.9k videos | unstated, no release link seen | eval |

### Inferences
- Edit3K's pipeline (one component per rendered clip, applied to stock footage) is the strongest published template for our synthetic data, but it has only one edit per clip. We would need compositing of many edits per reel to match our schema.
- AutoTransition's filters (top-30 classes, at most six uses per transition, at least three types) bias its transition distribution. Use it as additional transition supervision, not as a distribution estimate for real reels.
- The cc-by-4.0 tag on AutoTransition sits on an empty dataset card over videos that are renders of third-party templates. The tag should not be read as clearance for the video content. This is my reading; the pages do not state the rights position.
- Edit3K's repo is MIT but the HF dataset is gated with no licence, so commercial training use is unresolved. A written query to the authors is the practical way to settle it.
- Since the 800 real labelled reels target is not met by any open dataset, real labelled data must come from our own pipeline (Key question 3). Public sets mainly supplement the cut, transition and effect tracks and supply eval sets.

### Gaps
- The dataset sizes, label schema and licence of AutoTransition's annotation JSON were not inspected (only file names and sizes). The `_en` in the filename may indicate an English-language set; untested.
- Edit3K paper's supplementary details (open-set split of 1,547/1,547 components, per-component list) were not accessible. The GitHub `edit_3k.json` content was not opened.
- AutoCut's dataset: no size, annotation or licence found; code repo has no licence tag.
- VEU-Bench and VEBench licences and download availability: not found in the pages read. VEU-Bench project page was not opened.
- Not researched or not found: RAI and BBC shot-boundary dataset details, V2V-edit, MovieNet editing annotations, other effect/transition datasets, a template datasets survey (the one targeted search for template datasets returned only CapCut marketing pages), text-in-video licences beyond the two named, TikTok/Reels-specific edit datasets.
- Whether any of these sets was cleared for commercial or training use by their source platforms: no source found.

## Key question 3: How did the AutoTransition and Edit3K authors source their template data, and can we replicate that method?

### Takeaway
Edit3K's method is documented and replicable with a CapCut install: render each component alone on random footage. AutoTransition's method is only partially documented: it says "publicly available templates on editing software" and gives filtering rules, but names neither platform nor extraction mechanism, and says only rendered videos plus per-template transition category and start/end times were released. Neither pipeline outputs reel-level multi-edit labels. Our reel-level equivalent needs draft access (own-authored drafts, or open-format projects).

### Cited Findings
- Edit3K: each of 3,094 components is applied in isolation to two random ImageNet / ImageNet-VID images or videos, 2 s per slot, 200 renders per component, using CapCut. — [arXiv v2](https://arxiv.org/html/2403.16048v2)
- Edit3K: the authors state the result is more balanced than AutoTransition, since AutoTransition's online videos apply components "sparsely and unevenly"; it has about 29.75 times more components than AutoTransition. — [arXiv v2](https://arxiv.org/html/2403.16048v2)
- AutoTransition: templates were gathered from online video platforms; templates provide the transition category and start/end times as labels; raw shots not public; filtering rules as in B1. — [arXiv](https://arxiv.org/html/2207.13479)
- The HF release folder is named `template_download/<id>/<id>out_video` per the dataset viewer, and a `tools/download_videos.py` script exists in one repo mirror. — [HF card](https://huggingface.co/datasets/yaojie-shen/AutoTransition); [search summary](https://github.com/acherstyx/AutoTransition)
- Edit3K's rendering tool is the free CapCut app. Whether automation or manual rendering was used is not described in the pages read. — [arXiv v2](https://arxiv.org/html/2403.16048v2)

### Inferences
- Replicating Edit3K: feasible. Use pyJianYingDraft or pyCapCut or VectCutAPI to generate a draft with one component and a pair of slots, then export from the CapCut or JianYing desktop app. pyJianYingDraft's UI-automation export works on Windows up to JianYing 6.8. CapCut export must be done by hand (pyCapCut README). This scales to many thousands of renders only with some automation. Per-component effect resource IDs must be known, and the app may need to download them.
- Replicating AutoTransition: the mechanism is likely that the platform's public template page exposes the template's structure (transition type and timing) together with a rendered preview video. This is my inference. The paper does not say how the labels were obtained, and I could not confirm which platform. A replication would require locating the equivalent (e.g. CapCut template pages) and checking the platform's terms.
- Because the label source in AutoTransition is the template metadata and not a vision model, the labels are exact for the template's own transitions. A reel produced from a template with the user's own footage has labels that match the template unless the creator changed them. Our own pipeline could mimic this by using templates' draft payloads, if obtainable.
- Rights risk: template previews are third-party content. The cc-by-4.0 tag on the HF set does not establish clearance (inference).

### Gaps
- Which platform AutoTransition used, and how its transition labels and times were obtained: not stated in the paper text fetched or in the README. (The introduction and appendix were not fully read.)
- Whether Edit3K authors used CapCut's built-in assets, templates, or JianYing, and how they automated rendering: not stated.
- Whether CapCut/JianYing template pages expose machine-readable structure for public templates: not researched.
- Any CapCut terms-of-service position on scraping or automating renders: only a secondary marketing blog was found.

## Sources (primary or near-primary)
- pyJianYingDraft: https://github.com/GuanYixuan/pyJianYingDraft
- pyCapCut: https://github.com/GuanYixuan/pyCapCut
- VectCutAPI: https://github.com/sun-guannan/VectCutAPI
- capcut-cli: https://github.com/renezander030/capcut-cli
- capcut-mate: https://github.com/Hommy-master/capcut-mate
- Edit3K paper and repo: https://arxiv.org/html/2403.16048v2 ; https://github.com/GX77/Edit3K
- AutoTransition paper and HF: https://arxiv.org/html/2207.13479 ; https://huggingface.co/datasets/yaojie-shen/AutoTransition
- OTIO feature matrix: https://github.com/AcademySoftwareFoundation/OpenTimelineIO/blob/v0.16.0/docs/tutorials/feature-matrix.rst
