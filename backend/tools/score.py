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
    vids = [p for p in sorted(d.iterdir()) if p.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv")]
    # the README layout is <name>/<name>.mp4; other videos in the folder (compare.mp4) are outputs
    return next((p for p in vids if p.stem == d.name), vids[0] if vids else None)


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
    out["effects_all"] = [{"type": i.data["type"], "start": i.start, "end": i.end} for i in ev.track("effects")]
    for c in ev.track("camera"):  # zoom punches are effects too (drawn by the camera path)
        out["effects_all"] += [{"type": "zoom_punch", "start": c.start + int(a), "end": c.start + int(b) + 1}
                               for a, _, b, _ in c.data.get("punches", [])]
    out["shake"] = [(c.start + int(a), c.start + int(b)) for c in ev.track("camera")
                    for a, b, _, _ in c.data.get("shake_windows", [])]
    out["shake"] += [(c.start, c.end) for c in ev.track("camera")
                     if c.data.get("value") == "shake" and not c.data.get("shake_windows")]
    out["match_cuts"] = [i.data["frame"] for i in ev.track("match_cuts")]
    out["layers"] = [(i.start, i.end) for i in ev.track("masks")]
    anim = {i.data["text_id"]: i.data for i in ev.track("text_anim")}
    for t, i in zip(out.get("texts", []), ev.track("text")):
        a = anim.get(i.id, {})
        lit, words = i.data.get("lit") or [], i.data.get("words") or []
        t["anim_in"] = "word_highlight" if len({w["start"] for w in lit}) >= 2 else "typewriter" if words \
            else a.get("in", "none")
        t["rotation"] = i.data.get("rotation", 0.0)
    return out


def _row(p: float, r: float, f1: float, mae: float, n: int) -> dict:
    return {"precision": p, "recall": r, "f1": f1, "mae": mae, "n_truth": n}


def score_optional(labels: dict, pred: dict) -> dict[str, dict]:
    """Tracks for the optional label fields (gold/README.md): scored only on reels whose labels carry the field."""
    rows: dict[str, dict] = {}
    gold_fx = [e for e in labels.get("effects", []) if e["type"] != "flash"]
    for kind in sorted({e["type"] for e in gold_fx} | {e["type"] for e in pred.get("effects_all", []) if gold_fx}):
        if kind == "flash":
            continue
        truth = [(e["frame"], e["frame"] + e.get("length", 1)) for e in gold_fx if e["type"] == kind]
        got = [(e["start"], e["end"]) for e in pred.get("effects_all", []) if e["type"] == kind]
        rows[f"fx:{kind}"] = _row(*compare.match_spans(got, truth, 0.3), len(truth))
    if "shake" in labels:
        truth = [(w["start"], w["end"]) for w in labels["shake"]]
        rows["shake"] = _row(*compare.match_spans(pred.get("shake", []), truth, 0.3), len(truth))
    if "match_cuts" in labels:
        rows["match_cuts"] = _row(*compare.match_events(pred.get("match_cuts", []), labels["match_cuts"], 1),
                                  len(labels["match_cuts"]))
    if "layers" in labels:
        truth = [(x["start"], x["end"]) for x in labels["layers"] if x.get("kind") == "shape_mask"]
        rows["shape_masks"] = _row(*compare.match_spans(pred.get("layers", []), truth, 0.3), len(truth))
    gold_anim = [t for t in labels.get("texts", []) if t.get("anim_in")]
    if gold_anim and pred.get("texts"):  # accuracy over gold events that found a predicted event
        hits = []
        for g in gold_anim:
            p = max(pred["texts"], key=lambda x: _iou((x["start"], x["end"]), (g["start"], g["end"])))
            if _iou((p["start"], p["end"]), (g["start"], g["end"])) >= MIN_IOU["texts"]:
                hits.append(p.get("anim_in") == g["anim_in"])
        acc = sum(hits) / len(hits) if hits else 0.0
        rows["text_anim"] = _row(acc, acc, acc, 0.0, len(gold_anim))
    return rows


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    return inter / max(1, max(a[1], b[1]) - min(a[0], b[0]))


def score(labels: dict, pred: dict) -> dict[str, dict]:
    rows: dict[str, dict] = score_optional(labels, pred)
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


def agreement(a: list, b: list) -> dict[str, float]:
    """Share of slots where two providers' SlotMeanings give the same value, per field."""
    from app.stages.meaning import VOCAB

    out = {}
    for f in VOCAB:
        pairs = [(x.fields.get(f), y.fields.get(f)) for x, y in zip(a, b)]
        pairs = [(x, y) for x, y in pairs if x and y]
        out[f] = sum(x.value.lower() == y.value.lower() for x, y in pairs) / len(pairs) if pairs else float("nan")
    return out


def provider_ab(reels: list[Path]) -> None:
    """The A/B the research asked for: Gemini vs Pegasus on the same measured slots."""
    from app import evidence
    from app.stages import analyze, fusion, meaning

    rows: dict[str, list[float]] = {}
    for d in reels:
        f = reel_file(d)
        src = analyze.ingest(f)
        ev = evidence.run_all(src.key)
        slots, _ = fusion.slots_from_cuts(src, ev)
        got = {}
        for p in ("gemini", "pegasus"):
            with meaning.Session(src.key, f, p) as s:
                got[p] = meaning.describe_slots(s, slots, ev)
        for field, v in agreement(got["gemini"], got["pegasus"]).items():
            rows.setdefault(field, []).append(v)
    print(f"{'field':12} {'agreement':>9}  (gemini vs pegasus, mean over {len(reels)} reels)")
    for field, vs in rows.items():
        vs = [v for v in vs if v == v]
        print(f"{field:12} {sum(vs) / len(vs) if vs else float('nan'):9.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--providers", action="store_true", help="per-field agreement between Gemini and Pegasus")
    a = ap.parse_args()
    reels = [d for d in sorted(GOLD.iterdir()) if (d / "labels.json").exists()] if GOLD.exists() else []
    if not reels:
        print(f"no gold reels in {GOLD} (each needs <reel>/labels.json and the video file)")
        return
    if a.providers:
        provider_ab(reels)
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
