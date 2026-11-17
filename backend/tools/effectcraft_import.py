"""Open each Mixkit .mogrt in EffectCraft and read it back as a neutral scene for tools.app_readers.

    .venv\\Scripts\\python -m tools.effectcraft_import                   # every data/mixkit/*/<slug> with ae/*.aep
    .venv\\Scripts\\python -m tools.effectcraft_import path/to/<slug> ... # only these

Needs the EffectCraft release (effectcraft-cli.exe) under tools-bin/effectcraft/. Per template, in <slug>/ae/:
  import_report.json   file.importAep dry run: everything EffectCraft could not bring over
  template.ecproj      the project, openable in EffectCraft (File > Open)
  dump.json            evaluated layers of the main comp (expressions, parenting and precomps resolved)
  frame_<s>.png        EffectCraft renders at a few times, to compare with preview.mp4
The .aep inside the .mogrt is the After Effects project; definition.json's capsuleName names its main comp."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[2]
MIXKIT = ROOT / "data" / "mixkit"
FPS = 30
MAX_SAMPLES = 150  # per layer; boxes are sampled every STEP frames
STEP = 2
MAX_RECORDS = 400  # layer records per dump: rigs that reuse precomps hundreds of times would exhaust memory


def cli() -> Path:
    found = sorted((ROOT / "tools-bin" / "effectcraft").rglob("effectcraft-cli.exe"))
    if not found:
        raise FileNotFoundError("effectcraft-cli.exe not found under tools-bin/effectcraft (unzip the release there)")
    return found[0]


def ec(*args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run([str(cli()), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def last_json(text: str):
    """The CLI's JSON answer: the last line that parses."""
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


