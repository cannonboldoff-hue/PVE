"""Meaning: what each measured slot shows and why it is there, from a video AI behind one interface.

Each answer is {value, note, confidence}; value is from a closed vocabulary where one exists, note (free text) is
kept as raw. An out-of-vocabulary value lands as "other" with the model's word kept in the note, never as a default.
Timing never comes from here: slot windows are the measured cuts."""
import json
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import get_args

from pydantic import BaseModel, Field

from .. import config, ir
from ..clients import ff

RETRIES = 3  # rate-limit retries per call
BACKOFF = 5.0  # seconds, doubled each retry
PROMPT_VERSION = 4  # 2: text roles, font class; 3: masks, cutouts, moving layers; 4: reverse, effects, tiles,
# match cut in, 3D text tilt
TRANS_PAD = 30  # frames of context each side of a transition window (one second)
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
TEXT_ROLES = get_args(ir.TextRole)
BOX = {"type": "object", "description": "x, y, w, h as shares of the frame (0..1, top-left origin)",
       "properties": {k: {"type": "number"} for k in "xywh"}}
FONT_CLASSES = ("sans", "serif", "script", "display", "mono")
SLOT_SCHEMA = {
    "type": "object",
    "properties": {**{k: _answer_schema(v) for k, v in VOCAB.items()},
                   "style": {"type": "object", "properties": {k: {"type": "string"} for k in STYLE_KEYS}},
                   "texts": {"type": "array", "items": {"type": "object", "properties": {
                       "id": {"type": "string"},
                       "role": {"type": "string", "description": "one of: " + ", ".join(TEXT_ROLES)},
                       "font_class": {"type": "string", "description": "one of: " + ", ".join(FONT_CLASSES)},
                       "anim_note": {"type": "string"},
                       "tilt_x": {"type": "number", "description": "3D tilt back/forward in degrees, 0 if flat"},
                       "tilt_y": {"type": "number", "description": "3D turn left/right in degrees, 0 if flat"}}}},
                   "layers": {"type": "array", "items": {"type": "object", "properties": {
                       "kind": {"type": "string", "description": "one of: " + ", ".join(get_args(ir.LayerKind))},
                       "shape": {"type": "string"}, "box": BOX, "end_box": BOX, "note": {"type": "string"},
                       "in_front_of_text": {"type": "boolean"}, "confidence": {"type": "number"}}}},
                   "reverse": _answer_schema(("yes", "no")),
                   "match_cut_in": _answer_schema(("yes", "no")),
                   "effects": {"type": "array", "items": {"type": "object", "properties": {
                       "type": {"type": "string", "description": "one of: " + ", ".join(get_args(ir.EffectType))},
                       "start_s": {"type": "number"}, "end_s": {"type": "number"}, "confidence": {"type": "number"}}}},
                   "tiles": {"type": "array", "items": {"type": "object", "properties": {
                       "box": {"type": "integer", "description": "0-based, in the order of the measured layout boxes"},
                       "role": {"type": "string"}}}}},
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
      "animates in), color_look and, for a collage, tiles / background / style. For each measured text event listed "
      "in the facts, return `texts` with its id, its role (" + ", ".join(TEXT_ROLES) + "), the font_class of its "
      "lettering (" + ", ".join(FONT_CLASSES) + ") and anim_note: how it appears (pop, slide, typewriter, word "
      "highlight, fade...), plus tilt_x / tilt_y when the lettering is tilted in 3D (0 when flat). If the footage is "
      "shown through a shape (shape_mask), a subject is cut out from its background (cutout), or a picture layer "
      "moves across the frame (moving_layer), list each in `layers` with its shape, box at the start of the shot, "
      "end_box at the end, in_front_of_text (true when the cut-out subject covers on-screen words), a note and "
      "confidence; leave `layers` empty otherwise. reverse: yes when the footage plays backwards. match_cut_in: yes "
      "when this shot starts with a match cut (the subject or a shape stays in the same place and size while the "
      "scene, outfit or location changes). effects: each visual effect with its type (" +
    ", ".join(get_args(ir.EffectType)) + "), start_s / end_s in seconds from the start of this shot and confidence; "
      "empty when there is none. tiles: for a split screen, picture in picture or collage, what each box shows "
      "(box 0-based in the measured layout order, role e.g. 'main content', 'satisfying loop', 'reaction face').")
REEL_PROMPT = (
    "This is a vertical short-form video cut into {n} shots at these times (seconds): {cuts}. Describe its story: the "
    "hook, the arc, the payoff and the call to action, its overall style, and how shots relate to each other "
    "(setup/payoff, before/after, list items). Shots are numbered from 1.")

