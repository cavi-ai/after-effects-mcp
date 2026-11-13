"""MCP server for headless Adobe After Effects."""

import asyncio
from typing import Annotated, Any, Literal

from cavi_adobe_mcp.config import workspace
from cavi_adobe_mcp.contracts import Result
from cavi_mcp_core.server import READ_ONLY, WRITES, Server
from pydantic import BaseModel, ConfigDict, Field

from . import host, models
from . import recipe as recipes
from .models import Color, Ease, Keyframe, LayerSpec, QueueAdd, QueueUpdate

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
    """Add a solid, text, footage, rectangle, null, camera, light or adjustment layer with transform, 3D, timing, parent, blend mode and matte."""
    if layer.kind == "footage":
        host.absolute(layer.file or "")
    return await scene("ae_layer_add", project, {**layer.model_dump(), "file": layer.file})


@mcp.tool(annotations=WRITES)
async def ae_keyframes(project: str, comp: str, layer: models.Layer, property: str,
                       keyframes: list[Keyframe] = [], ease: Ease | None = None, expression: str | None = None,
                       replace: bool = True) -> models.Keyframed:
    """Set keyframes on a layer property ("position", "Transform/Opacity" or match-name path) and/or an expression."""
    if not keyframes and expression is None:
        raise ValueError("Give keyframes or an expression")
    args = {"comp": comp, "layer": layer, "property": property, "replace": replace, "expression": expression,
            "keyframes": [k.model_dump() for k in keyframes], "ease": ease.model_dump() if ease else None}
    return await scene("ae_keyframes", project, args)


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
                           name: str | None = None) -> models.Script:
    """Add a text animator whose range selector opens over characters, words or lines from `start` for `duration`."""
    properties = {"opacity": opacity, "position": position, "tracking": tracking, "scale": scale,
                  "blur": blur, "rotation": rotation}
    if all(v is None for v in properties.values()):
        raise ValueError("Give at least one animator property")
    args = {"comp": comp, "layer": layer, "unit": unit, "properties": properties, "start": start,
            "duration": duration, "name": name, "ease": ease.model_dump() if ease else None}
    return await scene("ae_text_animator", project, args)


@mcp.tool(annotations=WRITES)
async def ae_footage_replace(project: str, item: str, file: str) -> models.Footage:
    """Replace a footage item's source file in place; every layer using it updates."""
    return await scene("ae_footage_replace", project, {"item": item, "file": str(host.absolute(file))})


@mcp.tool(annotations=WRITES)
async def ae_render_queue_set(project: str, add: list[QueueAdd] = [], update: list[QueueUpdate] = [],
                              clear: bool = False) -> models.Queue:
    """Add comps to the render queue (template names as ae_presets lists them), set render on/off and comp label, and list it. clear first removes only entries of the comps in add."""
    for entry in add:
        host.absolute(entry.file)
    if clear and not add:
        raise ValueError("clear removes the queue entries of the comps in add; add none to clear")
    args = {"add": [a.model_dump() for a in add], "update": [u.model_dump() for u in update], "clear": clear}
    return await scene("ae_render_queue_set", project, args)


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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