DUMP_JS = r"""
var MAIN = __MAIN__, FPS = __FPS__, STEP = __STEP__, MAXS = __MAXS__, MAXREC = __MAXREC__;
function comps() { var r = []; for (var i = 1; i <= app.project.numItems; i++) { var it = app.project.item(i); if (it instanceof CompItem) r.push(it); } return r; }
function norm(s) { return String(s).toLowerCase().replace(/[^a-z0-9]/g, ""); }
var all = comps(), main = null, how = "", used = {};
for (var i = 0; i < all.length; i++) for (var j = 1; j <= all[i].numLayers; j++) { var src = all[i].layer(j).source; if (src instanceof CompItem) used[src.id] = true; }
var roots = all.filter(function (c) { return !used[c.id]; });  // the exported comp is never nested in another
// MAIN: candidate names (capsuleName, the collect report's first comp); a root that matches wins
for (var m = 0; m < MAIN.length && !main; m++) for (var i = 0; i < roots.length; i++) if (norm(roots[i].name) === norm(MAIN[m])) { main = roots[i]; how = "name " + m; }
if (!main) { var size = function (c) { return /^settings/i.test(c.name) ? -1 : c.numLayers * c.duration; };
  for (var i = 0; i < roots.length; i++) if (!main || size(roots[i]) > size(main)) main = roots[i]; how = "largest root of " + roots.length; }
if (!main) { main = all[0]; how = "first"; }
if (/^settings/i.test(main.name)) {  // a settings comp that wraps the real one: "SETTINGS STORY05" -> "STORY05"
  var want = norm(main.name).replace(/^settings/, "");
  for (var i = 0; i < all.length; i++) if (norm(all[i].name) === want) { main = all[i]; how += ", inside settings"; }
}
function kind(l) {
  if (l instanceof TextLayer) return "text"; if (l instanceof ShapeLayer) return "shape";
  if (l instanceof CameraLayer) return "camera"; if (l instanceof LightLayer) return "light";
  if (l.nullLayer) return "null"; if (l.adjustmentLayer) return "adjustment";
  var s = l.source; if (s instanceof CompItem) return "precomp";
  if (s instanceof FootageItem) return String(s.mainSource) === "[object SolidSource]" ? "solid" : "footage";
  return "other";
}
function safe(f, d) { try { return f(); } catch (e) { return d; } }
function opac(l, t) { return safe(function () { return l.property("ADBE Transform Group").property("ADBE Opacity").valueAtTime(t, false); }, 100); }
function fx(l) {
  var out = [], g = safe(function () { return l.property("ADBE Effect Parade"); }, null);
  if (!g) return out;
  for (var i = 1; i <= g.numProperties; i++) { var e = g.property(i); out.push({ match: e.matchName, name: e.name, enabled: safe(function () { return e.enabled; }, true) }); }
  return out;
}
function fillOf(l, t) {  // colour of an enabled Fill effect (it recolours the whole layer)
  var g = safe(function () { return l.property("ADBE Effect Parade"); }, null), c = null;
  for (var i = 1; g && i <= g.numProperties; i++) { var e = g.property(i);
    if (!safe(function () { return e.enabled; }, true)) continue;
    if (e.matchName === "ADBE Fill") c = safe(function () { return e.property("Color").valueAtTime(t, false); }, c);
    if (e.matchName === "ADBE Ramp") c = safe(function () { var s0 = e.property("Start Color").valueAtTime(t, false), s1 = e.property("End Color").valueAtTime(t, false);
      return [0, 1, 2, 3].map(function (k) { return (s0[k] + s1[k]) / 2; }); }, c); }
  return c;
}
function shapeStyle(l, t) {  // first enabled fill and stroke inside a shape layer's contents
  var r = { fill: null, stroke: null, strokeWidth: 0 };
  function on(p) { return safe(function () { return p.enabled; }, true); }
  function walk(g, d) { for (var i = 1; i <= g.numProperties && d < 8; i++) { var p = g.property(i);
    if (p.matchName === "ADBE Vector Graphic - Fill" && on(p) && !r.fill) r.fill = safe(function () { return p.property("ADBE Vector Fill Color").valueAtTime(t, false); }, null);
    else if (p.matchName === "ADBE Vector Graphic - Stroke" && on(p) && !r.stroke) { r.stroke = safe(function () { return p.property("ADBE Vector Stroke Color").valueAtTime(t, false); }, null);
      r.strokeWidth = safe(function () { return p.property("ADBE Vector Stroke Width").valueAtTime(t, false); }, 0); }
    else if (p.propertyType !== PropertyType.PROPERTY && on(p)) walk(p, d + 1); } }
  safe(function () { walk(l.property("ADBE Root Vectors Group"), 0); }, null);
  return r;
}
function textDoc(l, t) {
  return safe(function () { var d = l.property("ADBE Text Properties").property("ADBE Text Document").valueAtTime(t, false);
    var r = { text: d.text, font: d.font, size: d.fontSize, fill: d.fillColor, justification: String(d.justification), animators: 0, animFill: null };
    var an = safe(function () { return l.property("ADBE Text Properties").property("ADBE Text Animators"); }, null);
    if (an) { r.animators = an.numProperties;
      for (var i = 1; i <= an.numProperties; i++) {  // an animator's Fill Color overrides the document's (expression-driven colours live here)
        var fc = safe(function () { return an.property(i).property("ADBE Text Animator Properties").property("ADBE Text Fill Color").valueAtTime(t, false); }, null);
        if (fc) r.animFill = fc; } }
    return r; }, null);
}
// chain: [{layer, comp}] from the innermost layer out to main; a point in a precomp layer's source
// space is a point in that precomp, so the outer layer's sourcePointToComp carries it up.
function setTimes(chain, tMain) {
  var t = tMain;
  for (var i = chain.length - 1; i >= 0; i--) { chain[i].comp.time = t; var L = chain[i].layer; if (i > 0) t = (t - L.startTime) / (L.stretch / 100); }
}
function localTime(chain, tMain) { var t = tMain; for (var i = chain.length - 1; i > 0; i--) { var L = chain[i].layer; t = (t - L.startTime) / (L.stretch / 100); } return t; }
function toMain(chain, p) { for (var i = 0; i < chain.length; i++) p = chain[i].layer.sourcePointToComp(p); return p; }
var out = { main: main.name, mainFrom: how, width: main.width, height: main.height, fps: main.frameRate, duration: main.duration, comps: all.map(function (c) { return c.name; }), layers: [] };
var visits = 0;
function walk(comp, chain, t0, t1, depth) {
  for (var i = comp.numLayers; i >= 1; i--) {  // bottom first
    var l = comp.layer(i), k = kind(l);
    if (!l.enabled && !l.isTrackMatte) continue;
    var c = [{ layer: l, comp: comp }].concat(chain);
    var a = t0, b = t1, inn = l.inPoint, ou = l.outPoint;
    // layer in/out in main time
    var off = 0, sc = 1; for (var j = chain.length - 1; j >= 0; j--) { var P = chain[j].layer; off = off + P.startTime * sc; sc = sc * P.stretch / 100; }
    a = Math.max(t0, off + inn * sc); b = Math.min(t1, off + ou * sc);
    if (b <= a) continue;
    var rec = { kind: k, name: l.name, depth: depth, index: i, comp: comp.name, start: a, end: b, blend: String(l.blendingMode), matte: l.isTrackMatte,
                effects: fx(l), samples: [] };
    // past the record budget: keep walking for text (the labels need it), drop everything else
    var over = out.layers.length >= MAXREC;
    if (++visits > 60000 || out.layers.length >= MAXREC + 300) { out.truncated = (out.truncated || 0) + 1; continue; }
    if (over && k !== "text" && k !== "precomp") { out.truncated = (out.truncated || 0) + 1; continue; }
    if (k === "precomp") { if (!over) out.layers.push(rec); if (depth < 6) walk(l.source, c, a, b, depth + 1); else rec.truncated = true; continue; }
    if (k === "solid") rec.color = safe(function () { return l.source.mainSource.color; }, null);
    if (k === "shape") { var st = shapeStyle(l, localTime(c, (a + b) / 2)); rec.color = st.fill; rec.stroke = st.stroke; rec.strokeWidth = st.strokeWidth; }
    if (k === "shape" || k === "solid") for (var j = 0; j < c.length; j++) { var f = fillOf(c[j].layer, localTime(c.slice(j), (a + b) / 2)); if (f) rec.color = f; }
    if (k === "footage") rec.media = safe(function () { return l.source.mainSource.file ? l.source.mainSource.file.fsName : l.source.name; }, l.source ? l.source.name : "");
    if (k === "text") { var tm = (a + b) / 2; rec.doc = textDoc(l, localTime(c, tm));
      for (var j = 0; j < c.length && rec.doc; j++) { var f = fillOf(c[j].layer, localTime(c.slice(j), tm)); if (f) rec.doc.effectFill = f; } }
    var n = Math.min(k === "text" && !over ? MAXS : 12, Math.max(2, Math.ceil((b - a) * FPS / STEP)));
    for (var s = 0; s < n; s++) {
      var t = a + (b - a) * s / (n - 1); if (t >= b) t = b - 1 / FPS / 2;
      var smp = { t: t, opacity: 1 };
      for (var j = 0; j < c.length; j++) smp.opacity *= opac(c[j].layer, localTime(c.slice(j), t)) / 100;
      if (k === "text" || k === "shape" || k === "solid" || k === "footage") {
        setTimes(c, t);
        var r = safe(function () { return l.sourceRectAtTime(localTime(c, t), false); }, null);
        if (!r && k !== "text" && k !== "shape") r = { left: 0, top: 0, width: l.width, height: l.height };
        if (r) { var pts = [[r.left, r.top], [r.left + r.width, r.top], [r.left, r.top + r.height], [r.left + r.width, r.top + r.height]].map(function (p) { return safe(function () { return toMain(c, p); }, null); });
          if (pts.every(function (p) { return p; })) { smp.quad = pts; smp.rw = r.width; smp.rh = r.height; } }
      }
      rec.samples.push(smp);
    }
    out.layers.push(rec);
  }
}
walk(main, [], 0, main.duration, 0);
JSON.stringify(out);
"""