TRANS_VOCAB = get_args(ir.TransitionType)
TRANS_SCHEMA = _answer_schema(TRANS_VOCAB)
TRANS_PROMPT = (
    "This clip of a vertical short-form video holds the change from one shot to the next{window}. The change runs "
    "from {a:.2f} s to {b:.2f} s; frame analysis classes it as '{kind}'. Name the transition: value one of "
    + ", ".join(TRANS_VOCAB) + " (direction is where the new shot or the edge travels; use 'other' and explain in the "
    "note if none fits), a short note on what you see, and confidence 0..1.")


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
    texts: list[dict] = Field(default_factory=list)  # [{id, role, font_class, anim_note}] for measured text events
    layers: list[dict] = Field(default_factory=list)  # [{kind, shape, box, end_box, note, confidence}]
    reverse: Answer | None = None  # yes / no
    match_cut_in: Answer | None = None  # yes / no: this shot starts with a match cut
    effects: list[dict] = Field(default_factory=list)  # [{type, start_s, end_s, confidence}], seconds into the slot
    tiles: list[dict] = Field(default_factory=list)  # [{box, role}]
    error: str = ""


class TransitionMeaning(BaseModel):
    after_slot: str
    start: int
    end: int
    provider: str
    answer: Answer
    error: str = ""


def normalise(field: str, raw: dict | None, vocab: tuple[str, ...] | None = None) -> Answer:
    vocab = vocab or VOCAB.get(field)
    if not isinstance(raw, dict) or not str(raw.get("value", "")).strip():
        return Answer(value="other" if vocab else "", note="no answer", confidence=NO_ANSWER_CONF)
    value = str(raw["value"]).strip()
    note = str(raw.get("note") or "")
    conf = min(1.0, max(0.0, float(raw.get("confidence") or 0.5)))
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
        """One provider call, retried with backoff when the provider says it is rate limited."""
        for attempt in range(RETRIES + 1):
            try:
                return self._ask(prompt, schema, start, end)
            except Exception as e:
                text = str(e).lower()
                if attempt == RETRIES or not any(k in text for k in ("429", "rate", "quota", "resource_exhausted",
                                                                    "too many")):
                    raise
                time.sleep(BACKOFF * 2 ** attempt)
        raise AssertionError("unreachable")

    def _ask(self, prompt: str, schema: dict, start: int | None = None, end: int | None = None) -> dict:
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
        if i.track == "text" and slot.start <= i.start < slot.end:
            facts.append(f"text event {i.id}: {json.dumps(i.data['text'])} from {ir.f2s(i.start - slot.start):.2f} s "
                         f"to {ir.f2s(i.end - slot.start):.2f} s of this shot")
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
    m.texts = [t for t in raw.get("texts") or [] if isinstance(t, dict) and t.get("id")]
    m.layers = [x for x in raw.get("layers") or [] if isinstance(x, dict)]
    m.reverse = normalise("reverse", raw.get("reverse"), ("yes", "no")) if raw.get("reverse") else None
    m.match_cut_in = normalise("match_cut_in", raw.get("match_cut_in"), ("yes", "no")) if raw.get("match_cut_in") else None
    m.effects = [x for x in raw.get("effects") or [] if isinstance(x, dict) and x.get("type")]
    m.tiles = [x for x in raw.get("tiles") or [] if isinstance(x, dict) and isinstance(x.get("box"), int)]
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


def describe_transition(s: Session, t: ir.Transition, n_frames: int) -> TransitionMeaning:
    """The measured window plus a second each side; the model names it, evidence keeps the window."""
    cache = _cache_path(s.key, "transition", t.start, t.end, t.type.value, s.provider)
    if cache.exists():
        return TransitionMeaning.model_validate_json(cache.read_text(encoding="utf-8"))
    lo, hi = max(0, t.start - TRANS_PAD), min(n_frames, t.end + TRANS_PAD)
    base = lo if s.provider == "gemini" else 0  # gemini sees the window cut out; pegasus the whole reel
    window = "" if s.provider == "gemini" else f" from {ir.f2s(lo):.2f} s to {ir.f2s(hi):.2f} s"
    m = TransitionMeaning(after_slot=t.after_slot, start=t.start, end=t.end, provider=s.provider,
                          answer=normalise("transition", None, TRANS_VOCAB))
    try:
        raw = s.ask(TRANS_PROMPT.format(window=window, a=ir.f2s(t.start - base), b=ir.f2s(t.end - base),
                                        kind=t.type.value), TRANS_SCHEMA, lo, hi)
    except Exception as e:  # not cached, so a rerun retries
        m.error = str(e)[:300]
        return m
    m.answer = normalise("transition", raw, TRANS_VOCAB)
    cache.write_text(m.model_dump_json(), encoding="utf-8")
    return m


def describe_transitions(s: Session, trans: list[ir.Transition], n_frames: int) -> list[TransitionMeaning]:
    """Gradual transitions only: a hard cut has nothing to name."""
    gradual = [t for t in trans if t.end > t.start]
    with ThreadPoolExecutor(WORKERS) as pool:
        return list(pool.map(lambda t: describe_transition(s, t, n_frames), gradual))
