"""Intermediate representation of a reference reel: Evidence -> Observed -> Template -> Delta.
Every time is an integer frame at config.FPS (docs/mvp-plan.md 3.3). Seconds appear only at the edges via f2s."""
import hashlib
import json
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from . import config

FPS = config.FPS
T = TypeVar("T")


def f2s(frame: int | float) -> float:
    return frame / FPS


def s2f(seconds: float) -> int:
    return int(round(seconds * FPS))


# closed vocabularies; each has "other", and an "other" value always carries raw
TransitionType = Literal[
    "cut", "fade", "dissolve", "fade_black", "fade_white",
    "slide_left", "slide_right", "slide_up", "slide_down",
    "push_left", "push_right", "push_up", "push_down",
    "wipe_left", "wipe_right", "wipe_up", "wipe_down",
    "zoom_in", "zoom_out", "whip_left", "whip_right", "whip_up", "whip_down",
    "spin", "glitch", "blur", "other",
]
EffectType = Literal["flash", "shake", "glitch", "rgb_split", "glow", "blur", "grain", "vignette", "scanlines",
                     "zoom_punch", "other"]
CameraMove = Literal["static", "zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "handheld",
                     "shake", "other"]
TextAnim = Literal["none", "fade", "pop", "slide_up", "slide_down", "slide_left", "slide_right", "typewriter",
                   "word_highlight", "bounce", "other"]
Layout = Literal["single", "blur_fill", "letterbox", "split_h", "split_v", "collage", "pip"]
OverlayKind = Literal["sticker", "emoji", "shape", "frame", "progress_bar", "logo", "other"]
Role = Literal["hook", "establish", "detail", "action", "reveal", "reaction", "payoff", "cta", "other"]
TextRole = Literal["hook_line", "title", "list_item", "label", "punchline", "cta", "caption", "other"]
ShotSize = Literal["extreme_close", "close", "medium", "wide", "extreme_wide", "none"]
Binding = Literal["keep", "swap", "drop"]
Media = Literal["video", "photo", "other"]
LayerKind = Literal["shape_mask", "cutout", "moving_layer", "other"]


class F(BaseModel, Generic[T]):
    """One observed or templated value. A label never travels without its raw value."""
    value: T
    raw: Any = None  # measurement or free text the value came from
    conf: float = 1.0  # 0..1
    source: str = ""  # "cuts", "ocr", "gemini", "fusion", "llm", "user"
    evidence: list[str] = Field(default_factory=list)  # ids of Evidence items
    binding: Binding | None = None  # set in extraction


class Item(BaseModel):
    """One Evidence item. Append-only."""
    id: str  # "<track>_<n>", stable within a reference
    track: str
    start: int  # frame, inclusive
    end: int  # frame, exclusive
    data: dict = Field(default_factory=dict)  # track-specific payload
    conf: float = 1.0
    tool: str = ""  # "pyscenedetect 0.7.3", "opencv flow", ...


class Source(BaseModel):
    key: str
    fingerprint: str
    n_frames: int
    width: int
    height: int
    src_fps: float  # the original frame rate, for the record


class Evidence(BaseModel):
    items: list[Item] = Field(default_factory=list)

    def track(self, name: str) -> list[Item]:
        return [i for i in self.items if i.track == name]


class Box(BaseModel):  # normalised 0..1, origin top-left
    x: float
    y: float
    w: float
    h: float


class Key(BaseModel):  # one keyframe of a moving thing
    frame: int
    box: Box
    scale: float = 1.0
    rotation: float = 0.0
    opacity: float = 1.0


class ColourTarget(BaseModel):
    """Per-shot Lab statistics (text and overlays masked out)."""
    l_mean: float
    l_std: float
    a_mean: float
    a_std: float
    b_mean: float
    b_std: float
    saturation: float
    contrast: float


class Requirement(BaseModel):
    media: Literal["video", "photo", "any"] = "any"
    orientation: Literal["portrait", "landscape", "any"] = "any"
    footage_frames: int = 0  # source frames the slot consumes, incl. lead and tail
    shot_size: ShotSize = "none"
    camera_from_clip: CameraMove = "static"  # movement the clip itself must contain (vs added by the template)
    subject_role: str = ""
    movement: str = ""
    hard: dict = Field(default_factory=dict)
    soft: dict = Field(default_factory=dict)


class Slot(BaseModel):
    id: str  # "s01"
    start: int  # nominal frames; boundaries between slots are the cut frames
    end: int
    media: F[Media] = Field(default_factory=lambda: F[Media](value="video"))
    role: F[Role] = Field(default_factory=lambda: F[Role](value="other"))
    function: F[str] = Field(default_factory=lambda: F[str](value=""))  # why this shot exists in the story
    subject: F[str] = Field(default_factory=lambda: F[str](value="", binding="swap"))
    action: F[str] = Field(default_factory=lambda: F[str](value="", binding="swap"))
    shot_size: F[ShotSize] = Field(default_factory=lambda: F[ShotSize](value="none"))
    angle: F[str] = Field(default_factory=lambda: F[str](value=""))
    layout: F[Layout] = Field(default_factory=lambda: F[Layout](value="single"))
    layout_boxes: list[Box] = Field(default_factory=list)
    camera: F[CameraMove] = Field(default_factory=lambda: F[CameraMove](value="static"))
    camera_path: list[Key] = Field(default_factory=list)  # zoom / pan as keyframes of the view region
    shake: dict | None = None  # {amp: residual std as share of width, hz}
    speed: list[tuple[float, float]] = Field(default_factory=lambda: [(0.0, 1.0)])  # (position 0..1, factor)
    reverse: bool = False
    freeze: list[tuple[int, int]] = Field(default_factory=list)  # frame ranges inside the slot that hold one frame
    colour: ColourTarget | None = None
    requirement: Requirement | None = None  # filled by requirements.py
    evidence: list[str] = Field(default_factory=list)  # measurement items consumed (speed, colour, geometry)

    @property
    def frames(self) -> int:
        return self.end - self.start


