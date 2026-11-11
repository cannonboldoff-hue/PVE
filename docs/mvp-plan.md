# Reel Template Compiler: MVP build plan

Audience: the model (Opus) that will execute this, one milestone per session.
Design write-up: https://claude.ai/artifact/6CiWnyQETJZXrztSoZa4Rf
Research: `reports/*.md`.

Status of this document: a plan. Nothing in it has been run. Every threshold is a starting value to tune, every third-party package and model ID must be verified at install time, and every FFmpeg recipe must be proven by the test named beside it.

---

## 0. How to execute this plan

1. Do one milestone per session, in order. Do not start a milestone whose dependencies are unchecked.
2. Before writing code, read the files listed under "Read first" for that milestone.
3. Run `cd backend && .venv\Scripts\python -m pytest -q` before you start and after you finish. The 53 existing tests must stay green unless a task says to delete a test.
4. Reuse before you write. Check `app/clients/video.py` (Kinocut `Client`, 164 methods, see section 2.3) and the existing stage modules first.
5. Keep the old path working until the milestone that switches it. New `PlanShot` and `Plan` fields are optional with defaults so old plans still render.
6. Every detector gets a test on a synthetic reel with exact ground truth (section 5.1). Every renderer feature gets a test that re-measures the output.
7. No new dependency without the install check in M0. If a package will not install on Windows with Python 3.12, use the listed fallback and record it in section 8.
8. Thresholds live as named constants at the top of their module, each with a one-line comment saying what it trades off.
9. When a milestone is done, tick its boxes in this file and append one line to section 9 (decisions log). Commit with the milestone ID in the message.
10. If something in this plan turns out to be wrong, fix the plan in the same commit and say so in the decisions log. Do not silently work around it.
11. Subagents: follow `CLAUDE.md` rule 5 (pass `model` explicitly, one tier below the main agent).

Environment facts (checked 2026-11-11): Windows 11, Python 3.12.10 in `backend/.venv`, FFmpeg 9.0.2 full build, Node v24.19.0, NVIDIA RTX 2050 with 4 GB VRAM. The project is not a git repository yet.

---

## 1. Scope and fixed decisions

### 1.1 What the MVP is

Upload a reference reel. The system measures it, builds a reusable template, proves the template with a round trip, works out what footage each slot needs, matches the user's clips, renders a new reel with the same structure, and reports the delta.

Target: everything a beginner to medium-level editor uses.

| Group | In the MVP |
|---|---|
| Cutting | trim, split, freeze frame, reverse |
| Speed | constant speed, speed ramps, slow motion (without frame interpolation) |
| Framing | cover crop to 9:16, blurred background fill, rotate, flip |
| Motion | zoom in/out, pan on photos, shake, keyframed position/scale/rotation/opacity for layers |
| Transitions | basic (cut, fade, dissolve, slide, wipe, push) and shader (whip, zoom blur, spin, glitch) |
| Effects | flash, glitch, RGB split, glow, blur, grain, vignette, scanlines |
| Colour | brightness, contrast, saturation, warmth, filter presets |
| Text | font, colour, outline, shadow, box, position, animate in/out, typewriter, word highlight |
| Overlays | stickers and emoji as slots, shapes, frames, progress bar |
| Layout | split screen, collage, picture in picture |
| Masks | shape masks, background removal (cutout) |

### 1.2 Decisions already made by the user (do not reopen)

- The output uses the reference reel's audio, unchanged. No song swap.
- The audio is never analysed. No beat detection, no speech-to-text, no stem separation.
- Timing is frame-exact and pinned to the reference audio. Slot count, slot lengths and total length come from the reference.
- LUT colour grading, green screen and object-tracked text are advanced tools. Not in the MVP.
- Render engines: FFmpeg + libass as the base, HyperFrames first and Remotion second as overlay engines, both behind one interface.
- The round trip is a required validation step.

### 1.3 Explicitly out of scope

Face identity matching, generative fill for missing shots, LUTs, chroma key, a library index beyond the existing TwelveLabs one, multi-user accounts, cloud hosting.

`backend/app/stages/reference.py:102` fetches links with `yt_dlp`. The research reports flag that as a platform-terms risk. This plan does not touch it. The new pipeline works from the file path it is given either way.

---

## 2. The code today

### 2.1 Flow

`actions.submit_reference` -> `pipeline.run_analyze` -> `reference.analyze` (one Pegasus call, free-text fields, video deleted) -> `brief.save_template` (`extract_template` keyword-maps text into `ShotSpec`) -> `brief.make_brief` -> user confirms -> `brief.fill_shots` -> `preproduction.match` (TwelveLabs search + Pegasus judge) -> user approves -> `plan.build` -> `music.sync_plan` (beat snap) -> `orchestrator.run` (`graph.compile_plan`, `editor.prep_clip` per shot, `editor.assemble`) -> `verifier.verify` -> repair loop (max 3) -> FINAL.

### 2.2 What changes, by file

| File | Fate |
|---|---|
| `app/stages/reference.py` | `_analyze_file` and `pick_analysis` replaced by the new analysis pipeline. Caching, fingerprint and `DownloadFailed` stay. The reference proxy is kept until validation passes. |
| `app/stages/brief.py` | `extract_template` (keyword mapping) retired for new templates. `make_brief` loses the `[:12000]` truncation. `fill_shots` learns text slots. `retime` no longer runs on new templates. |
| `app/stages/styles.py` | Used only for legacy analyses. No new callers. |
| `app/stages/music.py` | Beat code deleted (`detect_beats`, `snap_to_beats`, `_retime`, `sync_plan`). `audio_path`, `extract`, `music_for` stay. |
| `app/models.py` | `PlanShot` and `Plan` gain optional fields. `ShotSpec` stays as the UI contract. |
| `app/stages/editor.py` | Kept for legacy plans and collage. New single-pass renderer lives in `app/render/`. |
| `app/stages/graph.py`, `orchestrator.py` | Gain node kinds `trans` and `overlay`. Caching model unchanged. |
| `app/stages/verifier.py` | Gains deterministic structure checks before the LLM judge. |
| `app/stages/preproduction.py` | Gains hard filters from slot requirements and all-slots assignment. |
| `app/pipeline.py` | `run_analyze` calls the new pipeline and the template validation loop. `run_production` stops calling `music.sync_plan`. |
| `app/db.py` | New table `refs`; new columns on `templates`. |
| `frontend/src/components/cards.tsx` | One new card: template report (delta table + items to confirm). |

### 2.3 Kinocut `Client` methods worth reusing

Confirmed present by introspection (names only; check each signature with `help(Client.<name>)` before use):
`trim, speed, reverse, resize, crop, rotate, blur, fade, filter, color_grade, overlay_video, composite_layers, layout_pip, layout_grid, split_screen, shape_mask, apply_mask, luma_key, stabilize, effect_chromatic_aberration, effect_glow, effect_noise, effect_scanlines, effect_vignette, transition_glitch, transition_morph, transition_pixelate, text_animated, subtitles, subtitles_styled, mograph_progress, mograph_count, extract_frame, export_frames, detect_scenes, quality_check, compare_quality, info, video_info_detailed, hyperframes_doctor, hyperframes_init, hyperframes_catalog, hyperframes_add_block, hyperframes_validate, hyperframes_render, hyperframes_remove_background`.

Kinocut has no documented speed-ramp curve or smooth zoom. Those are written here with raw FFmpeg.

---

## 3. Target architecture

### 3.1 Data flow

```
reference file
  -> ingest          (fingerprint, 30 fps proxy, audio wav)            code
  -> evidence        (15 tracks, in parallel)                           specialist tools + OpenCV
  -> meaning         (per-shot description, effect names, story)        video AI
  -> fusion          (one owner per field, conflicts logged)            code
  -> extraction      (keep / swap / drop, roles, text slots)            code + LLM
  -> validation A    (same-shot pass, marker pass, coverage, critic)    code + video AI
  -> template saved
  -> brief -> fill -> requirements -> match -> approve                  existing flow
  -> compile -> render (FFmpeg base + overlay engine + reference audio)
  -> validation B    (plan lint, file checks, structure vs template, judge)
```

### 3.2 Module layout (new files in bold)