# Essential Graphics controls live in a pseudo effect EffectCraft cannot import, so every expression that
# reads one (thisComp.layer("Controller").effect("<pseudo>")("main c1")) would fail. Replace that read
# with the control's default from definition.json: the look the template ships with.
BAKE_JS = r"""
var CONTROLS = __CONTROLS__, PSEUDO = __PSEUDO__, baked = 0, left = [];
function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
function bake(expr) {
  var out = expr;
  for (var i = 0; i < PSEUDO.length; i++) {
    var re = new RegExp("(?:thisComp|comp\\(\"[^\"]*\"\\))\\s*\\.\\s*layer\\((?:\"[^\"]*\"|\\d+)\\)\\s*\\.\\s*effect\\(\"" + esc(PSEUDO[i]) + "\"\\)\\(\"([^\"]+)\"\\)(?:\\.value)?", "g");
    out = out.replace(re, function (m, name) { return name in CONTROLS ? "(" + JSON.stringify(CONTROLS[name]) + ")" : m; });
  }
  return out;
}
function walk(g, where) {
  for (var i = 1; i <= g.numProperties; i++) {
    var p = g.property(i);
    if (p.propertyType === PropertyType.PROPERTY) {
      var e = ""; try { e = p.expression; } catch (x) {}
      if (e) { var b = bake(e); if (b !== e) { p.expression = b; baked++; }
               for (var k = 0; k < PSEUDO.length; k++) if (b.indexOf(PSEUDO[k]) >= 0) left.push(where + " > " + p.name); }
    } else walk(p, where + " > " + p.name);
  }
}
for (var i = 1; i <= app.project.numItems; i++) { var c = app.project.item(i); if (!(c instanceof CompItem)) continue;
  for (var j = 1; j <= c.numLayers; j++) walk(c.layer(j), c.name + " > " + c.layer(j).name); }
JSON.stringify({ baked: baked, unresolved: left });
"""


