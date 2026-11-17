# REA, rea-capcut (ReaCut) and FilmCraft: usefulness for building (reel video, edit-structure JSON) pairs from CapCut / JianYing projects

Research date: 2026-11-15. All repo claims were read via page fetches on that date. The fetch tool summarises pages with a small model, so quoted strings are as relayed, not byte-checked. Release dates on GitHub showed day+month only; year 2026 is inferred.

## What is REA, and what can it do for this pipeline?

### Takeaway
REA ("Reverse Engineer Anything") is a general MCP server that lets AI agents reverse-engineer binaries, apps, websites and runtime behaviour. It is not a CapCut/JianYing tool and cannot read, render or convert drafts. Its only relevance is that rea-capcut's author used it to study JianYing.

### Cited Findings
- REA stands for "Reverse Engineer Anything"; README tagline: "One MCP for reverse engineering across binaries, applications, and runtime behavior." Analysis runs locally. — [morluto/rea](https://github.com/morluto/rea)
- Install is `npx rea-agents setup`; supports Claude Code, Codex, Cursor, Gemini CLI, Grok Build and other MCP agents; "Your agent calls REA through MCP to inspect the target and trace relevant code." — [REA README](https://raw.githubusercontent.com/morluto/rea/main/README.md)
- Requires Node.js 22.x (>=22.23.4), 24.x (>=24.22.1) or 26.12.1+. Native analysis needs Hopper, Ghidra, IDA or Kuna installed. Windows Ghidra support is "experimental"; runtime capture covers Linux and macOS. — [REA README](https://github.com/morluto/rea)
- Target types listed: native binaries, JavaScript/Electron apps, .NET assemblies, websites, Android APKs, firmware, packet captures, process behaviour. — [REA README](https://raw.githubusercontent.com/morluto/rea/main/README.md)
- Licence: REA-authored code MIT; third-party material keeps its own licences; commercial tools (IDA Pro, Hopper, JEB) need their own licences. — [REA README](https://github.com/morluto/rea)
- Documented uses (none about video editors): DX-Ball sound-pan reconstruction, tracing a Notion Electron clipboard bridge, recovering a DOS bullet-ring angle calculation from TH04, turning recorded web app sessions into RL environments, building Linux desktop app environments for agents. — [REA README](https://github.com/morluto/rea)
- The README does not mention CapCut, JianYing or video editors. Releases page is empty; no version numbers or dates given (only "© 2026"). — [REA README](https://github.com/morluto/rea)
- Star count shown as 461.2k in the fetch, while the text cites a 400,000-star milestone. The number is surprisingly large and I did not verify it independently; treat as unverified.

### Inferences
- REA is a generic RE agent toolkit. For us it is only a method (point an agent at the JianYing/CapCut app to learn the draft schema and encryption), not a data tool.
- Using REA ourselves to break JianYing encryption would be a separate, legally and ToS-sensitive effort. I found no REA doc suggesting it ships any JianYing-specific capability.

### Gaps
- No release version/date for REA. Star count unverified.

## What can rea-capcut (ReaCut) do with CapCut/JianYing projects and templates?

### Takeaway
ReaCut is a macOS Apple-Silicon-only Electron video editor (v0.7.1 preview) with an experimental, lossy, one-way JianYing draft import. It decodes encrypted JianYing 11.x drafts (AES-256-GCM, tested on one build), but maps only basic clips and text. Transitions, effects, keyframes, curve speed and templates are explicitly not mapped, there is no draft write-back, and it cannot open downloaded template packages. It can export MP4/MOV but has no machine-readable timeline export aimed at labels beyond its own `.reacut` file.

### Cited Findings
- Description: "An independently implemented, open-source video editor informed by REA-assisted research into Jianying / CapCut"; research limited to authorised scope, no copied proprietary code or assets; not affiliated with JianYing/CapCut. — [rea-capcut README](https://github.com/Xiangyu-CAS/rea-capcut)
- Built with Electron, React, TypeScript and FFmpeg. "The project uses REA to study Jianying's interface behavior and local project formats, then independently implements an editor"; REA, Ghidra and Jianying are not runtime dependencies. — [README](https://github.com/Xiangyu-CAS/rea-capcut)
- Import claim: "Experimental Jianying import: converts basic clips from verified formats." Warning: "Complex text styles, effects and keyframes may be lost." — [README](https://github.com/Xiangyu-CAS/rea-capcut)
- "Writing back to Jianying format is unsupported" (README) and the interop doc says it provides no JianYing write-back; conversion is lossy and the original project is not modified. — [README](https://github.com/Xiangyu-CAS/rea-capcut), [CAPCUT_INTEROP.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/CAPCUT_INTEROP.md)
- Verified build: a local JianYing install with `CFBundleShortVersionString = 11.0.12922`, `CFBundleVersion = 11.1.0-beta3`, tested on two dedicated controlled projects. The doc says this does not prove compatibility with arbitrary JianYing versions, cloud drafts or other packaging. — [CAPCUT_INTEROP.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/CAPCUT_INTEROP.md)
- Formats handled: plaintext JSON "classic" drafts (`tracks`/`materials`); embedded AES-256-GCM payloads (key and IV derived from twelve shards inside the payload, remaining Base64 is ciphertext plus auth tag); modern project folders identified by `Timelines/project.json` with `timeline_layout.json` for the current timeline; classic folders try `draft_info.json` then fall back to `draft_content.json`. Import is refused if authentication fails or payload structure is unknown. — [CAPCUT_INTEROP.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/CAPCUT_INTEROP.md)
- Decoding uses Node.js standard crypto, independently implemented; it does not run JianYing native libraries, look up account credentials or call remote services. Browser build handles plaintext JSON only; encrypted payloads and project folders need the desktop bridge. — [CAPCUT_INTEROP.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/CAPCUT_INTEROP.md)
- Fields mapped: time ranges (microseconds to seconds: timeline start, duration, source in-point); base speed clamped 0.1-8x; linear volume; uniform scale, rotation, opacity, flip; position offsets (Y inverted); canvas size (fallback 1920x1080 if missing); media only via local absolute paths; text: basic content only, fonts/styles/layout use ReaCut defaults. — [CAPCUT_INTEROP.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/CAPCUT_INTEROP.md)
- Explicitly NOT mapped: keyframes, curve speed, complex effects, templates, transitions, cropping, reverse playback, special sound effects, canvas background; non-uniform scale becomes uniform. Out of scope: accounts, cloud projects, SaaS, API AI features. Missing media: references kept, user must relink, nothing downloaded. — [CAPCUT_INTEROP.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/CAPCUT_INTEROP.md)
- The doc describes no template-package format; "templates" appear only in the unmapped list. ReaCut's own "project templates" are its own format (`模板.reacut-template`, `项目.reacut`, `media/`, `manifest.json`, up to 200 placeholders) with no stated relation to JianYing/CapCut templates. — [CAPCUT_INTEROP.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/CAPCUT_INTEROP.md), [PROJECT_TEMPLATES.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/PROJECT_TEMPLATES.md)
- REA findings doc: states the REA research did not establish a verified external file spec ("这不是已经验证的外部文件格式规范"), did not identify the encryption scheme from the unparseable `draft_info.json`, and attempted no decryption or access-control bypass. Observed 11.0 draft folder contained `draft_info.json`, `timeline_layout.json`, `Timelines/project.json`, `template.tmp`. (Note: this conflicts in tone with the interop doc, which later describes a working AES-256-GCM decoder; the interop doc is the later, more specific one, but I could not verify the decoder against real drafts.) — [REA_FINDINGS.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/research/REA_FINDINGS.md)
- Own editor features: multitrack, keyframe curves (linear/ease), transform, crop, colour, chroma key, masks, constant speed, reverse/freeze, SRT/WebVTT import, text/motion/transition libraries. Projects saved as `.reacut`. Export MP4/MOV (H.264/AAC), full timeline, selection or range. — [README](https://github.com/Xiangyu-CAS/rea-capcut)
- Platform: macOS first, verified on macOS arm64; DMG Apple Silicon only, ad-hoc signed, not notarized; "Windows/Linux binaries are not provided, and existing Windows test failures remain" (15 Windows baseline/CI test failures noted in releases). Source build needs Node.js 26 (or 24.x from 24.11) plus FFmpeg/FFprobe. — [README](https://github.com/Xiangyu-CAS/rea-capcut), [Releases](https://github.com/Xiangyu-CAS/rea-capcut/releases)
- Licence: source MIT; bundled FFmpeg/x264 GPL; Noto Sans SC SIL OFL 1.1. — [README](https://github.com/Xiangyu-CAS/rea-capcut)
- Releases (all pre-releases): v0.5.0 (13 Oct, first preview, "experimental and lossy CapCut draft import" listed as known issue), v0.6.0 (22 Oct), v0.7.0 (27 Oct), v0.7.1 (27 Oct; manual update check). Years not shown; presumably 2026. — [Releases](https://github.com/Xiangyu-CAS/rea-capcut/releases)
- Maturity: 148 stars, 42 forks, 41 commits on main at fetch time; Issues tab shows 0 open and no closed count shown. README calls the project "early stages". A third-party directory listed 52 stars at an earlier capture. — [repo page](https://github.com/Xiangyu-CAS/rea-capcut), [SkillsLLM](https://skillsllm.com/skill/rea-capcut)
- Codex plugin exists (needs ReaCut 0.5.0+, Codex desktop); assistant sends text and a limited timeline summary, not media. — [README](https://github.com/Xiangyu-CAS/rea-capcut)

### Inferences
- Can it open a project made from a CapCut template? Only if the resulting local project folder is a JianYing 11.0-style (or classic plaintext) draft with local absolute media paths AND the template's content is basic clips/text. Template-derived edits are exactly the content (transitions, effects, text animations, keyframes, curve speed) that ReaCut drops. Nothing in the repo supports template packages directly.
- Even where import works, the output is a lossy `.reacut`; the lost fields are the ones our label JSON most cares about (transitions, text animation, effects, speed ramps, keyframed camera moves). So ReaCut's import is not a faithful converter for our purpose.
- However, its interop doc is a useful reference for how a JianYing 11.x draft is structured and decrypted (AES-256-GCM, key/IV from twelve shards), and its MIT-licensed decoder code could be read or reused for a decryption step, subject to checking it works on real drafts.
- Export render is from ReaCut's own engine on the lossy import, so the exported video would NOT match the original app render. Pair labels with a render from the CapCut/JianYing app itself instead.
- macOS Apple-Silicon-only prebuilt; you would need to build from source for Windows (you are on Windows 11) and Windows tests currently fail.

### Gaps
- Did not read the TypeScript source, so field coverage beyond the docs, and whether the AES decoder works across JianYing versions, is unverified.
- No year on release dates; no issue history available (0 issues). No independent third-party reviews found (WebSearch returned only a directory listing).
- Interop doc is a hand-written claim of verification on two controlled projects of one JianYing build (11.0.12922); real-world draft/template coverage unknown.

## Does any tool handle JianYing 6+ encryption?

### Takeaway
Community consensus: JianYing 6.0+ encrypts the draft on disk, CapCut International does not. Most tools refuse to decrypt (workarounds: pin JianYing 5.9.x, or use CapCut International). Only rea-capcut claims an independent decoder, and only for JianYing 11.x; a hosted third-party decrypt API also exists but is a privacy/ToS risk.

### Cited Findings
- "Starting with JianYing 6.0, `draft_content.json` is encrypted on disk"; the capcut-cli project decided "detect, do not decrypt"; keys changed across JianYing point releases; workarounds: pin JianYing to 5.9.x and disable auto-update, or use CapCut International. — [capcut-cli COMPATIBILITY.md](https://cdn.jsdelivr.net/npm/capcut-cli-david@2.5.0/COMPATIBILITY.md), [jianying-encryption.md](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md)
- "CapCut International is not encrypted — only JianYing." Encryption blocks reading drafts the app created, not writing new ones; on JianYing 11.4 (macOS) a plaintext `draft_info.json` is upgraded in place by the app. — [jianying-encryption.md](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md)
- capcut-cli test fixtures were CapCut 8.x desktop (mac 8.2.0, win 8.5.0/8.6.0), schema integer 360000; JianYing 6.x+ listed as unsupported. — [COMPATIBILITY.md](https://cdn.jsdelivr.net/npm/capcut-cli-david@2.5.0/COMPATIBILITY.md)
- pyJianYingDraft states 剪映6+ encrypts `draft_content.json` (quoted in the capcut-cli doc); its template mode works on unencrypted drafts. — [capcut-cli COMPATIBILITY.md](https://cdn.jsdelivr.net/npm/capcut-cli-david@2.5.0/COMPATIBILITY.md), [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)
- rea-capcut README says nothing about encryption; the interop doc documents the AES-256-GCM decoder (see previous section). — [CAPCUT_INTEROP.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/CAPCUT_INTEROP.md)
- A third-party hosted decrypt endpoint is documented by the JyDraft project (`POST https://htwmedia.dpdns.org/home/DecryptDraft`), unverified. — [JyDraft README](https://gh.r-mj.com/HTWMedia/JyDraft/blob/main/README_EN.md) (via search summary only)
- Sources disagree on which file is encrypted: most say `draft_content.json`; one source says CapCut template-library downloads have encrypted `draft_info.json`; REA_FINDINGS saw an unparseable `draft_info.json` in a JianYing 11.0 draft. Practical test suggested: try `json.loads()`. — [search summary](https://raw.githubusercontent.com/renezander030/capcut-cli/master/docs/jianying-encryption.md), [REA_FINDINGS.md](https://github.com/Xiangyu-CAS/rea-capcut/blob/main/docs/research/REA_FINDINGS.md)
- Neither REA nor FilmCraft mention encryption. — [REA](https://github.com/morluto/rea), [FilmCraft](https://github.com/storytold/filmcraft)

### Inferences
- Safest data path: CapCut International (unencrypted JSON), where the capcut-cli / pyJianYingDraft / pycapcut ecosystem can already read drafts. For JianYing, ReaCut's decoder is the only open reference found, valid for 11.0 and unknown for others.
- Whether CapCut International drafts have stayed unencrypted through late 2026 is not confirmed by a source dated after May 2026 in what I read (capcut-cli doc dated 2026-05-11); must be tested on current builds.

### Gaps
- No authoritative (ByteDance) statement; no verification of the hosted decrypt service.
- Key/IV scheme details beyond ReaCut's short description not found.

## What can FilmCraft (ArtCraft) do with CapCut/JianYing files?

### Takeaway
Nothing. FilmCraft is an alpha Rust clean-room Premiere-Pro-style editor with its own `.fcproj` format and pro interchange formats (FCP7 XML, FCPXML, OTIO, EDL, AAF, OMF). CapCut/JianYing are not mentioned anywhere in the README or in the format-parity doc.

### Cited Findings
- "Open-source, clean-room reimplementation of Adobe Premiere Pro, rebuilt in pure Rust" by the ArtCraft team; repos CapCuuStudio/filmcraft and storytold/filmcraft return the same description. — [storytold/filmcraft](https://github.com/storytold/filmcraft), [CapCuuStudio/filmcraft](https://github.com/CapCuuStudio/filmcraft)
- Formats: native `.fcproj` (docs/project-files.md); read/write FCP7 XML, FCPXML 1.9-1.11, OpenTimelineIO, CMX 3600 EDL, AAF, marker CSV; OMF/ALE write-only; `.prproj` not openable ("bring sequences over as FCP7 XML, AAF or OTIO"). — [README](https://github.com/storytold/filmcraft), [file-format-parity.md](https://github.com/storytold/filmcraft/blob/main/docs/file-format-parity.md)
- Licence: dual MIT or Apache-2.0; copyright 2026 ArtCraft Team and contributors; name/logos are trademarks under separate terms. — [README](https://github.com/CapCuuStudio/filmcraft)
- Maturity: "FilmCraft is in alpha", "young and moving fast"; self-estimated ~86% feature breadth, ~56% real-work readiness vs Premiere Pro; gaps include large-footage speed, no plugin hosting, limited delivery codecs (H.264 only, H.265 hardware). — [README](https://github.com/storytold/filmcraft)
- Platforms: macOS, Windows (x64/arm64/x86), Linux (x86_64/aarch64, RISC-V tarball), FreeBSD, WebAssembly browser build; Windows/Linux less tested than macOS. — [README](https://github.com/storytold/filmcraft)
- The docs folder (including `file-format-parity.md`, `project-files.md`, `target-app-parity.md`) contains no CapCut/JianYing mention in what I read; I read only file-format-parity.md in full. — [docs listing](https://github.com/storytold/filmcraft/tree/main/docs)

### Inferences
- FilmCraft is irrelevant for CapCut/JianYing decoding. Its one possible use is as an OTIO/FCPXML-capable renderer of timelines you convert yourself, but it is alpha, and it would not reproduce CapCut effects, text animations or transitions, so renders would not match the original reels.

### Gaps
- Did not read `target-app-parity.md` or `project-files.md`; did not confirm that the two GitHub orgs' repos are the same code (descriptions are identical).
- No release version numbers/dates retrieved.

## Which tool is most useful, and what glue code is still needed?

### Takeaway
None of the three gives a pipeline for (reel, exact label) pairs. REA is a generic RE toolkit, FilmCraft is unrelated, and ReaCut only partially, lossily imports basic clips and text. The most useful pieces found are ReaCut's CAPCUT_INTEROP.md (draft layout and decryption reference) and, outside the three, CapCut International + unencrypted-draft tools (pyJianYingDraft/pycapcut/capcut-cli) for reading JSON.

### Cited Findings
- No tool among the three exports a rendered video plus a faithful machine-readable timeline from a CapCut/JianYing draft. ReaCut exports MP4/MOV only from its own `.reacut` project (lossy import); FilmCraft and REA have no draft support. — [rea-capcut README](https://github.com/Xiangyu-CAS/rea-capcut), [FilmCraft](https://github.com/storytold/filmcraft), [REA](https://github.com/morluto/rea)
- Related ecosystem (outside the three tools, not deeply evaluated): pyJianYingDraft (load an existing draft as a template and import tracks), pycapcut, CapCutAPI/VectCutAPI (generate draft folders), capcut-cli, capcut-export, capcut-mate. — [search results](https://github.com/GuanYixuan/pyJianYingDraft), [pycapcut](https://pypi.org/project/pycapcut/), [capcut-cli README](https://cdn.jsdelivr.net/npm/capcut-cli@0.9.0/README.md)
- capcut-cli notes drafts are readable for CapCut 8.x and JianYing pre-6 (plaintext); version-differences doc exists in its draft-schema docs. — [05-version-differences.md](https://cdn.jsdelivr.net/npm/capcut-cli-david@2.5.0/docs/draft-schema/05-version-differences.md)

### Inferences
- Recommended approach (inference, not from repos): do not use ReaCut as the converter. Instead (1) get drafts from CapCut International desktop (plaintext) or JianYing <=5.9; (2) parse the draft JSON yourself into the label schema, using ReaCut's interop doc and the capcut-cli draft-schema docs as field references; (3) render the video with the real CapCut/JianYing app export so video matches the labels; (4) optionally borrow ReaCut's MIT decoder for JianYing 11.x drafts after testing.
- Glue code still needed: draft JSON to our label JSON mapper (cuts, transitions by resource id/name, text plus animation ids, effects, speed including curve speed, keyframes to camera moves, canvas/layout, colour/filters, audio untouched); resource-id to human name lookup tables for effects/transitions/animations (drafts carry ids, names may require the app's cached resource metadata); media relinking to absolute paths; scripted export (UI automation or an existing exporter such as capcut-export) to get video; validation by re-extracting frames and comparing cut times against labels.
- Template-derived projects: since template packages are not described by any of these tools, you would need to open each template in the app, apply it to your own media (or the template's placeholder media), save the draft, then parse. Whether template-sourced drafts are decryptable or contain full template data is untested here.
- Scale (800 reels) needs automation of the app, which none of the three tools provides.

### Gaps
- Not verified: how the downloaded CapCut template cache is structured on disk, or whether templates can be applied/exported programmatically.
- Not verified: ToS/legal position of automating or decoding JianYing/CapCut projects and using template content for model training.
- Not searched: Hacker News / Reddit / V2EX / Zhihu discussions (web search surfaced none for rea-capcut; one search returned only a directory listing). Treat community sentiment on ReaCut as unknown.
