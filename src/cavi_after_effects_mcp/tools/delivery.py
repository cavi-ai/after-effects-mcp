"""Delivery: render queue, renders, frames, templates, Essential Graphics."""

import asyncio
from pathlib import Path
from typing import Annotated, Any, Literal

from cavi_adobe_mcp import native_media
from cavi_adobe_mcp.config import workspace
from cavi_mcp_core.server import DESTRUCTIVE, WRITES
from pydantic import Field

from .. import edit, host, models
from ..app import mcp, scene
from ..models import Output, QueueAdd, QueueUpdate


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_render_queue(project: str, outputs: Annotated[list[Output], Field(min_length=1)],
                          render_settings: str = "Best Settings",
                          output_module: str = "High Quality") -> models.Render:
    """aerender a saved .aep queue; each output movie must have `frames` frames or renders once more. When aerender still leaves no movie or a short one, the movie is made from saveFrameToPng frames and ffmpeg (.mp4 H.264 or .mov ProRes from frame 0 at the comp's frame rate); each output's `path` says which path produced it."""
    return await asyncio.to_thread(edit.render_outputs, project, [o.model_dump() for o in outputs],
                                   render_settings, output_module)


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


@mcp.tool(annotations=WRITES)
async def after_effects_render(recipe: str, directory: str) -> models.AERender:
    """aerender one declared AEP comp range to a new PNG directory (workspace-relative), max 300 s/8 GiB."""
    return await asyncio.to_thread(native_media.ae_render, workspace(), recipe, directory)


@mcp.tool(annotations=WRITES)
async def ae_frame(project: str, comp: str, times: Annotated[list[float], Field(min_length=1, max_length=50)],
                   directory: str, alpha: bool = False,
                   method: Literal["auto", "aerender"] = "auto") -> models.FramesRendered:
    """Render the frame at each time (seconds) of a comp to PNG in `directory`; returns the file paths. The comp background color is in the frame; alpha keeps transparency instead. `auto` writes the frames with saveFrameToPng and falls back to aerender through a temporary render queue entry; `aerender` uses only aerender."""
    host.absolute(directory)
    frames = await asyncio.to_thread(edit.render_frames, project, comp, times, directory, alpha, method == "auto")
    return {"project": project, "comp": comp, "frames": frames}


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_export_frames(project: str, comp: str, directory: str, start: Annotated[float, Field(ge=0)] = 0,
                           duration: Annotated[float, Field(gt=0)] | None = None,
                           step: Annotated[int, Field(ge=1, le=240)] = 1, alpha: bool = False,
                           movie: str | None = None, codec: Literal["h264", "prores"] = "h264",
                           max_frames: Annotated[int, Field(ge=1, le=5000)] = 1800) -> models.FramesExported:
    """Write a frame range of a comp as frame_00001.png ... in `directory` without aerender (every `step`-th frame from `start` for `duration` seconds, default to the end), optionally encoded with ffmpeg to `movie` (.mp4 H.264, or ProRes .mov, with alpha when alpha is set). Use it when aerender renders nothing."""
    host.absolute(directory)
    if movie:
        suffix = Path(movie).suffix.lower()
        if codec == "h264" and suffix != ".mp4":
            raise ValueError("An H.264 movie is a .mp4 file")
        if codec == "prores" and suffix != ".mov":
            raise ValueError("A ProRes movie is a .mov file")
        if alpha and codec == "h264":
            raise ValueError("H.264 has no alpha; use codec prores or leave movie empty")
    result = await asyncio.to_thread(edit.export_frames, project, comp, directory, start, duration, step, alpha,
                                     movie, codec, max_frames)
    return {"project": project, "comp": comp, "directory": directory, **result}


@mcp.tool(annotations=DESTRUCTIVE)
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