def controls(definition: dict) -> dict:
    """uiName -> default value of each Essential Graphics control that is a plain number, colour or switch."""
    out = {}
    for c in definition.get("clientControls", []):
        names = (c.get("uiName") or {}).get("strDB") or []
        v = c.get("value")
        if names and isinstance(v, (int, float, bool, list)) and not (isinstance(v, list) and not all(isinstance(x, (int, float)) for x in v)):
            out[names[0]["str"]] = v
    return out


def pseudo_effects(report) -> list[str]:
    import re
    found = set()
    for loss in (report or {}).get("report", {}).get("losses", []) if isinstance(report, dict) else []:
        for d in loss.get("details", []):
            found.update(re.findall(r"has the effect '([^']+)' \(Pseudo/", d))
    return sorted(found)


def target_comp(ae: Path) -> str | None:
    """The comp After Effects exported: first of "Collected comps:" in the .aegraphic's collect report."""
    import re
    for rp in ae.glob("*Report.txt"):
        t = rp.read_text(encoding="utf-8", errors="replace")
        m = re.search("Collected comps:\\s*([^\\t\\r\\n]+)", t)
        if m:
            return m.group(1).strip()
    return None


def dump_js(main: list[str]) -> str:
    return (DUMP_JS.replace("__MAIN__", json.dumps(main)).replace("__FPS__", str(FPS))
            .replace("__STEP__", str(STEP)).replace("__MAXS__", str(MAX_SAMPLES)).replace("__MAXREC__", str(MAX_RECORDS)))


def run(folder: Path) -> str:
    ae = folder / "ae"
    aeps = sorted(ae.glob("*.aep"))
    if not aeps:
        return "skipped: no ae/*.aep (unpack the .mogrt first)"
    aep = aeps[0]
    main = [n for n in (json.loads((ae / "definition.json").read_text(encoding="utf-8")).get("capsuleName"), target_comp(ae)) if n]
    # 1. what would be lost
    r = ec("--empty", "exec", "file.importAep", "--params", json.dumps({"path": str(aep), "dryRun": True}), "--json")
    report = last_json(r.stdout)
    (ae / "import_report.json").write_text(json.dumps({"exit": r.returncode, "report": report, "stderr": r.stderr[-4000:]}, indent=1), encoding="utf-8")
    # 2. import and save
    proj = ae / "template.ecproj"
    r = ec("--empty", "exec", "file.importAep", "--params", json.dumps({"path": str(aep), "allowLosses": True}), "--save-as", str(proj), "--json")
    if r.returncode or not proj.exists():
        return f"import failed ({r.returncode}): {(r.stderr or r.stdout).strip()[-400:]}"
    relinked = relink(proj, ae)
    # 2b. bake Essential Graphics control reads into literals
    definition = json.loads((ae / "definition.json").read_text(encoding="utf-8"))
    pseudo = pseudo_effects(report)
    bake = {"baked": 0, "unresolved": []}
    if pseudo:
        bj = ae / "bake.jsx"
        bj.write_text(BAKE_JS.replace("__CONTROLS__", json.dumps(controls(definition))).replace("__PSEUDO__", json.dumps(pseudo)), encoding="utf-8")
        r = ec("--project", str(proj), "script", str(bj), "--save", "--json")
        got = unwrap(last_json(r.stdout))
        bake = got if isinstance(got, dict) and "baked" in got else {"baked": 0, "unresolved": [], "error": (r.stderr or r.stdout)[-600:]}
    (ae / "bake_report.json").write_text(json.dumps({"pseudo_effects": pseudo, **bake}, indent=1), encoding="utf-8")
    # 3. evaluated dump
    js = ae / "dump.jsx"
    js.write_text(dump_js(main), encoding="utf-8")
    r = ec("--project", str(proj), "script", str(js), "--json", timeout=1800)
    dump = unwrap(last_json(r.stdout))
    if not isinstance(dump, dict) or "layers" not in dump:
        (ae / "dump_error.txt").write_text(r.stdout[-8000:] + "\n---\n" + r.stderr[-8000:], encoding="utf-8")
        return f"dump failed ({r.returncode}), see ae/dump_error.txt"
    (ae / "dump.json").write_text(json.dumps(dump, indent=1), encoding="utf-8")
    open_on_main(proj, dump["main"])
    # 4. a few frames for the eye
    for s in (0.5, dump["duration"] / 2, max(0.0, dump["duration"] - 0.5)):
        ec("--project", str(proj), "render-frame", "--comp", dump["main"], "--time", f"{s:.3f}", "--max-side", "960", "--out", str(ae / f"frame_{s:.1f}.png"))
    losses = report.get("report", report) if isinstance(report, dict) else report
    trunc = f" (TRUNCATED: {dump['truncated']} layers past {MAX_RECORDS} not sampled)" if dump.get("truncated") else ""
    return (f"ok: main comp {dump['main']!r}, {len(dump['layers'])} layers{trunc}; losses: {summary(losses)}; "
            f"baked {bake.get('baked', 0)} control reads, {len(bake.get('unresolved', []))} unresolved; relinked {relinked} footage paths")


