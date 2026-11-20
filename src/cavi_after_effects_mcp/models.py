"""Typed inputs and results of the After Effects scene tools."""

from typing import Annotated, Any, Literal

from cavi_mcp_core.contracts import Result
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


Color = Annotated[list[float], Field(min_length=3, max_length=3, description="RGB, 0 to 1")]
Layer = Annotated[int | str, Field(description="Layer index (1-based) or name")]
BoxFit = Literal["none", "cursor", "bounds", "baseline"]
BOX_FIT = ("Grow a paragraph box down to fit its text, measured to the cursor height, the glyph bounds or the last "
           "baseline (After Effects 24.6+).")
BoxAlign = Literal["top", "center", "bottom", "justify"]
BOX_ALIGN = "Vertical alignment of the text in its paragraph box (After Effects 24.6+)."


def box_fit_check(fit, align):
    """Refuse a box fit that After Effects would switch off: it grows a box only when the text sits at its top."""
    if fit not in (None, "none") and align not in (None, "top"):
        raise ValueError(f"box_fit grows a box only with box_align top, not {align}")
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


class MeshOptions(Model):
    """Mesh Options of a parametric mesh layer; each mesh type takes its own subset."""
    width: float | None = Field(None, gt=0, description="cube, plane")
    height: float | None = Field(None, gt=0, description="cube, cone, cylinder")
    depth: float | None = Field(None, gt=0, description="cube")
    length: float | None = Field(None, gt=0, description="plane")
    radius: float | None = Field(None, gt=0, description="sphere, cylinder")
    top_radius: float | None = Field(None, ge=0, description="cone")
    bottom_radius: float | None = Field(None, ge=0, description="cone")
    ring_radius: float | None = Field(None, gt=0, description="torus")
    pipe_radius: float | None = Field(None, gt=0, description="torus")
    corner_radius: float | None = Field(None, ge=0, description="plane")
    sides: int | None = Field(None, ge=3, description="sphere, cone, cylinder")
    ring_sides: int | None = Field(None, ge=3, description="torus")
    pipe_sides: int | None = Field(None, ge=3, description="torus")
    corner_sides: int | None = Field(None, ge=1, description="plane")
    top_cap: bool | None = Field(None, description="cone, cylinder")
    bottom_cap: bool | None = Field(None, description="cone, cylinder")
    caps: bool | None = Field(None, description="torus")
    slice_caps: bool | None = Field(None, description="sphere, cone, cylinder")
    slice_start: float | None = Field(None, description="Degrees; sphere, cone, cylinder, torus")
    slice_end: float | None = Field(None, description="Degrees; sphere, cone, cylinder, torus")
    invert_slice: bool | None = Field(None, description="sphere, cone, cylinder, torus")
    smoothing_angle: float | None = Field(None, ge=0, description="Degrees; all but plane")


class BevelOptions(Model):
    """Bevel Options of a cube, cylinder (radius, sides) or cone (top and bottom) mesh layer."""
    radius: float | None = Field(None, ge=0)
    sides: int | None = Field(None, ge=1)
    top_radius: float | None = Field(None, ge=0)
    top_sides: int | None = Field(None, ge=1)
    bottom_radius: float | None = Field(None, ge=0)
    bottom_sides: int | None = Field(None, ge=1)


MESH = "Parametric mesh layers: Mesh Options (After Effects 26.3+)."
BEVEL = "Parametric cube, cylinder and cone layers: Bevel Options (After Effects 26.3+)."


