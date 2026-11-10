"""Prefill a gold label file from the detectors (docs/mvp-plan.md 5.2).

    .venv\\Scripts\\python -m tools.label ..\\gold\\<reel>\\<file>.mp4

Writes labels.draft.json and shots/shot_NN.png (contact sheets) next to the reel. Correct the draft by scrubbing
the video frame by frame, not by accepting it, then save it as labels.json (format: gold/README.md)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

THUMB_W = 180
PER_SHOT = 4


def empty_labels(reel: str, n_frames: int) -> dict:
    return {"reel": reel, "fps": 30, "n_frames": n_frames, "cuts": [], "transitions": [], "texts": [],
            "effects": [], "speed": [], "camera": [], "layout": [], "overlays": []}


def contact_sheets(proxy: Path, cuts: list[int], n_frames: int, out: Path) -> None:
    from app.clients import ff

    info = ff.video_stream(ff.probe(proxy))
    th = int(THUMB_W * int(info["height"]) / int(info["width"])) // 2 * 2
    frames = ff.decode(proxy, THUMB_W, th)
    out.mkdir(exist_ok=True)
    bounds = [0, *cuts, n_frames]
    for k, (s, e) in enumerate(zip(bounds[:-1], bounds[1:])):
        picks = np.linspace(s, e - 1, PER_SHOT).round().astype(int)
        sheet = Image.new("RGB", (THUMB_W * PER_SHOT, th + 16), "black")
        d = ImageDraw.Draw(sheet)
        for j, f in enumerate(picks):
            sheet.paste(Image.fromarray(frames[min(f, len(frames) - 1)]), (j * THUMB_W, 16))
            d.text((j * THUMB_W + 4, 2), f"frame {f}", fill="white")
        sheet.save(out / f"shot_{k + 1:02d}.png")


def main() -> None:
    reel = Path(sys.argv[1]).resolve()
    from app import evidence
    from app.stages import analyze

    src = analyze.ingest(reel)
    ev = evidence.run_all(src.key)
    labels = empty_labels(reel.name, src.n_frames)
    labels["cuts"] = sorted(i.data["frame"] for i in ev.track("cuts"))
    labels["transitions"] = [{"type": i.data.get("type", "other"), "start": i.start, "end": i.end}
                             for i in ev.track("transitions") if i.end > i.start]
    labels["texts"] = [{"text": i.data["text"], "start": i.start, "end": i.end, "box": i.data.get("box")}
                       for i in ev.track("text")]
    labels["effects"] = [{"type": i.data.get("type"), "frame": i.start, "length": i.end - i.start}
                         for i in ev.track("effects")]
    (reel.parent / "labels.draft.json").write_text(json.dumps(labels, indent=1), encoding="utf-8")
    contact_sheets(analyze.proxy_path(src.key), labels["cuts"], src.n_frames, reel.parent / "shots")
    print(f"wrote {reel.parent / 'labels.draft.json'} and {len(labels['cuts']) + 1} contact sheets")


if __name__ == "__main__":
    main()
