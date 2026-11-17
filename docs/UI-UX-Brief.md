# PVE UI and UX Brief

For whoever designs or extends the front end. Based on `frontend/src` (React 18, Vite, plain CSS in `styles.css`) on 2026-11-18. Keep this brief short in your head: one chat thread, cards that carry decisions, nothing else.

## 1. Principles

1. **Chat first.** The product is one conversation per reel. The user never navigates between pages to finish a reel.
2. **Cards carry decisions.** Text bubbles inform; cards hold the buttons that move the project forward. One primary action per card.
3. **Honest about loss.** Whatever the renderer could not reproduce is shown, not hidden. Low-confidence fields are asked, not guessed.
4. **Frames, not guesses.** Timing is shown in seconds for people, stored in frames. Never show raw frame numbers unless the user opens details.
5. **No audio controls.** The output uses the reference's audio. Do not add a music picker to the new-template flow.
6. **Approve is deliberate.** Production starts only from the Approve button. Nothing in the chat triggers it.

## 2. Users and context

Creators editing on a laptop, often with the reference Reel open on their phone. Familiar with CapCut, VN, InShot; not with timelines or frame counts. They want to know what to film, not how the template works.

## 3. Layout (exists today)

```
+-----------+---------------------------------------------+
| Sidebar   | Thread (max ~760 px column)                  |
| New Reel  |   assistant bubble                           |
| convo 1   |   user bubble (right, tinted)                |
| convo 2   |   Card (max 640 px)                          |
| ...       |                                              |
|           +---------------------------------------------+
|           | Composer: textarea + send; drop clips here   |
+-----------+---------------------------------------------+
```

- Sidebar 260 px, hidden under 700 px width. Needs a drawer on small screens (gap).
- Thread and composer share a centred column: `padding: 0 max(16px, calc(50% - 380px))`.
- Error banner above the thread for FAILED states.

## 3.1 Visual tokens (`styles.css`)

- Colours: `--bg, --fg, --muted, --side, --line, --accent #2563eb, --user, --ok #16a34a, --warn #d97706, --bad #dc2626`. Light and dark via `prefers-color-scheme`.
- Type: system UI, 15 px base, 1.5 line height. Radius 8 px controls, 12 px cards, 14 px bubbles, 99 px chips.
- Chips: `exact`/`done` green, `similar`/`running` amber, `adaptable` blue, `missing`/`failed` red. Never rely on colour alone: the label text is always present.

## 4. Cards (screens in the flow)

| Card | When | Content | Primary action |
|---|---|---|---|
| Reference input | NEW, link failed | Link field, file drop, one-line prompt | Analyse |
| Progress | ANALYZING, PRODUCING | Stage list with running / done / cached chips | none; Cancel as a text link |
| **Template** | after analysis | Delta table (track, what was compared, gap, pass/fail), "Shown differently" list (renderer downgrades), "Possible omissions", "Please confirm" rows with Accept / Edit | Continue to brief |
| Brief | BRIEF | Goal, captions on/off, music line (legacy), editable fields | Confirm brief |
| Shots | SHOT_SPECS | Numbered list: purpose, length in seconds, text slots with character limit; skip toggle | Confirm shots |
| Matches | PREPRODUCTION, AWAITING_* | One row per shot: clip name, chip, reason; Swap; for missing: filming instruction (min seconds, framing, orientation, what to show); Skip | Approve (enabled when nothing is missing or skipped) |
| Draft / Final | VERIFYING, FINAL | 9:16 video player (max 320 px wide), verifier summary, Download | Download; "Ask for a change" is the composer |
| Error | FAILED | Plain reason, what was tried | Retry |

Rules for every card: title in a 16 px bold line, one sentence of context, then content, then actions at the bottom. Old cards collapse to one muted line (`.card.old`) once superseded.

## 5. Key flows to get right

1. **First minute.** New Reel, welcome message tells what to paste. Paste a link or drop a file. Within 2 seconds the Progress card appears. Progress messages are plain ("Reading the cuts", "Reading the text", "Checking the template").
2. **Reading the template card.** Lead with one sentence: "Template ready: 14 shots, 18.4 s, timing exact." Then the pass/fail table. A failed timing row is a red "Template is wrong, retry" state, not a soft score. Downgrades read as "Shown differently: spin transition drawn as a radial wipe".
3. **Confirming fields.** Each low-confidence row shows the value, what the model saw (`raw`), Accept and Edit. Accept and Edit both mark the field as the user's. Timing cannot be edited here.
4. **Matching.** The user can drag clips into the chat at any time; newly indexed clips trigger a re-match of open shots only. A "missing" row always says what to film.
5. **Approve.** Shows the summary (shots, seconds, clips used, captions) once more. After approval the Matches card goes read-only.
6. **Revision.** A typed change in the composer produces a new draft; the previous draft stays playable (drafts are numbered).

## 6. Microcopy (use the `ux-copy` skill for new strings)

- Say shots, clips, text, transitions. Not slots, evidence, IR, tracks, bindings.
- Errors name the cause and the next step: "Couldn't download that link. Upload the video file instead."
- Chip labels: Exact, Similar, Adaptable, Missing. Adaptable = "fits after a crop or small speed change".
- No exclamation marks, no emoji in system text.

## 7. Accessibility

- Contrast at least 4.5:1 for text in both themes; check chips in dark mode.
- Every button reachable by keyboard; visible focus ring (add: none today).
- Video has controls and a text summary beneath it; delta table uses real `<table>` with header cells.
- Chat updates announce through an `aria-live="polite"` region (gap).
- Touch targets at least 44 px on small screens (gap).
- Respect `prefers-reduced-motion` for any progress animation.

## 8. Responsive behaviour

Under 700 px: sidebar becomes a drawer behind a menu button, cards go full width, the video card stays 320 px max, composer stays pinned. Tables scroll horizontally inside the card, never the page.

## 9. Empty, loading and error states

- No conversations: one button, "New Reel".
- Analysing: Progress card with a time hint ("about 1 to 5 minutes").
- No clips yet at matching: Matches card shows every row as Missing with filming instructions, plus a drop zone.
- Server unreachable: banner "Can't reach the backend" with Retry; keep the thread visible.

## 10. Future surfaces (not built; do not start without a decision)

1. **Open as project.** After the model path exists: a button on the Final card to open the FilmCraft / EffectCraft project, with the converter's loss report shown as a list.
2. **Template library.** `GET /api/templates` exists; no browse UI yet. A grid of saved templates with length and shot count.
3. **Developer view.** Gold-set scores per track over time (reads `gold/history.jsonl`). Internal only.
4. **Per-region diff.** For captions that pop in: a 4 x 4 grid heat map in the template card, only if the per-region test is built.

## 11. Open design questions

1. Should the template card default to collapsed after the first confirm? (Lean: yes, collapse to one line.)
2. How to explain "adaptable" in one short phrase.
3. Whether to show timing in frames for power users (details toggle).
4. Where the audio-rights notice sits (see `docs/Security.md` 4.1): at analysis start or at approve.
