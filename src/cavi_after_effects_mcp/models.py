"""Typed inputs and results of the After Effects scene tools."""

from typing import Annotated, Any, Literal

from cavi_adobe_mcp.contracts import Result
from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


Color = Annotated[list[float], Field(min_length=3, max_length=3, description="RGB, 0 to 1")]
Layer = Annotated[int | str, Field(description="Layer index (1-based) or name")]
Vector = Annotated[list[float], Field(min_length=2, max_length=3)]


class Transform(Model):
    position: Vector | None = None
    anchor: Vector | None = None
    scale: Vector | None = Field(None, description="Percent")
    rotation: float | None = Field(None, description="Z rotation, degrees")
    rotationx: float | None = None
    rotationy: float | None = None
    opacity: float | None = Field(None, ge=0, le=100)


class Ease(Model):
    speed: float = 0
    influence: float = Field(75, ge=0.1, le=100)


class Keyframe(Model):
    time: float = Field(ge=0)
    value: Any
    ease_in: Ease | None = None
    ease_out: Ease | None = None
    interpolation: Literal["linear", "bezier", "hold"] | None = None


class TrackMatte(Model):
    layer: Layer
    type: Literal["alpha", "alpha_inverted", "luma", "luma_inverted"] = "alpha"


class LayerSpec(Model):
    comp: str = Field(min_length=1)
    kind: Literal["solid", "text", "footage", "shape_rect", "null", "camera", "light", "adjustment"]
    name: str = Field(min_length=1)
    color: Color = [0, 0, 0]
    width: float | None = Field(None, gt=0, description="Solid or rectangle width; default comp width")
    height: float | None = Field(None, gt=0, description="Solid or rectangle height; default comp height")
    text: str = ""
    font: str = "ArialMT"
    size: float = Field(60, gt=0)
    tracking: float = 0
    fill: Color | None = None
    stroke: Color | None = None
    stroke_width: float = Field(1, ge=0)
    justification: Literal["left", "center", "right", "full"] = "left"
    box: Annotated[list[float], Field(min_length=2, max_length=2)] | None = Field(
        None, description="Paragraph text box [width, height]")
    file: str | None = Field(None, description="Absolute footage path, imported on first use")
    light_type: Literal["point", "spot", "parallel", "ambient"] = "point"
    transform: Transform = Transform()
    three_d: bool = False
    in_point: float | None = None
    out_point: float | None = None
    start_time: float | None = None
    parent: Layer | None = None
    blend_mode: str | None = Field(None, description="BlendingMode name such as ADD, SCREEN, MULTIPLY")
    motion_blur: bool = False
    track_matte: TrackMatte | None = None


class QueueAdd(Model):
    comp: str = Field(min_length=1)
    file: str = Field(min_length=1, description="Absolute output movie path")
    output_module: str = "High Quality"
    render_settings: str = "Best Settings"
    locked: bool = Field(False, description="Render off and comp label 0: an approved shot")


class QueueUpdate(Model):
    index: int = Field(ge=1)
    render: bool | None = None
    label: int | None = Field(None, ge=0, le=16)
    locked: bool = False


class Script(Result):
    project: str
    report: dict[str, Any]


class Inspect(Script):
    scope: Literal["project", "comp", "queue"]


class CompNew(Script):
    comp: str
    renderer: str
    replaced: bool


class LayerAdded(Script):
    layer: dict[str, Any]


class Keyframed(Script):
    keys: int


class EffectAdded(Script):
    effect: dict[str, Any]


class Footage(Script):
    item: str
    layers_using: int


class Queue(Script):
    queue: list[dict[str, Any]]
