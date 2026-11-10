# Gold reels

Hand-labelled reference reels. They are the only measure of real detector accuracy. Use only reels you own or have rights to. Video files are gitignored; only `labels.json` is committed.

## Layout

```
gold/
  <name>/
    <name>.mp4          the reel (gitignored)
    labels.json         your corrected labels (committed)
    labels.draft.json   detector prefill (do not commit)
    shots/shot_NN.png   contact sheets, four frames per detected shot
  history.jsonl         one line per scoring run (tools/score.py)
```

## Making a label file

1. Put the reel in `gold/<name>/`.
2. From `backend/`: `.venv\Scripts\python -m tools.label ..\gold\<name>\<name>.mp4`
3. Open the reel in a player that steps one frame at a time (mpv: `.` and `,`; VLC: `e`). The analysis runs at a constant 30 fps, so convert any timestamp with `frame = round(seconds * 30)`.
4. Correct `labels.draft.json` **by watching the video, not by trusting the draft.** The draft comes from the same detectors being scored; accepting it makes the score meaningless. Check every cut, add the ones it missed, delete the false ones.
5. Save it as `labels.json`.
6. Score: `.venv\Scripts\python -m tools.score`

## Format

All times are integer frames at 30 fps. `start` is inclusive, `end` exclusive. Boxes are `[x, y, w, h]`, normalised 0..1, origin top-left.

```json
{
  "reel": "name.mp4",
  "fps": 30,
  "n_frames": 450,
  "cuts": [31, 77, 120],
  "transitions": [{"type": "fade", "start": 70, "end": 84}],
  "texts": [{"text": "3 tips for...", "start": 0, "end": 60, "box": [0.1, 0.12, 0.8, 0.08]}],
  "effects": [{"type": "flash", "frame": 120, "length": 2}],
  "speed": [{"start": 120, "end": 160, "factor": 0.5}],
  "camera": [{"shot": 1, "move": "zoom_in"}],
  "layout": [{"shot": 1, "layout": "single"}],
  "overlays": [{"kind": "sticker", "start": 10, "end": 90, "box": [0.7, 0.1, 0.2, 0.1]}]
}
```

- `cuts`: the first frame of each new shot. A transition's cut is the frame where the new shot first dominates.
- `transitions`: gradual boundaries only, with the window where both shots are visible. Types use the vocabulary in `backend/app/ir.py` (`TransitionType`).
- `texts`: one entry per on-screen text event, words exactly as shown, first and last frame it is visible.
- `effects`: `type` from `EffectType` in `ir.py`; `frame` is the first affected frame.
- `speed`: only segments that are clearly not 1x. Leave empty if unsure.
- `camera`, `layout`: one entry per shot, `shot` is 1-based, values from `CameraMove` and `Layout`.