class Transition(BaseModel):
    after_slot: str  # sits between this slot and the next
    type: F[TransitionType] = Field(default_factory=lambda: F[TransitionType](value="cut"))
    start: int  # window in frames; start == end means a hard cut
    end: int
    params: dict = Field(default_factory=dict)  # direction, softness ...
    render: str = ""  # engine:name chosen by capabilities.py
    loss: str = ""  # what the render could not reproduce


class Effect(BaseModel):
    id: str
    type: F[EffectType]
    start: int
    end: int
    strength: float = 1.0
    params: dict = Field(default_factory=dict)
    render: str = ""
    loss: str = ""


class TextStyle(BaseModel):
    font_class: Literal["sans", "serif", "script", "display", "mono"] = "sans"
    font: str = "Arial"  # one of models.FONTS, nearest to font_class
    size: float = 0.04  # glyph height as a fraction of frame height
    fill: str = "#FFFFFF"
    outline: str | None = "#000000"
    outline_w: float = 0.0  # fraction of frame height
    shadow: bool = False
    box: str | None = None  # background box colour, None when there is none
    align: Literal["left", "center", "right"] = "center"
    bold: bool = True


class TextEvent(BaseModel):
    id: str
    start: int
    end: int
    text: F[str]  # binding "swap"; raw holds the reference's words
    role: F[TextRole] = Field(default_factory=lambda: F[TextRole](value="caption"))
    keys: list[Key]  # box path; first key is the resting position
    style: TextStyle = Field(default_factory=TextStyle)
    anim_in: F[TextAnim] = Field(default_factory=lambda: F[TextAnim](value="none"))
    anim_out: F[TextAnim] = Field(default_factory=lambda: F[TextAnim](value="none"))
    anim_in_frames: int = 0
    anim_out_frames: int = 0
    max_chars: int = 0  # from box width and display time


class Overlay(BaseModel):
    id: str
    kind: F[OverlayKind]
    start: int
    end: int
    keys: list[Key]
    description: F[str] = Field(default_factory=lambda: F[str](value=""))  # "red arrow sticker"
    binding: Binding = "swap"


class Layer(BaseModel):
    """A mask, cutout or moving layer the video AI reported. No measurement behind it: low confidence."""
    id: str
    kind: F[LayerKind]
    start: int
    end: int
    keys: list[Key]  # first and last box; two keys when it moves
    shape: str = ""  # circle, heart, person outline ...
    render: str = ""
    loss: str = ""


class Template(BaseModel):
    v: int
    key: str
    n_frames: int
    audio: str
    slots: list[Slot]
    transitions: list[Transition] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    texts: list[TextEvent] = Field(default_factory=list)
    overlays: list[Overlay] = Field(default_factory=list)
    layers: list[Layer] = Field(default_factory=list)
    narrative: dict = Field(default_factory=dict)  # hook, arc, payoff, cta as free text
    unsupported: list[str] = Field(default_factory=list)  # evidence ids nothing could represent
    low_conf: list[str] = Field(default_factory=list)  # field paths that need a user confirm
    dropped: dict[str, str] = Field(default_factory=dict)  # evidence id -> reason it was dropped

    def cuts(self) -> list[int]:
        return [s.start for s in self.slots[1:]]


class DeltaRow(BaseModel):
    track: str
    metric: str
    ref: Any = None
    render: Any = None
    gap: float = 0.0
    ok: bool = True


class Delta(BaseModel):
    rows: list[DeltaRow] = Field(default_factory=list)
    coverage: float = 1.0  # share of evidence items used, dropped with a reason, or listed unsupported
    passed: bool = False


# ---- storage: data/refs/<key>/ir/<layer>.json = {"v", "inputs", "data"} ----

def ref_dir(key: str) -> Path:
    d = config.REFS / key
    d.mkdir(parents=True, exist_ok=True)
    return d


def digest(obj: Any) -> str:
    """Stable hash of what a layer was built from."""
    s = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha1(s.encode()).hexdigest()[:16]


def save(key: str, layer: str, model: BaseModel, v: int = 1, inputs: str = "") -> Path:
    p = ref_dir(key) / "ir" / f"{layer}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({"v": v, "inputs": inputs, "data": model.model_dump(mode="json")}), encoding="utf-8")
    return p


def load(key: str, layer: str, cls: type[BaseModel], v: int | None = None, inputs: str | None = None):
    """The stored layer, or None when missing or built by another stage version / from other inputs."""
    p = config.REFS / key / "ir" / f"{layer}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if (v is not None and d.get("v") != v) or (inputs is not None and d.get("inputs") != inputs):
        return None
    return cls.model_validate(d["data"])
