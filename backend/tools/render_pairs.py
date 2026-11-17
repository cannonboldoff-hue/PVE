"""Render each Mixkit template to a video, giving the (rendered.mp4, template.json) dataset pair.

    .venv\\Scripts\\python -m tools.render_pairs [-j 3] [slug ...]

After Effects templates: EffectCraft opens <slug>/ae/template.ecproj and renders the main comp at half size
(540x960 for 1080x1920), 30 fps, no audio -> <slug>/rendered.mp4. Premiere templates (.prproj) have no
EffectCraft project and FilmCraft only gets labels, so their pair video is Mixkit's preview.mp4.
Writes data/mixkit/pairs.jsonl: one line per template with the video, the template.json and how the video was made."""
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.effectcraft_import import cli  # noqa: E402

CHUNK, RETRIES = 5, 10
MIXKIT = Path(__file__).resolve().parents[2] / "data" / "mixkit"


def chunk(ec: Path, part: Path, i: int, k: int) -> str:
    """Render k frames from frame i. EffectCraft's batch render dies at random with 'memory allocation ... failed'
    (not a real shortage), so a chunk is retried; the end time stops half a frame early so exactly k frames come out."""
    err = ""
    for _ in range(RETRIES):
        r = subprocess.run([str(cli()), "render", str(ec), "--out", str(part), "--format", "h264", "--fps", "30", "--audio", "off",
                            "--resolution", "half", "--quality", "draft", "--start", f"{i / 30:.6f}", "--end", f"{(i + k - 0.5) / 30:.6f}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if not r.returncode and part.exists():
            return ""
        err = (r.stderr or r.stdout).strip()[-200:]
        part.unlink(missing_ok=True)
    return err


def render(d: Path) -> dict:
    tpl = d / "labels" / "template.json"
    ec, out = d / "ae" / "template.ecproj", d / "rendered.mp4"
    row = {"slug": d.name, "template": str(tpl.relative_to(MIXKIT)), "n_frames": json.loads(tpl.read_text("utf-8"))["n_frames"]}
    if not ec.exists():
        return row | {"video": str((d / "preview.mp4").relative_to(MIXKIT)), "source": "mixkit_preview", "status": "ok"}
    if out.exists():
        return row | {"video": str(out.relative_to(MIXKIT)), "source": "effectcraft", "status": "ok"}
    work = d / "render_parts"
    work.mkdir(exist_ok=True)
    n, parts = row["n_frames"], []
    for i in range(0, n, CHUNK):
        k = min(CHUNK, n - i)
        part = work / f"p{i:05d}.mp4"
        if not part.exists() or part.stat().st_size == 0:
            err = chunk(ec, part, i, k)
            if err:
                return row | {"video": None, "source": "effectcraft", "status": "fail", "error": f"frames {i}+{k}: {err}"}
        parts.append(part)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), "utf-8")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-i", str(lst), "-c", "copy", str(out)], capture_output=True, text=True)
    if r.returncode:
        return row | {"video": None, "source": "effectcraft", "status": "fail", "error": r.stderr[-300:]}
    shutil.rmtree(work)
    return row | {"video": str(out.relative_to(MIXKIT)), "source": "effectcraft", "status": "ok"}


def main():
    args = sys.argv[1:]
    jobs = 3
    if args[:1] == ["-j"]:
        jobs, args = int(args[1]), args[2:]
    dirs = [d for d in sorted((MIXKIT / "instagram").iterdir()) if (not args or d.name in args) and (d / "labels" / "template.json").exists()]
    with ThreadPoolExecutor(jobs) as ex:
        rows = list(ex.map(render, dirs))
    for r in rows:
        print(r["status"], r["slug"], r.get("error", ""), flush=True)
    (MIXKIT / "pairs.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", "utf-8")


if __name__ == "__main__":
    main()