class LayerSpec(Model):
    comp: str = Field(min_length=1)
    kind: Literal["solid", "text", "footage", "shape_rect", "null", "camera", "light", "adjustment", "model", "comp",
                  "mesh"]
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
    file: str | None = Field(None, description="Absolute footage or 3D model (.glb, .gltf, .obj) path, imported on first use")
    source: str | None = Field(None, description="Comp name for kind comp, a nested instance of that comp")
    fit: bool = Field(True, description="Model layers: scale so its largest extent times the square root of 3 (a rotation-safe bound) is 60% of the comp height, centered; false keeps the raw import")
    light_type: Literal["point", "spot", "parallel", "ambient", "environment"] = "point"
    mesh_type: Literal["cube", "sphere", "plane", "cylinder", "cone", "torus"] = Field(
        "cube", description="Parametric 3D mesh for kind mesh (After Effects 26.3+); size it with mesh")
    mesh: MeshOptions | None = Field(None, description=MESH)
    bevel: BevelOptions | None = Field(None, description=BEVEL)
    transform: Transform = Transform()
    three_d: bool = False
    in_point: float | None = None
    out_point: float | None = None
    start_time: float | None = None
    parent: Layer | None = None
    blend_mode: str | None = Field(None, description="BlendingMode name such as ADD, SCREEN, MULTIPLY")
    motion_blur: bool = False
    track_matte: TrackMatte | None = None

    @model_validator(mode="after")
    def visible(self):
        if self.kind == "shape_rect" and self.fill is None and self.stroke is None:
            raise ValueError("A shape_rect needs fill or stroke; color applies only to solids")
        if self.kind != "mesh" and (self.mesh is not None or self.bevel is not None):
            raise ValueError("mesh and bevel apply only to kind mesh")
        return self


class SequenceItem(Model):
    layer: Layer | None = Field(None, description="Existing layer to move")
    file: str | None = Field(None, description="Absolute footage path to add as a layer")
    duration: float | None = Field(None, gt=0, description="Seconds on the timeline, at most the source left from "
                                                           "the layer's in point; default the layer's own length")


class SequenceTransition(Model):
    kind: str = Field("crossfade", description="A kind from ae_transitions")
    seconds: float | None = Field(None, gt=0, description="Default the overlap")
    color: Color = [0, 0, 0]
    ease: Ease | None = Ease()


class TimeSpan(Model):
    start: float = Field(ge=0)
    duration: float = Field(gt=0)


class OutputSettings(Model):
    """The output module settings scripts can set; Format, Channels, Depth and Color are read-only."""
    resize: Annotated[list[int], Field(min_length=2, max_length=2)] | None = Field(None, description="[width, height]")
    resize_quality: Literal["low", "high"] | None = None
    crop: Annotated[list[int], Field(min_length=4, max_length=4)] | None = Field(None, description="[top, left, bottom, right]")
    audio: Literal["on", "off", "auto"] | None = None
    audio_sample_rate: Literal[22050, 44100, 48000, 96000] | None = None
    audio_channels: Literal["mono", "stereo"] | None = None
    audio_bit_depth: Literal[8, 16, 32] | None = None
    format: str | None = Field(None, description="Read-only: refused")
    channels: str | None = Field(None, description="Read-only: refused")
    depth: str | None = Field(None, description="Read-only: refused")
    color: str | None = Field(None, description="Read-only: refused")


class RenderSettings(Model):
    """Render settings an entry accepts; frame_rate switches the entry to that fixed rate."""
    quality: Literal["wireframe", "draft", "best"] | None = None
    resolution: Literal["full", "half", "third", "quarter"] | None = None
    proxy_use: Literal["none", "comp", "all"] | None = None
    effects: Literal["on", "off", "current"] | None = None
    motion_blur: Literal["checked", "off_all", "current"] | None = None
    frame_blending: Literal["checked", "off_all", "current"] | None = None
    frame_rate: float | None = Field(None, gt=0)


class QueueAdd(Model):
    comp: str = Field(min_length=1)
    file: str = Field(min_length=1, description="Absolute output movie path")
    output_module: str = "High Quality"
    render_settings: str = "Best Settings"
    locked: bool = Field(False, description="Render off and comp label 0: an approved shot")
    time_span: Literal["work_area", "comp"] | TimeSpan | None = None
    output: OutputSettings | None = None
    settings: RenderSettings | None = None


class QueueUpdate(Model):
    index: int = Field(ge=1, description="Position in the queue as it stands when this update runs")
    settings: RenderSettings | None = None
    duplicate: bool = False
    remove: bool = False
    render: bool | None = None
    label: int | None = Field(None, ge=0, le=16)
    locked: bool = False


class Status(Result):
    app: str | None
    version: str
    aerender: str | None
    headless_pids: list[int]
    ui_pids: list[int]
    error: str | None


class Script(Result):
    project: str
    report: dict[str, Any]


