"""Build a template from each gold reel, render it back, and compare (docs/mvp-plan.md 5.3 on the gold set).

    .venv\\Scripts\\python -m tools.templates                  # every gold/<reel> with labels.json
    .venv\\Scripts\\python -m tools.templates reel09 reel03    # only these

Per reel: analyze.run (template + same-shot pass + marker pass, renders kept), then
gold/<reel>/compare.mp4 (original | same shots | template on markers) and gold/<reel>/template_report.json
(delta rows + the template scored against labels.json)."""
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, ir  # noqa: E402
from app.clients import ff  # noqa: E402
from tools.score import GOLD, reel_file, score  # noqa: E402

PANEL_W, PANEL_H = 360, 640
FONT_DIR = Path("C:/Windows/Fonts")  # ffmpeg runs from here so drawtext takes a bare font name (no drive colon)


def template_pred(t: ir.Template) -> dict:
    """The template in the label shape tools/score.score compares."""
    return {"cuts": t.cuts(),
            "transitions": [{"type": x.type.value, "start": x.start, "end": x.end} for x in t.transitions
                            if x.end > x.start],
            "texts": [{"start": x.start, "end": x.end} for x in t.texts],
            "flashes": [e.start for e in t.effects if e.type.value == "flash"],
            "effects_all": [{"type": e.type.value, "start": e.start, "end": e.end} for e in t.effects]}


def side_by_side(panels: list[tuple[Path, str]], audio: str, out: Path) -> None:
    args, chains = [], []
    for k, (p, label) in enumerate(panels):
        args += ["-i", str(p)]
        chains.append(f"[{k}:v]scale={PANEL_W}:{PANEL_H}:force_original_aspect_ratio=decrease,"
                      f"pad={PANEL_W}:{PANEL_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,drawtext=fontfile=arial.ttf:text='{label}':x=8:y=8:"
                      f"fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6[v{k}]")
    n = len(panels)
    graph = ";".join(chains) + ";" + "".join(f"[v{k}]" for k in range(n)) + f"hstack=inputs={n}[v]"
    a = ["-i", audio, "-map", f"{n}:a", "-c:a", "aac"] if audio and Path(audio).exists() else []
    ff.run([*args, *a[:2], "-filter_complex", graph, "-map", "[v]", *a[2:], "-c:v", "libx264", "-crf", "20",
            "-pix_fmt", "yuv420p", "-shortest", str(out.resolve())], cwd=FONT_DIR)


def one(d: Path) -> dict:
    from app.stages import analyze

    rep: dict = {"reel": d.name, "key": None, "error": None}
    try:
        video = reel_file(d)
        key, t, delta = analyze.run(video, progress=lambda m: print(f"  {d.name}: {m}", flush=True))
        rep["key"] = key
        rep["template"] = {"slots": len(t.slots), "transitions": len(t.transitions), "texts": len(t.texts),
                           "effects": len(t.effects), "unsupported": len(t.unsupported), "dropped": len(t.dropped)}
        rep["delta"] = delta.model_dump(mode="json")
        labels = json.loads((d / "labels.json").read_text(encoding="utf-8"))
        rep["labels"] = score(labels, template_pred(t))
        rd = ir.ref_dir(key)
        panels = [(analyze.proxy_path(key), "original"), (rd / "rt" / "render.mp4", "same shots"),
                  (rd / "mk" / "render.mp4", "template on markers")]
        side_by_side([p for p in panels if p[0].exists()], t.audio, d / "compare.mp4")
    except Exception as e:  # one bad reel must not stop the batch; the report says what broke
        rep["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    (d / "template_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    return rep


def row(rep: dict) -> str:
    if rep["error"]:
        return f"{rep['reel']:8} ERROR {rep['error'][:100]}"
    rows = rep["delta"]["rows"]
    get = lambda m: next((r for r in rows if r["metric"] == m), None)  # noqa: E731
    fc, ss = get("frame count"), get("per-frame SSIM min")
    marker = [r for r in rows if r["track"] not in ("timing", "audio")]
    agree = f"{sum(r['ok'] for r in marker)}/{len(marker)}" if marker else "-"
    f1 = " ".join(f"{k}={v['f1']:.2f}" for k, v in rep["labels"].items() if k in ("cuts", "transitions", "texts",
                                                                                     "flashes"))
    return (f"{rep['reel']:8} passed={rep['delta']['passed']!s:5} cov={rep['delta']['coverage']:.2f} "
            f"frames={'ok' if fc and fc['ok'] else 'BAD'} ssim={ss['render'] if ss else '-'} marker={agree} {f1}")


def main() -> None:
    config.KEEP_REFS = True  # keep proxy, rt/ and mk/ renders for the side-by-side
    names = sys.argv[1:]
    reels = [d for d in sorted(GOLD.glob("reel*")) if (d / "labels.json").exists() and (not names or d.name in names)]
    reps = []
    for d in reels:
        print(f"== {d.name}", flush=True)
        reps.append(one(d))
        print(row(reps[-1]), flush=True)
    print("\n".join(["", "summary:"] + [row(r) for r in reps]))


if __name__ == "__main__":
    main()