```
backend/app/
  ir.py                      **all IR models and enums (section 4)**
  clients/
    ff.py                    **ffprobe / ffmpeg subprocess helpers**
    gemini.py                **video AI client (direct to Google)**
    twelvelabs.py            existing; Pegasus becomes the second video-AI arm
  evidence/                  **one module per track; each exposes run(ctx) -> list[Item]**
    __init__.py              **track registry, parallel runner, cache**
    frames.py                **decode proxy once to small grayscale + colour arrays**
    cuts.py  transitions.py  speed.py  effects.py  camera.py
    text.py  text_anim.py  subjects.py  colour.py  layout.py
    overlays.py  inset.py  masks.py  layer_motion.py  still.py
  stages/
    meaning.py               **per-shot and whole-reel video-AI calls**
    fusion.py                **Evidence + Meaning -> Observed**
    extract.py               **Observed -> Template**
    requirements.py          **Template -> per-slot footage needs**
    roundtrip.py             **validation A and the delta report**
    analyze.py               **orchestrates ingest..template; called by reference.analyze**
  render/
    shot.py                  **single-pass FFmpeg prep for one slot (frame-exact)**
    transition.py            **transition segment between two prepped clips**
    textlayer.py             **text events -> ASS (libass)**
    overlay.py               **overlay engine interface + HyperFrames / Remotion adapters**
    assemble.py              **concat bodies + transitions, composite overlay, mux audio**
    capabilities.py          **template feature -> engine lookup, with recorded downgrades**
backend/tests/
  synth.py                   **synthetic reel generator with exact ground truth**
  test_evidence_*.py  test_render_*.py  test_roundtrip.py  test_ir.py
backend/tools/
  label.py                   **prefill a gold label file from detectors**
  score.py                   **score evidence against gold labels, print table**
gold/                        **<reel>/labels.json (reel files are gitignored)**
```

### 3.3 Timebase rule

Everything is in integer frames at `config.FPS` (30). The proxy is constant 30 fps, so a reference frame index equals an output frame index. Seconds appear only at the edges: user clips (source in/out), ASS timestamps, the UI. Convert with one helper in `ir.py`: `f2s(frame) = frame / FPS`.

### 3.4 Storage

```
data/refs/<key>/
  proxy.mp4          30 fps constant, original aspect, max 1080 on the long side. Deleted after validation unless PVE_KEEP_REFS=1.
  audio.wav          the existing ref_audio file may be reused; keep one source of truth
  ir/source.json  evidence.json  meaning.json  observed.json  template.json  delta.json
```

Each `ir/*.json` stores `{"v": <stage version>, "inputs": <hash of what it was built from>, ...}`. A stage re-runs only when its version or inputs change.

DB (`app/db.py`): add `refs(key TEXT PRIMARY KEY, fingerprint TEXT, n_frames INTEGER, proxy_path TEXT, validated INTEGER DEFAULT 0, created REAL)`. Add columns `template TEXT`, `delta TEXT`, `ir_version INTEGER` to `templates`. `CREATE TABLE IF NOT EXISTS` does not add columns, so add a small `_migrate()` that runs `ALTER TABLE ... ADD COLUMN` inside `try/except sqlite3.OperationalError`. Add `"template"`, `"delta"` to `JSON_COLS`.

---

## 4. Data contracts (`app/ir.py`)

Pydantic v2, same style as `app/models.py`. These definitions are the contract. Add fields when a milestone needs them; do not rename existing ones.

```python
FPS = config.FPS

class F(BaseModel, Generic[T]):
    """One observed or templated value. A label never travels without its raw value."""
    value: T
    raw: Any = None                 # measurement or free text the value came from
    conf: float = 1.0               # 0..1
    source: str = ""                # "cuts", "ocr", "gemini", "fusion", "llm", "user"
    evidence: list[str] = []        # ids of Evidence items
    binding: Literal["keep", "swap", "drop"] | None = None   # set in extraction

class Item(BaseModel):
    """One Evidence item. Append-only."""
    id: str                         # "<track>_<n>", stable within a reference
    track: str
    start: int                      # frame, inclusive
    end: int                        # frame, exclusive
    data: dict                      # track-specific payload (see each milestone)
    conf: float = 1.0
    tool: str                       # "pyscenedetect 0.7.2", "opencv flow", ...

class Source(BaseModel):
    key: str; fingerprint: str; n_frames: int; width: int; height: int
    src_fps: float                  # the original frame rate, for the record

class Evidence(BaseModel):
    items: list[Item]
    def track(self, name) -> list[Item]: ...

class Box(BaseModel):               # normalised 0..1, origin top-left
    x: float; y: float; w: float; h: float

class Key(BaseModel):               # one keyframe of a moving thing
    frame: int; box: Box; scale: float = 1.0; rotation: float = 0.0; opacity: float = 1.0

class Slot(BaseModel):
    id: str                         # "s01"
    start: int; end: int            # nominal frames; boundaries between slots are the cut frames
    media: F[Literal["video", "photo"]]
    role: F[Role]; function: F[str]             # why this shot exists in the story
    subject: F[str]; action: F[str]             # binding "swap"
    shot_size: F[ShotSize]; angle: F[str]
    layout: F[Layout]; layout_boxes: list[Box] = []
    camera: F[CameraMove]; camera_path: list[Key] = []   # zoom / pan / shake as keyframes
    speed: list[tuple[float, float]] = [(0.0, 1.0)]      # (position 0..1 in the slot, speed factor)
    reverse: bool = False
    freeze: list[tuple[int, int]] = []          # frame ranges inside the slot that hold one frame
    colour: ColourTarget | None = None
    requirement: Requirement | None = None      # filled by requirements.py

class Transition(BaseModel):
    after_slot: str                 # sits between this slot and the next
    type: F[TransitionType]
    start: int; end: int            # window in frames; start == end means a hard cut
    params: dict = {}               # direction, softness ...
    render: str = ""                # engine:name chosen by capabilities.py
    loss: str = ""                  # what the render could not reproduce

class Effect(BaseModel):
    id: str; type: F[EffectType]; start: int; end: int
    strength: float = 1.0; params: dict = {}; render: str = ""; loss: str = ""

class TextEvent(BaseModel):
    id: str; start: int; end: int
    text: F[str]                    # binding "swap"; raw holds the reference's words
    role: F[TextRole]
    keys: list[Key]                 # box path; first key is the resting position
    style: TextStyle                # font family class, size as fraction of height, fill, outline, shadow, box
    anim_in: F[TextAnim]; anim_out: F[TextAnim]; anim_in_frames: int = 0; anim_out_frames: int = 0
    max_chars: int = 0              # from box width and display time

class Overlay(BaseModel):
    id: str; kind: F[OverlayKind]; start: int; end: int; keys: list[Key]
    description: F[str]             # "red arrow sticker", "white rounded frame"
    binding: Literal["keep", "swap", "drop"] = "swap"

class Template(BaseModel):
    v: int; key: str; n_frames: int; audio: str
    slots: list[Slot]; transitions: list[Transition]; effects: list[Effect]
    texts: list[TextEvent]; overlays: list[Overlay]
    narrative: dict = {}            # hook, arc, payoff, cta as free text
    unsupported: list[str] = []     # evidence ids nothing could represent
    low_conf: list[str] = []        # field paths that need a user confirm

class Delta(BaseModel):
    rows: list[DeltaRow]            # track, metric, reference value, render value, gap, ok
    coverage: float                 # share of evidence items used, dropped with a reason, or listed unsupported
    passed: bool
```

Closed vocabularies (each has `other`; `other` always carries `raw`):

- `TransitionType`: cut, fade, dissolve, fade_black, fade_white, slide_left/right/up/down, push_left/right/up/down, wipe_left/right/up/down, zoom_in, zoom_out, whip_left/right/up/down, spin, glitch, blur, other
- `EffectType`: flash, shake, glitch, rgb_split, glow, blur, grain, vignette, scanlines, zoom_punch, other
- `CameraMove`: static, zoom_in, zoom_out, pan_left, pan_right, tilt_up, tilt_down, handheld, shake, other
- `TextAnim`: none, fade, pop, slide_up, slide_down, slide_left, slide_right, typewriter, word_highlight, bounce, other
- `Layout`: single, blur_fill, letterbox, split_h, split_v, collage, pip
- `OverlayKind`: sticker, emoji, shape, frame, progress_bar, logo, other
- `Role`: hook, establish, detail, action, reveal, reaction, payoff, cta, other
- `TextRole`: hook_line, title, list_item, label, punchline, cta, caption, other
- `ShotSize`: extreme_close, close, medium, wide, extreme_wide, none

`Plan` additions in `app/models.py` (all optional, so legacy plans are unaffected):

```python
class PlanShot:  # add
    frames: int | None = None            # exact output length incl. transition overlaps
    lead: int = 0; tail: int = 0         # overlap frames shared with the previous / next transition
    speed_curve: list[tuple[float, float]] | None = None
    reverse: bool = False
    freeze: list[tuple[int, int]] = []
    camera_path: list[dict] = []         # Key dicts
    layout_boxes: list[dict] = []
    colour: dict | None = None
class Plan:      # add
    n_frames: int | None = None
    transitions: list[dict] = []         # Transition dicts
    effects: list[dict] = []
    texts: list[dict] = []
    overlays: list[dict] = []
    audio_mode: Literal["legacy", "reference"] = "legacy"
```

---

## 5. How correctness is tested

### 5.1 Synthetic reels (`tests/synth.py`)

Real reels have no exact ground truth. Synthetic ones do. Build a generator that renders a reel from a spec with FFmpeg and returns the spec as ground truth.

```python
def make_reel(spec: SynthSpec, out: Path) -> SynthTruth
```

