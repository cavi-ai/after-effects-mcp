"""Delivery: render queue, renders, frames, templates, Essential Graphics."""

import asyncio
from pathlib import Path
from typing import Annotated, Any, Literal

from cavi_adobe_mcp import native_media
from cavi_adobe_mcp.config import workspace
from cavi_mcp_core.server import DESTRUCTIVE, WRITES
from pydantic import Field

from .. import edit, host, models
from ..app import Comp, Project, mcp, scene
from ..models import Output, QueueAdd, QueueUpdate


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_render_queue(
        project: Annotated[str, Field(description="Absolute path of the saved .aep to render.")],
        outputs: Annotated[list[Output], Field(min_length=1, description="Comps to render, each with its movie "
                                                                         "and frame count.")],
        render_settings: Annotated[str, Field(description="Render settings template.")] = "Best Settings",
        output_module: Annotated[str, Field(description="Output module template.")] = "High Quality"
) -> models.Render:
    """aerender a saved .aep queue; a movie short of its frames renders once more. When aerender still leaves no
    movie or a short one, it is made from saveFrameToPng frames and ffmpeg (.mp4 H.264 or .mov ProRes); each
    output's path says which way produced it."""
    return await asyncio.to_thread(edit.render_outputs, project, [o.model_dump() for o in outputs],
                                   render_settings, output_module)


@mcp.tool(annotations=WRITES)
async def ae_render_queue_set(
        project: Project,
        add: Annotated[list[QueueAdd], Field(description="Comps to queue with time span, templates, render "
                                                         "settings and output settings.")] = [],
        update: Annotated[list[QueueUpdate], Field(description="Changes to existing entries, applied in "
                                                               "order.")] = [],
        clear: Annotated[bool, Field(description="First remove the existing entries of the comps in "
                                                 "add.")] = False) -> models.Queue:
    """Add comps to the render queue and update entries (render on or off, settings, duplicate, remove); the
    queue is listed afterwards. Template names are those ae_presets lists."""
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
async def after_effects_render(
        recipe: Annotated[str, Field(description="Workspace-relative path of the render recipe .json.")],
        directory: Annotated[str, Field(description="New workspace-relative directory for the PNGs.")]
) -> models.AERender:
    """aerender one declared AEP comp range to a new PNG directory (workspace-relative), max 300 s/8 GiB."""
    return await asyncio.to_thread(native_media.ae_render, workspace(), recipe, directory)


@mcp.tool(annotations=WRITES)
async def ae_frame(
        project: Project, comp: Comp,
        times: Annotated[list[float], Field(min_length=1, max_length=50, description="Comp times of the frames, "
                                                                                     "in seconds.")],
        directory: Annotated[str, Field(description="Absolute path of the folder for the PNGs.")],
        alpha: Annotated[bool, Field(description="Keep transparency instead of the comp background.")] = False,
        method: Annotated[Literal["auto", "aerender"],
                          Field(description="auto uses saveFrameToPng and falls back to aerender; aerender uses "
                                            "only aerender.")] = "auto") -> models.FramesRendered:
    """Render one PNG per time of a comp and return the file paths."""
    host.absolute(directory)
    frames = await asyncio.to_thread(edit.render_frames, project, comp, times, directory, alpha, method == "auto")
    return {"project": project, "comp": comp, "frames": frames}


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_export_frames(
        project: Project, comp: Comp,
        directory: Annotated[str, Field(description="Absolute path of the folder for the PNGs.")],
        start: Annotated[float, Field(ge=0, description="First frame time, comp seconds.")] = 0,
        duration: Annotated[Annotated[float, Field(gt=0)] | None,
                            Field(description="Seconds to export; to the comp's end when omitted.")] = None,
        step: Annotated[int, Field(ge=1, le=240, description="Export every step-th frame.")] = 1,
        alpha: Annotated[bool, Field(description="Keep transparency.")] = False,
        movie: Annotated[str | None, Field(description="Absolute path of a movie ffmpeg encodes from the "
                                                       "frames.")] = None,
        codec: Annotated[Literal["h264", "prores"], Field(description="Movie codec: .mp4 H.264 or .mov "
                                                                      "ProRes.")] = "h264",
        max_frames: Annotated[int, Field(ge=1, le=5000, description="Most frames to write.")] = 1800
) -> models.FramesExported:
    """Write a frame range of a comp as frame_00001.png ... without aerender, optionally encoded to a movie.
    Use it when aerender renders nothing."""
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
async def ae_template_render(
        template: Annotated[str, Field(description="Absolute path of the template .aep.")],
        project: Annotated[str, Field(description="Absolute path the filled-in .aep is saved to.")],
        renders: Annotated[list[models.RenderTarget], Field(min_length=1, description="Comps to render and their "
                                                                                      "files.")],
        texts: Annotated[list[models.TextEdit], Field(description="Text layers to set, by name.")] = [],
        footage: Annotated[dict[str, str], Field(description="Footage items to replace: name to absolute "
                                                             "path.")] = {},
        discard: Annotated[bool, Field(description="Drop unsaved changes in the open project.")] = False
) -> models.TemplateRendered:
    """Fill a template .aep (text layers and footage by name), save it, and aerender the named comps with frame
    checks."""
    template, target = host.absolute(template, ".aep"), host.absolute(project, ".aep")
    files = {name: str(host.absolute(path)) for name, path in footage.items()}
    for render in renders:
        host.absolute(render.file)
    outputs = await asyncio.to_thread(edit.template_render, template, target, [t.model_dump() for t in texts],
                                      files, [r.model_dump() for r in renders], discard)
    return {"project": str(target), "texts": len(texts), "footage": len(files), "outputs": outputs}


@mcp.tool(annotations=WRITES)
async def ae_essential_graphics(
        project: Project, comp: Comp,
        add: Annotated[list[models.EssentialProperty], Field(description="Layer properties to add, each under a "
                                                                         "name.")] = [],
        template_name: Annotated[str | None, Field(description="Name of the Essential Graphics "
                                                               "template.")] = None
) -> models.EssentialGraphics:
    """Add layer properties (source text, color, slider or effect parameters, position ...) to a comp's Essential Graphics under a name, optionally name the template, and list the controls the comp has."""
    return await scene("ae_essential_graphics", project, {"comp": comp, "add": [a.model_dump() for a in add],
                                                          "template_name": template_name})


@mcp.tool(annotations=WRITES)
async def ae_essential_override(
        project: Project, comp: Comp, layer: models.Layer,
        values: Annotated[dict[str, Any], Field(min_length=1, description="Values by Essential Property "
                                                                          "name.")]
) -> models.EssentialOverridden:
    """Override Essential Properties on one nested-comp layer by their ae_essential_graphics names: a string sets source text, a number, array or color list sets that value. Each instance of the same comp keeps its own values."""
    return await scene("ae_essential_override", project, {"comp": comp, "layer": layer, "values": values})


@mcp.tool(annotations=WRITES)
async def ae_mogrt_export(project: Project, comp: Comp,
                          file: Annotated[str, Field(description="Absolute .mogrt path.")]) -> models.Script:
    """Refused: headless After Effects does not write the .mogrt. Use ae_essential_graphics to prepare the comp."""
    host.absolute(file, ".mogrt")
    raise ValueError("Refused: comp.exportAsMotionGraphicsTemplate returns true in headless After Effects but writes "
                     "no file; it only creates an empty folder at the path (measured). Export the .mogrt from "
                     "an After Effects window instead")
