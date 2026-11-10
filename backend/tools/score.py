"""Score evidence tracks against hand-labelled gold reels (docs/mvp-plan.md 5.2).

    .venv\\Scripts\\python -m tools.score            # every gold/<reel>/labels.json
    .venv\\Scripts\\python -m tools.score --no-log   # do not append to gold/history.jsonl

Prints precision, recall, F1 and mean absolute frame error per track; appends the run to gold/history.jsonl."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.stages import compare  # noqa: E402

GOLD = config.ROOT / "gold"
TOL = {"cuts": 1, "flashes": 1}  # frame tolerance per point-event track
MIN_IOU = {"transitions": 0.3, "texts": 0.5, "freezes": 0.5}


def reel_file(d: Path) -> Path | None:
    return next((p for p in sorted(d.iterdir()) if p.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv")), None)


def predictions(reel: Path) -> dict:
    """Run the analysis instruments on one reel; returns label-shaped predictions for the tracks that exist."""
    from app import evidence
    from app.stages import analyze

    src = analyze.ingest(reel)
    ev = evidence.run_all(src.key)
    out: dict = {"n_frames": src.n_frames, "cuts": sorted(i.data["frame"] for i in ev.track("cuts"))}
    if ev.track("transitions"):
        out["transitions"] = [{"type": i.data.get("type", "other"), "start": i.start, "end": i.end}
                              for i in ev.track("transitions") if i.end > i.start]
    if ev.track("text"):
        out["texts"] = [{"text": i.data["text"], "start": i.start, "end": i.end, "box": i.data.get("box")}
                        for i in ev.track("text")]
    if ev.track("effects"):
        out["flashes"] = [i.start for i in ev.track("effects") if i.data.get("type") == "flash"]
    return out


def score(labels: dict, pred: dict) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for track in ("cuts", "flashes"):
        if track in pred:
            truth = labels.get(track) if track == "cuts" else [e["frame"] for e in labels.get("effects", [])
                                                                if e["type"] == "flash"]
            p, r, f1, mae = compare.match_events(pred[track], truth or [], TOL[track])
            rows[track] = {"precision": p, "recall": r, "f1": f1, "mae": mae, "n_truth": len(truth or [])}
    for track in ("transitions", "texts"):
        if track in pred:
            truth = [(t["start"], t["end"]) for t in labels.get(track, [])]
            p, r, f1, mae = compare.match_spans([(t["start"], t["end"]) for t in pred[track]], truth, MIN_IOU[track])
            rows[track] = {"precision": p, "recall": r, "f1": f1, "mae": mae, "n_truth": len(truth)}
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-log", action="store_true")
    a = ap.parse_args()
    reels = [d for d in sorted(GOLD.iterdir()) if (d / "labels.json").exists()] if GOLD.exists() else []
    if not reels:
        print(f"no gold reels in {GOLD} (each needs <reel>/labels.json and the video file)")
        return
    run = {"time": time.time(), "reels": {}}
    print(f"{'reel':24} {'track':12} {'P':>6} {'R':>6} {'F1':>6} {'MAE':>6} {'n':>4}")
    for d in reels:
        f = reel_file(d)
        if not f:
            print(f"{d.name:24} missing video file")
            continue
        rows = score(json.loads((d / "labels.json").read_text(encoding="utf-8")), predictions(f))
        run["reels"][d.name] = rows
        for track, m in rows.items():
            print(f"{d.name:24} {track:12} {m['precision']:6.3f} {m['recall']:6.3f} {m['f1']:6.3f} {m['mae']:6.2f} "
                  f"{m['n_truth']:4d}")
    if not a.no_log:
        with (GOLD / "history.jsonl").open("a", encoding="utf-8") as h:
            h.write(json.dumps(run) + "\n")


if __name__ == "__main__":
    main()
