# PVE Backend Schema

Three stores: SQLite (`data/pve.db`), per-reference IR files (`data/refs/<key>/ir/*.json`), and the filesystem under `data/`. Source of truth for tables is `backend/app/db.py`; for IR models it is `backend/app/ir.py`. If this file and the code disagree, the code is right: fix this file.

## 1. SQLite tables

WAL mode, one connection per thread. JSON columns (`db.JSON_COLS`) are stored as text and decoded on read: `error, brief, shots, matches, plan, verifier, analysis, card, data, template, delta`.

### conversations
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | 12 hex chars from `db.new_id()` |
| title | TEXT | "New Reel" at creation |
| project_id | TEXT | one project per conversation |
| created | REAL | epoch seconds |

### messages
`id INTEGER PK AUTOINCREMENT, conv_id, role ("user"/"assistant"), kind, content TEXT, card (JSON), created`. A message is either text or a card; `kind` selects the card component in `cards.tsx`.

### projects
| Column | Notes |
|---|---|
| id, conv_id | PK, back-reference |
| state | one of `state.STATES` |
| error | JSON; set when state is FAILED |
| goal, ref_url | the user's description and the reference link |
| reference_id | key into `reference_cache` / `templates` |
| brief (JSON), brief_confirmed | the brief and whether the user confirmed it |
| shots (JSON) | `ShotSpec` list derived from the template (UI contract) |
| matches (JSON) | per shot: `asset_id`, `label` (exact, similar, adaptable, missing), `reason`, `extra_assets` |
| plan (JSON), approved | render plan and the approval flag |
| music_asset | uploaded soundtrack asset id (legacy plans only; reference audio is used for new templates) |
| draft_n, final_path, verifier (JSON) | latest draft number, final MP4, last verifier report |
| created, updated | epoch seconds |

### assets
`id, kind ("clip"/"music"), filename, path, duration, status ("indexing", "ready", "too_short", "failed"), tl_asset_id, tl_indexed_id, error, created`. `tl_*` are TwelveLabs ids. Clips shorter than `MIN_INDEX_SECONDS = 4.0` are `too_short`.

### reference_cache
`key PK, platform, fingerprint, analysis (JSON), created`. Legacy analysis cache by link or file.

### templates
| Column | Notes |
|---|---|
| key PK | reference key (`fingerprint[:16]`) |
| title, shots (JSON), analysis_version, created | legacy fields; `shots` is the derived `ShotSpec` list |
| template (JSON) | source of truth: `ir.Template` |
| delta (JSON) | `ir.Delta` from validation |
| ir_version | IR schema version |

Columns `template`, `delta`, `ir_version` were added through `db.MIGRATIONS` (`ALTER TABLE` inside `try/except OperationalError`, because `CREATE TABLE IF NOT EXISTS` does not add columns). New columns go in the same list.

### refs
`key PK, fingerprint, n_frames, proxy_path, validated (0/1), created`. `validated = 1` lets cleanup delete `proxy.mp4`, `rt/`, `mk/`, `frames/` unless `PVE_KEEP_REFS=1`.

### graph_runs
`(project_id, node) PK, hash, status, cached (0/1), output_path, error, updated`. One row per render graph node (`prep`, `trans`, `overlay`, `assemble`). A node re-runs only when its hash changes; the hash includes `PlanShot` frame fields.

### drafts
`id INTEGER PK AUTOINCREMENT, project_id, n, path, plan (JSON), verifier (JSON), created`.

### project_events
`id INTEGER PK AUTOINCREMENT, project_id, type, data (JSON), created`. Types in use: `stage_time` (duration per stage), `llm_usage` (tokens per call, attributed through `state.CURRENT`).

### preferences, match_feedback, kv
- `preferences(key PK, value, count)`: learned user preferences.
- `match_feedback(id, descriptor, asset_id, accepted, created)`: accept/reject signals for matching.
- `kv(key PK, value)`: small settings.

### Relationships

```
conversations 1--1 projects 1--* messages (by conv_id)
projects 1--* drafts, graph_runs, project_events
projects *--* assets (through projects.matches JSON)
projects *--1 templates (projects.reference_id = templates.key)
templates 1--1 refs (same key)
```

There are no foreign-key constraints. Deletes cascade by hand in `main.delete_conversation` and `main.delete_asset`.

## 2. Reference IR files

```
data/refs/<key>/
  proxy.mp4     30 fps constant, long side at most 1080 (deleted after validation)
  frames/       memory-mapped grayscale and colour stacks (deleted after validation)
  rt/  mk/      round-trip and marker-pass renders (deleted after validation)
  ir/source.json evidence.json meaning.json observed.json template.json delta.json
```

