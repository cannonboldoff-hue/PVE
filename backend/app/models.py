from typing import Literal

from pydantic import BaseModel, Field

# the xfade transitions mcp-video's merge accepts, plus a hard cut
Transition = Literal[
    "cut", "fade", "dissolve", "wipeleft", "wiperight", "slideleft", "slideright", "slideup", "slidedown",
    "circlecrop", "radial", "smoothleft", "smoothright", "smoothup", "smoothdown",
]


class Brief(BaseModel):
    topic: str = Field(description="What the new Reel is about (subject, product, business)")
    keep: list[str] = Field(default_factory=list, description="Reference traits to keep: pacing, style, structure, transitions")
    change: list[str] = Field(default_factory=list, description="What differs from the reference: subject, text, product")
    target_length: float = Field(gt=0, description="Target length in seconds")
    tone: str = "energetic"
    caption_language: str = "English"
    captions: bool = True
    media: Literal["photo", "video", "mixed"] = Field(default="mixed", description="what the user will supply: photo if they say photos or images")
    music: Literal["none", "uploaded", "reference"] = Field(default="none", description="reference = the reference Reel's own song")


Fit = Literal["cover", "blur_fit"]  # cover: crop to fill 9:16; blur_fit: whole frame over a blurred copy of itself
Animation = Literal["none", "zoom_in", "zoom_out"]
CaptionAnimation = Literal["none", "fade", "pop", "slide_up"]


FONTS = ("Arial", "Impact", "Georgia", "Comic Sans MS", "Segoe Script", "Times New Roman", "Courier New", "Verdana", "Trebuchet MS")
HEX = r"^#[0-9A-Fa-f]{6}$"


class CaptionStyle(BaseModel):
    font: Literal[FONTS] = "Arial"  # type: ignore[valid-type]
    size: int = Field(default=72, ge=36, le=140)
    color: str = Field(default="#FFFFFF", pattern=HEX)
    outline_color: str = Field(default="#000000", pattern=HEX)
    outline: int = Field(default=5, ge=0, le=12)
    position: Literal["top", "center", "bottom"] = "bottom"
    bold: bool = True
    uppercase: bool = False
    emphasis_words: list[str] = Field(default_factory=list, description="words drawn in emphasis_color")
    emphasis_color: str = Field(default="#FFD400", pattern=HEX)


class Grade(BaseModel):
    preset: Literal["none", "warm", "cool", "vintage", "cinematic", "noir"] = "none"
    brightness: float = Field(default=0.0, ge=-0.4, le=0.4)
    contrast: float = Field(default=1.0, ge=0.6, le=1.6)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)

    @property
    def is_neutral(self) -> bool:
        return self.preset == "none" and self.brightness == 0 and self.contrast == 1 and self.saturation == 1


class Collage(BaseModel):
    tiles: int = Field(default=4, ge=2, le=6)
    background: str = Field(default="#F7C6D9", pattern=HEX)
    border: bool = True  # white polaroid-style frame around each tile
    tilt: float = Field(default=4.0, ge=0, le=10, description="degrees; tiles alternate +/-")


class ShotSpec(BaseModel):
    shot_id: int
    start: float
    end: float
    purpose: str
    subject: str
    action: str
    direction: str = ""
    camera: str = ""
    camera_motion: str = ""
    asset_type: str = "video"
    text: str = ""
    transition_out: Transition = "cut"
    background: str = ""  # what is behind or around the subject (informational)
    fit: Fit = "cover"
    animation: Animation = "none"
    caption_animation: CaptionAnimation = "fade"
    overlay: str = ""  # stickers / graphics in the reference (informational, not rendered yet)
    caption_style: CaptionStyle = Field(default_factory=CaptionStyle)
    caption_start: float | None = Field(default=None, description="seconds after the shot starts; default 0.2")
    caption_end: float | None = Field(default=None, description="seconds after the shot starts; default shot end - 0.2")
    grade: Grade = Field(default_factory=Grade)
    layout: Literal["single", "collage"] = "single"
    collage: Collage = Field(default_factory=Collage)
    skipped: bool = False

    @property
    def duration(self) -> float:
        return max(0.5, self.end - self.start)


