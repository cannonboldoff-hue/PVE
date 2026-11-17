"""Download every free Premiere Pro template from a Mixkit category page.

    python backend/tools/mixkit.py                      # instagram -> data/mixkit/instagram
    python backend/tools/mixkit.py --category stories --out data/mixkit/stories

Each template lands as one folder, zip deleted after:
    <slug>/
      preview.mp4                    site preview, highest res served (1080 > 720 > 360)
      template.mogrt | template.prproj
      fonts.txt                      only if the zip had one
      <asset dirs>/                  verbatim (prproj media links are relative to them)
      meta.json                      written last; its presence marks the template done
"""
import argparse
import json
import re
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://mixkit.co"
UA = {"User-Agent": "Mozilla/5.0"}
ITEM = re.compile(r'href="/free-premiere-pro-templates/([a-z0-9-]+-(\d+))/"')
ZIP = re.compile(r'data-download--modal-url-value="([^"]+\.zip)"')


def retry(fn, *args, tries: int = 3):
    for i in range(tries):
        try:
            return fn(*args)
        except urllib.error.HTTPError:
            raise  # 403/404 are answers, not flakes
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def _get(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def get(url: str) -> str:
    return retry(_get, url)


def items(category: str) -> dict[str, str]:
    """{id: slug} across all listing pages; stops at the first page with nothing new."""
    found: dict[str, str] = {}
    page = 1
    while True:
        html = get(f"{BASE}/free-premiere-pro-templates/{category}/?page={page}")
        new = {i: s for s, i in ITEM.findall(html) if i not in found}
        if not new:
            return found
        found.update(new)
        print(f"page {page}: +{len(new)} (total {len(found)})")
        page += 1
        time.sleep(1)


def zip_url(tid: str) -> str:
    m = ZIP.search(get(f"{BASE}/free-premiere-pro-templates/download/{tid}/?context=sidebar"))
    return m.group(1) if m else f"https://assets.mixkit.co/video-templates/{tid}/mixkit-{tid}.zip"


def download(url: str, dest: Path) -> None:
    retry(_download, url, dest)


def _download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(".part")  # no half-written zips left behind on failure
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 16):
            f.write(chunk)
    tmp.replace(dest)


def preview(tid: str, dest: Path) -> int:
    for res in (1080, 720, 360):
        try:
            download(f"https://assets.mixkit.co/video-templates/{tid}/mixkit-{tid}-{res}.mp4", dest)
            return res
        except urllib.error.HTTPError as e:
            if e.code not in (403, 404):
                raise
    raise RuntimeError(f"no preview for {tid}")


def unpack(zpath: Path, dest: Path) -> tuple[str, list[str]]:
    """Extract with uniform names; returns (template kind, sorted file list)."""
    kind = None
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir() or name.startswith("__MACOSX/"):
                continue
            ext = Path(name).suffix.lower()
            if "/" not in name and ext in (".mogrt", ".prproj"):
                if kind:
                    raise RuntimeError(f"{zpath.name}: more than one template file")
                kind, target = ext[1:], dest / f"template{ext}"
            elif "/" not in name and name.endswith("-fonts.txt"):
                target = dest / "fonts.txt"
            elif "/" not in name and name.endswith("-preview.mp4"):
                continue  # same clip as preview.mp4, lower res
            else:
                target = dest / name
            if not target.resolve().is_relative_to(dest.resolve()):
                raise RuntimeError(f"{zpath.name}: unsafe path {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as f:
                shutil.copyfileobj(src, f)
    if not kind:
        raise RuntimeError(f"{zpath.name}: no .mogrt/.prproj")
    return kind, sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())


def fetch(tid: str, slug: str, out: Path) -> None:
    dest = out / slug
    zpath = out / f"{slug}.zip"
    if not zpath.exists():
        download(zip_url(tid), zpath)
    if dest.exists():
        shutil.rmtree(dest)  # leftover from an interrupted run (no meta.json)
    dest.mkdir()
    res = preview(tid, dest / "preview.mp4")
    kind, files = unpack(zpath, dest)
    meta = {"id": int(tid), "slug": slug, "url": f"{BASE}/free-premiere-pro-templates/{slug}/",
            "kind": kind, "preview_res": res, "files": files}
    (dest / "meta.json").write_text(json.dumps(meta, indent=2))
    zpath.unlink()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="instagram")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out or f"data/mixkit/{a.category}")
    out.mkdir(parents=True, exist_ok=True)

    found = items(a.category)
    failed = []
    for n, (tid, slug) in enumerate(sorted(found.items(), key=lambda kv: int(kv[0])), 1):
        if (out / slug / "meta.json").exists():
            print(f"[{n}/{len(found)}] skip {slug}")
            continue
        try:
            fetch(tid, slug, out)
            print(f"[{n}/{len(found)}] ok   {slug}")
        except Exception as e:  # keep going; report at end
            failed.append(slug)
            print(f"[{n}/{len(found)}] FAIL {slug}: {e}")
        time.sleep(1)
    print(f"done: {len(found) - len(failed)}/{len(found)} in {out}" + (f"; failed: {failed}" if failed else ""))


if __name__ == "__main__":
    main()