class Output(Model):
    comp: str = Field(min_length=1)
    file: str = Field(min_length=1, description="The output file of its queue entry; an image sequence keeps [#####]")
    frames: int | None = Field(None, ge=1, description="Frames the output must have; defaults to the queue entry's "
                                                       "time span at its frame rate, and a different count is refused")


class RenderJob(Result):
    job: str
    state: Literal["running", "done", "failed", "cancelled", "unresolved"]
    comp: str
    file: str
    frames: int = Field(description="Frames the queue entry renders")
    done: int = Field(description="Frames aerender has logged")
    written: int | None = Field(None, description="Frames the output has, once the render ended")
    error: str | None = None


class RenderedOutput(Model):
    comp: str
    file: str
    frames: int
    rerendered: bool
    path: Literal["aerender", "saveFrameToPng"]


class Render(Result):
    project: str
    outputs: list[RenderedOutput]


class AERender(Result):
    status: Literal["inputs_unchanged"]
    receipt: str
    sha256: str
    frame_count: int
    fps: dict[str, int]
    execution: dict
    composition: str
    timing_authority: Literal["caller_declared"]
    dependencies_authority: Literal["caller_declared"]
    launches_applications: Literal[True]


class ProjectSettings(Script):
    settings: dict[str, Any]


class Sequenced(Script):
    layers: list[dict[str, Any]]
    joins: list[dict[str, Any]]


ItemRef = Annotated[int | Annotated[str, Field(min_length=1)],
                    Field(description="Project item name (comp, footage or folder), or its id from ae_inspect")]


class ItemMove(Model):
    item: ItemRef
    folder: str = Field(min_length=1, description="Folder path such as Footage/Audio, created when missing")


class ItemRename(Model):
    item: ItemRef
    name: str = Field(min_length=1)


class Organized(Script):
    folders: list[str]
    renamed: list[str]
    moved: list[str]


class Properties(Script):
    comp: str
    layer: str
    count: int
    truncated: bool
    properties: list[dict[str, Any]]


class Fonts(Script):
    fonts: list[dict[str, Any]]
    count: int


class FontReplaced(Script):
    font: str
    to: str
    replaced: bool
    layers: list[dict[str, Any]]


class Expressions(Script):
    comp: str
    expressions: list[dict[str, Any]]
    broken: int
    removed: int


class Material(Model):
    casts_shadows: Literal["off", "on", "only"] | None = None
    accepts_shadows: bool | None = None
    accepts_lights: bool | None = None
    appears_in_reflections: bool | None = None
    light_transmission: float | None = Field(None, ge=0, le=100)
    shadow_color: Color | None = None
    ambient: float | None = Field(None, ge=0, le=100)
    diffuse: float | None = Field(None, ge=0, le=100)
    specular: float | None = Field(None, ge=0, le=100, description="Specular intensity")
    shininess: float | None = Field(None, ge=0, le=100, description="Specular shininess")
    metal: float | None = Field(None, ge=0, le=100)
    reflection: float | None = Field(None, ge=0, le=100, description="Reflection intensity")
    glossiness: float | None = Field(None, ge=0, le=100, description="Reflection sharpness")
    fresnel: float | None = Field(None, ge=0, le=100, description="Reflection rolloff")
    transparency: float | None = Field(None, ge=0, le=100)
    transparency_rolloff: float | None = Field(None, ge=0, le=100)
    index_of_refraction: float | None = Field(None, ge=0)


class Materialed(Script):
    comp: str
    layer: str
    renderer: str
    material: dict[str, Any]


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


class Presets(Script):
    render_settings: list[str]
    output_modules: list[str]
    animation_presets: list[dict[str, str]]


class Transitions(Result):
    kinds: list[dict[str, Any]]


class ProjectState(Script):
    action: Literal["new", "open", "save", "save_as", "info", "reduce", "remove_unused", "consolidate"]
    removed: int | None
    path: str | None
    previous: str | None
    items: int
    comps: int
    footage: int


class LayerChanged(Script):
    comp: str
    layer: dict[str, Any]
    mesh: dict[str, Any] | None = Field(None, description="Mesh type and the mesh and bevel values set")
    properties_set: list[str]
    values: dict[str, Any]