- A segment is a marker clip: a distinct solid colour, the slot number drawn large, and a bar that moves at a constant known rate (so speed and freeze are measurable). Add a textured variant (`testsrc2`) so feature tracking has corners to follow.
- The spec can add: cut frames, a transition of a given type and length at a boundary, a zoom or pan over a segment, shake, a flash at a frame, a speed curve, a freeze range, captions at a frame range with a position and an animation, a split-screen or picture-in-picture layout, a static overlay rectangle.
- Use the same `render/` functions the product uses where possible. For the first detector tests (before `render/` exists) use plain `lavfi` sources, `drawtext` and `xfade` through `tests/helpers.ff`.
- Marker clips are also what validation A uses in the marker pass. One generator, two uses.

### 5.2 Gold set (`gold/`)

Ten real reels the user owns or has rights to, hand-labelled. `gold/<name>/labels.json` holds: cut frames; transitions (type, window); text events (string, in/out frame, box); effects (type, frame, length); speed segments; camera move per shot; layout per shot; overlays.

- `tools/label.py <reel>` runs the detectors and writes a prefilled `labels.draft.json` plus a contact sheet PNG per shot. The user corrects the draft and saves it as `labels.json`. Prefilling biases labels toward the detector; the labelling instructions must tell the user to scrub the video, not just accept the draft.
- `tools/score.py` runs evidence on every gold reel and prints, per track: precision, recall, F1 at a frame tolerance, and mean absolute frame error. It appends the run to `gold/history.jsonl` so regressions are visible.
- Until gold reels exist, synthetic reels are the only score. Do not invent gold targets; record the first real baseline, then set targets from it.

### 5.3 Validation A, exactly

1. **Same-shot pass.** Every slot is filled with the reference's own footage for that slot. Transitions become hard cuts. Text, overlays, colour, added motion and effects are off. Expected: the render matches the proxy almost frame for frame (FFmpeg `ssim` filter, per-frame minimum above `SSIM_MIN`), the frame count equals `n_frames`, and the audio is identical in length and aligned (cross-correlation peak at lag 0).
   What it proves: slot lengths add up, rendering is frame-exact, audio is in sync.
   What it cannot prove: that a cut is in the right place. Any split of one video joins back into the same video. Cut positions are judged by the gold set and by step 2.
2. **Marker pass.** Every slot is filled with a marker clip, and the whole template is applied. The evidence extractors run on the render. Each track is compared with the reference's track: cut frames, transition windows and types, speed curve shape, freeze ranges, flash frames, shake amplitude, zoom rate, text strings, text boxes (IoU), text in/out frames, text animation type, layout boxes. Because marker clips are plain, whatever is measured on them was put there by the template. A gap means a renderer downgrade, a vocabulary mapping loss, or a detector that disagrees with itself.
3. **Coverage.** Every evidence item id must appear in the template (`evidence` lists), in a `drop` with a reason, or in `unsupported`. Coverage below 100% is a bug, not a score.
4. **Omission critic.** The video AI watches the reference with the template summary and lists what the template does not mention. Findings become patches or `unsupported` entries.
5. **Repair.** Deltas become typed patches on the template. Keep the best-scoring template. Stop after `MAX_TEMPLATE_ROUNDS = 3`.
6. **Confirm.** Fields with `conf < CONF_ASK` are listed in `template.low_conf` and shown on the template report card.

Colour is not checked in the marker pass (marker clips have no meaningful grade). It is checked on real renders in validation B by comparing per-shot Lab statistics with the template's colour target.

### 5.4 Validation B (every render)

Layer 0 plan lint, layer 1 file checks (existing `video.tech_checks`), layer 2 structure against the template (re-run cuts, text and effects evidence on the render; same comparators as the marker pass), layer 3 clip-to-slot fit (existing Pegasus judge), layer 4 LLM judge (existing). Stop at the first failing layer and repair from there.

---

## 6. Milestones

Dependency order: M0 -> M1 -> M2 -> M3. After M3, M4 to M8 depend only on M2 and can be done in any order, though the listed order is recommended. M9 needs M4 and M6. M10 needs M3 to M8. M11 needs M10. M12 is last.

After M2 the product works end to end with exact timing and the reference audio. Every later milestone widens it by one group of tracks, using the same four steps: detect, store, render, measure the delta.

---

### M0. Foundations

Goal: a repository, verified dependencies, and the two low-level helpers everything else needs.

Read first: `backend/requirements.txt`, `app/config.py`, `app/clients/video.py`, `tests/helpers.py`.

- [x] `git init`, first commit of the current tree. Add `gold/**/*.mp4`, `gold/**/*.mov` to `.gitignore`.
- [x] Install and import-check each new dependency in the venv, one at a time. Pin the installed version in `requirements.txt` only after the import works.
  - `opencv-contrib-python` (all OpenCV work; was `opencv-python-headless`, changed because mediapipe requires contrib, see section 8)
  - `scenedetect` (PySceneDetect; cuts)
  - `paddleocr` + `paddlepaddle` (PP-OCRv5; text). Fallback if it will not install or import: `rapidocr` + `onnxruntime`, which runs PP-OCR models. Record which one is in use.
  - `mediapipe` (person and face boxes). Fallback: OpenCV's bundled face detector. Subjects are a low-priority track.
  - `google-genai` (Gemini). No fallback needed; Pegasus is the second arm.