class ShotSpecList(BaseModel):
    shots: list[ShotSpec]


class ShotContent(BaseModel):
    """What the brief rewrites per template slot; every other ShotSpec field is structure and comes from the template."""
    purpose: str
    subject: str
    action: str
    direction: str = ""
    asset_type: str = "video"
    text: str = ""


class ShotContentList(BaseModel):
    shots: list[ShotContent]


class Match(BaseModel):
    shot_id: int
    asset_id: str | None = None
    start: float = 0
    end: float = 0
    label: Literal["exact", "similar", "missing"] = "missing"
    extra_assets: list[str] = Field(default_factory=list)  # more tiles for a collage shot
    reason: str = ""
    instruction: str = ""  # filming instruction when missing


class PlanShot(BaseModel):
    shot_id: int
    asset_id: str
    path: str
    src_in: float
    src_out: float
    speed: float = 1.0
    caption: str = ""
    cap_start: float = 0.0
    cap_end: float = 0.0
    transition: Transition = "cut"
    fit: Fit = "cover"
    animation: Animation = "none"
    caption_animation: CaptionAnimation = "fade"
    caption_style: CaptionStyle = Field(default_factory=CaptionStyle)
    grade: Grade = Field(default_factory=Grade)
    collage: Collage | None = None  # set when this shot is a collage
    tiles: list[str] = Field(default_factory=list)  # extra tile files for the collage (the main clip is tile 1)
    # frame-exact path (docs/mvp-plan.md 4); all optional so legacy plans are unaffected
    frames: int | None = None  # exact output length incl. transition overlaps
    lead: int = 0  # overlap frames shared with the previous transition
    tail: int = 0  # overlap frames shared with the next transition
    speed_curve: list[tuple[float, float]] | None = None
    reverse: bool = False
    freeze: list[tuple[int, int]] = Field(default_factory=list)
    camera_path: list[dict] = Field(default_factory=list)  # ir.Key dicts
    layout_boxes: list[dict] = Field(default_factory=list)
    colour: dict | None = None

    @property
    def duration(self) -> float:
        if self.frames is not None:
            return self.frames / 30  # config.FPS; models stay free of app imports
        return (self.src_out - self.src_in) / self.speed


class Plan(BaseModel):
    shots: list[PlanShot]
    music_path: str | None = None
    music_volume: float = 0.35
    music_mode: Literal["duck", "replace"] = "duck"  # replace: the song is the whole soundtrack
    captions: bool = True
    n_frames: int | None = None
    transitions: list[dict] = Field(default_factory=list)  # ir.Transition dicts
    effects: list[dict] = Field(default_factory=list)
    texts: list[dict] = Field(default_factory=list)
    overlays: list[dict] = Field(default_factory=list)
    audio_mode: Literal["legacy", "reference"] = "legacy"


PatchField = Literal["in", "out", "speed", "caption", "cap_start", "cap_end", "transition", "fit", "animation",
                     "caption_animation", "caption_color", "caption_size", "caption_position", "clip", "drop"]


class PatchOp(BaseModel):
    shot_id: int
    field: PatchField
    value: str | float | None = None


class PatchList(BaseModel):
    ops: list[PatchOp]


class Issue(BaseModel):
    shot_id: int | None = None
    problem: str
    fixes: list[PatchOp] = Field(default_factory=list)


class JudgeResult(BaseModel):
    verdict: Literal["PASS", "REPAIR"]
    summary: str
    issues: list[Issue] = Field(default_factory=list)


class MissingInstruction(BaseModel):
    shot_id: int
    instruction: str


class MissingList(BaseModel):
    items: list[MissingInstruction]