class TextRange(Model):
    start: int = Field(ge=0, description="First character, 0-based")
    end: int = Field(gt=0, description="Character after the last one")
    font: str | None = Field(None, description="PostScript font name, as ae_fonts lists it")
    size: float | None = Field(None, gt=0, description="Font size in pixels")
    fill: Color | None = None
    stroke: Color | None = None
    stroke_width: float | None = Field(None, ge=0)
    tracking: float | None = Field(None, description="Thousandths of an em")
    bold: bool | None = Field(None, description="Faux bold")
    italic: bool | None = Field(None, description="Faux italic")
    baseline_shift: float | None = Field(None, description="Pixels")

    @model_validator(mode="after")
    def styled(self):
        if self.end <= self.start:
            raise ValueError(f"Range {self.start}-{self.end} ends at or before its start")
        if all(getattr(self, k) is None for k in ("font", "size", "fill", "stroke", "stroke_width", "tracking",
                                                  "bold", "italic", "baseline_shift")):
            raise ValueError(f"Range {self.start}-{self.end} sets no style")
        return self


class TextChanged(Script):
    comp: str
    layer: str
    text: str
    animators: int
    overflow: bool | None = None


class LayersEdited(Script):
    comp: str
    action: Literal["duplicate", "delete", "reorder", "split", "precompose", "copy"]
    layers: list[Any]
    layer_count: int
    to_comp: str | None = None


class PartEdit(Model):
    path: str = Field(min_length=1, description="An effect, mask, shape group or text animator by property path, "
                                                "such as Effects/Glow, Masks/Mask 1, Contents/Group 1 or "
                                                "Text/Animators/Animator 1")
    action: Literal["remove", "enable", "disable", "move"]
    to: int | None = Field(None, ge=1, description="move: the new 1-based position among its siblings")

    @model_validator(mode="after")
    def target(self):
        if (self.action == "move") != (self.to is not None):
            raise ValueError("to is given with move and only with move")
        return self


class BatchStep(Model):
    tool: str = Field(min_length=1, description="A typed write tool, such as ae_layer_add or ae_keyframes")
    args: dict[str, Any] = Field(default_factory=dict, description="The tool's arguments without project")


class Batched(Script):
    steps: list[dict[str, Any]]


class PartsEdited(Script):
    comp: str
    layer: str
    groups: dict[str, list[dict[str, Any]]]


class CompChanged(Script):
    comp: str
    source: str
    duplicated: bool
    width: int
    height: int
    duration: float
    fps: float


class Imported(Script):
    items: list[dict[str, Any]]


class MarkerList(Script):
    comp: str
    count: int
    markers: list[dict[str, Any]]


class FramesRendered(Result):
    project: str
    comp: str
    frames: list[dict[str, Any]]


class FramesExported(Result):
    project: str
    comp: str
    directory: str
    frames: int
    fps: float
    first: str
    last: str
    movie: str | None


class BeatGrid(Model):
    bpm: float = Field(gt=0, le=1000)
    beats_per_bar: int = Field(4, ge=1, le=64)
    start: float = Field(0, ge=0)
    end: float = Field(gt=0, description="Seconds; the last beat falls before it")


class Onsets(Model):
    file: str = Field(min_length=1, description="Absolute path of an audio or video file")
    offset: float = Field(0, description="Comp seconds where the file starts; onsets before comp time 0 are dropped")
    rise: float = Field(6, gt=0, le=60, description="dB a frame's level must rise over the previous 70 ms")
    floor: float = Field(-50, ge=-120, le=0, description="dB a frame's level must reach")
    gap: float = Field(0.1, ge=0.01, le=10, description="Seconds between onsets at least")
    comment: str = "onset"


class Cuts(Model):
    file: str = Field(min_length=1, description="Absolute path of a video file")
    offset: float = Field(0, description="Comp seconds where the file starts; cuts before comp time 0 are dropped")
    threshold: float = Field(0.4, gt=0, le=1, description="FFmpeg scene score, the change from the frame before "
                                                          "from 0 to 1, a cut must reach")
    comment: str = "cut"


class MarkerSpec(Model):
    time: float = Field(ge=0)
    comment: str = ""
    duration: float = Field(0, ge=0)
    chapter: str | None = None


Point = Annotated[list[float], Field(min_length=2, max_length=2)]


