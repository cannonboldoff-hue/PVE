"""One bridge: PVE template JSON (the labels) -> FilmCraft project (.fcproj), to check labels by eye.

    .venv\\Scripts\\python -m tools.filmcraft_bridge                    # every data/mixkit/*/<slug>/labels/template.json
    .venv\\Scripts\\python -m tools.filmcraft_bridge path/to/<slug> ...  # only these

Writes <slug>/labels/template.fcproj. FilmCraft refuses .mogrt / .aep by design, so it never sees the
editor file: only the labels, which is the same for every app reader. Layout of the sequence (bottom first):
  V1     one colour-matte placeholder per slot: drop footage over it
  V2..   layers with a flat colour (solids) as colour mattes
  then   one graphic clip per text event (FilmCraft text layer, position and opacity keyed from the box path)
  top    preview.mp4, switched off: turn it on to compare with the original
Effects, overlays, transitions and every unsupported line become sequence markers, so nothing is hidden.
Written as the schema-1 project shape (FilmCraft migrates it on open; docs/project-files.md)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import ir  # noqa: E402

TICKS = 254_016_000_000
FPS = ir.FPS
MIXKIT = Path(__file__).resolve().parents[2] / "data" / "mixkit"
ALIGN = {"left": 0, "center": 1, "right": 2}  # filmcraft_project::graphic::ALIGN_OPTS
SLOT_GREYS = [(0.22, 0.24, 0.30), (0.30, 0.22, 0.26), (0.20, 0.30, 0.24), (0.30, 0.28, 0.20)]


def tk(frame: int | float) -> int:
    return int(round(frame * TICKS / FPS))


def P(kind: str, v) -> dict:
    return {"value": {kind: v}}


def rgba(hexc: str | None, a: float = 1.0) -> list[float]:
    h = (hexc or "#FFFFFF").lstrip("#")
    try:
        return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [a]
    except ValueError:
        return [1.0, 1.0, 1.0, a]


class Builder:
    def __init__(self, name: str, w: int, h: int):
        self.w, self.h, self.next = w, h, 2
        self.items: dict[str, dict] = {}
        self.bin_children: list = []
        self.video_tracks: list[dict] = []
        self.markers: list[dict] = []
        self.name = name

    def id(self) -> int:
        self.next += 1
        return self.next

    def video_info(self, name: str, kind: str, dur: int, w: int, h: int) -> dict:
        return {"name": name, "kind": kind, "duration": dur,
                "video": {"width": w, "height": h, "frame_rate": {"num": FPS, "den": 1}, "par": [1, 1], "codec": "", "pixel_format": "RGBA 8-bit",
                          "color": {"matrix": "Bt709", "transfer": "Srgb", "primaries": "Bt709", "range": "Full"}, "has_alpha": False, "bitrate": None},
                "audio": None, "container": "", "start_timecode": None, "file_size": None}

    def media_item(self, name: str, media: dict, info: dict) -> int:
        i = self.id()
        self.items[str(i)] = {"id": i, "name": name, "label": "Iris", "kind": {"Media": {
            "media": media, "info": info, "interpret": {"frame_rate": None, "par": None, "ignore_alpha": False, "invert_alpha": False},
            "mark_in": None, "mark_out": None, "markers": [], "offline": False, "proxy": None}}}
        self.bin_children.append({"Item": i})
        return i

    def matte(self, name: str, color: list[float], dur: int) -> int:
        return self.media_item(name, {"Generator": {"ColorMatte": {"color": color}}}, self.video_info(name, "Synthetic", dur, self.w, self.h))

    def graphic(self) -> int:
        i = self.id()
        self.items[str(i)] = {"id": i, "name": "Graphic", "label": "Mango", "kind": {"Graphic": {"width": self.w, "height": self.h, "rate": {"num": FPS, "den": 1}}}}
        return i

    def motion(self) -> list[dict]:
        return [{"effect": "motion", "enabled": True, "params": {
                    "anchor": P("Vec2", {"x": self.w / 2, "y": self.h / 2}), "anti_flicker": P("Float", 0.0),
                    "position": P("Vec2", {"x": self.w / 2, "y": self.h / 2}), "rotation": P("Float", 0.0), "scale": P("Float", 100.0),
                    "scale_width": P("Float", 100.0), "uniform_scale": P("Bool", True)}},
                {"effect": "opacity", "enabled": True, "params": {"blend": P("Choice", 0), "opacity": P("Float", 100.0)}},
                {"effect": "time_remap", "enabled": True, "params": {"speed": P("Float", 100.0)}}]

    def clip(self, item: int, name: str, start: int, end: int, effects: list | None = None, enabled: bool = True) -> dict:
        return {"id": self.id(), "item": item, "name": name, "label": "Iris", "start": tk(start), "duration": tk(end) - tk(start),
                "source_in": 0, "speed": 1.0, "enabled": enabled, "effects": self.motion() + (effects or [])}

    def track(self, name: str, clips: list[dict], enabled: bool = True) -> None:
        self.video_tracks.append({"id": self.id(), "kind": "Video", "name": name, "items": sorted(clips, key=lambda c: c["start"]),
                                  "transitions": [], "locked": False, "sync_lock": True, "enabled": enabled, "muted": False,
                                  "solo": False, "channels": "Stereo", "volume_db": 0.0, "pan": 0.0})

    def marker(self, frame: int, end: int, name: str, comment: str) -> None:
        self.markers.append({"id": 800000 + len(self.markers), "start": tk(frame), "duration": max(0, tk(end) - tk(frame)),
                             "name": name[:60], "comment": comment[:2000], "kind": "Comment", "color": "Green"})

    def project(self, dur: int) -> dict:
        seq = self.id()
        self.items[str(seq)] = {"id": seq, "name": self.name, "label": "Forest", "kind": {"Sequence": {
            "settings": {"width": self.w, "height": self.h, "frame_rate": {"num": FPS, "den": 1}, "par": [1, 1], "sample_rate": 48000,
                         "drop_frame": False, "preset": f"{self.w}x{self.h} {FPS}p", "audio_master": "Stereo", "preview_codec": "ProRes 422",
                         "max_bit_depth": False, "max_render_quality": False, "working_space": "Rec. 709"},
            "video_tracks": self.video_tracks, "audio_tracks": [], "markers": sorted(self.markers, key=lambda m: m["start"]),
            "mark_in": None, "mark_out": None, "work_area": None, "start_timecode": 0}}}
        return {"name": self.name, "settings": {"renderer": "FilmCraft GPU Acceleration (wgpu)", "video_display": "Timecode",
                                                "audio_display_samples": True, "default_still_duration": 1270080000000,
                                                "default_transition_duration_frames": 24, "default_audio_transition_duration": TICKS},
                "root": {"id": 0, "name": self.name, "children": [{"Bin": {"id": 1, "name": "Placeholders and media", "children": self.bin_children}},
                                                                  {"Item": seq}]},
                "items": self.items, "next_id": self.id() + 1, "version": 1}


def text_effect(t: ir.TextEvent, w: int, h: int) -> dict:
    """A FilmCraft text layer from a TextEvent: rest box centre as position, opacity / position keyed from the path."""
    rest = t.keys[0].box
    size = max(1.0, t.style.size * h)
    text = t.text.value.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10))
    lines = max(1, round(rest.h * h / (size * 1.2)))
    paragraph = lines > text.count(chr(10)) + 1  # wraps inside a box (AE box text): keep the measured box
    ax = {"left": 0.0, "center": 0.5, "right": 1.0}.get(t.style.align, 0.5)

    def origin(b: ir.Box) -> dict:  # paragraph: box top-left; point: alignment point on the first baseline
        if paragraph:
            return {"x": b.x * w, "y": b.y * h}
        return {"x": (b.x + b.w * ax) * w, "y": b.y * h + size * 0.8}
    params = {"name": {"value": {"Text": t.id}}, "text": {"value": {"Text": text}},
              "font": {"value": {"Text": t.style.font}}, "size": P("Float", size),
              "box_width": P("Float", rest.w * w * 1.06 if paragraph else 0.0),
              "align": P("Choice", ALIGN.get(t.style.align, 1)), "fill_color": P("Color", rgba(t.style.fill)),
              "shadow": P("Bool", t.style.shadow), "anchor": P("Vec2", {"x": 0.0, "y": 0.0}),
              "position": P("Vec2", origin(rest))}
    path = t.keys[1:] if len(t.keys) > 1 else []
    if path:  # keyframe times are relative to the clip start (source_in 0, speed 1)
        params["position"]["keyframes"] = [{"time": tk(k.frame - t.start), "value": {"Vec2": origin(k.box)},
                                            "interp": "Linear"} for k in path if t.start <= k.frame <= t.end]
        params["opacity"] = {"value": {"Float": 100.0}, "keyframes": [{"time": tk(k.frame - t.start), "value": {"Float": round(k.opacity * 100, 2)}, "interp": "Linear"}
                                                                     for k in path if t.start <= k.frame <= t.end]}
    elif "fade" in (t.anim_in.value, t.anim_out.value):  # no path: key the named fades
        d, ks = t.end - t.start, []
        if t.anim_in.value == "fade":
            ks += [(0, 0.0), (min(d, max(1, t.anim_in_frames)), 100.0)]
        if t.anim_out.value == "fade":
            ks += [(max(0, d - max(1, t.anim_out_frames)), 100.0), (d, 0.0)]
        ks = sorted(dict(ks).items())
        params["opacity"] = {"value": {"Float": 100.0}, "keyframes": [{"time": tk(f), "value": {"Float": v}, "interp": "Linear"} for f, v in ks]}
    return {"effect": "graphic_text", "enabled": True, "params": params}


def build(t: ir.Template, preview: Path | None) -> dict:
    src = t.narrative.get("source", {})
    w, h = int(src.get("width") or 1080), int(src.get("height") or 1920)
    b = Builder(t.key, w, h)
    n = t.n_frames
    # V1: slot placeholders
    clips = []
    for i, s in enumerate(t.slots):
        g = SLOT_GREYS[i % len(SLOT_GREYS)]
        m = b.matte(f"{s.id} placeholder", [*g, 1.0], tk(n))
        clips.append(b.clip(m, f"{s.id} ({s.media.value})", s.start, s.end))
    b.track("Slots", clips)
    # solid layers
    for L in t.layers:
        name = L.kind.raw.get("name", "") if isinstance(L.kind.raw, dict) else ""
        k = L.keys[1] if len(L.keys) == 3 else L.keys[0]  # [first, rest pose, last] from the readers
        raw = L.kind.raw if isinstance(L.kind.raw, dict) else {}
        full = k.box.w >= 0.98 and k.box.h >= 0.98
        if L.bg and full:  # a full-frame solid: colour matte at the layer's opacity
            m = b.matte(f"{L.id} {name}", rgba(L.bg), tk(n))
            c = b.clip(m, L.id, L.start, L.end)
            c["effects"][1]["params"]["opacity"] = P("Float", round(k.opacity * 100, 2))
            b.track(f"Layer {L.id}", [c])
        elif L.bg or raw.get("stroke"):  # a smaller shape: a rectangle on its measured bounding box (rotation kept out)
            g = b.graphic()
            shape = {"effect": "graphic_shape", "enabled": True, "params": {
                "name": {"value": {"Text": f"{L.id} {name}"}}, "shape": P("Choice", 0),
                "size": P("Vec2", {"x": k.box.w * w, "y": k.box.h * h}), "fill": P("Bool", bool(L.bg)), "fill_color": P("Color", rgba(L.bg)),
                "stroke": P("Bool", bool(raw.get("stroke"))), "stroke_color": P("Color", rgba(raw.get("stroke"))),
                "stroke_width": P("Float", float(raw.get("stroke_px") or 0)), "stroke_type": P("Choice", 2),
                "position": P("Vec2", {"x": (k.box.x + k.box.w / 2) * w, "y": (k.box.y + k.box.h / 2) * h}),
                "opacity": P("Float", round(k.opacity * 100, 2))}}
            b.track(f"Layer {L.id}", [b.clip(g, f"{L.id} {name}", L.start, L.end, [shape])])
        else:
            b.marker(L.start, L.end, f"layer {L.id}", json.dumps(L.kind.raw, default=str))
    # texts, one track each (FilmCraft track items may not overlap)
    for x in t.texts:
        g = b.graphic()
        b.track(f"Text {x.id}", [b.clip(g, x.text.value[:40], x.start, x.end, [text_effect(x, w, h)])])
        b.marker(x.start, x.end, f"{x.id} in:{x.anim_in.value} out:{x.anim_out.value}", f"{x.text.value} | font {x.style.font}")
    for e in t.effects:
        b.marker(e.start, e.end, f"fx {e.type.value}: {(e.type.raw or {}).get('name', '')}", json.dumps(e.type.raw, default=str))
    for o in t.overlays:
        b.marker(o.start, o.end, f"overlay {o.id}", json.dumps(o.kind.raw, default=str))
    for tr in t.transitions:
        b.marker(tr.start, tr.end, f"transition {tr.type.value}", json.dumps(tr.params))
    for u in t.unsupported:
        b.marker(0, 0, "unsupported", u)
    # the original, off: turn the track on to compare
    if preview and preview.exists():
        info = probe(preview)
        if info:
            m = b.media_item(preview.name, {"File": {"path": str(preview.resolve())}}, info)
            c = b.clip(m, "original", 0, min(n, int(info["duration"] * FPS / TICKS)))
            c["scale_to_frame"] = True  # previews are smaller re-encodes (608x1080)
            for k in ("anchor", "position"):  # null = auto: the source centre / frame centre (anchor is in source pixels)
                c["effects"][0]["params"][k] = P("Vec2", {"x": None, "y": None})
            b.track("Original (off)", [c], enabled=False)
    return b.project(n)


def probe(p: Path) -> dict | None:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(p)],
                           capture_output=True, text=True, timeout=60)
        j = json.loads(r.stdout)
        v = next(s for s in j["streams"] if s["codec_type"] == "video")
        num, den = (int(x) for x in v["r_frame_rate"].split("/"))
        dur = int(float(j["format"]["duration"]) * TICKS)
    except (subprocess.SubprocessError, json.JSONDecodeError, StopIteration, KeyError, ValueError):
        return None
    return {"name": p.name, "kind": "Movie", "duration": dur,
            "video": {"width": v["width"], "height": v["height"], "frame_rate": {"num": num, "den": den or 1}, "par": [1, 1],
                      "codec": v.get("codec_name", ""), "pixel_format": "YUV 4:2:0 8-bit",
                      "color": {"matrix": "Bt709", "transfer": "Bt709", "primaries": "Bt709", "range": "Limited"}, "has_alpha": False, "bitrate": None},
            "audio": None, "container": "MPEG-4", "start_timecode": None, "file_size": p.stat().st_size}


def run(folder: Path) -> str:
    f = folder / "labels" / "template.json"
    if not f.exists():
        return "skipped: no labels/template.json (run tools.app_readers first)"
    t = ir.Template.model_validate(json.loads(f.read_text(encoding="utf-8")))
    proj = build(t, folder / "preview.mp4")
    out = folder / "labels" / "template.fcproj"
    out.write_text(json.dumps(proj, separators=(",", ":")), encoding="utf-8")
    seq = next(v for v in proj["items"].values() if "Sequence" in v["kind"])["kind"]["Sequence"]
    return f"ok: {out.name}, {len(seq['video_tracks'])} tracks, {len(seq['markers'])} markers"


def main():
    folders = [Path(a) for a in sys.argv[1:]] or sorted(p.parent.parent for p in MIXKIT.glob("*/*/labels/template.json"))
    for f in folders:
        try:
            print(f"{f.name}: {run(f)}")
        except Exception as e:  # one bad template must not stop the batch
            print(f"{f.name}: FAILED {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
