"""MCP server for headless Adobe After Effects."""

import asyncio
from typing import Annotated, Any, Literal

from cavi_adobe_mcp.config import workspace
from cavi_adobe_mcp.contracts import Result
from cavi_mcp_core.server import READ_ONLY, WRITES, Server
from pydantic import BaseModel, ConfigDict, Field

from . import edit, host, models
from . import recipe as recipes
from .models import (
    BeatGrid,
    CameraSpec,
    Color,
    Ease,
    ExpressionPreset,
    Fill,
    Gradient,
    GroupTransform,
    Keyframe,
    LayerSpec,
    LightSpec,
    MarkerSpec,
    MaskKey,
    MaskShape,
    Operator,
    QueueAdd,
    QueueUpdate,
    ShapeSpec,
    Stroke,
    TrackMatte,
)

mcp = Server("cavi-after-effects", package="cavi-after-effects-mcp",
             instructions="Headless After Effects: ae_launch, then ae_script or the typed ae_* scene tools; ae_render_queue renders.")


class Status(Result):
    app: str
    version: str
    aerender: str
    headless_pids: list[int]
    ui_pids: list[int]


class Script(Result):
    project: str
    report: dict[str, Any]


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comp: str = Field(min_length=1)
    file: str = Field(min_length=1)
    frames: int = Field(ge=1)


class RenderedOutput(Output):
    rerendered: bool


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


@mcp.tool(annotations=READ_ONLY)
async def ae_status() -> Status:
    """Installed After Effects and its running headless and UI pids."""
    return await asyncio.to_thread(host.status)


@mcp.tool(annotations=WRITES)
async def ae_launch() -> Status:
    """Start headless After Effects (-noui) and wait until it answers scripts."""
    return await asyncio.to_thread(host.launch)


@mcp.tool(annotations=WRITES)
async def ae_script(script: str, project: str, args: dict[str, Any] | None = None,
                    timeout: Annotated[int, Field(ge=10, le=3600)] = 900) -> Script:
    """Run a .jsx with global CAVI_ARGS; it calls caviReport(obj) and the project saves to `project` (.aep).

    Paths are absolute. Returns the report; report.errors fails the call.
    """
    host.refuse_crashing_calls(host.absolute(script, ".jsx"))
    report = await asyncio.to_thread(host.run_script, script, project, args or {}, timeout)
    return {"project": project, "report": report}


@mcp.tool(annotations=WRITES)
async def ae_render_queue(project: str, outputs: Annotated[list[Output], Field(min_length=1)],
                          render_settings: str = "Best Settings",
                          output_module: str = "High Quality") -> Render:
    """aerender a saved .aep queue; each output movie must have `frames` frames or renders once more."""
    return await asyncio.to_thread(host.render_queue, project, [o.model_dump() for o in outputs],
                                   render_settings, output_module)


@mcp.tool(annotations=WRITES)
async def after_effects_render(recipe: str, directory: str) -> AERender:
    """aerender one declared AEP comp range to a new PNG directory (workspace-relative), max 300 s/8 GiB."""
    return await asyncio.to_thread(recipes.ae_render, workspace(), recipe, directory)