class PathShape(Model):
    vertices: Annotated[list[Point], Field(min_length=2)]
    in_tangents: list[Point] | None = Field(None, description="Per vertex, relative to it; default none")
    out_tangents: list[Point] | None = None
    closed: bool = True

    @model_validator(mode="after")
    def tangents_match(self):
        zero = [[0.0, 0.0] for _ in self.vertices]
        self.in_tangents = self.in_tangents or zero
        self.out_tangents = self.out_tangents or zero
        if len(self.in_tangents) != len(self.vertices) or len(self.out_tangents) != len(self.vertices):
            raise ValueError("Give one in and one out tangent per vertex")
        return self


class ShapeSpec(Model):
    kind: Literal["rect", "ellipse", "polystar", "path"]
    size: Point = [100, 100]
    position: Point = [0, 0]
    roundness: float = Field(0, ge=0)
    star: bool = Field(True, description="polystar: star, or a polygon when false")
    points: int = Field(5, ge=3, le=100)
    outer_radius: float = Field(100, gt=0)
    inner_radius: float = Field(50, gt=0)
    outer_roundness: float = 0
    inner_roundness: float = 0
    rotation: float = 0
    path: PathShape | None = None

    @model_validator(mode="after")
    def path_given(self):
        if self.kind == "path" and self.path is None:
            raise ValueError("A path shape needs path")
        return self


class Fill(Model):
    color: Color
    opacity: float = Field(100, ge=0, le=100)


class Stroke(Model):
    color: Color
    width: float = Field(2, ge=0)
    opacity: float = Field(100, ge=0, le=100)
    cap: Literal["butt", "round", "square"] = "butt"
    join: Literal["miter", "round", "bevel"] = "miter"
    dashes: list[float] = Field([], max_length=6, description="Dash, gap, dash, gap ...")


class Gradient(Model):
    type: Literal["linear", "radial"] = "linear"
    start: Point = [0, 0]
    end: Point = [100, 0]
    opacity: float | None = Field(None, ge=0, le=100)
    width: float | None = Field(None, ge=0, description="Stroke width, gradient stroke only")


class Operator(Model):
    type: Literal["trim", "repeater", "round_corners", "offset", "wiggle", "merge"]
    start: float | None = None
    end: float | None = None
    offset: float | None = None
    individually: bool = False
    copies: float | None = None
    anchor: Point | None = None
    position: Point | None = None
    scale: Point | None = None
    rotation: float | None = None
    start_opacity: float | None = None
    end_opacity: float | None = None
    radius: float | None = None
    amount: float | None = None
    join: Literal["miter", "round", "bevel"] | None = None
    miter_limit: float | None = None
    size: float | None = None
    detail: float | None = None
    smooth: bool = False
    speed: float | None = None
    correlation: float | None = None
    seed: float | None = None
    mode: Literal["merge", "add", "subtract", "intersect", "exclude"] = "merge"

    @model_validator(mode="after")
    def required(self):
        need = {"round_corners": self.radius, "offset": self.amount, "wiggle": self.size, "repeater": self.copies}
        if self.type in need and need[self.type] is None:
            raise ValueError(f"{self.type} needs {dict(round_corners='radius', offset='amount', wiggle='size', repeater='copies')[self.type]}")
        if self.type == "trim" and self.start is None and self.end is None and self.offset is None:
            raise ValueError("trim needs start, end or offset")
        return self


class GroupTransform(Model):
    anchor: Point | None = None
    position: Point | None = None
    scale: Point | None = None
    rotation: float | None = None
    opacity: float | None = Field(None, ge=0, le=100)


class MaskShape(Model):
    kind: Literal["rect", "ellipse", "points"]
    box: Annotated[list[float], Field(min_length=4, max_length=4)] | None = Field(
        None, description="rect or ellipse bounds [x, y, width, height]")
    path: PathShape | None = None

    @model_validator(mode="after")
    def given(self):
        if self.kind == "points" and self.path is None:
            raise ValueError("A points mask needs path")
        if self.kind != "points" and self.box is None:
            raise ValueError(f"A {self.kind} mask needs box")
        return self


class MaskKey(Model):
    time: float = Field(ge=0)
    shape: MaskShape


