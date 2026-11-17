"""App readers: an editor's own project file -> PVE template JSON (the labels), no AI.

    .venv\\Scripts\\python -m tools.app_readers                    # every data/mixkit/*/<slug>
    .venv\\Scripts\\python -m tools.app_readers path/to/<slug> ...  # only these

Per template folder writes labels/scene.json (everything the reader saw, raw) and labels/template.json
(ir.Template, validated). Three readers feed one neutral scene, then one mapping makes the template:
  .prproj  gzip XML, parsed here directly (Premiere ticks = 254 016 000 000 per second)
  .aep     decoded by EffectCraft's importer (`effectcraft-cli exec file.importAep`) into .ecproj JSON,
           read here. That is one intermediate format, unlike the artifact's "direct parse" rule:
           writing a RIFX/AEP decoder would duplicate EffectCraft's tested one.
  VN       an unpacked template / project folder (Data/brief.json), plain JSON, parsed here directly.
           A .vnt is a password-locked zip and is not read.
Anything without a template field is kept raw: Effect type "other" with app + params, or a line in
`unsupported` naming the scene path, never dropped."""
import base64
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, ir  # noqa: E402

TICKS = 254_016_000_000  # Premiere (and FilmCraft / EffectCraft) ticks per second
FPS = config.FPS
MAX_DEPTH = 16  # nested sequences / precomps
MIXKIT = Path(__file__).resolve().parents[2] / "data" / "mixkit"

# Premiere synthetic media: Media/FilePath holds a fourcc as a decimal number
FOURCC = {1129270354: "color_matte", 1112293707: "black_video", 1196574294: "graphic", 1414680405: "transparent_video"}
INTRINSIC = {"AE.ADBE Motion", "AE.ADBE Opacity", "AE.ADBE Text", "AE.ADBE AESDRConform", "AE.ADBE Time Remapping"}
EFFECT_TYPE = {  # editor effect -> ir.EffectType; everything else is "other" with raw
    "gaussian blur": "blur", "fast box blur": "blur", "camera lens blur": "blur", "directional blur": "blur",
    "channel blur": "blur", "box blur": "blur", "glow": "glow", "noise": "grain", "noise hls auto": "grain",
    "vignette": "vignette", "venetian blinds": "scanlines",
}


# ---------------------------------------------------------------- neutral scene

def layer(kind: str, name: str, start: float, end: float, **kw) -> dict:
    """One visible thing on the timeline, times in seconds of the main sequence / comp."""
    return {"kind": kind, "name": name, "start": start, "end": end, "depth": 0, "track": 0,
            "media": None, "color": None, "text": None, "font": None, "size_px": None, "fill": None,
            "align": "center", "pos": None, "keys": {}, "effects": [], "blend": "normal", **kw}


# ---------------------------------------------------------------- .prproj

class Prproj:
    def __init__(self, path: Path):
        self.root = ET.fromstring(gzip.open(path).read())
        self.id = {e.get("ObjectID"): e for e in self.root if e.get("ObjectID")}
        self.uid = {e.get("ObjectUID"): e for e in self.root if e.get("ObjectUID")}

    def ref(self, e):
        if e is None:
            return None
        if e.get("ObjectRef"):
            return self.id.get(e.get("ObjectRef"))
        return self.uid.get(e.get("ObjectURef"))

    def seq_video_tracks(self, seq) -> tuple[list, tuple[int, int], float]:
        """(tracks bottom first, frame size, fps) of a Sequence element."""
        for tg in seq.findall("TrackGroups/TrackGroup"):
            g = self.ref(tg.find("Second"))
            if g is not None and g.tag == "VideoTrackGroup":
                w, h = (int(x) for x in g.findtext("FrameRect", "0,0,1080,1920").split(",")[2:4])
                per = int(g.findtext("TrackGroup/FrameRate") or 0)
                tracks = sorted(g.findall("TrackGroup/Tracks/Track"), key=lambda t: int(t.get("Index", 0)))
                return [self.ref(t) for t in tracks], (w, h), (TICKS / per if per else 30.0)
        return [], (1080, 1920), 30.0

    def items(self, track) -> list:
        return [self.ref(t) for t in track.findall("ClipTrack/ClipItems/TrackItems/TrackItem")] if track is not None else []

    def components(self, item) -> list[dict]:
        chain = self.ref(item.find("ClipTrackItem/ComponentOwner/Components"))
        out = []
        for c in chain.findall("ComponentChain/Components/Component") if chain is not None else []:
            comp = self.ref(c)
            if comp is None or comp.tag != "VideoFilterComponent":
                continue
            params = {}
            for i, p in enumerate(comp.findall("Component/Params/Param")):
                pe = self.ref(p)
                if pe is None:
                    continue
                name = (pe.findtext("Name") or "").strip() or f"#{i}"
                if pe.tag == "ArbVideoComponentParam":
                    params[name] = {"arb": source_text(pe.findtext("StartKeyframeValue"))} if name == "Source Text" else {"arb": True}
                else:
                    params[name] = {"value": kf_value(pe.findtext("StartKeyframe") or pe.findtext("CurrentValue") or ""),
                                    "keys": [(int(k.split(",")[0]), kf_value(k)) for k in (pe.findtext("Keyframes") or "").split(";") if k]}
            out.append({"match": comp.findtext("MatchName") or "", "name": comp.findtext("Component/DisplayName") or "",
                        "bypass": comp.findtext("Component/Bypass") == "true", "params": params})
        return out

    def media(self, item) -> dict:
        """{kind: file|sequence|<synthetic>, path|seq, in_ticks}."""
        sub = self.ref(item.find("ClipTrackItem/SubClip"))
        clip = self.ref(sub.find("Clip")) if sub is not None else None
        src = self.ref(clip.find("Clip/Source")) if clip is not None else None
        info = {"name": sub.findtext("Name") if sub is not None else "", "in": int(clip.findtext("Clip/InPoint") or 0) if clip is not None else 0}
        if src is None:
            return {**info, "kind": "unknown"}
        if src.tag == "VideoSequenceSource":
            return {**info, "kind": "sequence", "seq": self.ref(src.find("SequenceSource/Sequence"))}
        m = self.ref(src.find("MediaSource/Media"))
        fp = m.findtext("ActualMediaFilePath") or m.findtext("FilePath") or "" if m is not None else ""
        if fp.isdigit():
            return {**info, "kind": FOURCC.get(int(fp), f"synthetic_{fp}")}
        return {**info, "kind": "file", "path": fp}


