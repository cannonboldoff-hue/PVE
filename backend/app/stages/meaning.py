"""Meaning: what each measured slot shows and why it is there, from a video AI behind one interface.

Each answer is {value, note, confidence}; value is from a closed vocabulary where one exists, note (free text) is
kept as raw. An out-of-vocabulary value lands as "other" with the model's word kept in the note, never as a default.
Timing never comes from here: slot windows are the measured cuts."""
import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import get_args

from pydantic import BaseModel, Field

from .. import config, ir
from ..clients import ff

PROMPT_VERSION = 1
WORKERS = 4
NO_ANSWER_CONF = 0.0

VOCAB: dict[str, tuple[str, ...] | None] = {  # Slot semantic field -> closed vocabulary (None: free text)
    "media": get_args(ir.Media),
    "role": get_args(ir.Role),
    "function": None,
    "subject": None,
    "action": None,
    "shot_size": get_args(ir.ShotSize),
    "angle": None,
    "layout": get_args(ir.Layout),
    "camera": get_args(ir.CameraMove),
}
# legacy style notes still feed styles.py (captions, colour, collage) until M4 and M8 replace them
STYLE_KEYS = ("on_screen_text", "background", "frame_motion", "overlays", "caption_animation", "caption_font",
              "caption_color", "caption_position", "caption_size", "caption_emphasis", "color_look", "collage_tiles",
              "collage_background", "collage_style", "camera_motion")


def _answer_schema(vocab) -> dict:
    v = {"type": "string"}
    if vocab:
        v["description"] = "one of: " + ", ".join(vocab)
    return {"type": "object", "properties": {"value": v, "note": {"type": "string"}, "confidence": {"type": "number"}},
            "required": ["value", "note", "confidence"]}


# no "enum": not every provider accepts it in a response schema; the vocabulary is in the descriptions and prompt
SLOT_SCHEMA = {
    "type": "object",
    "properties": {**{k: _answer_schema(v) for k, v in VOCAB.items()},
                   "style": {"type": "object", "properties": {k: {"type": "string"} for k in STYLE_KEYS}}},
    "required": list(VOCAB),
}
REEL_SCHEMA = {
    "type": "object",
    "properties": {"hook": {"type": "string"}, "arc": {"type": "string"}, "payoff": {"type": "string"},
                   "cta": {"type": "string"}, "overall_style": {"type": "string"},
                   "relations": {"type": "array", "items": {"type": "object", "properties": {
                       "from_slot": {"type": "integer"}, "to_slot": {"type": "integer"}, "relation": {"type": "string"}}}}},
    "required": ["hook", "arc", "payoff", "cta", "overall_style"],
}

SLOT_PROMPT = (
    "You see one shot of a vertical short-form video{window}. Measured facts about it: {facts}.\n"
    "For each field give value, a short note in your own words, and confidence 0..1.\n"
    + "\n".join(f"- {k}: " + ("one of " + ", ".join(v) + " (use 'other' and explain in the note if none fits)" if v
                               else "free text") for k, v in VOCAB.items())
    + "\nrole is why this shot is in the story (hook, establish, detail, action, reveal, reaction, payoff, cta); "
      "function is one line on what the shot does for the viewer. Also fill `style` with the on-screen text (exact "
      "words), background, frame_motion, overlays, caption look (font, colour, position, size, emphasis, how it "
      "animates in), color_look and, for a collage, tiles / background / style.")
REEL_PROMPT = (
    "This is a vertical short-form video cut into {n} shots at these times (seconds): {cuts}. Describe its story: the "
    "hook, the arc, the payoff and the call to action, its overall style, and how shots relate to each other "
    "(setup/payoff, before/after, list items). Shots are numbered from 1.")


class Answer(BaseModel):
    value: str
    note: str = ""
    confidence: float = 0.5


class SlotMeaning(BaseModel):
    slot: str
    start: int
    end: int
    provider: str
    fields: dict[str, Answer] = Field(default_factory=dict)
    style: dict = Field(default_factory=dict)
    error: str = ""


def normalise(field: str, raw: dict | None) -> Answer:
    if not isinstance(raw, dict) or not str(raw.get("value", "")).strip():
        return Answer(value="other" if VOCAB.get(field) else "", note="no answer", confidence=NO_ANSWER_CONF)
    value = str(raw["value"]).strip()
    note = str(raw.get("note") or "")
    conf = min(1.0, max(0.0, float(raw.get("confidence") or 0.5)))
    vocab = VOCAB.get(field)
    if vocab:
        v = value.lower().replace(" ", "_").replace("-", "_")
        if v not in vocab:  # out of vocabulary: keep the model's word, never fall back to a default
            return Answer(value="other", note=f"{value}: {note}".strip(": "), confidence=conf)
        value = v
    return Answer(value=value, note=note, confidence=conf)