class ExpressionPreset(Model):
    kind: Literal["wiggle", "loop_cycle", "loop_pingpong", "inertial_bounce", "time_rotation"]
    freq: float = Field(3, gt=0, description="wiggle and bounce frequency, Hz")
    amp: float = Field(10, description="wiggle amplitude; bounce amplitude percent")
    decay: float = Field(5, ge=0, description="bounce decay")
    speed: float = Field(90, description="time_rotation degrees per second")


class CameraSpec(Model):
    layer: Layer | None = Field(None, description="Change this camera instead of adding one")
    name: str = "Camera"
    nodes: Literal[1, 2] | None = Field(None, description="One-node, or two-node with a point of interest")
    position: Vector | None = None
    point_of_interest: Vector | None = None
    zoom: float | None = Field(None, gt=0, description="Pixels")
    focal_length: float | None = Field(None, gt=0, description="mm on a 36 mm film; sets zoom")
    depth_of_field: bool | None = None
    focus_distance: float | None = Field(None, ge=0)
    aperture: float | None = Field(None, ge=0)
    blur_level: float | None = Field(None, ge=0, le=1000)


class LightSpec(Model):
    layer: Layer | None = Field(None, description="Change this light instead of adding one")
    name: str = "Light"
    type: Literal["point", "spot", "parallel", "ambient", "environment"] | None = None
    intensity: float | None = Field(None, ge=0)
    color: Color | None = None
    cone_angle: float | None = Field(None, ge=0, le=180)
    cone_feather: float | None = Field(None, ge=0, le=100)
    casts_shadows: bool | None = None
    shadow_darkness: float | None = Field(None, ge=0, le=100)
    shadow_diffusion: float | None = Field(None, ge=0)
    position: Vector | None = None
    point_of_interest: Vector | None = None
    source: Layer | None = Field(None, description="Environment light: a 2D footage, still or comp layer of the comp "
                                                   "whose image lights the scene")

    @model_validator(mode="after")
    def environment_source(self):
        if self.source is not None and self.type not in (None, "environment"):
            raise ValueError("source lights only an environment light; set type environment")
        return self


class ShapeAdded(Script):
    comp: str
    layer: dict[str, Any]
    group: str
    contents: list[str]


class MaskSet(Script):
    comp: str
    layer: str
    mask: str
    mask_count: int
    path_keys: int


class EffectList(Script):
    effects: list[dict[str, str]]
    total: int
    categories: dict[str, int]


class CameraSet(Script):
    comp: str


class EssentialGraphics(Script):
    comp: str
    name: str
    added: list[str]
    controls: list[str]


class TemplateRendered(Result):
    project: str
    texts: int
    overflow: list[dict[str, Any]]
    footage: int
    outputs: list[dict[str, Any]]


class Collected(Result):
    project: str
    folder: str
    items: int
    copied: int
    relinked: int
    skipped: list[str]
    missing: int


class EssentialProperty(Model):
    layer: Layer
    property: str | None = Field(None, description="Property path as in ae_keyframes, e.g. Text/Source Text or "
                                                   "Transform/Position; omitted, the footage or comp layer itself "
                                                   "becomes a media replacement control")
    name: str = Field(min_length=1)


class EssentialOverridden(Script):
    layer: str
    source: str
    available: list[str]
    overridden: list[str]


class TextEdit(Model):
    comp: str = Field(min_length=1)
    layer: Layer
    text: str | None = None
    font: str | None = None
    size: float | None = Field(None, gt=0)
    fill: Color | None = None
    stroke: Color | None = None
    stroke_width: float | None = Field(None, ge=0)
    tracking: float | None = None
    leading: float | None = None
    justification: Literal["left", "center", "right", "full"] | None = None
    box: Annotated[list[float], Field(min_length=2, max_length=2)] | None = None
    box_fit: BoxFit | None = Field(None, description=BOX_FIT)
    box_align: BoxAlign | None = Field(None, description=BOX_ALIGN)
    box_inset: float | None = Field(None, ge=0, description="Pixels between the box and its text on every side")
    ranges: list[TextRange] = Field([], max_length=1000, description="Character ranges styled after the whole text")

    @model_validator(mode="after")
    def fit_at_top(self):
        box_fit_check(self.box_fit, self.box_align)
        return self