Each `ir/*.json` is `{"v": <stage version>, "inputs": <hash>, "data": <model>}`. A stage reruns only when its version or inputs change. Load and save with `ir.load(key, layer)` and `ir.save(key, layer, model)`.

## 3. IR models (`backend/app/ir.py`, Pydantic v2)

Timebase: integer frames at 30 fps; `ir.f2s(frame) = frame / FPS`, `ir.s2f` the inverse. Seconds appear only for user clips, ASS timestamps and the UI.

| Model | Purpose | Key fields |
|---|---|---|
| `F[T]` | one value that carries its origin | `value, raw, conf, source, evidence[], binding` (`keep`, `swap`, `drop`) |
| `Item` | one evidence measurement, append-only | `id "<track>_<n>", track, start, end, data, conf, tool` |
| `Source` | reference facts | `key, fingerprint, n_frames, width, height, src_fps` |
| `Evidence` | all items | `items`, `.track(name)` |
| `Box`, `Key` | normalised box, one keyframe | `x,y,w,h`; `frame, box, scale, rotation, opacity` |
| `Slot` | one shot | `id "s01", start, end, media, role, function, subject, action, shot_size, angle, layout, layout_boxes, camera, camera_path, shake, speed[(pos,factor)], reverse, freeze[(a,b)], colour, requirement, evidence` |
| `Transition` | between slots | `after_slot, type, start, end, params, render, loss` (`start == end` is a hard cut) |
| `Effect` | timed effect | `id, type, start, end, strength, params, render, loss` |
| `TextEvent` | on-screen text | `id, start, end, text (swap), role, keys, style, anim_in, anim_out, anim_*_frames, max_chars` |
| `Overlay` | sticker, emoji, shape, frame, progress bar, logo | `id, kind, start, end, keys, description, binding` |
| `Layer` | mask, cutout, moving layer (video-AI led, conf capped at 0.4) | box at start, optional second key, loss |
| `Template` | the artifact the product runs on | `v, key, n_frames, audio, slots, transitions, effects, texts, overlays, narrative, unsupported, low_conf, dropped` |
| `Delta` | validation result | `rows[DeltaRow(track, metric, reference, render, gap, ok)], coverage, passed` |

Invariants the validator must check (also the model join step):
1. Slots tile `[0, n_frames)` with no gap or overlap.
2. Every transition's `after_slot` exists; window lies inside neighbouring slots.
3. Every evidence id is used, in `dropped` (with a reason), or in `unsupported`.
4. Every `F` keeps its `raw` value; an out-of-vocabulary answer becomes `other` with the raw word, never a default.

Closed vocabularies (each has `other`): `TransitionType`, `EffectType`, `CameraMove`, `TextAnim`, `Layout`, `OverlayKind`, `Role`, `TextRole`, `ShotSize`, `Media`. Full lists in `ir.py` and `mvp-plan.md` section 4.

## 4. Render plan (`backend/app/models.py`)

`PlanShot` and `Plan` gained optional fields so legacy plans still render:
- `PlanShot`: `frames, lead, tail, speed_curve, reverse, freeze, camera_path, layout_boxes, colour, shake`.
- `Plan`: `n_frames, transitions, effects, texts, overlays, audio_mode ("legacy" or "reference")`.

`ShotSpec` stays the UI contract. `extract.to_shotspecs(template, legacy_fields)` derives it from the template.

## 5. Filesystem layout under `data/`

| Path | Content |
|---|---|
| `pve.db` | SQLite |
| `assets/` | uploaded clips and music |
| `projects/<pid>/` | per-project render nodes, drafts, `ref_tmp/` |
| `ref_audio/<cache key>.wav` | reference soundtrack; `Template.audio` points here |
| `refs/<key>/` | IR and proxies (section 2) |
| `mixkit/`, `vn/` | template reader samples and status table |

`data/` is gitignored.

## 6. Planned additions for the model path (not built)

Proposed; confirm before implementing.

| Item | Shape |
|---|---|
| `model_runs` table | `id, ref_key, stage (trial, pilot, whole, largest, prod), checkpoint, gate_threshold, chunks, kept_frames, total_frames, tokens, template (JSON), score (JSON), created` |
| Training sample record | JSON lines: `{reel_id, source: real|synthetic, frames[], gap_notes[], label: Template}` kept outside SQLite under `training/` |
| `conversion_reports` | per-reel list of items the converter could not build: `ref_key, item_id, reason` |
| `Template.v` bump | when the model JSON adds fields; keep the old `load` path working |

The model must emit `ir.Template` exactly. Do not invent a second schema.