def kf_value(s: str):
    """'time,value,...' -> value; points 'x:y' -> [x, y]; bools and numbers typed."""
    parts = s.split(",")
    v = parts[1] if len(parts) > 1 else parts[0]
    if ":" in v:
        return [float(x) for x in v.split(":")[:2]]
    if v in ("true", "false"):
        return v == "true"
    try:
        return float(v)
    except ValueError:
        return v


def source_text(b64: str | None) -> dict | None:
    """Premiere's Source Text blob: u32 length, u32 0, then UTF-16LE JSON."""
    if not b64:
        return None
    try:
        b = base64.b64decode(b64)
        n = int.from_bytes(b[:4], "little")
        s = b[8:8 + n].decode("utf-16-le", "replace")
        j = json.loads(s[: s.rfind("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return None
    tp = j.get("mTextParam", {})
    ss = tp.get("mStyleSheet", {})
    run = (tp.get("mDefaultRun") or [{}])[0].get("mStyleParam", {})

    def first(k):  # mParamValues = [[from character index, value], ...]; the first run styles the text
        v = ss.get(k, {}).get("mParamValues") or []
        return v[0][1] if v and len(v[0]) > 1 else None
    fill = first("mFillColor")
    fonts = [v[1] for v in ss.get("mFontName", {}).get("mParamValues") or [] if len(v) > 1 and "-" in str(v[1]) and len(str(v[1])) != 36]
    return {"text": ss.get("mText") or "", "font": fonts[0] if fonts else run.get("mFontName"),
            "fonts": sorted(set(fonts)), "size": first("mFontSize") or run.get("mFontSize"),
            "fill": f"#{int(fill) & 0xFF:02X}{int(fill) >> 8 & 0xFF:02X}{int(fill) >> 16 & 0xFF:02X}" if isinstance(fill, (int, float)) else None,
            "align": {0: "left", 1: "right", 2: "center"}.get(tp.get("mAlignment"), "center"),
            "shadow": bool(tp.get("mShadowVisible")), "stroke": bool(run.get("mStrokeVisible"))}


def read_prproj(path: Path) -> dict:
    p = Prproj(path)
    seqs = [e for e in p.root if e.tag == "Sequence"]
    nested = set()
    for e in p.root:
        if e.tag == "VideoSequenceSource":
            s = p.ref(e.find("SequenceSource/Sequence"))
            if s is not None:
                nested.add(id(s))

    def span(seq):
        return max((int(i.findtext("ClipTrackItem/TrackItem/End") or 0) for t in p.seq_video_tracks(seq)[0] for i in p.items(t) if i is not None), default=0)
    top = [s for s in seqs if id(s) not in nested] or seqs
    main = max(top, key=span)
    _, (w, h), fps = p.seq_video_tracks(main)
    scene = {"app": "premiere", "file": path.name, "name": main.findtext("Name"), "width": w, "height": h, "src_fps": fps,
             "duration": span(main) / TICKS, "layers": [], "unsupported": []}

    def walk(seq, offset: float, t0: float, t1: float, depth: int, track_base: int):
        tracks, _, _ = p.seq_video_tracks(seq)
        for ti, track in enumerate(tracks):
            for it in p.items(track):
                if it is None or it.tag != "VideoClipTrackItem":
                    continue
                s = int(it.findtext("ClipTrackItem/TrackItem/Start") or 0) / TICKS
                e = int(it.findtext("ClipTrackItem/TrackItem/End") or 0) / TICKS
                a, b = max(s + offset, t0), min(e + offset, t1)  # clipped to the parent window
                if b <= a:
                    continue
                m = p.media(it)
                comps = p.components(it)
                tr = track_base + ti
                if m["kind"] == "sequence" and m.get("seq") is not None:
                    if depth >= MAX_DEPTH:
                        scene["unsupported"].append(f"prproj: nesting deeper than {MAX_DEPTH} at {m['name']}")
                        continue
                    # nested sequence time = parent time - clip start + clip in point
                    walk(m["seq"], s + offset - m["in"] / TICKS, a, b, depth + 1, tr * 100)
                    extra = [c for c in comps if c["match"] not in INTRINSIC]
                    if extra:
                        scene["layers"].append(layer("precomp_fx", m["name"], a, b, depth=depth, track=tr, effects=extra))
                    continue
                keys = clip_keys(comps, m["in"], s + offset)
                blend = next((c["params"].get("Blend Mode", {}).get("value") for c in comps if c["match"] == "AE.ADBE Opacity"), None)
                base = dict(depth=depth, track=tr, keys=keys, blend=blend if blend not in (None, 0.0, 18.0) else "normal",
                            effects=[c for c in comps if c["match"] not in INTRINSIC])
                texts = [c for c in comps if c["match"] == "AE.ADBE Text"]
                if texts:
                    for c in texts:
                        st = c["params"].get("Source Text", {}).get("arb") or {}
                        pos = c["params"].get("Position", {}).get("value")
                        scene["layers"].append(layer("text", m["name"], a, b, text=st.get("text", ""), font=st.get("font"),
                                                     size_px=st.get("size"), fill=st.get("fill"), align=st.get("align", "center"),
                                                     pos=[pos[0] * w, pos[1] * h] if isinstance(pos, list) else None, raw_style=st, **base))
                elif m["kind"] == "file":
                    scene["layers"].append(layer("footage", m["name"], a, b, media=m.get("path"), **base))
                elif m["kind"] in ("color_matte", "black_video"):
                    scene["layers"].append(layer("solid", m["name"], a, b, color="#000000" if m["kind"] == "black_video" else None, **base))
                else:
                    scene["layers"].append(layer("other", m["name"], a, b, raw_kind=m["kind"], **base))
                for c in comps:
                    if c["match"] == "AE.ADBE PPro SimpleText" or c["match"].startswith("AE.ADBE PPro Timecode"):
                        scene["unsupported"].append(f"prproj: {c['match']} on {m['name']} at {a:.2f}s")
    walk(main, 0.0, 0.0, scene["duration"], 0, 0)
    return scene


def clip_keys(comps: list[dict], in_ticks: int, clip_start: float) -> dict:
    """Opacity / Motion keyframes as {param: [(seconds in sequence, value)]}; key time = media time - in point."""
    out = {}
    for c in comps:
        if c["match"] not in ("AE.ADBE Opacity", "AE.ADBE Motion"):
            continue
        for name, pr in c["params"].items():
            ks = pr.get("keys") or []
            if ks and name in ("Opacity", "Position", "Scale", "Rotation"):
                out[name.lower()] = [(clip_start + (t - in_ticks) / TICKS, v) for t, v in ks]
    return out


# ---------------------------------------------------------------- .aep through EffectCraft

def read_effectcraft(ae: Path) -> dict:
    """ae/dump.json (tools.effectcraft_import: evaluated main comp) + ae/import_report.json -> scene."""
    d = json.loads((ae / "dump.json").read_text(encoding="utf-8"))
    rep = json.loads((ae / "import_report.json").read_text(encoding="utf-8")) if (ae / "import_report.json").exists() else {}
    scene = {"app": "after_effects", "file": next((p.name for p in ae.glob("*.aep")), ""), "name": d["main"], "width": d["width"],
             "height": d["height"], "src_fps": d["fps"], "duration": d["duration"], "layers": [], "unsupported": [],
             "effectcraft_report": rep.get("report")}
    for r in d["layers"]:
        doc = r.get("doc") or {}
        fill = doc.get("effectFill") or doc.get("animFill") or doc.get("fill")
        hexc = lambda c: "#" + "".join(f"{max(0, min(255, round(v * 255))):02X}" for v in c[:3]) if isinstance(c, list) and len(c) >= 3 else None  # noqa: E731
        samples = [{"t": s["t"], "opacity": s.get("opacity", 1.0),
                    "box": quad_box(s["quad"]) if s.get("quad") else None} for s in r.get("samples", [])]
        # effective scale (layer, parents, precomps): main-comp box width / layer-space rect width
        ratios = sorted(sm["box"][2] / s["rw"] for sm, s in zip(samples, r.get("samples", [])) if sm["box"] and s.get("rw"))
        scale = ratios[len(ratios) // 2] if ratios else 1.0
        scene["layers"].append(layer(
            r["kind"] if r["kind"] in ("text", "shape", "solid", "footage", "precomp") else "other", r["name"], r["start"], r["end"],
            depth=r.get("depth", 0), track=-r.get("index", 0), media=r.get("media"), color=hexc(r.get("color")),
            text=doc.get("text"), font=doc.get("font"), size_px=doc["size"] * scale if doc.get("size") else None, fill=hexc(fill),
            align={"LEFT_JUSTIFY": "left", "RIGHT_JUSTIFY": "right"}.get(str(doc.get("justification", "")).split(".")[-1], "center"),
            blend="normal" if str(r.get("blend", "")).upper().endswith("NORMAL") else r.get("blend"),
            effects=[{"match": e["match"], "name": e["name"], "bypass": not e.get("enabled", True), "params": {}} for e in r.get("effects", [])],
            samples=samples, raw_kind=r["kind"], comp=r.get("comp"), matte=r.get("matte"), animators=doc.get("animators", 0),
            stroke=hexc(r.get("stroke")), stroke_px=r.get("strokeWidth", 0) * scale))
        if doc.get("animators"):
            scene["unsupported"].append(f"after_effects: {doc['animators']} text animator(s) on {r['name']!r}: per-character motion is not in TextEvent; anim names come from the box path")
    if d.get("truncated"):
        scene["unsupported"].append(f"effectcraft dump: {d['truncated']} layers past the first {len(d['layers'])} were not read (precomp rig too large)")
    for line in report_lines(rep.get("report")):
        scene["unsupported"].append(f"effectcraft import: {line}")
    return scene


def quad_box(q: list) -> list[float]:
    xs, ys = [p[0] for p in q], [p[1] for p in q]
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]


def report_lines(rep) -> list[str]:
    """Every loss EffectCraft's importer reported, one line each, never dropped."""
    if isinstance(rep, dict) and isinstance(rep.get("report"), dict):  # file.importAep wraps it: {dryRun, report}
        rep = rep["report"]
    if not isinstance(rep, dict):
        return [json.dumps(rep)[:500]] if rep else []
    out = []
    for k, v in rep.items():
        if k in ("aeVersion", "comps", "items", "folder", "imported", "dryRun") or not v:
            continue
        if isinstance(v, list):
            out += [f"{k}: {json.dumps(x, ensure_ascii=False)[:300]}" for x in v]
        elif isinstance(v, dict):
            out += [f"{k}.{a}: {json.dumps(b, ensure_ascii=False)[:300]}" for a, b in v.items()]
        else:
            out.append(f"{k}: {v}")
    return out


# ---------------------------------------------------------------- VN (unpacked folder)

VN_PT_WIDTH = 375  # fontPointSize is in points of a 375-wide canvas: matched two titles of one preview, not more
# integer codes named from one template's preview; every other code stays "other" with the raw number
VN_TRANSITION = {1001: ("fade_black", 1.0), 1015: ("spin", 0.6)}  # 1001: brightness dip measured at 6 cuts; 1015: seen once
VN_MASK = {5: "circle"}
VN_ANIM_IN, VN_ANIM_OUT = {0: "none"}, {100: "fade"}  # each seen on one text and one layer
VN_MEDIA = {1000: "video", 1002: "photo"}
VN_CLIP_KEYS = {  # clip fields this reader reads or knowingly keeps raw; any other field is reported, e.g. a speed curve
    "animatorParameters", "backgroundModel", "beginUs", "blendMode", "displayDurationUs", "durationUsWithSpeed", "endUs",
    "fadeInIntervalUs", "fadeOutIntervalUs", "fillCropMode", "fillingHighlight", "filter", "frameSVGInfo", "isFlip", "isMirror",
    "isReverse", "keyframeContext", "lockedInEditor", "lockedRatio", "mCropRectF", "mSpeed", "mZoomType", "manualLocked",
    "mediaInfo", "representationType", "rotation", "scaleMode", "startTimeUs", "svgColorMap", "transition", "transitionSliceId",
    "uuid", "volume"}
VN_TOP_LISTS = {"mVideoSlices", "mStickerItems", "mSubtitleItems", "mMusicItems"}


def vn_clean(v):
    """Drop GPS: a clip's mediaInfo.location is where someone filmed it."""
    if isinstance(v, dict):
        return {k: vn_clean(x) for k, x in v.items() if k != "location"}
    return [vn_clean(x) for x in v] if isinstance(v, list) else v


def vn_colour(m: dict) -> str | None:
    """VN's colour cards are images named after their RGBA hex: Asset/000000FF.svg."""
    stem = Path(m.get("imagePath") or "").stem
    return f"#{stem[:6].upper()}" if re.fullmatch(r"[0-9A-Fa-f]{8}", stem) else None


def vn_rgb(c) -> str | None:
    """Signed 32-bit RGBA -> #RRGGBB."""
    return f"#{(c & 0xFFFFFFFF) >> 8:06X}" if isinstance(c, int) else None


def vn_fit(v: dict, w: int, h: int) -> tuple[float, float]:
    """A clip's size at scale 1: its cropped media fitted inside the canvas (scaleMode 1001)."""
    m, c = v["mediaInfo"], v.get("mCropRectF") or {}
    mw = (m.get("imageWidth") or w) * (c.get("right", 1) - c.get("left", 0))
    mh = (m.get("imageHeight") or h) * (c.get("bottom", 1) - c.get("top", 0))
    f = min(w / mw, h / mh) if mw > 0 and mh > 0 else 1.0
    return mw * f, mh * f


def vn_samples(ctx: dict, w: int, h: int, start: float, dur: float, size) -> list[dict]:
    """keyframeContext -> boxes in canvas pixels. Key times count from the item's own start. A split clip keeps its
    parent's keys outside its range: the nearest one on each side is kept and moved to the edge (not interpolated)."""
    us = dur * 1e6
    ks = sorted(ctx.get("keyframeArray") or [], key=lambda k: k["timeOffsetUs"])
    ks = ([k for k in ks if k["timeOffsetUs"] <= 0][-1:] + [k for k in ks if 0 < k["timeOffsetUs"] < us]
          + [k for k in ks if k["timeOffsetUs"] >= us][:1]) or [ctx["original"]]
    out = []
    for k in ks:
        bw, bh = size(k)
        out.append({"t": start + min(max(k.get("timeOffsetUs", 0), 0), us) / 1e6, "opacity": k.get("alpha", 1.0),
                    "box": [k.get("centerX", 0.5) * w - bw / 2, k.get("centerY", 0.5) * h - bh / 2, bw, bh]})
    return [{**out[0], "t": start}, *out] if out[0]["t"] > start else out  # the first key's pose holds from the item's start


def vn_raw(v: dict) -> dict:
    """What a clip carries that has no template field, as VN wrote it."""
    ctx = v["keyframeContext"]
    o = ctx["original"]
    mask = o.get("mask")
    raw = {"src_in_us": v.get("beginUs"), "src_out_us": v.get("endUs"), "zoom_type": v.get("mZoomType"), "scale_mode": v.get("scaleMode"),
           "blend": v.get("blendMode"), "flip": v.get("isFlip"), "mirror": v.get("isMirror"), "crop": v.get("mCropRectF"),
           "background": v.get("backgroundModel"), "animator": v.get("animatorParameters"),
           "transform": {k: x for k, x in o.items() if k != "mask"}, "mask": mask,
           "mask_shape": VN_MASK.get(mask.get("type")) if mask else None,
           "mask_keys": [[k["timeOffsetUs"], k["mask"]] for k in ctx.get("keyframeArray") or [] if k.get("mask")]}
    return {k: x for k, x in raw.items() if x not in (None, [], False, 0)}


def vn_fx(v: dict) -> list[dict]:
    f = v.get("filter") or {}
    if not f.get("id"):  # id 0 is "Original"
        return []
    return [{"match": f"vn.filter.{f['id']}", "name": f.get("name") or "", "bypass": False,
             "params": {"intensity": f.get("intensity"), "adjust": {a["name"]: a["value"] for a in f.get("adjustArray") or [] if a.get("value")}}}]


def read_vn(folder: Path) -> dict:
    """Data/brief.json -> BriefSteps -> the latest page's Steps json (backups and cover steps sit beside it)."""
    data = folder / "Data"
    load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))  # noqa: E731
    brief = load(data / "brief.json")
    pages = load(data / brief["briefSteps"][-1])
    page = next(p for p in pages["pages"] if p["localID"] == pages["latestPageLocalID"])
    d = vn_clean(load(data / page["step"].lstrip("/")))
    meta = load(folder / "template.json") if (folder / "template.json").exists() else {}
    w, h = d["renderRatioWidth"], d["renderRatioHeight"]
    scene = {"app": "vn", "file": page["step"].lstrip("/"), "name": meta.get("title") or folder.name, "width": w, "height": h,
             "src_fps": float((brief.get("exportSettings") or {}).get("fps") or 30), "duration": d["mDurationMs"] / 1000,
             "layers": [], "slots": [], "transitions": [], "unsupported": [], "preview": meta.get("video_filename"),
             "declared_clips": meta.get("clips"),
             "music": [{"name": m.get("name"), "start": m.get("startTimeUs", 0) / 1e6, "src_in": m.get("beginUs", 0) / 1e6,
                        "length": m.get("sliceDurationUs", 0) / 1e6, "fade_out": m.get("fadeOutDurationUs", 0) / 1e6 if m.get("hasFadeOut") else 0.0,
                        "volume": m.get("volume")} for m in d.get("mMusicItems") or []]}
    unknown = {}

    def note(v: dict, at: float):
        for k in v.keys() - VN_CLIP_KEYS:
            unknown.setdefault(k, at)
        if v.get("scaleMode") not in (None, 1001):
            scene["unsupported"].append(f"vn: scaleMode {v['scaleMode']} at {at:.2f}s: the box assumes fit-inside (1001)")
        if v["keyframeContext"]["original"].get("radians"):
            scene["unsupported"].append(f"vn: rotation {v['keyframeContext']['original']['radians']:.3f} rad at {at:.2f}s is kept raw; the box is unrotated")

    for i, s in enumerate(d.get("mVideoSlices") or []):  # main track: every clip and colour card is a slot
        m, a = s["mediaInfo"], s["startTimeUs"] / 1e6
        colour = vn_colour(m)
        scene["slots"].append({"start": a, "end": a + s["displayDurationUs"] / 1e6, "swap": not s.get("manualLocked"), "colour": colour,
                               "media": "other" if colour else VN_MEDIA.get(m.get("type"), "other"), "speed": s.get("mSpeed") or 1.0,
                               "reverse": bool(s.get("isReverse")), "effects": vn_fx(s), "raw": vn_raw(s)})
        if not colour:
            note(s, a)
        if s.get("transition") and i:  # sits at this clip's head, centred on the cut (measured on the preview)
            scene["transitions"].append({"before": i, "at": a, "dur": s["transition"]["intervalUs"] / 1e6, "code": s["transition"]["type"]})
    if d.get("tailTransition"):  # the reel's own fade-out: ir.Transition only joins two slots, so it stays in narrative.source
        scene["tail"] = {"code": d["tailTransition"]["type"], "type": VN_TRANSITION.get(d["tailTransition"]["type"], ("other",))[0],
                         "frames": frame(d["tailTransition"]["intervalUs"] / 1e6)}
        scene["unsupported"].append(f"vn: reel-end transition {scene['tail']['type']} over the last {scene['tail']['frames']} frames has no template field (narrative.source.tail)")
    for s in d.get("mStickerItems") or []:  # every layer above the main track: clips, photos, stickers
        v = s["stickerVideoSlice"]
        m, a, dur = v["mediaInfo"], v["startTimeUs"] / 1e6, v["displayDurationUs"] / 1e6
        fw, fh = vn_fit(v, w, h)
        note(v, a)
        scene["layers"].append(layer(
            "footage", m.get("originalFileName") or Path(m.get("videoPath") or m.get("imagePath") or "").name, a, a + dur,
            track=1 + s.get("mZOrder", 0), media=VN_MEDIA.get(m.get("type"), "other"), color=vn_colour(m), swap=not v.get("manualLocked"),
            samples=vn_samples(v["keyframeContext"], w, h, a, dur, lambda k: (fw * k.get("scale", 1.0), fh * k.get("scale", 1.0))),
            effects=vn_fx(v), speed=v.get("mSpeed") or 1.0, reverse=bool(v.get("isReverse")), raw=vn_raw(v)))
    for s in d.get("mSubtitleItems") or []:
        ctx = s["keyframeContext"]
        o, a, dur = ctx["original"], s["startUs"] / 1e6, s["lengthUs"] / 1e6
        lines = [x for t in s.get("textArray") or [] for x in str(t).split("\n")]
        px = lambda k: s.get("fontPointSize", 36) * k.get("scale", 1.0) * w / VN_PT_WIDTH  # noqa: E731
        an = s.get("animatorParameters") or {}
        mks = [k for k in ctx.get("keyframeArray") or [] if k.get("mask") and 0 <= k["timeOffsetUs"] <= dur * 1e6]
        mk = sorted(k["timeOffsetUs"] for k in mks) if len({json.dumps(k["mask"], sort_keys=True) for k in mks}) > 1 else []  # the mask must move
        code_in, code_out = (an.get("inItem") or {}).get("type"), (an.get("outItem") or {}).get("type")
        a_in = (VN_ANIM_IN.get(code_in, "other"), frame((an.get("inItem") or {}).get("interval", 0))) if code_in is not None else ("none", 0)
        a_out = (VN_ANIM_OUT.get(code_out, "other"), frame((an.get("outItem") or {}).get("interval", 0))) if code_out is not None else ("none", 0)
        if len(mk) > 1 and a_in[0] == "none":  # a keyframed mask opening over the text: a reveal with no template name
            a_in = ("other", max(1, frame((mk[-1] - mk[0]) / 1e6)))
        scene["layers"].append(layer(
            "text", s.get("fontName") or "text", a, a + dur, track=1000 + s.get("mZOrder", 0), text="\n".join(lines), font=s.get("fontName"),
            size_px=px(o), fill=vn_rgb(o.get("color")), align={0: "left", 1: "right", 2: "center"}.get(s.get("alignment"), "center"),
            outline=vn_rgb(o.get("strokeColor")) if o.get("strokeWidth") else None,
            outline_px=o.get("strokeWidth", 0) * o.get("scale", 1.0) * w / VN_PT_WIDTH / 10,  # shortcut: stroke unit is a guess (1/10 pt), measure it on a second template
            samples=vn_samples(ctx, w, h, a, dur, lambda k: (min(w, max(map(len, lines), default=1) * px(k) * 0.5), px(k) * 1.2 * max(1, len(lines)))),
            estimated=True, animators=1 if "other" in (a_in[0], a_out[0]) else 0, anim_conf=0.7,  # codes named from two sightings
            anim_in=a_in if a_in[0] != "none" else None, anim_out=a_out if a_out[0] != "none" else None,
            raw_style={"shadow": bool(o.get("shadowRadius") and o.get("shadowColor"))},
            anim_raw={"animator": an, "mask_shape": VN_MASK.get((o.get("mask") or {}).get("type")), "mask": o.get("mask"),
                      "mask_keys": [[k["timeOffsetUs"], k["mask"]] for k in ctx.get("keyframeArray") or [] if k.get("mask")],
                      "title_type": s.get("titleType"), "stroke_width": o.get("strokeWidth")}))
    for k, at in sorted(unknown.items()):
        scene["unsupported"].append(f"vn: clip field {k!r} is not read (first at {at:.2f}s)")
    for k, v in d.items():
        if isinstance(v, list) and v and k not in VN_TOP_LISTS:
            scene["unsupported"].append(f"vn: {k} ({len(v)} items) is not read")
    return scene


def sample_keys(samples, w: int, h: int) -> list[ir.Key]:
    """Evaluated boxes -> keys at 30 fps, only where something changed."""
    keys = []
    for s in samples or []:
        if not s.get("box"):
            continue
        x, y, bw, bh = s["box"]
        k = ir.Key(frame=frame(s["t"]), box=ir.Box(x=x / w, y=y / h, w=bw / w, h=bh / h), opacity=round(float(s.get("opacity", 1.0)), 3))
        if keys and keys[-1].box == k.box and keys[-1].opacity == k.opacity:
            continue
        keys.append(k)
    return keys


def rest_key(keys: list[ir.Key], end: int) -> ir.Key:
    """The pose held longest: the resting position the animations start from and return to."""
    holds = [(b.frame if b else end) - a.frame for a, b in zip(keys, [*keys[1:], None])]
    return keys[max(range(len(keys)), key=holds.__getitem__)]


def anim_samples(keys: list[ir.Key], at_start: bool, end: int) -> tuple[str, int]:
    """In / out animation from the evaluated path: compare the edge key with the rest pose."""
    if len(keys) < 2:
        return "none", 0
    rest = rest_key(keys, end)
    edge = keys[0] if at_start else keys[-1]
    moving = [k for k in keys if abs(k.box.x - rest.box.x) + abs(k.box.y - rest.box.y) > 0.01 or abs(k.box.w * k.box.h - rest.box.w * rest.box.h) > 0.002 or abs(k.opacity - rest.opacity) > 0.05]
    side = [k for k in moving if (k.frame < rest.frame) == at_start]
    if not side:
        return "none", 0
    n = max(1, (max(k.frame for k in side) - min(k.frame for k in side)) if len(side) > 1 else 1)
    area0, area1 = edge.box.w * edge.box.h, rest.box.w * rest.box.h
    if area1 > 0 and area0 / area1 < 0.5:
        return "pop", n
    dx, dy = rest.box.x - edge.box.x, rest.box.y - edge.box.y
    if abs(dx) + abs(dy) > 0.02:
        if not at_start:
            dx, dy = -dx, -dy
        return (("slide_right" if dx > 0 else "slide_left") if abs(dx) > abs(dy) else ("slide_down" if dy > 0 else "slide_up")), n
    if edge.opacity < rest.opacity - 0.3:
        return "fade", n
    if area1 > 0 and edge.box.w / max(rest.box.w, 1e-6) < 0.7 and abs(edge.box.h - rest.box.h) < 0.01:
        return "typewriter", n
    return "other", n


# ---------------------------------------------------------------- scene -> ir.Template

def frame(seconds: float) -> int:
    return ir.s2f(seconds)


def anim(keys: dict, start: float, end: float, at_start: bool) -> tuple[str, int, dict | None]:
    """Name the in/out animation from opacity / scale / position keys near an edge."""
    edge = start if at_start else end
    near = lambda ks: [k for k in ks if abs(k[0] - edge) <= 1.0]  # noqa: E731
    op, sc, ps = near(keys.get("opacity", [])), near(keys.get("scale", [])), near(keys.get("position", []))
    span = lambda ks: max(1, frame(max(k[0] for k in ks) - min(k[0] for k in ks)))  # noqa: E731
    if sc and isinstance(sc[0][1], (int, float)) and min(k[1] for k in sc) < 50:
        return "pop", span(sc), None
    if ps and isinstance(ps[0][1], list) and len(ps) > 1:
        (x0, y0), (x1, y1) = ps[0][1], ps[-1][1]
        dx, dy = (x1 - x0, y1 - y0) if at_start else (x0 - x1, y0 - y1)
        d = ("slide_right" if dx > 0 else "slide_left") if abs(dx) > abs(dy) else ("slide_down" if dy > 0 else "slide_up")
        return d, span(ps), None
    if op and len(op) > 1:
        return "fade", span(op), None
    return "none", 0, None


def to_template(scene: dict, key: str) -> ir.Template:
    w, h = scene["width"], scene["height"]
    n = max(1, frame(scene["duration"]))
    L = sorted(scene["layers"], key=lambda x: (x["start"], x["track"]))
    low, unsupported = [], list(scene["unsupported"])
    # slots: cuts between footage on the lowest footage track of the main timeline
    # Premiere footage on the timeline is the user's shots; After Effects footage in a .mogrt is packed assets
    foot = [x for x in L if x["kind"] == "footage" and x["blend"] == "normal" and scene["app"] == "premiere"]
    texts, layers, overlays, effects, transitions = [], [], [], [], []

    def add_fx(name: str, a: int, b: int, fxs: list):
        for fx in fxs:
            if fx.get("bypass"):
                continue
            t = EFFECT_TYPE.get((fx["name"] or "").lower(), "other")
            effects.append(ir.Effect(id=f"e{len(effects) + 1:02d}", start=a, end=b, params={"layer": name, "params": fx["params"]},
                                     type=ir.F[ir.EffectType](value=t, raw={"app": scene["app"], "match": fx["match"], "name": fx["name"]}, source=scene["app"])))
    if scene.get("slots"):  # the reader names every slot itself (VN main track: clips and colour cards)
        slots, at = [], []  # at[i] = id of the slot made from scene slot i, None when it rounds to no frames
        for s in scene["slots"]:
            a, b = frame(s["start"]), min(n, frame(s["end"]))
            if b <= a:
                unsupported.append(f"{scene['app']}: main-track item at {s['start']:.3f}s is shorter than one frame")
                at.append(None)
                continue
            sid = f"s{len(slots) + 1:02d}"
            at.append(sid)
            zoom = s["raw"].get("zoom_type")
            slots.append(ir.Slot(
                id=sid, start=a, end=b, speed=[(0.0, float(s["speed"]))], reverse=s["reverse"],
                media=ir.F[ir.Media](value=s["media"], raw={"colour": s["colour"], **s["raw"]}, source=scene["app"], binding="swap" if s["swap"] else "keep"),
                camera=ir.F[ir.CameraMove](value="static" if zoom in (None, 1000) else "other", raw={"zoom_type": zoom}, source=scene["app"],
                                           conf=1.0 if zoom in (None, 1000) else 0.5)))
            add_fx(sid, a, b, s.get("effects", []))
        if slots:
            slots[0].start, slots[-1].end = 0, n  # slots tile 0..n
        joins = {tr["before"]: tr for tr in scene.get("transitions", []) if tr["before"] < len(at)}
        for a, b in zip(slots, slots[1:]):  # one entry per boundary, hard cuts included, as stages/fusion.py writes them
            tr = joins.get(at.index(b.id))
            if tr is None:
                transitions.append(ir.Transition(after_slot=a.id, start=b.start, end=b.start,
                                                 type=ir.F[ir.TransitionType](value="cut", source=scene["app"])))
                continue
            half = frame(tr["dur"]) / 2  # the window sits centred on the cut
            name, conf = VN_TRANSITION.get(tr["code"], ("other", 0.5))
            transitions.append(ir.Transition(
                after_slot=a.id, start=max(0, round(b.start - half)), end=min(n, round(b.start + half)), params={"seconds": tr["dur"]},
                type=ir.F[ir.TransitionType](value=name, raw={"app": scene["app"], "code": tr["code"]}, conf=conf, source=scene["app"])))
    else:
        cuts = sorted({frame(x["start"]) for x in foot if 0 < frame(x["start"]) < n}) if foot else []
        bounds = [0, *cuts, n]
        slots = [ir.Slot(id=f"s{i + 1:02d}", start=a, end=b) for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]
        if not foot:
            for s in slots:
                s.media = ir.F[ir.Media](value="other", raw="no footage layer: motion graphic over a placeholder", source=scene["app"])
    for x in L:
        a, b = frame(x["start"]), min(n, frame(x["end"]))
        if b <= a:
            continue
        if x.get("matte"):  # a track matte shapes another layer; it is never seen itself
            lk = sample_keys(x.get("samples"), w, h)
            layers.append(ir.Layer(id=f"l{len(layers) + 1:02d}", start=a, end=b, keys=[lk[0], rest_key(lk, b), lk[-1]] if lk else [ir.Key(frame=a, box=ir.Box(x=0, y=0, w=1, h=1))],
                                   kind=ir.F[ir.LayerKind](value="shape_mask", raw={"kind": x["kind"], "name": x["name"], "matte": True, "text": x.get("text")}, source=scene["app"], conf=0.7)))
            continue
        if x["kind"] == "text" and (x["text"] or "").strip():
            tid = f"t{len(texts) + 1:02d}"
            size = (x["size_px"] or 60) / h
            keys = sample_keys(x.get("samples"), w, h)
            if keys:  # evaluated boxes (EffectCraft): rest pose first, then the path
                (ai, ai_n), (ao, ao_n) = anim_samples(keys, True, b), anim_samples(keys, False, b)
                rest = rest_key(keys, b)
                box = rest.box
                path = [rest, *keys]
            else:  # estimated: no glyph metrics here
                px, py = x["pos"] or [w / 2, h / 2]
                tw = min(1.0, len(x["text"]) * size * 0.55 * h / w)
                box = ir.Box(x=max(0.0, px / w - tw / 2), y=max(0.0, py / h - size), w=tw, h=size * 1.2)
                (ai, ai_n, _), (ao, ao_n, _) = anim(x["keys"], x["start"], x["end"], True), anim(x["keys"], x["start"], x["end"], False)
                path = [ir.Key(frame=a, box=box)]
                low.append(f"texts.{tid}.keys.0.box")
            if x.get("estimated"):  # box and size come from a character count and a point-size guess, not glyph metrics
                low += [f"texts.{tid}.keys.0.box", f"texts.{tid}.style.size", f"texts.{tid}.style.outline_w"]
            ai, ai_n = x.get("anim_in") or (ai, ai_n)  # the reader took the animation from the project itself
            ao, ao_n = x.get("anim_out") or (ao, ao_n)
            how = {"from": "project" if x.get("anim_raw") else "box path" if keys else "keyframes", "animators": x.get("animators", 0),
                   **({"app": x["anim_raw"]} if x.get("anim_raw") else {})}
            if x.get("animators"):  # per-character animators move glyphs inside a still box: names from the box are a guess
                low += [f"texts.{tid}.anim_in", f"texts.{tid}.anim_out"]
            texts.append(ir.TextEvent(
                id=tid, start=a, end=b, text=ir.F[str](value=x["text"], raw=x["text"], source=scene["app"], binding="swap"),
                keys=path,
                style=ir.TextStyle(font=x["font"] or "Arial", size=size, fill=x["fill"] or "#FFFFFF", outline=x.get("outline"),
                                   outline_w=x.get("outline_px", 0) / h, shadow=bool((x.get("raw_style") or {}).get("shadow")), align=x["align"] or "center"),
                anim_in=ir.F[ir.TextAnim](value=ai, raw={"edge_frames": ai_n, **how}, source=scene["app"], conf=0.5 if x.get("animators") else x.get("anim_conf", 1.0)), anim_in_frames=ai_n,
                anim_out=ir.F[ir.TextAnim](value=ao, raw={"edge_frames": ao_n, **how}, source=scene["app"], conf=0.5 if x.get("animators") else x.get("anim_conf", 1.0)), anim_out_frames=ao_n))
        elif x["kind"] == "footage" and (x["blend"] != "normal" or x not in foot):
            vn = {"track": x["track"], "colour": x["color"], "speed": x["speed"], "reverse": x["reverse"], **x["raw"]} if "raw" in x else {}
            overlays.append(ir.Overlay(id=f"o{len(overlays) + 1:02d}", start=a, end=b,
                                       # After Effects footage keeps its full-frame key: its stored labels were built that way
                                       keys=(sample_keys(x.get("samples"), w, h) if vn else None) or [ir.Key(frame=a, box=ir.Box(x=0, y=0, w=1, h=1))],
                                       kind=ir.F[ir.OverlayKind](value="other", raw={"media": x["media"], "blend": x["blend"], **vn}, source=scene["app"]),
                                       description=ir.F[str](value=x["name"]), binding="swap" if x.get("swap") else "keep"))
        elif x["kind"] in ("solid", "shape", "other", "precomp_fx"):
            lk = sample_keys(x.get("samples"), w, h)
            layers.append(ir.Layer(id=f"l{len(layers) + 1:02d}", start=a, end=b, keys=[lk[0], rest_key(lk, b), lk[-1]] if lk else [ir.Key(frame=a, box=ir.Box(x=0, y=0, w=1, h=1))],
                                   kind=ir.F[ir.LayerKind](value="other", raw={k: x[k] for k in ("kind", "name", "color", "blend", "track", "depth")} | {"extra": x.get("raw_kind") or x.get("shape"), "stroke": x.get("stroke"), "stroke_px": x.get("stroke_px")},
                                                           source=scene["app"], conf=0.5),
                                   bg=x["color"]))
        add_fx(x["name"], a, b, x["effects"])
    if (w, h) != (config.W, config.H):
        low.append(f"source frame is {w}x{h}, not {config.W}x{config.H}: boxes are fractions of the source frame")
    source = {"app": scene["app"], "file": scene["file"], "name": scene["name"], "width": w, "height": h,
              "src_fps": scene["src_fps"], "duration_s": scene["duration"]}
    if scene["app"] == "vn":  # swappable must equal VN's own clip count (template.json "clips")
        source |= {"music": scene["music"], "tail": scene.get("tail"), "declared_clips": scene["declared_clips"],
                   "swappable": sum(s.media.binding == "swap" for s in slots) + sum(o.binding == "swap" for o in overlays)}
    return ir.Template(v=1, key=key, n_frames=n, audio="", slots=slots, transitions=transitions, texts=texts, layers=layers, overlays=overlays,
                       effects=effects, unsupported=unsupported, low_conf=low, narrative={"source": source})


# ---------------------------------------------------------------- driver

def read(folder: Path) -> dict | None:
    if (folder / "template.prproj").exists():
        return read_prproj(folder / "template.prproj")
    if (folder / "ae" / "dump.json").exists():
        return read_effectcraft(folder / "ae")
    if (folder / "Data" / "brief.json").exists():
        return read_vn(folder)
    return None


def preview_match(video: Path, scene: dict) -> dict:
    """Is preview.mp4 an export of this project? Same length (±0.1 s) and orientation; cut timing is not checked here."""
    from app.clients import ff
    try:
        info = ff.probe(video)
        vs = ff.video_stream(info)
    except Exception as e:
        return {"pair": False, "why": f"preview unreadable: {e}"}
    dur, w, h = float(info["format"].get("duration") or 0), vs.get("width") or 0, vs.get("height") or 0
    same_len = abs(dur - scene["duration"]) <= 0.1  # Mixkit previews are 59.94 fps re-encodes, a few frames short
    same_ori = (w > h) == (scene["width"] > scene["height"])
    return {"pair": same_len and same_ori, "duration": dur, "diff_s": round(dur - scene["duration"], 3), "width": w, "height": h,
            "why": "" if same_len and same_ori else f"preview {dur:.2f}s {w}x{h} vs project {scene['duration']:.2f}s {scene['width']}x{scene['height']}"}


def run(folder: Path) -> str:
    scene = read(folder)
    if scene is None:
        return "skipped: no .prproj, no ae/dump.json (run tools.effectcraft_import first) and no VN Data/brief.json"
    t = to_template(scene, folder.name)
    t.narrative["source"]["preview"] = preview_match(folder / (scene.get("preview") or "preview.mp4"), scene)
    t = ir.Template.model_validate(t.model_dump(mode="json"))  # schema check
    out = folder / "labels"
    out.mkdir(exist_ok=True)
    (out / "scene.json").write_text(json.dumps(scene, indent=1, default=str), encoding="utf-8")
    (out / "template.json").write_text(json.dumps(t.model_dump(mode="json"), indent=1), encoding="utf-8")
    return (f"ok: {len(t.slots)} slots, {len(t.transitions)} transitions, {len(t.texts)} texts, {len(t.overlays)} overlays, "
            f"{len(t.layers)} layers, {len(t.effects)} effects, {len(t.unsupported)} unsupported")


def main():
    folders = [Path(a) for a in sys.argv[1:]] or sorted(p.parent for p in MIXKIT.glob("*/*/meta.json"))
    for f in folders:
        try:
            print(f"{f.name}: {run(f)}")
        except Exception as e:  # one bad file must not stop the batch
            print(f"{f.name}: FAILED {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