def _cache_path(key: str, *parts) -> Path:
    src = ir.load(key, "source", ir.Source)
    p = ir.ref_dir(key) / "meaning" / f"{ir.digest([src.fingerprint, *parts, PROMPT_VERSION])}.json"
    p.parent.mkdir(exist_ok=True)
    return p


def _cut(media: Path, start: int, end: int, out: Path) -> Path:
    """The slot alone, so the model cannot see neighbouring shots (sound kept when the media has it)."""
    ff.run(["-ss", f"{ir.f2s(start):.4f}", "-i", str(media), "-t", f"{ir.f2s(end - start):.4f}", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)])
    return out


class Session:
    """One provider conversation over one reference. Pegasus: the media is uploaded once and deleted at the end.
    Gemini: each slot is cut to its own clip and uploaded on its own."""

    def __init__(self, key: str, media: Path, provider: str | None = None):
        self.key, self.media, self.provider = key, Path(media), provider or config.VLM_PROVIDER
        self._asset: str | None = None
        self._lock = threading.Lock()  # slots are described in parallel; upload once

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self._asset:
            from ..clients import twelvelabs

            twelvelabs.delete_asset(self._asset)

    def ask(self, prompt: str, schema: dict, start: int | None = None, end: int | None = None) -> dict:
        if self.provider == "gemini":
            from ..clients import gemini

            if start is None:
                return gemini.describe(self.media, prompt, schema)
            with tempfile.TemporaryDirectory() as d:
                return gemini.describe(_cut(self.media, start, end, Path(d) / "slot.mp4"), prompt, schema)
        from ..clients import twelvelabs

        with self._lock:
            if self._asset is None:
                self._asset = twelvelabs.upload_asset(str(self.media))
        if start is None:
            return twelvelabs.analyze(self._asset, prompt, schema)
        return twelvelabs.analyze(self._asset, prompt, schema, ir.f2s(start), ir.f2s(end))


def _facts(slot: ir.Slot, ev: ir.Evidence) -> str:
    """Measured facts for one slot, so the model describes rather than re-measures."""
    facts = [f"{ir.f2s(slot.frames):.2f} s long ({slot.frames} frames at {ir.FPS} fps)"]
    for i in ev.items:
        if i.track != "cuts" and i.start < slot.end and i.end > slot.start and "value" in i.data:
            facts.append(f"{i.track}: {i.data['value']}")
    return "; ".join(facts)


def describe_slot(s: Session, slot: ir.Slot, ev: ir.Evidence) -> SlotMeaning:
    cache = _cache_path(s.key, "slot", slot.start, slot.end, s.provider)
    if cache.exists():
        return SlotMeaning.model_validate_json(cache.read_text(encoding="utf-8"))
    window = "" if s.provider == "gemini" else f" from {ir.f2s(slot.start):.2f} s to {ir.f2s(slot.end):.2f} s"
    m = SlotMeaning(slot=slot.id, start=slot.start, end=slot.end, provider=s.provider)
    try:
        raw = s.ask(SLOT_PROMPT.format(window=window, facts=_facts(slot, ev)), SLOT_SCHEMA, slot.start, slot.end)
    except Exception as e:  # one slot failing must not lose the measured template; not cached, so a rerun retries
        m.error = str(e)[:300]
        m.fields = {k: normalise(k, None) for k in VOCAB}
        return m
    m.fields = {k: normalise(k, raw.get(k)) for k in VOCAB}
    m.style = {k: v for k, v in (raw.get("style") or {}).items() if k in STYLE_KEYS and v not in (None, "")}
    cache.write_text(m.model_dump_json(), encoding="utf-8")
    return m


def describe_slots(s: Session, slots: list[ir.Slot], ev: ir.Evidence) -> list[SlotMeaning]:
    with ThreadPoolExecutor(WORKERS) as pool:
        return list(pool.map(lambda sl: describe_slot(s, sl, ev), slots))


def describe_reel(s: Session, slots: list[ir.Slot]) -> dict:
    cuts = [round(ir.f2s(x.start), 2) for x in slots[1:]]
    cache = _cache_path(s.key, "reel", cuts, s.provider)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        r = s.ask(REEL_PROMPT.format(n=len(slots), cuts=cuts or "none"), REEL_SCHEMA)
    except Exception as e:
        return {"error": str(e)[:300]}
    cache.write_text(json.dumps(r), encoding="utf-8")
    return r