class RenderTarget(Model):
    comp: str = Field(min_length=1)
    file: str = Field(min_length=1, description="Absolute output movie path")
    output_module: str = "High Quality"
    render_settings: str = "Best Settings"


class TemplateVariant(Model):
    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$",
                      description="Replaces {name} in project and every renders file")
    texts: list[TextEdit] = Field([], description="Text layers set after the shared texts")
    footage: dict[str, str] = Field({}, description="Footage items replaced after the shared footage: name to "
                                                    "absolute path")


class RemapKey(Model):
    time: float = Field(ge=0, description="Comp time")
    source_time: float = Field(ge=0, description="Time in the layer's source")


class AudioSet(Script):
    comp: str
    layer: str
    audio_enabled: bool
    keys: list[dict[str, Any]]


class TimeSet(Script):
    comp: str
    layer: str
    time_remap: bool
    keys: list[dict[str, Any]]
    stretch: float
    in_point: float
    out_point: float
    visible_start: float
    visible_end: float


class RangeAnimation(Model):
    start: float = Field(0, ge=0)
    duration: float = Field(1, gt=0)
    ease: Ease | None = Ease()


class TextSelector(Model):
    kind: Literal["range", "wiggly", "expression"] = "range"
    unit: Literal["characters", "characters_no_spaces", "words", "lines"] = "characters"
    start: float | None = Field(None, description="range: percent")
    end: float | None = Field(None, description="range: percent")
    offset: float | None = Field(None, description="range: percent")
    shape: Literal["square", "ramp_up", "ramp_down", "triangle", "round", "smooth"] | None = None
    ease_high: float | None = Field(None, ge=-100, le=100)
    ease_low: float | None = Field(None, ge=-100, le=100)
    smoothness: float | None = Field(None, ge=0, le=100)
    animate: RangeAnimation | None = Field(None, description="range: Start keys 0 to 100 over seconds")
    max_amount: float | None = Field(None, description="wiggly")
    min_amount: float | None = None
    per_second: float | None = Field(None, gt=0, description="wiggly: wiggles per second")
    correlation: float | None = Field(None, ge=0, le=100)
    seed: float | None = None
    amount: str | None = Field(None, description="expression: the Amount expression, 0 to 100")


class AnimatorProperties(Model):
    opacity: float | None = Field(None, ge=0, le=100)
    position: Vector | None = None
    scale: Vector | None = None
    tracking: float | None = None
    blur: Vector | None = None
    rotation: float | None = None
    rotation_x: float | None = Field(None, description="Per-character 3D")
    rotation_y: float | None = Field(None, description="Per-character 3D")
    fill_color: Color | None = None
    stroke_color: Color | None = None
    stroke_width: float | None = Field(None, ge=0)
    skew: float | None = None
    skew_axis: float | None = None
    character_offset: float | None = None


class TextAnimator(Model):
    name: str | None = None
    properties: AnimatorProperties
    selectors: list[TextSelector] = [TextSelector()]


class TextPath(Model):
    mask: Layer = Field(description="Mask index or name on the text layer")
    first_margin: float | None = None
    last_margin: float | None = None
    reverse: bool = False
    perpendicular: bool = True
    force_align: bool = False


class TextAnimated(Script):
    comp: str
    layer: str
    animators: list[dict[str, Any]]
    animator_count: int


class ControlSpec(Model):
    kind: Literal["slider", "angle", "point", "point3d", "color", "checkbox", "layer", "dropdown"]
    name: str = Field(min_length=1)
    value: Any = Field(None, description="Number, [x, y], [x, y, z], [r, g, b], bool, a layer ref, or a dropdown item's text or 1-based index")
    items: list[str] = Field([], description="dropdown menu items")


class ControlLink(Model):
    control: str = Field(description="Name of a control on the control layer")
    property: str = Field(description="Target property path, as in ae_keyframes")
    layer: Layer | None = Field(None, description="Target layer; default the control layer")
    scale: float = 1
    offset: float = 0
    axis: Literal["x", "y", "z"] | None = Field(None, description="Drive one component of a vector property")


class ControlsSet(Script):
    comp: str
    layer: str
    controls: list[str]
    links: list[dict[str, Any]]