RELINK_JS = r"""
var FILES = __FILES__, n = 0, left = [];
for (var i = 1; i <= app.project.numItems; i++) { var it = app.project.item(i);
  if (!(it instanceof FootageItem) || !it.footageMissing) continue;
  var want = String(it.missingFootagePath || it.name).split(/[\/]/).pop();
  if (FILES[want]) { try { it.replace(new File(FILES[want])); n++; } catch (e) { left.push(want + ": " + e); } } else left.push(want);
}
JSON.stringify({ relinked: n, missing: left });
"""


def relink(proj: Path, ae: Path) -> int:
    """Point missing footage at the copies packed in the .mogrt (the stored paths are the author's temp collect folder)."""
    files = {f.name: str(f.resolve()) for f in ae.rglob("*") if f.is_file() and f.suffix.lower() not in (".aep", ".json", ".jsx", ".ecproj", ".txt", ".png") or (f.is_file() and "(Footage)" in f.parts)}
    js = ae / "relink.jsx"
    js.write_text(RELINK_JS.replace("__FILES__", json.dumps(files)), encoding="utf-8")
    r = ec("--project", str(proj), "script", str(js), "--save", "--json")
    got = unwrap(last_json(r.stdout))
    return got.get("relinked", 0) if isinstance(got, dict) else 0


def open_on_main(proj: Path, main: str) -> bool:
    """Make File > Open show the template's main comp (activeComp / openComps are editor state in .ecproj)."""
    d = json.loads(proj.read_text(encoding="utf-8"))
    ids = [int(k) for k, v in d.get("items", {}).items() if v.get("name") == main and "Comp" in json.dumps(v.get("kind"))[:20]]
    if not ids:
        return False
    d["activeComp"], d["openComps"] = ids[0], [ids[0]]
    proj.write_text(json.dumps(d), encoding="utf-8")
    return True


def unwrap(v):
    """The script's completion value: the CLI may wrap it ({"result": "..."}) or print the JSON text."""
    if isinstance(v, dict) and isinstance(v.get("result"), str):
        v = v["result"]
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return v
    return v


def summary(rep) -> str:
    if not isinstance(rep, dict):
        return str(rep)[:200]
    keys = [k for k in ("losses", "lost", "unsupported", "effects", "limitations", "missingFootage", "missingFonts") if rep.get(k)]
    return ", ".join(f"{k}={len(rep[k]) if isinstance(rep[k], (list, dict)) else rep[k]}" for k in keys) or "none listed"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    skip = "--skip-done" in sys.argv  # keep dumps newer than this script
    folders = [Path(a) for a in args] or sorted(p.parent.parent for p in MIXKIT.glob("*/*/ae/definition.json"))
    for f in folders:
        dump = f / "ae" / "dump.json"
        if skip and dump.exists() and dump.stat().st_mtime > Path(__file__).stat().st_mtime:
            print(f"{f.name}: kept existing dump", flush=True)
            continue
        try:
            print(f"{f.name}: {run(f)}", flush=True)
        except Exception as e:  # one bad template must not stop the batch
            print(f"{f.name}: FAILED {type(e).__name__}: {e}", flush=True)


if __name__ == "__main__":
    main()