async def scene(name: str, project: str, args: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
    report = await asyncio.to_thread(host.run_template, name, project, args, timeout)
    return {"project": project, "report": report, **{k: v for k, v in report.items() if k != "errors"}}


@mcp.tool(annotations=READ_ONLY)
async def ae_inspect(project: str, scope: Literal["project", "comp", "queue"] = "project",
                     comp: str | None = None) -> models.Inspect:
    """List project items (comps, footage with missing flag, folders), one comp's layers, or the render queue."""
    if scope == "comp" and not comp:
        raise ValueError("scope comp needs a comp name")
    return await scene("ae_inspect", project, {"scope": scope, "comp": comp})


@mcp.tool(annotations=WRITES)
async def ae_comp_new(project: str, name: str, width: Annotated[int, Field(ge=4, le=30000)],
                      height: Annotated[int, Field(ge=4, le=30000)],
                      duration: Annotated[float, Field(gt=0, le=10800)],
                      fps: Annotated[float, Field(gt=0, le=240)] = 30, background: Color = [0, 0, 0],
                      renderer: str | None = None, replace: bool = False) -> models.CompNew:
    """Create a comp; replace removes an existing comp of that name. renderer: ADBE Advanced 3d, ADBE Calder, ADBE Ernst."""
    return await scene("ae_comp_new", project, {"name": name, "width": width, "height": height,
                                                "duration": duration, "fps": fps, "background": background,
                                                "renderer": renderer, "replace": replace})


@mcp.tool(annotations=WRITES)
async def ae_layer_add(project: str, layer: LayerSpec) -> models.LayerAdded:
    """Add a solid, text, footage, 3D model (.glb, .gltf, .obj; Advanced 3D comps only), nested comp (`source`), rectangle, null, camera, light (point, spot, parallel, ambient, environment) or adjustment layer with transform, 3D, timing, parent, blend mode and matte."""
    if layer.kind == "comp" and not layer.source:
        raise ValueError("A comp layer needs source, the name of the comp to nest")
    if layer.kind in ("footage", "model"):
        path = host.absolute(layer.file or "")
        if layer.kind == "model" and path.suffix.lower() not in (".glb", ".gltf", ".obj"):
            raise ValueError("A 3D model file is .glb, .gltf or .obj")
    return await scene("ae_layer_add", project, {**layer.model_dump(), "file": layer.file})


@mcp.tool(annotations=WRITES)
async def ae_keyframes(project: str, comp: str, layer: models.Layer, property: str,
                       keyframes: list[Keyframe] = [], ease: Ease | None = None, expression: str | None = None,
                       preset: ExpressionPreset | None = None, replace: bool = True, easy_ease: bool = False,
                       hold: bool = False, spatial: Literal["bezier", "linear"] | None = None, rove: bool = False,
                       remove: Literal["all"] | Annotated[list[float], Field(min_length=2, max_length=2)] | None = None
                       ) -> models.Keyframed:
    """Set keyframes on a layer property ("position", "Transform/Opacity" or match-name path), an expression or an expression preset (wiggle, loop_cycle, loop_pingpong, inertial_bounce, time_rotation). Without keyframes, easy_ease, ease, hold, spatial (position paths) and rove restyle the existing keys; remove drops all keys or those in [start, end]."""
    if expression is not None and preset is not None:
        raise ValueError("Give an expression or a preset, not both")
    if easy_ease and ease is None:
        ease = Ease(speed=0, influence=33.333)
    restyle = hold or spatial is not None or rove or (ease is not None and not keyframes)
    if not (keyframes or expression is not None or preset or remove or restyle):
        raise ValueError("Give keyframes or an expression (or a preset, remove, easy_ease, hold, spatial or rove)")
    if preset:
        expression = edit.expression_preset(preset.kind, preset.freq, preset.amp, preset.decay, preset.speed)
    args = {"comp": comp, "layer": layer, "property": property, "expression": expression, "remove": remove,
            "replace": replace and bool(keyframes or (expression is not None and preset is None)),
            "keyframes": [k.model_dump() for k in keyframes], "ease": ease.model_dump() if ease else None,
            "restyle": restyle, "hold": hold, "spatial": spatial, "rove": rove}
    return await scene("ae_keyframes", project, args)


@mcp.tool(annotations=WRITES)
async def ae_expressions(project: str, comp: str, layer: models.Layer | None = None,
                         remove_broken: bool = False) -> models.Expressions:
    """List every expression in a comp (or one layer) as {layer, property path, expression, enabled, error}; `broken` counts expressions After Effects reports an error for. remove_broken clears those expressions."""
    return await scene("ae_expressions", project, {"comp": comp, "layer": layer, "remove_broken": remove_broken})


@mcp.tool(annotations=WRITES)
async def ae_material(project: str, comp: str, layer: models.Layer, material: models.Material) -> models.Materialed:
    """Set a 3D layer's material options: casts shadows (off, on, only), accepts shadows and lights, light transmission, ambient, diffuse, specular, shininess, metal, reflection, glossiness, fresnel, transparency, rolloff, index of refraction. Refuses 2D layers; the report lists every option after the change."""
    values = {k: v for k, v in material.model_dump().items() if v is not None}
    if not values:
        raise ValueError("Give at least one material option")
    return await scene("ae_material", project, {"comp": comp, "layer": layer, "values": values})


@mcp.tool(annotations=WRITES)
async def ae_effect_add(project: str, comp: str, layer: models.Layer, match_name: str,
                        params: dict[str, Any] | None = None, name: str | None = None) -> models.EffectAdded:
    """Add an effect by matchName (e.g. ADBE Glo2) and set parameters by name or matchName."""
    return await scene("ae_effect_add", project, {"comp": comp, "layer": layer, "match_name": match_name,
                                                  "params": params or {}, "name": name})


@mcp.tool(annotations=WRITES)
async def ae_text_animator(project: str, comp: str, layer: models.Layer,
                           unit: Literal["characters", "words", "lines"] = "characters",
                           opacity: float | None = None, position: models.Vector | None = None,
                           tracking: float | None = None, scale: models.Vector | None = None,
                           blur: models.Vector | None = None, rotation: float | None = None,
                           start: Annotated[float, Field(ge=0)] = 0,
                           duration: Annotated[float, Field(gt=0)] = 1, ease: Ease | None = Ease(),
                           name: str | None = None, animators: list[models.TextAnimator] = [],
                           path: models.TextPath | None = None) -> models.TextAnimated:
    """Add a text animator whose range selector opens over characters, words or lines from `start` for `duration`; or `animators`, each with properties (fill and stroke color, stroke width, skew, character offset, per-character 3D rotation ...) and several selectors (range with shape, ease high and low, wiggly, expression); and/or text on a path from a layer mask (`path`, first and last margin)."""
    properties = {"opacity": opacity, "position": position, "tracking": tracking, "scale": scale,
                  "blur": blur, "rotation": rotation}
    listed = [a.model_dump() for a in animators]
    if not listed and any(v is not None for v in properties.values()):
        listed = [{"name": name, "properties": properties, "selectors": [
            models.TextSelector(unit=unit, animate=models.RangeAnimation(start=start, duration=duration,
                                                                         ease=ease)).model_dump()]}]
    if not listed and path is None:
        raise ValueError("Give at least one animator property")
    args = {"comp": comp, "layer": layer, "animators": listed, "path": path.model_dump() if path else None}
    return await scene("ae_text_animator", project, args)


@mcp.tool(annotations=WRITES)
async def ae_footage_replace(project: str, item: str, file: str) -> models.Footage:
    """Replace a footage item's source file in place; every layer using it updates."""
    return await scene("ae_footage_replace", project, {"item": item, "file": str(host.absolute(file))})


@mcp.tool(annotations=WRITES)
async def ae_render_queue_set(project: str, add: list[QueueAdd] = [], update: list[QueueUpdate] = [],
                              clear: bool = False) -> models.Queue:
    """Add comps to the render queue (template names as ae_presets lists them) with a time span (work_area, comp or {start, duration}), render settings (quality, resolution, proxy use, effects, motion blur, frame blending, frame rate) and the output settings scripts can set (resize, crop, audio); updates, applied in order, set render on/off, comp label and render settings, duplicate or remove an entry; the queue is listed afterwards. clear first removes only entries of the comps in add."""
    for u in update:
        if u.duplicate and u.remove:
            raise ValueError(f"Queue item {u.index}: duplicate and remove cannot be combined")
    for entry in add:
        host.absolute(entry.file)
        if entry.output:
            fixed = [k for k in ("format", "channels", "depth", "color") if getattr(entry.output, k) is not None]
            if fixed:
                raise ValueError(f"{', '.join(fixed)} cannot be set from scripts (read-only in setSettings, "
                                 "note 22); pick an output module template such as High Quality with Alpha")
    if clear and not add:
        raise ValueError("clear removes the queue entries of the comps in add; add none to clear")
    args = {"add": [a.model_dump() for a in add], "update": [u.model_dump() for u in update], "clear": clear}
    return await scene("ae_render_queue_set", project, args)


@mcp.tool(annotations=READ_ONLY)
async def ae_fonts(project: str, filter: str = "", limit: Annotated[int, Field(ge=1, le=2000)] = 200) -> models.Fonts:
    """List installed fonts as {postscript, family, style}; filter matches any of the three. Text tools take the PostScript name and refuse names that are not installed."""
    return await scene("ae_fonts", project, {"filter": filter, "limit": limit}, 120)


@mcp.tool(annotations=READ_ONLY)
async def ae_presets(project: str, filter: str = "", limit: Annotated[int, Field(ge=1, le=1000)] = 200
                     ) -> models.Presets:
    """List render settings templates, output module templates and installed .ffx animation presets (filter matches category and name)."""
    report = await asyncio.to_thread(host.run_template, "ae_presets", project, {}, 120)
    found = await asyncio.to_thread(host.animation_presets, None, filter)
    return {"project": project, "report": report, "render_settings": report["render_settings"],
            "output_modules": report["output_modules"], "animation_presets": found[:limit],
            "preset_count": len(found)}


@mcp.tool(annotations=WRITES)
async def ae_preset_apply(project: str, comp: str, layer: models.Layer, preset: str,
                          time: Annotated[float, Field(ge=0)] = 0) -> models.Script:
    """Refused: layer.applyPreset exits headless After Effects. Resolves `preset` first, so bad names fail clearly."""
    await asyncio.to_thread(host.resolve_preset, preset)
    raise ValueError("Refused: applying an animation preset (layer.applyPreset) exits headless After Effects "
                     "(measured with two presets); build the look with ae_effect_add, ae_keyframes and "
                     "ae_text_animator instead")


@mcp.tool(annotations=READ_ONLY)
async def ae_transitions(project: str) -> models.Transitions:
    """List the transition kinds this install has: effect-based wipes and dissolves, crossfade and dip."""
    report = await asyncio.to_thread(host.run_template, "ae_transitions", project,
                                     {"match_names": list(host.TRANSITIONS.values())}, 120)
    have = {e["match_name"]: e["available"] for e in report["effects"]}
    kinds = [{"kind": k, "match_name": m, "available": have.get(m, False)} for k, m in host.TRANSITIONS.items()]
    kinds += [{"kind": k, "match_name": None, "available": True} for k in host.BUILT_IN_TRANSITIONS]
    return {"project": project, "kinds": kinds}


@mcp.tool(annotations=WRITES)
async def ae_transition(project: str, comp: str, kind: str, layer: models.Layer | None = None,
                        edge: Literal["in", "out"] = "out", from_layer: models.Layer | None = None,
                        to_layer: models.Layer | None = None, seconds: Annotated[float, Field(gt=0)] | None = None,
                        frames: Annotated[int, Field(ge=1)] | None = None, color: Color = [0, 0, 0],
                        ease: Ease | None = Ease()) -> models.Script:
    """Transition on one layer's in/out point (`layer`, `edge`) or between `from_layer` and `to_layer` (starts at to_layer's in point). Kinds: see ae_transitions."""
    if kind not in host.TRANSITIONS and kind not in host.BUILT_IN_TRANSITIONS:
        raise ValueError(f"Unknown transition {kind}; see ae_transitions")
    if (seconds is None) == (frames is None):
        raise ValueError("Give seconds or frames, not both")
    if layer is None and (from_layer is None or to_layer is None):
        raise ValueError("Give layer, or from_layer and to_layer")
    if layer is not None and (from_layer is not None or to_layer is not None):
        raise ValueError("Give layer, or from_layer and to_layer, not both")
    args = {"comp": comp, "kind": kind, "layer": layer, "edge": edge, "from_layer": from_layer,
            "to_layer": to_layer, "seconds": seconds, "frames": frames, "color": color,
            "match_name": host.TRANSITIONS.get(kind), "ease": ease.model_dump() if ease else None}
    return await scene("ae_transition", project, args)


@mcp.tool(annotations=WRITES)
async def ae_sequence_layers(project: str, comp: str, items: Annotated[list[models.SequenceItem], Field(min_length=1)],
                             start: Annotated[float, Field(ge=0)] = 0, overlap: Annotated[float, Field(ge=0)] = 0,
                             transition: models.SequenceTransition | None = None) -> models.Sequenced:
    """Place existing layers and/or footage files end to end from `start`, each overlapping the previous by `overlap` seconds; earlier items sit above later ones. `transition` (a kind from ae_transitions) is applied at every join, default length the overlap. Refuses a sequence that runs past the comp."""
    for item in items:
        if (item.layer is None) == (item.file is None):
            raise ValueError("Each item needs a layer or a file, not both")
        if item.file:
            host.absolute(item.file)
    if transition is not None:
        if transition.kind not in host.TRANSITIONS and transition.kind not in host.BUILT_IN_TRANSITIONS:
            raise ValueError(f"Unknown transition {transition.kind}; see ae_transitions")
        if transition.seconds is None and overlap == 0:
            raise ValueError("A transition needs seconds when there is no overlap")
    result = await scene("ae_sequence_layers", project, {"comp": comp, "start": start, "overlap": overlap,
                                                         "items": [i.model_dump() for i in items]})
    if transition is not None:
        for join in result["joins"]:
            await ae_transition(project, comp, transition.kind, from_layer=join["from_layer"],
                                to_layer=join["to_layer"], seconds=transition.seconds or overlap,
                                color=transition.color, ease=transition.ease)
    return result


def given(**fields):
    if all(v is None for v in fields.values()):
        raise ValueError("Give at least one of: " + ", ".join(fields))


@mcp.tool(annotations=WRITES)
async def ae_project_settings(project: str, bits_per_channel: Literal[8, 16, 32] | None = None,
                              linear_blending: bool | None = None, working_space: str | None = None,
                              display_start_frame: Annotated[int, Field(ge=0)] | None = None,
                              time_display: Literal["frames", "timecode"] | None = None,
                              frames_count: Literal["start_0", "start_1", "timecode_conversion"] | None = None,
                              expression_engine: Literal["javascript-1.0", "extendscript"] | None = None,
                              gpu: Literal["metal", "software"] | None = None) -> models.ProjectSettings:
    """Set project-wide bit depth, working color space (a name from the install's color profile list), linear blending, display start frame, time display and frame count, expression engine and GPU acceleration; the report lists every setting after the change. Unset fields stay as they are."""
    given(bits_per_channel=bits_per_channel, linear_blending=linear_blending, working_space=working_space,
          display_start_frame=display_start_frame, time_display=time_display, frames_count=frames_count,
          expression_engine=expression_engine, gpu=gpu)
    args = {"bits_per_channel": bits_per_channel, "linear_blending": linear_blending,
            "working_space": working_space, "display_start_frame": display_start_frame,
            "time_display": time_display, "frames_count": frames_count,
            "expression_engine": expression_engine, "gpu": gpu}
    return await scene("ae_project_settings", project, args)


@mcp.tool(annotations=WRITES)
async def ae_project(action: Literal["open", "save", "save_as", "info", "reduce", "remove_unused", "consolidate"],
                     path: str | None = None, discard: bool = False, overwrite: bool = False,
                     comps: list[str] = []) -> models.ProjectState:
    """Open a saved .aep in the headless instance, save it, save it under a new path, or report the open project's path. Open refuses unsaved changes unless discard; save_as refuses an existing file unless overwrite. reduce keeps only `comps` and what they use, remove_unused drops unused footage, consolidate merges duplicate footage; each rewrites the open project, or saves to `path` instead when given. removed reports the count."""
    if action in ("open", "save_as") and not path:
        raise ValueError(f"{action} needs a path")
    if action == "reduce" and not comps:
        raise ValueError("reduce needs comps")
    target = host.absolute(path, ".aep") if path else host.CURRENT[0]
    if action == "open" and not target.is_file():
        raise ValueError(f"No project at {target}")
    if action in ("save", "info", "reduce", "remove_unused", "consolidate") and target is None:
        raise ValueError(f"{action} needs a path until a project has been used in this session")
    args = {"action": action, "path": str(target) if target else None, "discard": discard, "overwrite": overwrite,
            "comps": comps}
    report = await asyncio.to_thread(edit.project_op, args, target)
    return {"project": report["path"] or "", "report": report, **{k: v for k, v in report.items() if k != "errors"}}


@mcp.tool(annotations=WRITES)
async def ae_layer_set(project: str, comp: str, layer: models.Layer, name: str | None = None,
                       enabled: bool | None = None, solo: bool | None = None, shy: bool | None = None,
                       locked: bool | None = None, label: Annotated[int, Field(ge=0, le=16)] | None = None,
                       in_point: float | None = None, out_point: float | None = None,
                       start_time: float | None = None, stretch: Annotated[float, Field(ge=-9900, le=9900)] | None = None,
                       blend_mode: str | None = None, parent: models.Layer | None = None, no_parent: bool = False,
                       three_d: bool | None = None, motion_blur: bool | None = None,
                       track_matte: TrackMatte | Literal["none"] | None = None,
                       properties: dict[str, Any] | None = None) -> models.LayerChanged:
    """Change an existing layer: switches, label, timing, stretch percent, blend mode, parent, 3D, motion blur, track matte. `properties` sets static values by path ("position", "Transform/Opacity", "Geometry Options/Extrusion Depth", "Effects/Glow/Glow Threshold" or match names)."""
    given(name=name, enabled=enabled, solo=solo, shy=shy, locked=locked, label=label, in_point=in_point,
          out_point=out_point, start_time=start_time, stretch=stretch, blend_mode=blend_mode, parent=parent,
          three_d=three_d, motion_blur=motion_blur, track_matte=track_matte, properties=properties,
          no_parent=True if no_parent else None)
    if stretch == 0:
        raise ValueError("stretch cannot be 0")
    if no_parent and parent is not None:
        raise ValueError("Give parent or no_parent, not both")
    args = {"comp": comp, "layer": layer, "name": name, "enabled": enabled, "solo": solo, "shy": shy,
            "locked": locked, "label": label, "in_point": in_point, "out_point": out_point,
            "start_time": start_time, "stretch": stretch, "blend_mode": blend_mode, "parent": parent,
            "no_parent": no_parent, "three_d": three_d, "motion_blur": motion_blur,
            "track_matte": track_matte.model_dump() if isinstance(track_matte, TrackMatte) else track_matte,
            "properties": properties or {}}
    return await scene("ae_layer_set", project, args)


@mcp.tool(annotations=WRITES)
async def ae_text_set(project: str, comp: str, layer: models.Layer, text: str | None = None,
                      font: str | None = None, size: Annotated[float, Field(gt=0)] | None = None,
                      fill: Color | None = None, stroke: Color | None = None,
                      stroke_width: Annotated[float, Field(ge=0)] | None = None, tracking: float | None = None,
                      leading: float | None = None,
                      justification: Literal["left", "center", "right", "full"] | None = None,
                      box: Annotated[list[float], Field(min_length=2, max_length=2)] | None = None
                      ) -> models.TextChanged:
    """Replace the source text and/or style of an existing text layer; its animators and keyframes stay."""
    style = {"text": text, "font": font, "size": size, "fill": fill, "stroke": stroke, "stroke_width": stroke_width,
             "tracking": tracking, "leading": leading, "justification": justification, "box": box}
    given(**style)
    return await scene("ae_text_set", project, {"comp": comp, "layer": layer, **style})


@mcp.tool(annotations=WRITES)
async def ae_layer_edit(project: str, comp: str, layers: Annotated[list[models.Layer], Field(min_length=1)],
                        action: Literal["duplicate", "delete", "reorder", "split", "precompose"],
                        time: Annotated[float, Field(ge=0)] | None = None,
                        move_to: Literal["top", "bottom"] | Annotated[int, Field(ge=1)] | None = None,
                        name: str | None = None) -> models.LayersEdited:
    """Duplicate (name renames a single copy), delete, reorder (move_to top, bottom or a 1-based index), split at `time`, or precompose the layers into a comp called `name` with all attributes moved."""
    if action == "split" and time is None:
        raise ValueError("split needs a time")
    if action == "reorder" and move_to is None:
        raise ValueError("reorder needs move_to")
    if action == "precompose" and not name:
        raise ValueError("precompose needs a name")
    args = {"comp": comp, "layers": layers, "action": action, "time": time, "move_to": move_to, "name": name}
    return await scene("ae_layer_edit", project, args)


@mcp.tool(annotations=WRITES)
async def ae_comp_set(project: str, comp: str, name: str | None = None,
                      width: Annotated[int, Field(ge=4, le=30000)] | None = None,
                      height: Annotated[int, Field(ge=4, le=30000)] | None = None,
                      duration: Annotated[float, Field(gt=0, le=10800)] | None = None,
                      fps: Annotated[float, Field(gt=0, le=240)] | None = None,
                      work_area: Annotated[list[float], Field(min_length=2, max_length=2)] | None = None,
                      background: Color | None = None, renderer: str | None = None,
                      motion_blur: bool | None = None, frame_blending: bool | None = None,
                      duplicate_as: str | None = None) -> models.CompChanged:
    """Change a comp's name, size, fps, duration, work area [start, duration], background, renderer and motion blur and frame blending switches. duplicate_as copies the comp first and changes the copy."""
    given(name=name, width=width, height=height, duration=duration, fps=fps, work_area=work_area,
          background=background, renderer=renderer, motion_blur=motion_blur, frame_blending=frame_blending,
          duplicate_as=duplicate_as)
    args = {"comp": comp, "name": name, "width": width, "height": height, "duration": duration, "fps": fps,
            "work_area": work_area, "background": background, "renderer": renderer, "motion_blur": motion_blur,
            "frame_blending": frame_blending, "duplicate_as": duplicate_as}
    return await scene("ae_comp_set", project, args)


@mcp.tool(annotations=WRITES)
async def ae_import(project: str, files: Annotated[list[str], Field(min_length=1)], folder: str | None = None,
                    sequence: bool = False,
                    import_as: Literal["footage", "comp", "comp_cropped"] = "footage",
                    alpha: Literal["ignore", "straight", "premultiplied"] | None = None,
                    conform_fps: Annotated[float, Field(gt=0, le=240)] | None = None,
                    loop: Annotated[int, Field(ge=1)] | None = None) -> models.Imported:
    """Import files (an image sequence from its first frame with `sequence`, a layered PSD or AI as a comp with `import_as`) into the named project folder, then set alpha mode, conform frame rate and loop count."""
    paths = [str(host.absolute(f)) for f in files]
    args = {"files": paths, "folder": folder, "sequence": sequence, "as": import_as, "alpha": alpha,
            "conform_fps": conform_fps, "loop": loop}
    return await scene("ae_import", project, args)


@mcp.tool(annotations=WRITES)
async def ae_markers(project: str, comp: str, layer: models.Layer | None = None,
                     markers: list[MarkerSpec] = [], grid: BeatGrid | None = None, clear: bool = False
                     ) -> models.MarkerList:
    """Set comp markers (or `layer` markers) with comment, duration and chapter, and/or a beat grid from bpm and beats per bar. clear removes the existing ones first."""
    if not markers and grid is None:
        raise ValueError("Give markers or a beat grid")
    if grid is not None and grid.end <= grid.start:
        raise ValueError("The beat grid end must be after start")
    listed = [m.model_dump() for m in markers]
    if grid is not None:
        listed += edit.beat_grid(grid.bpm, grid.beats_per_bar, grid.start, grid.end)
    return await scene("ae_markers", project, {"comp": comp, "layer": layer, "markers": listed, "clear": clear})


@mcp.tool(annotations=WRITES)
async def ae_frame(project: str, comp: str, times: Annotated[list[float], Field(min_length=1, max_length=50)],
                   directory: str, alpha: bool = False) -> models.FramesRendered:
    """Render the frame at each time (seconds) of a comp to PNG in `directory` through aerender and a temporary render queue entry; returns the file paths. The comp background color is in the frame; alpha keeps transparency instead."""
    host.absolute(directory)
    frames = await asyncio.to_thread(edit.render_frames, project, comp, times, directory, alpha)
    return {"project": project, "comp": comp, "frames": frames}


@mcp.tool(annotations=WRITES)
async def ae_shape_add(project: str, comp: str, shape: ShapeSpec, name: str = "Shape", layer: models.Layer | None = None,
                       group_name: str = "Group", fill: Fill | None = None, stroke: Stroke | None = None,
                       gradient_fill: Gradient | None = None, gradient_stroke: Gradient | None = None,
                       operators: list[Operator] = [], transform: GroupTransform | None = None) -> models.ShapeAdded:
    """Add a shape layer, or a group on the existing shape `layer`: a rect, ellipse, polystar or bezier path, then operators (trim, round_corners, offset, wiggle, merge), paint and finally repeaters, with a group transform; a new layer sits at the comp origin, so positions are comp pixels. Gradient color stops cannot be set from scripts (note 19): a gradient takes After Effects' default stops."""
    spec = shape.model_dump()
    if shape.kind == "path":
        spec = {**spec, **shape.path.model_dump()}
    grad = {"gradient_fill": gradient_fill, "gradient_stroke": gradient_stroke}
    args = {"comp": comp, "layer": layer, "name": name, "group_name": group_name, "shape": spec,
            "fill": fill.model_dump() if fill else None, "stroke": stroke.model_dump() if stroke else None,
            **{k: v.model_dump() if v else None for k, v in grad.items()},
            "operators": [o.model_dump() for o in operators],
            "transform": (transform or GroupTransform()).model_dump()}
    return await scene("ae_shape_add", project, args)


@mcp.tool(annotations=WRITES)
async def ae_mask(project: str, comp: str, layer: models.Layer, shape: MaskShape | None = None,
                  mask: models.Layer | None = None, name: str | None = None,
                  mode: Literal["none", "add", "subtract", "intersect", "lighten", "darken", "difference"] | None = None,
                  feather: models.Point | None = None, expansion: float | None = None,
                  opacity: Annotated[float, Field(ge=0, le=100)] | None = None, invert: bool | None = None,
                  path_keys: list[MaskKey] = []) -> models.MaskSet:
    """Add a mask to a layer, or change the existing `mask` (index or name): rect, ellipse or points path, mode, feather, expansion, opacity, invert, and a keyframed path as [{time, shape}]."""
    if mask is None and shape is None and not path_keys:
        raise ValueError("A new mask needs a shape or path_keys")
    given(shape=shape, name=name, mode=mode, feather=feather, expansion=expansion, opacity=opacity, invert=invert,
          path_keys=path_keys or None)
    args = {"comp": comp, "layer": layer, "mask": mask, "name": name, "mode": mode, "feather": feather,
            "expansion": expansion, "opacity": opacity, "invert": invert,
            "shape": edit.mask_shape(shape) if shape else None,
            "path_keys": [{"time": k.time, "shape": edit.mask_shape(k.shape)} for k in path_keys]}
    return await scene("ae_mask", project, args)


@mcp.tool(annotations=READ_ONLY)
async def ae_effects(project: str, filter: str = "", category: str | None = None,
                     limit: Annotated[int, Field(ge=1, le=1000)] = 200) -> models.EffectList:
    """List installed effects (app.effects) with category, display name and matchName; `filter` matches all three. The categories field counts the matches per category."""
    return await scene("ae_effects", project, {"filter": filter, "category": category, "limit": limit}, 120)


@mcp.tool(annotations=WRITES)
async def ae_camera(project: str, comp: str, camera: CameraSpec | None = None, rig: bool = False,
                    light: LightSpec | None = None) -> models.CameraSet:
    """Add or change a one- or two-node camera (position, point of interest, zoom or focal length, depth of field, focus distance, aperture, blur level), optionally parented to an orbit null at its point of interest (`rig`), and/or a light (type, intensity, color, cone angle and feather, shadows)."""
    if camera is None and light is None:
        raise ValueError("Give a camera or a light")
    if rig and camera is None:
        raise ValueError("rig needs a camera")
    return await scene("ae_camera", project, {"comp": comp, "rig": rig, "camera": camera.model_dump() if camera else None,
                                              "light": light.model_dump() if light else None})


@mcp.tool(annotations=WRITES)
async def ae_essential_graphics(project: str, comp: str, add: list[models.EssentialProperty] = [],
                                template_name: str | None = None) -> models.EssentialGraphics:
    """Add layer properties (source text, color, slider or effect parameters, position ...) to a comp's Essential Graphics under a name, optionally name the template, and list the controls the comp has."""
    return await scene("ae_essential_graphics", project, {"comp": comp, "add": [a.model_dump() for a in add],
                                                          "template_name": template_name})


@mcp.tool(annotations=WRITES)
async def ae_essential_override(project: str, comp: str, layer: models.Layer,
                                values: Annotated[dict[str, Any], Field(min_length=1)]) -> models.EssentialOverridden:
    """Override Essential Properties on one nested-comp layer by their ae_essential_graphics names: a string sets source text, a number, array or color list sets that value. Each instance of the same comp keeps its own values."""
    return await scene("ae_essential_override", project, {"comp": comp, "layer": layer, "values": values})


@mcp.tool(annotations=WRITES)
async def ae_mogrt_export(project: str, comp: str, file: str) -> models.Script:
    """Refused: headless After Effects does not write the .mogrt. Use ae_essential_graphics to prepare the comp."""
    host.absolute(file, ".mogrt")
    raise ValueError("Refused: comp.exportAsMotionGraphicsTemplate returns true in headless After Effects but writes "
                     "no file; it only creates an empty folder at the path (measured). Export the .mogrt from "
                     "an After Effects window instead")


@mcp.tool(annotations=WRITES)
async def ae_template_render(template: str, project: str, renders: Annotated[list[models.RenderTarget], Field(min_length=1)],
                             texts: list[models.TextEdit] = [], footage: dict[str, str] = {},
                             discard: bool = False) -> models.TemplateRendered:
    """Open a template .aep, set text layers by name, replace footage items by name, save the result to `project`, and aerender the named comps to their files with frame checks."""
    template, target = host.absolute(template, ".aep"), host.absolute(project, ".aep")
    files = {name: str(host.absolute(path)) for name, path in footage.items()}
    for render in renders:
        host.absolute(render.file)
    outputs = await asyncio.to_thread(edit.template_render, template, target, [t.model_dump() for t in texts],
                                      files, [r.model_dump() for r in renders], discard)
    return {"project": str(target), "texts": len(texts), "footage": len(files), "outputs": outputs}


@mcp.tool(annotations=WRITES)
async def ae_collect(project: str, folder: str) -> models.Collected:
    """Copy every used footage file into `folder`, relink each item there with item.replace, save to `project`, and report counts and items still missing. Solids and image sequences are skipped by name."""
    return await asyncio.to_thread(edit.collect, host.absolute(project, ".aep"), host.absolute(folder))


@mcp.tool(annotations=WRITES)
async def ae_audio(project: str, comp: str, layer: models.Layer, enabled: bool | None = None,
                   level: float | Annotated[list[float], Field(min_length=2, max_length=2)] | None = None,
                   level_keys: list[Keyframe] = [], fade_in: Annotated[float, Field(gt=0)] | None = None,
                   fade_out: Annotated[float, Field(gt=0)] | None = None, convert_to_keyframes: bool = False
                   ) -> models.AudioSet:
    """Set an audio layer's Audio Levels in dB (static `level`, or keyed `level_keys` with [left, right] or one value), fade in and out by seconds (from -100 dB), and audio on or off."""
    if convert_to_keyframes:
        raise ValueError("Refused: Convert Audio to Keyframes (app.executeCommand of the menu command 4218) exits "
                         "headless After Effects (measured twice); use ae_keyframes with an expression or keys")
    given(enabled=enabled, level=level, level_keys=level_keys or None, fade_in=fade_in, fade_out=fade_out)
    if level is not None and level_keys:
        raise ValueError("Give level or level_keys, not both")
    one = lambda v: [v, v] if isinstance(v, int | float) else v  # noqa: E731
    keys = [{**k.model_dump(), "value": one(k.value)} for k in level_keys]
    args = {"comp": comp, "layer": layer, "enabled": enabled, "level": one(level), "level_keys": keys,
            "fade_in": fade_in, "fade_out": fade_out}
    return await scene("ae_audio", project, args)


@mcp.tool(annotations=WRITES)
async def ae_time(project: str, comp: str, layer: models.Layer, time_remap: bool | None = None,
                  remap_keys: list[models.RemapKey] = [], freeze_at: Annotated[float, Field(ge=0)] | None = None,
                  reverse: bool | None = None, frame_blending: Literal["none", "mix", "pixel_motion"] | None = None
                  ) -> models.TimeSet:
    """Time remap on or off with keys [{time, source_time}], a freeze frame at a source time, reverse (stretch -100, keeping the in point), and the layer's frame blending (none, mix, pixel_motion; the comp switch is turned on)."""
    given(time_remap=time_remap, remap_keys=remap_keys or None, freeze_at=freeze_at, reverse=reverse,
          frame_blending=frame_blending)
    if freeze_at is not None and remap_keys:
        raise ValueError("Give freeze_at or remap_keys, not both")
    args = {"comp": comp, "layer": layer, "time_remap": time_remap, "remap_keys": [k.model_dump() for k in remap_keys],
            "freeze_at": freeze_at, "reverse": reverse, "frame_blending": frame_blending}
    return await scene("ae_time", project, args)


@mcp.tool(annotations=WRITES)
async def ae_controls(project: str, comp: str, layer: models.Layer, controls: list[models.ControlSpec] = [],
                      links: list[models.ControlLink] = []) -> models.ControlsSet:
    """Add named Expression Controls (slider, angle, point, point3d, color, checkbox, layer, dropdown) to `layer` and set their values, and link target properties on any layer to a control with a generated expression (scale, offset, one axis of a vector)."""
    if not controls and not links:
        raise ValueError("Give controls or links")
    args = {"comp": comp, "layer": layer, "controls": [c.model_dump() for c in controls],
            "links": [{**link.model_dump()} for link in links]}
    return await scene("ae_controls", project, args)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