- [x] `app/clients/ff.py`:
  - `probe(path) -> dict` (ffprobe JSON: streams, `nb_frames` via `-count_frames`, `r_frame_rate`, duration).
  - `run(args: list[str]) -> None` (raises with the last stderr lines on failure).
  - `count_frames(path) -> int`, `ssim(a, b) -> list[float]` (per-frame, parsed from the `ssim` filter's stats file), `audio_lag(a, b) -> int` (samples; numpy cross-correlation on mono 8 kHz).
  - Use `clients.video._ensure_ffmpeg_on_path` so PATH handling stays in one place.
- [x] `config.py`: add `REFS = DATA / "refs"`, `KEEP_REFS = os.getenv("PVE_KEEP_REFS") == "1"`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `VLM_PROVIDER` (`gemini` or `pegasus`, default `pegasus` until a Gemini key is set). Add the new keys to `.env.example`.
- [x] Check the overlay engine: call `video.client().hyperframes_doctor()` and record the result. Then try the smallest possible `hyperframes_init` + `hyperframes_render` of a transparent text clip. Record in section 8 whether it works on this Windows machine and whether the output has an alpha channel. This decides M9.
- [x] Record the available xfade transitions: `ffmpeg -hide_banner -h filter=xfade`. Paste the list into section 8. `ir.TransitionType` maps onto this list in M6.

Done when: all imports succeed or have a recorded fallback; `tests/test_ff.py` passes (`probe`, `count_frames` and `ssim` on two generated clips; `audio_lag` returns 0 for a file against itself and the right lag for a shifted copy); section 8 is filled in.

---

### M1. IR, synthetic reels, scoring harness

Goal: the contracts and the instruments. No product behaviour changes.

Read first: `app/models.py`, section 4 and section 5 of this file.

- [x] `app/ir.py`: the models and enums in section 4, plus `load(key, layer)` / `save(key, layer, model)` for `data/refs/<key>/ir/`, and `f2s`.
- [x] `app/db.py`: `refs` table, `templates` columns, `_migrate()`.
- [x] `tests/synth.py`: `SynthSpec`, `make_reel`, `marker_clip(slot_no, frames, out)`. First version supports: segments with cut frames, captions with position and frame range, one flash, one zoom, one `xfade` transition. Later milestones extend it.
- [x] `tools/score.py`: comparators shared with `stages/roundtrip.py`. Put the comparators in `app/stages/compare.py` so both import them:
  - `match_events(pred, truth, tol_frames) -> (precision, recall, f1, mean_abs_err)` for point events (cuts, flashes).
  - `match_spans(pred, truth, min_iou)` for spans (transitions, text events, freezes).
  - `box_iou`, `text_similarity` (normalised edit distance; `difflib.SequenceMatcher` is enough).
- [x] `tools/label.py`: writes the draft label file and contact sheets. It can only prefill tracks that exist; it grows with each milestone.
- [x] `gold/README.md`: the label format and the labelling instructions.

Done when: `tests/test_ir.py` round-trips every model through JSON; `tests/test_compare.py` covers each comparator with hand-made cases; `make_reel` produces a clip whose frame count and cut frames match its spec exactly (checked with `ff.count_frames` and a pixel probe at each cut).

---

### M2. Cuts, frame-exact rendering, reference audio, same-shot pass

Goal: the first full vertical slice. A cut-only template with exact timing, rendered with the reference's audio, validated by the same-shot pass, running through the existing UI.

Read first: `app/stages/reference.py`, `brief.py`, `editor.py`, `graph.py`, `orchestrator.py`, `music.py`, `plan.py`, `pipeline.py`, `tests/test_render.py`, `tests/test_flow.py`.

Ingest
- [x] `stages/analyze.py: ingest(path) -> Source`: fingerprint (reuse `reference.fingerprint`), write `proxy.mp4` at constant 30 fps (`-vf fps=30`, long side capped at 1080, CRF about 16, no audio), write the audio with the existing `music.extract`, save `ir/source.json`, insert the `refs` row.
- [x] `reference.analyze` keeps its signature and cache behaviour. It no longer deletes the proxy; `refs.validated` and `KEEP_REFS` decide deletion later (M11). The uploaded original is still deleted as today.

Evidence: cuts
- [x] `evidence/frames.py`: decode the proxy once into a small grayscale stack (for example 160 px wide) and a small colour stack, memory-mapped under `data/refs/<key>/`. Every track reads from these; nothing else decodes the video.
- [x] `evidence/__init__.py`: `run_all(key) -> Evidence` runs registered tracks in a thread pool, caches each track's items by (fingerprint, track version).
- [x] `evidence/cuts.py`: PySceneDetect `AdaptiveDetector` and `ContentDetector`; take the union, merge detections within `MERGE_FRAMES = 2`, and drop shots shorter than `MIN_SHOT_FRAMES = 6`. Emit one `Item` per cut with `data = {"frame": n, "detectors": [...]}` and `conf` 1.0 when both agree, lower when one does. Gradual transitions are M6; here a dissolve may show as zero, one or two cuts, and that is acceptable.

Template (cut-only)
- [x] `stages/extract.py: build(source, evidence, meaning=None) -> Template`: slots tile `[0, n_frames)` with boundaries at the cut frames. All transitions are hard cuts. Other lists are empty.
- [x] Per-shot meaning for now: reuse the existing Pegasus path, but cut-list-first. For each slot call `twelvelabs.analyze(aid, SHOT_PROMPT, SHOT, start, end)` with the slot's own start and end seconds. Delete `pick_analysis` and the whole-video call. Timestamps from the model are ignored entirely. Keep the existing `SHOT` schema fields so `styles.py` still works for captions and colour until M4 and M8 replace it.
- [x] `extract.to_shotspecs(template, legacy_fields) -> list[ShotSpec]`: the adapter that feeds the existing brief, fill and match steps. `start`/`end` come from frames via `f2s`. Store both: `templates.template` (source of truth) and `templates.shots` (derived).
- [x] `brief.make_brief`: remove `[:12000]`. Send a compact summary built from the template (slot count, lengths, roles, text) instead of the raw analysis.

Rendering
- [x] `render/shot.py: prep(params, out)`: one FFmpeg invocation per slot. Filter chain order: decode -> `fps=30` -> select the source range -> (speed: later) -> fit to 1080x1920 (cover crop, or blur fill) -> (motion, colour, effects: later) -> exact length. Output: H.264, CRF 14, `yuv420p`, no audio, exactly `frames` frames (`-frames:v`). Port the cover and blur-fill maths from `editor._cover` and `editor._blur_fit`. If the source is shorter than the slot, slow it down, never below 0.5x (same rule as `plan.build`), and if it is still short, hold the last frame.
  Test: for sources at 24, 25, 30 and 60 fps, output frame count equals `frames` exactly.
- [x] `render/assemble.py: assemble(plan, clips, out)`: concat demuxer with stream copy for the slot clips (they share codec settings), then one final pass that burns the text layer if any and muxes the audio. `audio_mode == "reference"`: the reference wav, volume 1.0, no loop, trimmed to the video length, AAC 192k.
  Test: total frames equal `plan.n_frames`; `ff.audio_lag(render, reference_audio) == 0`.
- [x] `plan.build`: when the project's template has `n_frames`, set `PlanShot.frames` from the slot, `Plan.n_frames`, `Plan.audio_mode = "reference"`. Otherwise behave as today.
- [x] `graph.compile_plan` / `orchestrator.run`: if `PlanShot.frames` is set, the prep node calls `render.shot.prep` and the assemble node calls `render.assemble.assemble`; else the legacy functions. Add the new fields to the node hash.
- [x] `pipeline.run_production`: stop calling `music.sync_plan`. Delete `detect_beats`, `snap_to_beats`, `_retime`, `sync_plan` and their tests in `tests/test_music.py`. Then grep for `librosa`, `numba`, `sklearn`, `soundfile`; remove from `requirements.txt` whichever has no remaining import.
- [x] `video.tech_checks`: with `audio_mode == "reference"` replace the true-peak rule with "audio length within one frame of the video and loudness within 1 LU of the reference audio". The reference's own mastering is not ours to judge.

Validation
- [x] `stages/roundtrip.py: same_shot_pass(key) -> list[DeltaRow]`: build a plan whose every slot uses `proxy.mp4` as its clip with `src_in = f2s(slot.start)`, render it into `data/refs/<key>/rt/`, compare with the proxy scaled the same way: frame count, per-frame SSIM minimum (`SSIM_MIN = 0.95` to start), audio lag.
- [x] `stages/analyze.py: run(path) -> (key, Template, Delta)` wires ingest -> evidence -> meaning -> build -> same-shot pass, and saves `delta.json`.

Done when:
- A synthetic reel with 6 known cuts yields a template whose slot boundaries equal the truth exactly.
- The same-shot pass on that reel passes all three checks.
- `tests/test_flow.py` passes with the new path (stub Pegasus per shot the same way the test stubs it today).
- A manual run in the UI: upload a reel, confirm brief and shots, approve, and the result has the reference's length, cut frames and audio.

---

### M3. Meaning: video AI behind one interface, fusion, story

Goal: replace free-text-then-keyword parsing with typed descriptions that carry raw values and confidence.

Read first: `app/clients/twelvelabs.py`, `app/clients/openrouter.py`, `stages/extract.py`.

- [x] `clients/gemini.py: describe(clip_path, prompt, schema) -> dict` using `google-genai`: upload the clip, request JSON with the schema, temperature 0. Before wiring, list the models available to the key and confirm `config.GEMINI_MODEL` exists. The research suggests a Flash-class model; do not hard-code an ID that was not seen in that list.
- [x] `stages/meaning.py`:
  - `describe_slot(key, slot, evidence_summary) -> SlotMeaning`. Cut the slot out of the proxy to a temp clip (so the model cannot see neighbouring shots), send it with the measured facts for that slot. Schema fields are the `Slot` semantic fields, each as `{value, note, confidence}` using the closed vocabularies. `note` is free text and is stored as `raw`.
  - `describe_reel(key, slots) -> dict`: one call on the whole proxy for hook, arc, payoff, call to action, and relations between shots.
  - Provider switch on `config.VLM_PROVIDER`. The Pegasus arm uses `twelvelabs.analyze(..., start, end)` on the uploaded proxy with the same schema.
  - Cache each response by (fingerprint, slot range, prompt version, provider).
- [x] `stages/fusion.py: fuse(source, evidence, meaning) -> Observed`: ownership table in one dict. Timing and geometry fields take the evidence value. Semantic fields take the model's value. Where both exist and disagree (for example the model says "zoom in" and the camera track says static), keep the owner's value, lower `conf`, and append to `observed.conflicts`.
- [x] `extract.build` reads `Observed`. Default bindings: structure fields `keep`; `subject`, `action`, text strings `swap`.
- [x] `tools/score.py`: add a per-field agreement table between the two providers on the gold reels. This is the A/B the research asked for.

Done when: with the provider stubbed, a slot description round-trips into `Slot` fields with `raw` and `conf` set; an out-of-vocabulary answer lands as `other` with its note preserved, never as a default; a forced disagreement appears in `conflicts`. Unit tests only; no live API call in the test suite.

---

### M4. Text: reading, style, animation, rebuilding

Goal: on-screen text as timed, positioned, styled, animated events, re-rendered at the same frames.

Read first: `app/stages/editor.py` (`_ass`, `_caption_text`, `_entrance`), `models.CaptionStyle`, `stages/styles.py`.

Evidence
- [x] `evidence/text.py`: OCR every third frame (10 per second). Link detections into tracks: same track when box IoU is above `LINK_IOU` and text similarity is above `LINK_SIM` between consecutive samples. For each track: refine the first and last frame by binary search on single frames; take the majority string; store the box per sample. Drop tracks shorter than `MIN_TEXT_FRAMES`. Merge lines that share timing and are vertically adjacent into one event with line breaks.
  Item `data`: `{"text", "boxes": [[frame, x, y, w, h]...], "samples": n}`.
- [x] Style, measured from pixels inside the box at the track's steadiest frame: text height as a fraction of frame height; fill colour and outline colour by clustering the pixels into two or three groups and using the OCR mask to tell glyph from edge; a filled background box if the area around the glyphs is uniform and differs from the frame; alignment from box position.
  Font: no font-identification model exists in the research. Use the video AI to choose a family class (sans, serif, script, display, mono), then map the class to one of `models.FONTS`. Record the loss.
- [x] `evidence/text_anim.py`, from each track's first and last `ANIM_WINDOW = 12` frames at every frame: growing box height means pop; a moving centre means slide (with direction); rising contrast at a fixed box means fade; a string that gains characters over time means typewriter; a colour change that moves word by word means word highlight (flag low confidence and let the video AI confirm). Store the type and its length in frames.

Template and UI
- [x] `extract.build`: `TextEvent` list. `max_chars` from the box width at the measured character size, and capped by reading time for the display length (start with 15 characters per second). `role` from the video AI.
- [x] `brief.fill_shots`: send text slots as `[{id, role, original, max_chars}]` and get back `{id, text}`. Reject and retry once if a text exceeds `max_chars`. The adapter still fills `ShotSpec.text` (joined per slot) so the existing shots card keeps working.

Rendering
- [x] `render/textlayer.py: ass(texts, fps) -> str`: one `Dialogue` per event with absolute frame times, `\pos` from the resting box, size from the measured height, colours, outline, shadow, box. Animations with libass tags: fade `\fad`, pop `\t` on `\fscx/\fscy`, slide `\move`, typewriter and word highlight with `\k` timing. Reuse `_bgr` and the escaping from `editor.py`. Anything libass cannot do is routed to the overlay engine in M9 and recorded as a loss until then.
- [x] `render/assemble.py` burns this layer when `plan.texts` is set; legacy plans keep using `editor._ass`.

Validation
- [x] `roundtrip.marker_pass` (first version): fill slots with marker clips, apply the template's text layer, run `evidence/text.py` and `text_anim.py` on the render, compare with the reference: string similarity, box IoU, start and end frame error, animation type.
- [x] Extend `tests/synth.py` captions with each animation type.

Done when: on a synthetic reel with five captions of known text, position, timing and animation, the detector recovers all five with start and end within 2 frames, IoU above 0.6 and the right animation for fade, pop and slide; the marker pass on that reel reports a small delta for every caption.

---

### M5. Camera path, zoom, pan, shake, photo or video

Goal: measure how the frame moves inside each shot and reproduce it on new footage.

- [x] `evidence/camera.py`: per slot, track corners between consecutive frames (`goodFeaturesToTrack` + `calcOpticalFlowPyrLK`), fit a similarity transform with RANSAC (`estimateAffinePartial2D`), accumulate scale, translation and rotation into a path. Mask out text boxes from M4 so captions do not anchor the estimate. Smooth the path; the smooth part is the move, the residual is shake. Classify: static, zoom in or out (scale trend), pan or tilt (translation trend), handheld (low-frequency residual), shake (high-frequency residual above `SHAKE_MIN`). Store keyframes of the smooth path plus shake amplitude and rough frequency.
- [x] `evidence/still.py`: after removing the camera path, if the residual frame difference stays below `STILL_MAX` for the whole slot, the slot is a photo. Sets `Slot.media`.
- [x] `render/shot.py` motion: do not use `zoompan` at output size; it steps in whole pixels and jitters. Scale the source up first (about 4x the crop region), then crop with a per-frame expression for x, y, width and height interpolated between keyframes, then scale down to 1080x1920. Shake: add a small deterministic pseudo-random offset per frame at the measured amplitude. Easing from the measured path shape (linear, ease in, ease out).
- [x] `extract.build`: `Slot.camera`, `Slot.camera_path`. A photo slot with a camera path renders as a photo with that move.
- [x] Marker pass: run `camera.py` on the render of textured marker clips; compare scale change per second, translation direction and shake amplitude.

Done when: a synthetic zoom from 1.0 to 1.3 over 60 frames is measured within 5% of the true end scale; a rendered zoom is measured back within the same tolerance; visual check shows no stepping; a photo-with-zoom segment is classified as a photo.

---

### M6. Transitions

Goal: every boundary gets a window and a type, and is rebuilt from two prepped clips.

- [x] `evidence/transitions.py`: for each cut from M2 and for each frame-difference ramp that is not a cut, examine a window of `TRANS_WINDOW = 15` frames each side. Signals: per-frame difference curve (a one-frame spike is a hard cut; a plateau of several frames is a gradual transition), mean brightness (a dip to black or a rise to white), a moving vertical or horizontal boundary between two regions with different content (slide, wipe, push; direction from the boundary's motion), a large uniform optical flow with blur (whip, with direction), radial flow (zoom transition), rotation (spin). Emit the window `[start, end)` and a coarse class with confidence.
- [ ] Naming: `meaning.py` sends the window plus one second each side to the video AI with the coarse class and asks for a `TransitionType`. Fusion: the window comes from evidence, the name from the model unless the evidence class is high-confidence and different.
- [x] Timeline model. For a transition window `[a, b)` between slot k and slot k+1: slot k's clip must extend to `b`, and slot k+1's clip must start at `a`. So each prepped clip covers `[a_prev, b_next)` and `PlanShot.lead`/`tail` hold the overlap lengths. The assembled timeline is: body of slot 1, transition segment, body of slot 2, and so on. Bodies exclude the overlaps. Total frames stay equal to `n_frames`. Add an assert.
- [x] `render/transition.py: render(a_tail, b_head, spec, out)`: both inputs have exactly `b - a` frames. Basic types use `xfade` with the matching name and `duration` equal to the window. Map `TransitionType` to the xfade names recorded in M0. Glitch uses Kinocut `transition_glitch`. Types with no equivalent fall back to the nearest basic type; write what was lost into `Transition.loss`. Shader transitions arrive in M9.
- [x] `graph.py`: node kind `trans`, depending on its two prep nodes. `assemble` concatenates bodies and transition segments.
- [x] `render/capabilities.py`: one table `feature -> (engine, name)` plus `downgrade -> (engine, name, loss text)`. `extract.build` fills `render` and `loss` from it.
- [x] `requirements`: a slot's needed footage now includes its lead and tail.
- [x] Marker pass: detect transitions on the render; compare window start, window length and coarse class.

Done when: synthetic reels with fade, dissolve, slide left, wipe up and fade to black are each detected with the right class and a window within 2 frames; the rebuilt reel has exactly `n_frames` frames; the marker pass finds the same windows.

---

### M7. Speed and effects

Goal: speed ramps, freeze, reverse, and the common effects, measured and rebuilt.

- [x] `evidence/speed.py` (reverse not measured, see log): per slot, after removing the camera path, compute the median optical-flow magnitude per frame (the "pace"). Smooth it, then find change points where the pace shifts by more than `RAMP_RATIO` for at least `RAMP_MIN_FRAMES`. Express the result as a piecewise speed curve relative to the slot's median pace. This is an approximation: a slow subject and slow motion look alike. Confidence is low unless the change is abrupt. Freeze: runs where frame difference is near zero inside a slot that is not a photo. Reverse: not measurable; ask the video AI, mark low confidence.
- [x] `evidence/effects.py`: flash is a brightness jump above `FLASH_DELTA` lasting 1 to 4 frames that returns to the previous level. RGB split and glitch: horizontal displacement between colour channels (phase correlation between the red and blue planes) in bursts. Blur and glow: a drop in Laplacian variance, with glow also raising brightness in highlights. Grain: high-frequency noise energy that is constant across a shot. Vignette: darker corners than centre across a shot. The last three are shot-level looks; let the video AI name them and use the measurement as support.
- [x] `render/shot.py`: speed curve by piecewise `setpts` (split the slot at the curve's breakpoints, each piece at constant speed, concatenated inside the filter graph), then a hard `fps=30` and exact frame count. Freeze by holding a frame for the range. Reverse with the `reverse` filter on the selected range. Effects: flash with a brightness keyframe (`eq` with a time expression) or a white overlay; RGB split with Kinocut `effect_chromatic_aberration` or `rgbashift`; glow, grain, vignette, scanlines with the Kinocut `effect_*` methods; blur with `gblur`. Effects that span several slots are applied in `assemble`.
- [x] `stages/requirements.py: footage_frames(slot) -> int`: the area under the speed curve over the slot's length, plus lead and tail, minus freeze ranges (a freeze uses no extra footage).
- [x] Marker pass: the marker clip's bar moves at a constant rate, so the measured pace curve of the render is the applied speed curve; compare its shape with the template's curve. Compare flash frames and freeze ranges exactly.

Done when: a synthetic 1x -> 3x -> 0.5x ramp is recovered with breakpoints within 3 frames and factors within 25%; flash frames are exact; a freeze range is within 2 frames; `footage_frames` for that ramp matches hand arithmetic; rendered clips still have the exact frame count.

---

### M8. Colour, layout, overlays, inset video, masks

Goal: the remaining visual structure.

- [x] `evidence/colour.py`: per slot, with text and overlay regions masked out: mean and spread of L, a, b; saturation; a contrast measure. `ColourTarget` stores them.
- [x] Colour rendering: measure the same statistics on the user's clip, then set brightness, contrast, saturation and warmth so the clip's statistics move toward the target. This is a per-channel mean and spread match, limited to `MAX_SHIFT` so a clip is never pushed into something unnatural. Presets (`models.Grade.preset`) are chosen by the video AI's look name. No LUT.
- [x] `evidence/layout.py`: letterbox or pillarbox (constant-colour bars); blur fill (top and bottom bands, or side bands, with very low detail and colours that track the centre); split screen (a straight full-length edge that persists for the slot with unrelated motion on each side); collage (several rectangles). Emit `Layout` and boxes.
- [x] `evidence/inset.py`: a rectangle with its own motion over a background (picture in picture). Ask the video AI for the box, then verify the box edges against image gradients.
- [x] `evidence/overlays.py`: pixels that stay the same across a cut cannot belong to either shot. Build a stability mask across each boundary, remove text boxes, and take the connected regions as overlays. Classify by shape and behaviour: a thin region that grows steadily is a progress bar; a border-shaped region is a frame; the rest are stickers or logos, described by the video AI.
- [ ] `evidence/masks.py`, `evidence/layer_motion.py`: video-AI led for the MVP. Shape masks and cutouts are reported with a box and low confidence. Layer motion reuses the box tracks from overlays and inset video as `Key` lists.
- [x] Rendering: split screen, collage and picture in picture with Kinocut `split_screen`, `layout_grid`, `layout_pip` or the existing `editor._collage`; shape masks with `shape_mask`/`apply_mask`; cutouts with `hyperframes_remove_background` if M0 showed it works, else recorded as unsupported. Progress bar with `mograph_progress`. Frames and shapes are drawn by the overlay layer.
- [x] Stickers and logos are content, not structure. The template stores the slot (where, when, how it moves, what kind) with binding `swap`; the user supplies an image, picks an emoji, or drops it. Never copy the graphic out of the reference.
- [x] Marker pass: layout boxes, overlay boxes and inset box compared by IoU.

Done when: synthetic reels with a split screen, a picture-in-picture box, a blurred-fill shot and a static overlay rectangle are each detected with IoU above 0.7 and rebuilt; a real render's per-shot colour statistics move measurably toward the target.

---

### M9. Overlay engine: HyperFrames first, Remotion second

Goal: animated layers that libass and FFmpeg filters cannot draw.

Depends on the M0 findings. If HyperFrames does not run on this machine or cannot produce a transparent layer, swap the order: build the Remotion adapter first and record the decision. Remotion is free for individuals and companies of up to three people; above that it needs a paid licence.

- [x] `render/overlay.py`:
  ```python
  class OverlayEngine(Protocol):
      name: str
      def supports(self, feature: str) -> bool: ...
      def render(self, layer: OverlaySpec, out: Path) -> Path: ...   # transparent video, exactly n frames
  ```
  `OverlaySpec`: size, fps, `n_frames`, and lists of text events, overlays and shader-transition windows. The template never names an engine; `capabilities.py` picks one.
- [x] HyperFrames adapter through Kinocut (`hyperframes_init`, `hyperframes_add_block`, `hyperframes_validate`, `hyperframes_render`): generate the composition from `OverlaySpec`. Transparent output format is whatever M0 proved (for example a format with alpha, or a colour key if alpha is not available).
- [ ] Remotion adapter: a small Remotion project under `overlay/remotion/` that takes `OverlaySpec` as input props and renders the same layer. Same interface, same tests.
- [x] `render/assemble.py`: composite the overlay layer over the concatenated video in the final pass.
- [x] Shader transitions (whip, zoom blur, spin): the engine receives the two overlap clips for the window and returns the transition segment, used in place of the `xfade` fallback from M6.
- [x] Text animations beyond libass (bounce, per-letter, word highlight with scaling) route here.

Done when: one overlay spec renders through the available engine with exactly `n_frames` frames and composites cleanly; a whip transition rendered this way is classified as a whip by `evidence/transitions.py`; the engine choice is invisible to `Template` and `Plan`.

---

### M10. Extraction decisions, requirements, matching

Goal: turn the observed reel into a reusable template with intent, and tell the user exactly what to supply.

Read first: `app/stages/preproduction.py`, `stages/memory.py`, `app/actions.py`.

- [x] `stages/extract.py: decide(observed) -> Template`: one LLM call (`openrouter.chat_json`) with the observed reel as compact JSON. It returns, per field path, `keep`, `swap` or `drop` with a reason, and per slot a `role` and a one-line `function`. Code applies the result; the model cannot change timing, frames or measured values. Anything dropped is listed with its reason.
- [x] `stages/requirements.py: derive(template) -> list[Requirement]`: per slot: media type, orientation, `footage_frames` (M7), shot size, camera move needed from the clip versus added by the template, subject role, subject movement. Hard constraints and weighted soft ones.
- [x] `preproduction.match`: before search, drop candidates that fail hard constraints (too short for `footage_frames`, wrong media type). After the judge step, assign all slots at once with `scipy.optimize.linear_sum_assignment` over a score matrix, so one clip is not used for two slots unless nothing else fits. Add the label `adaptable` for clips that fit after a crop, a speed change within limits, or a photo used with the template's own motion.
- [x] `preproduction.write_instructions`: build the filming instruction from the requirement (length in seconds rounded up, framing, movement, what to show).
- [x] `models.Match.label` gains `adaptable`. Update `cards.tsx` chips.

Done when: with the LLM stubbed, a template is produced whose timing equals the observed timing exactly; requirements for a ramped slot ask for the right footage length; the assignment test shows two slots that both prefer one clip getting two different clips when a second acceptable clip exists.

---

### M11. Validation loops in the product

Goal: the checks run automatically and the user sees the result.

- [x] `stages/roundtrip.py: validate(key) -> (Template, Delta)`: same-shot pass, full marker pass (all tracks built so far), coverage, omission critic, patches, up to `MAX_TEMPLATE_ROUNDS`, keep the best. Patches are typed (`field path`, `new value`) and applied by code.
- [x] `pipeline.run_analyze`: call `validate` before `run_brief`. Progress messages through `msgs.text`. No new project state; this stays inside `ANALYZING`.
- [x] After validation: set `refs.validated = 1` and delete `proxy.mp4` and `rt/` unless `KEEP_REFS`.
- [x] `verifier.verify`: add layer 0 (plan lint: every slot has a clip, frame counts add up, text inside the safe area) and layer 2 (structure against the template with the M4 to M8 comparators) before the existing content and judge layers. A failing deterministic layer forces `REPAIR` regardless of the LLM verdict, as the code already does for tech checks.
- [x] `cards.tsx`: a `template` card. Shows the delta table (track, what was compared, gap, pass or fail), the list of downgrades (`loss` fields), and the low-confidence items with accept or edit. Accepting writes `source = "user"` and `conf = 1.0` on the field.
- [x] `actions.py`: `confirm_template_field(pid, path, value)`.

Done when: the flow test covers analyse -> validate -> brief with a stubbed provider; a deliberately broken template (one slot one frame short) fails the same-shot pass and is repaired or reported; the card renders the delta and the confirm round trip updates the stored template.

---

### M12. Hardening

- [ ] `tools/score.py` on all gold reels; record the baseline in `gold/history.jsonl`; set per-track targets from it and add a test that fails on a regression beyond a margin.
- [x] Time and cost per stage logged to `project_events`.
- [x] Rate-limit backoff and response caching for both video-AI providers.
- [x] `README.md`: setup, the new environment keys, how to add a gold reel, how to read the delta report.
- [ ] Review every `loss` string seen on the gold reels; the most frequent ones are the next features.

---

## 7. Decisions needed from the user (defaults in use until answered)

| # | Question | Default |
|---|---|---|
| 1 | Gemini API key for the video AI? | Not set: run on the existing TwelveLabs Pegasus key. A free Gemini key may be used only on reels the user owns, because free-tier content can be used for training. |
| 2 | Ten gold reels the user owns or has rights to, placed in `gold/`? | None yet: synthetic reels only. Scores on real reels start when the first three arrive. |
| 3 | Keep link download through `yt_dlp`? | Left as is. Flagged as a platform-terms risk by the research. |
| 4 | Keep reference proxies during development? | `PVE_KEEP_REFS=1` in the developer's `.env`; deleted after validation otherwise. |
| 5 | LLM model for extraction and chat? | Whatever `OPENROUTER_MODEL` is set to. Verify the ID on OpenRouter before changing it. |

---

## 8. Findings to record during M0 (fill in)

- OCR package in use: **`rapidocr` 3.10.0 + `onnxruntime` 1.31.1** (PP-OCRv6 ONNX models, bundled). `paddleocr` 3.7.0 / `paddlepaddle` 3.3.1 installed and imported but failed at inference on Windows (`NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`, oneDNN). It also downgraded numpy to 2.3.5; it was uninstalled and numpy restored to 2.5.4. RapidOCR read a 64 px white "HELLO REEL" on a 540x960 frame at score 0.9997, about 4.7 s cold start.
- MediaPipe import on Python 3.12: **works**, `mediapipe` 1.2.2, `mediapipe.tasks.python.vision` imports. It requires `opencv-contrib-python`, so the project uses `opencv-contrib-python==5.0.0.93` instead of `opencv-python-headless` (two cv2 distributions in one venv overwrite each other). Task models (`.tflite`) are downloaded separately when the subjects track is built.
- `hyperframes_doctor` result: core checks pass (hyperframes 0.8.209, Node v24.19.0, FFmpeg 9.0.2, system Chrome). `ok: false` only because optional items are missing: whisper-cpp, Kokoro TTS, MusicGen, Docker. The CLI is pinned in `overlay/hyperframes/package.json` (0.8.209, the newest release older than two weeks on 2026-11-11). `config.py` points `MCP_VIDEO_HYPERFRAMES_COMMAND` at it and sets `HYPERFRAMES_NO_TELEMETRY=1`, `DO_NOT_TRACK=1`.
- HyperFrames transparent output on Windows: **works.** A blank portrait composition with `background: transparent` and a 0.5 s opacity tween, 2 s at 30 fps, rendered to exactly 60 frames in both formats. `--format webm`: VP9 `yuv420p` with `ALPHA_MODE=1` (decode with `-c:v libvpx-vp9` to get alpha); alpha plane 0 everywhere on frame 0, text at 255 on frame 30. `--format mov`: ProRes 4444 `yuva444p12le`. About 35 s per 2 s clip. Kinocut's render wrapper logs a harmless cp1252 `UnicodeDecodeError` from a reader thread; the render still succeeds. M9 keeps the order HyperFrames first.
- xfade transitions available in this FFmpeg build: custom, fade, wipeleft, wiperight, wipeup, wipedown, slideleft, slideright, slideup, slidedown, circlecrop, rectcrop, distance, fadeblack, fadewhite, radial, smoothleft, smoothright, smoothup, smoothdown, circleopen, circleclose, vertopen, vertclose, horzopen, horzclose, dissolve, pixelize, diagtl, diagtr, diagbl, diagbr, hlslice, hrslice, vuslice, vdslice, hblur, fadegrays, wipetl, wipetr, wipebl, wipebr, squeezeh, squeezev, zoomin, fadefast, fadeslow, hlwind, hrwind, vuwind, vdwind, coverleft, coverright, coverup, coverdown, revealleft, revealright, revealup, revealdown. No push: `push_*` maps to `cover*`/`reveal*` pairs or a custom expression (M6).
- Gemini models visible to the key: **no key set** (`GEMINI_API_KEY` absent from `.env`). `VLM_PROVIDER` defaults to `pegasus`. `google-genai` 3.0.0 is installed and imports.

---

## 9. Decisions log

- 2026-11-11: plan written. Same-shot pass scoped to timing integrity only; cut correctness comes from the gold set and the marker pass.
- 2026-11-11 M0: git repo created. OCR uses the RapidOCR fallback (PaddleOCR fails at inference on Windows). OpenCV is `opencv-contrib-python`, not headless, because mediapipe depends on it; the plan's dependency list is corrected. HyperFrames works with alpha, so M9 order stands. `ff.py` added with `fps()` and `video_stream()` beyond the listed helpers.
- 2026-11-11 M1: `ir.py`, `compare.py`, `tests/synth.py`, `tools/score.py`, `tools/label.py`, `gold/README.md`. Synthetic reels draw frames in numpy/PIL and pipe them to ffmpeg instead of lavfi + drawtext + xfade, so every caption box, transition window and zoom scale is exact by construction; the product's xfade output is measured in the marker pass instead. `ir.save` stores `{v, inputs, data}` (model under `data`, because `Template` has its own `v`). `Template` gains `dropped` (evidence id -> reason) for coverage; `ir.s2f` added. `label.py` and `score.py` need M2's ingest and evidence to run.
- 2026-11-11 M2: cut-only vertical slice works on synthetic reels: 6 known cuts recovered exactly, same-shot pass at frame count 240/240, SSIM min 0.9948, audio lag 0 samples (a one-frame slip at a boundary drops SSIM to 0.43, so the check is sensitive where it matters). `test_flow.py` now runs the real analysis on a synthetic reel with only download, Pegasus and the LLM stubbed. Choices: refs are keyed by `fingerprint[:16]`; the reference audio stays at `ref_audio/<cache key>.wav` (one source of truth, `Template.audio` points at it). `render/shot.py` seeks by whole seconds before `-i` then `trim=start_frame` so the frame index is exact in every timebase. Skipped slots give their frames to the previous kept slot (or the next), and `drop` patches do the same, so the total stays `n_frames`. Legacy `ShotSpec.animation` (zoompan) and `grade` (eq + approximated presets) are carried into the new renderer so new templates do not lose them before M5/M8. Clip audio is not used on the frame-exact path; with no soundtrack a silent track is muxed. `same_shot_pass` raises when slots do not tile the reel; M11 turns that into a reported failure. `reference.snap`, `pick_analysis`, `video.scene_cuts` and the beat code were deleted with their tests; `librosa`, `numba`, `scikit-learn`, `soundfile` left `requirements.txt`. **Not done:** the manual UI run, because `.env` has no OpenRouter or TwelveLabs key on this machine.
- 2026-11-11 M3: `meaning.py` (Session per provider, typed `{value, note, confidence}` answers, OOV -> `other` with the word kept in the note), `fusion.py` (`Observed`, `EVIDENCE_OWNER` table, conflicts), `extract.build(observed)`, `gemini.py`, `score.py --providers`. Deviations: the media sent to the video AI is the uploaded original, not the proxy, so the model hears the sound (timing is still the proxy's); the response schema carries the vocabulary in descriptions, not `enum`, because not every provider accepts `enum`; one call per slot also returns the legacy style notes so `styles.py` keeps feeding captions and colour until M4/M8. `ir.Media` gains `other` (every closed vocabulary has one). M2 and M3 share `analyze.py`, `extract.py` and `reference.py`, so they are one commit. No live Gemini call was made: no key.
- 2026-11-11 M4: text track (RapidOCR every 3rd frame at 640 px long side, linked, ends refined on single frames, lines merged), style from k-means clusters at the steadiest frame (fill = glyph cluster least adjacent to the ground, tight ink box from dense glyph rows/columns), `text_anim` (presence of the resting glyphs against a clean frame of the same shot for fades, OCR on a band around the box every 2nd frame for pop/slide/typewriter geometry), libass layer with frame-exact `ts()`, `fill_shots` text slots with one retry. On the synthetic reel all five captions are found within 2 frames, box IoU > 0.6, and fade/pop/slide_up are named right; the marker pass reproduces every caption's string, box, start and end. Calibration: libass size vs PIL ink 0.892 for Arial Bold, ink box 1.08x PIL ink (`textlayer.py`); a swapped string keeps the reference's font size, not its box. Choices: marker clips moved to `app/stages/markers.py` (the marker pass is product code); OCR cost is the bottleneck (~0.35 s per call on CPU), so samples identical to the previous one reuse its result; slide-out on an event that also slides in is a recorded libass loss; the marker digits are themselves on-screen text and are left for the comparison to ignore. Word highlight is detected only through the video AI note.
- 2026-11-11 M5: `evidence/camera.py` tracks corners per slot at 320 px (new `frames.load_mid`), fits frame-0-to-frame-k similarity transforms (points re-anchored through the current transform when topped up, so no transform chaining), smooths the view path, classifies, and stores keyframes plus `shake {amp, hz}` (new optional `Slot.shake` / `PlanShot.shake`). Photo vs video is decided in the same loop and emitted as track `still` instead of a separate `still.py`, because it needs the per-frame transforms. Rendering: cover fit, upscale x2, `zoompan` with piecewise-linear expressions in the output frame number; a zoom-out path is rescaled to start zoomed in; shake is two incommensurate sines at the measured amplitude. Measured: synthetic 1.0->1.3 zoom ends at 1.295 (raw) / 1.287 (smoothed); the rendered zoom measures back within 5%, monotone, even increments; a zoomed photo is classified photo. Rotation is measured but not rendered (recorded in the path, not reproduced).
- 2026-11-11 M6: `evidence/transitions.py` finds windows from the frame-difference curve (raised against the shots' own motion, one quiet frame allowed inside a run) around every cut and around gradual runs the cut detectors miss (PySceneDetect found 2 of 6 boundaries on the synthetic reel); slot boundaries now come from this track (gradual ones mid-window), and `text_anim`/`camera` use the same boundaries (`evidence.boundaries`). Classes from native-resolution frames (a downscaled dissolve averages into a fade): brightness dip/peak, single-mix fit (fade), pure-A/pure-B pixels with a straight edge (wipe), A held still (slide), no motion + scattered B (dissolve, because x264 chroma subsampling smears the per-pixel switch), else Farneback flow (push, whip with blur, zoom, spin). Measured on the textured synthetic reel: fade, dissolve, slide left, wipe up, fade to black all right with exact windows; on solid-colour footage slide and wipe cannot be told apart (no texture moves). Vocabulary decided against this FFmpeg build: `slide_*` = new shot covers the old (`cover*`), `push_*` = both move (`slide*`), `wipe_*` = `wipe*`; shader-type downgrades live in `render/capabilities.py`. Timeline: `plan.apply_transitions` grows each clip over its windows (`lead`/`tail` = window length), `trans[i]` graph nodes render xfade segments, `assemble` cuts bodies and concatenates; skipped neighbours keep a hard cut. **Not done:** naming windows with the video AI (no key to test; the coarse class is used), and requirements counting lead/tail (`PlanShot.frames` already includes them; `requirements.py` arrives in M7/M10).
- 2026-11-11 M7: `evidence/speed.py` (pace = mean Farneback flow of moving pixels at 320 px; means, not medians, because slow motion without interpolation repeats frames and pace alternates 0 / full), freezes by changed-pixel count (mean difference read only-the-bar-moves frames as frozen), `evidence/effects.py` (flash exact; RGB split, blur bursts, vignette against mid-edges so a bright subject is not a vignette; grain and glow left to the video AI). A flash was read as a cut by PySceneDetect: `transitions.py` now drops boundary candidates with the same shot on both sides of a short bright burst. One time map `render/shot.pieces` (output frame -> source position; a freeze `[a, b)` holds frame a and frame b moves on one step) drives the renderer, `requirements.footage_frames` and the synthetic truth. Renderer: `settb=1/30000` then a piecewise `setpts` and `fps=30:round=up` (the 1/30 timebase after the first `fps` floored fractional times, which showed frames two to three steps early at 3x). Measured: ramp 1x->3x->0.5x recovered as 0.97 / 3.10 / 0.44 with breakpoints at +0 and +1 frames, freeze exact, flash exact; rendered ramp shows the exact source frame for every output frame; marker pass reproduces speed factors within 25%, freeze within 2 frames, flash exactly. Effects are drawn in the final assemble pass (`capabilities.effect_filter`). **Not done:** reverse detection (needs the video AI; the renderer supports `reverse`). Suite time is now dominated by OCR (~0.35 s per call); M4-M6 full run took 1h40 with prototypes competing for CPU.
- 2026-11-11 M8: `colour.py` (per-slot Lab mean/spread, saturation, contrast; text and overlays masked), colour match in `render/shot.py` (eq + colorbalance from the clip's sampled stats toward the target, limited to MAX_SHIFT; moves brightness, warmth and saturation toward the target in the test), `layout.py` (letterbox / blur fill from row detail with a full-width-detail guard; split screens from mean-colour steps checked in 6 of 8 strips; picture in picture from rectangles whose four sides are covered by edges of the blurred time-mean colour picture, at least 20% per side and unlike their surroundings), `overlays.py` (pixels steady over the whole reel minus text). Box layouts render through one multi-input ffmpeg graph (`layout_graph`) over black or, for blur fill, over the blurred main clip; split / pip / collage slots ask the match step for one clip per box (ShotSpec layout `collage`). Measured on the textured synthetic reel: split_v, pip, blur_fill and the overlay all IoU > 0.7, and the marker pass rebuilds each. Lessons recorded in code: gray loses the colour difference between two textures, heavy texture breaks straight runs (gaps bridged, rectangles by side coverage), marker clips for extra boxes must differ in hue (golden-angle numbering wraps) and be shaped like their box. Plain-footage false positives found in this milestone's run and fixed: letterbox on flat colour, camera pans from a moving bar (RANSAC needs 25 inliers), speed and blur from animated captions (text boxes masked). Coverage: `Slot.evidence` lists consumed measurement items, so coverage is back to 1.0. **Not done:** masks and cutouts (video-AI led, no key), layer motion, overlays shown for only part of the reel, and user-supplied sticker images (overlay slots render as solid boxes only in the marker pass). Text style 'box' detection fires on large digits with a coloured outline; not fixed.
- 2026-11-11 M9: `render/overlay.py` with the `OverlayEngine` protocol, `OverlaySpec` and a HyperFrames adapter through Kinocut (`hyperframes_init`, generated HTML + GSAP composition, `hyperframes_render` to VP9 WebM with alpha, re-cut to exactly n frames). Routed to the engine: text animations libass cannot do (bounce, word highlight with growth, unknown), overlay slots with a user image, and whip transitions (`capabilities` marks them `overlay:<kind>` only when an engine is installed, else the xfade downgrade with its loss). `assemble` composites the layer under the libass text and effects; `transition.render` cuts the two overlaps and lets the engine draw the segment. Measured: a 60-frame layer with a bounce, a word highlight and a box renders to exactly 60 frames and composites; an engine whip renders to exactly 12 frames and `evidence/transitions.py` classifies it `whip_left`. Plan and template only ever carry `overlay:<kind>`. **Not done:** the Remotion adapter (HyperFrames works on this machine, so it stays second; installing Remotion and Chrome headless for a second engine is not justified until HyperFrames fails somewhere), spin / zoom-out / glitch as engine transitions (still xfade downgrades with a recorded loss). The overlay layer is rendered inside `assemble`, not as a cached graph node, so a re-assemble re-renders it (~35 s).
- 2026-11-11 M10: `extract.decide` (one `openrouter.chat_json` call returning per-path keep/swap/drop with reasons and per-slot role/function; code applies only bindings, roles and functions, asserts slot timing and n_frames unchanged, lists drops in `template.dropped`; skipped when no LLM key, so default bindings stand), `requirements.derive/apply` (media, orientation from layout box, footage frames incl. transition overlaps, camera the clip itself must have: none when the renderer redoes the move), `preproduction.screen` (hard filter: too short for half the needed footage, or a photo for a slot whose motion the template cannot add; otherwise ok or adaptable), `candidates` + `assign` (scipy `linear_sum_assignment` over judged candidates; a slot left over reuses its best clip rather than going missing), `Match.label` adaptable with a chip style, filming instructions with min seconds, framing and orientation. Tested with the LLM stubbed. Decisions run in the analysis thread through `asyncio.run`.
- 2026-11-11 M11: `roundtrip.validate` (same-shot pass, marker pass over every track built so far, coverage, omission critic through the video AI, typed patches: re-tiling slots and shifting caption start/end by the measured offset; up to 3 rounds, best kept; passed = timing and audio rows all ok, coverage 1.0 and 90% of marker rows ok), `roundtrip.cleanup` (refs.validated = 1; proxy, rt/, mk/, frames/ deleted unless PVE_KEEP_REFS; marker and verifier renders ingested only to be measured are removed right after), progress messages from the analysis thread, a `template` card (delta table, recorded losses, possible omissions, low-confidence fields with Accept / Edit) backed by `project.template_report` and `POST confirm-template-field` (labelled fields only; timing refused). Verifier: layer 0 lint (clips exist, frames add up, the new words' estimated width stays in the safe area) and layer 2 structure (the final render measured for boundaries and text timing; identical captions back to back count as one) before the content and LLM layers; a failing deterministic layer forces REPAIR. Found while wiring: marker-pass clips must not draw their slot digit (it collides with centre captions in OCR); a textured background was taken for a caption box (needs a flat cluster now); two different captions in the same place on consecutive shots were one track (tracks now split on a stable string change). The LLM key in `.env` is set, so `decide` runs for real in the product; the flow test stubs it. `test_flow.py` uses flat-colour reference markers: on 50% noise texture OCR boxes for large digits come out frame-wide (open weakness).
- 2026-11-11 M12: stage durations (`stage_time`, from the `pipeline.spawn` wrapper) and LLM token usage per call (`llm_usage`, from `openrouter`, attributed through a `state.CURRENT` context var) go to `project_events`; video-AI calls retry with exponential backoff on rate-limit errors (3 retries, 5 s doubling) and answers stay cached per fingerprint + prompt version; README rewritten (setup, keys, gold reels, reading the delta report); `tests/test_ops.py` holds the gold regression check (skips until `gold/targets.json` exists). HyperFrames pages loaded GSAP from a CDN and failed offline; they now use the GSAP the pinned hyperframes package vendors, copied into each project. **Not done:** gold baseline, targets and the loss review: no gold reels exist (decision 2). Full suite: 96 passed.

---

## 10. Known weak spots (plan accordingly)

1. Detection is harder than rendering. Speed ramps, reverse, masks and blend modes will be the least reliable tracks. They carry low confidence and go to the confirm card.
2. No reel benchmark exists. The gold set is the only measure of real accuracy, and it does not exist yet.
3. Fonts are a nearest match from a short list.
4. Colour is a statistics match, not a grade copy. It will look close, not identical.
5. HyperFrames on Windows with transparent output is unconfirmed until M0.
6. Thresholds in this plan are guesses. Expect to tune every one of them on the first real reels.
7. The MVP scope is large. The order protects against that: M2 already ships a working product, and each later milestone is independently useful.
