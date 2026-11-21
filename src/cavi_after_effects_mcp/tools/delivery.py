"""Delivery: render queue, renders, frames, templates, Essential Graphics."""

import asyncio
import csv
import json
import time
from pathlib import Path
from typing import Annotated, Any, Literal

from cavi_mcp_core.contracts import OperationUnknown
from cavi_mcp_core.media import png_content
from cavi_mcp_core.server import DESTRUCTIVE, READ_ONLY, WRITES
from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, TextContent
from pydantic import Field, ValidationError

from .. import edit, host, models
from .. import render as recipe_render
from ..app import Comp, Project, mcp, scene
from ..models import Output, QueueAdd, QueueUpdate

PREVIEW_EDGE = 768


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_render_queue(
        project: Annotated[str, Field(description="Absolute path of the saved .aep to render.")],
        outputs: Annotated[list[Output], Field(min_length=1, description="Queue entries to check, each by its comp "
                                                                         "and output file.")]
) -> models.Render:
    """aerender a saved .aep queue; an output short of its entry's frames renders once more by itself
    (aerender -rqindex). When aerender still leaves no movie or a short one, it is made from saveFrameToPng frames
    of the entry's time span and ffmpeg (.mp4 H.264 or .mov ProRes); each output's path says which way produced
    it."""
    return await asyncio.to_thread(edit.render_outputs, project, [o.model_dump() for o in outputs])


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_render_start(
        project: Annotated[str, Field(description="Absolute path of the saved .aep to render.")],
        output: Annotated[Output, Field(description="The queue entry to render, by its comp and output file.")]
) -> models.RenderJob:
    """Start rendering one queue entry in the background (aerender -rqindex) and return its job at once. The render
    outlives this server; read it with ae_render_status and stop it with ae_render_cancel. One render runs at a
    time."""
    return await asyncio.to_thread(host.render_start, project, output.model_dump())


@mcp.tool(annotations=READ_ONLY)
async def ae_render_status(
        ctx: Context,
        job: Annotated[str, Field(description="Job id from ae_render_start.")],
        wait: Annotated[float, Field(ge=0, le=600, description="Seconds to wait for the render to end, reporting "
                                                               "frames as progress.")] = 0
) -> models.RenderJob:
    """A background render's state: running, done (aerender exited 0 and the output has every frame), failed,
    cancelled or unresolved; frames logged so far, and the frames the output has once it ended."""
    deadline = time.monotonic() + wait
    status = await asyncio.to_thread(host.render_status, job)
    while status["state"] == "running" and time.monotonic() < deadline:
        await ctx.report_progress(status["done"], status["frames"],
                                  f"{status['comp']}: {status['done']} of {status['frames']} frames")
        await asyncio.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
        status = await asyncio.to_thread(host.render_status, job)
    return status


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_render_cancel(job: Annotated[str, Field(description="Job id from ae_render_start.")]) -> models.RenderJob:
    """Stop a background render; its output is left as aerender wrote it."""
    return await asyncio.to_thread(host.render_cancel, job)


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
                raise ValueError(f"{', '.join(fixed)} cannot be set from scripts (read-only in setSettings); "
                                 "pick an output module template such as High Quality with Alpha")
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
    return await asyncio.to_thread(recipe_render.ae_render, recipe_render.workspace(), recipe, directory)


@mcp.tool(annotations=WRITES)
async def ae_frame(
        project: Project, comp: Comp,
        times: Annotated[list[float], Field(min_length=1, max_length=50, description="Comp times of the frames, "
                                                                                     "in seconds.")],
        directory: Annotated[str, Field(description="Absolute path of the folder for the PNGs.")],
        alpha: Annotated[bool, Field(description="Keep transparency instead of the comp background.")] = False,
        method: Annotated[Literal["auto", "aerender"],
                          Field(description="auto uses saveFrameToPng and falls back to aerender; aerender uses "
                                            "only aerender.")] = "auto",
        previews: Annotated[int, Field(ge=0, le=16, description="Frames, from the first, also returned as images "
                                                                "at most 768 px on the long side; 0 returns only "
                                                                "the paths.")] = 4
) -> Annotated[CallToolResult, models.FramesRendered]:
    """Render one PNG per time of a comp and return the file paths; the first frames also come back as images."""
    host.absolute(directory)
    frames = await asyncio.to_thread(edit.render_frames, project, comp, times, directory, alpha, method == "auto")
    result = {"project": project, "comp": comp, "frames": frames}
    images = await asyncio.to_thread(lambda: [png_content(f["file"], PREVIEW_EDGE) for f in frames[:previews]])
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2)), *images],
                          structured_content=result)


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


_TEXT_FIELDS = tuple(models.TextEdit.model_fields)
_JSON_FIELDS = frozenset({"fill", "stroke", "box", "ranges"})


def _sheet_cell(row, key):
    value = row.get(key)
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _sheet_value(field, cell):
    if field == "layer" and cell.isascii() and cell.isdigit() and not cell.startswith("0"):
        return int(cell)
    if field not in _JSON_FIELDS:
        return cell
    try:
        return json.loads(cell)
    except json.JSONDecodeError as error:
        raise ValueError(f"sheet {field} is not JSON") from error


def _sheet_text(row):
    present = {}
    for field in _TEXT_FIELDS:
        cell = _sheet_cell(row, field)
        if cell is not None:
            present[field] = _sheet_value(field, cell)
    if not present:
        return None
    missing = [field for field in ("comp", "layer") if field not in present]
    if missing:
        raise ValueError(f"a text row needs {' and '.join(missing)}")
    return present


def _sheet_variant(data):
    try:
        return models.TemplateVariant.model_validate(data)
    except ValidationError as error:
        raise ValueError(str(error)) from error


def _csv_variants(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        fields = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
        if fields[-1:] == [""]:
            fields = fields[:-1]
        if "name" not in fields:
            raise ValueError("sheet needs a name column")
        if len(fields) != len(set(fields)):
            raise ValueError("sheet columns repeat")
        reader.fieldnames = fields
        grouped, order = {}, []
        for row in reader:
            if not any(_sheet_cell(row, key) for key in row if isinstance(key, str)):
                continue
            name = _sheet_cell(row, "name")
            if not name:
                raise ValueError("sheet row has an empty name")
            edit = _sheet_text(row)
            item, file = _sheet_cell(row, "item"), _sheet_cell(row, "file")
            if (item is None) != (file is None):
                raise ValueError("a footage row needs item and file")
            variant = grouped.get(name)
            if variant is None:
                variant = {"name": name, "texts": [], "footage": {}}
                grouped[name] = variant
                order.append(name)
            if edit is not None:
                variant["texts"].append(edit)
            if item is not None:
                variant["footage"][item] = file
    return [_sheet_variant(grouped[name]) for name in order]


def _json_variants(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as error:
        raise ValueError(f"sheet is not JSON: {error}") from error
    if isinstance(data, dict):
        variants = data.get("variants")
        if set(data) != {"variants"} or not isinstance(variants, list):
            raise ValueError('sheet JSON is a list of variants or {"variants": [...]}')
        data = variants
    if not isinstance(data, list):
        raise ValueError('sheet JSON is a list of variants or {"variants": [...]}')
    return [_sheet_variant(item) for item in data]


def sheet_variants(path):
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".json"}:
        raise ValueError(f"A sheet is a .csv or .json file: {path}")
    if not path.is_file():
        raise ValueError(f"No sheet at {path}")
    return _csv_variants(path) if suffix == ".csv" else _json_variants(path)


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_template_render(
        ctx: Context,
        template: Annotated[str, Field(description="Absolute path of the template .aep.")],
        project: Annotated[str, Field(description="Absolute path the filled-in .aep is saved to.")],
        renders: Annotated[list[models.RenderTarget], Field(min_length=1, description="Comps to render and their "
                                                                                      "files.")],
        texts: Annotated[list[models.TextEdit], Field(description="Text layers to set, by name.")] = [],
        footage: Annotated[dict[str, str], Field(description="Footage items to replace: name to absolute "
                                                             "path.")] = {},
        discard: Annotated[bool, Field(description="Drop unsaved changes in the open project.")] = False,
        variants: Annotated[list[models.TemplateVariant], Field(max_length=500, description="Versions filled and "
                                                                "rendered one after another, each with its own "
                                                                "texts and footage; its name replaces {name} in "
                                                                "project and every renders file.")] = [],
        sheet: Annotated[str | None, Field(description="Absolute path of a .csv or .json file that supplies "
                                                       "the variants; sheet or variants, not both. CSV rows "
                                                       "that share a name are one variant: comp, layer, text "
                                                       "and the other ae_text_set fields (fill, stroke, box "
                                                       "and ranges as JSON), plus item and file for footage. "
                                                       "A whole-number layer is an index. JSON is a list of "
                                                       "variants or {\"variants\": [...]}.")] = None
) -> models.TemplateRendered:
    """Fill a template .aep (text layers and footage by name), save it, and aerender the named comps with frame
    checks; with variants, once per variant. A CSV or JSON sheet supplies the variants. overflow lists
    the filled text layers whose paragraph text does not fit its box."""
    template, target = host.absolute(template, ".aep"), host.absolute(project, ".aep")
    shared = {name: str(host.absolute(path)) for name, path in footage.items()}
    for render in renders:
        host.absolute(render.file)
    if sheet is not None and variants:
        raise ValueError("sheet or variants, not both")
    if sheet is not None:
        variants = sheet_variants(host.absolute(sheet))
        if not variants:
            raise ValueError("sheet has no variants")
    if not variants:
        outputs, overflow = await asyncio.to_thread(edit.template_render, template, target,
                                                    [t.model_dump() for t in texts], shared,
                                                    [r.model_dump() for r in renders], discard)
        return {"project": str(target), "texts": len(texts), "overflow": overflow, "footage": len(shared),
                "outputs": outputs}
    names = [v.name for v in variants]
    if repeated := sorted({n for n in names if names.count(n) > 1}):
        raise ValueError(f"Variant names repeat: {', '.join(repeated)}")
    if "{name}" not in project or any("{name}" not in r.file for r in renders):
        raise ValueError("project and every renders file need {name} when variants are given")
    jobs = []
    for variant in variants:
        files = {**shared, **{item: str(host.absolute(path)) for item, path in variant.footage.items()}}
        outs = [{**r.model_dump(), "file": str(host.absolute(r.file.replace("{name}", variant.name)))}
                for r in renders]
        jobs.append((variant.name, host.absolute(project.replace("{name}", variant.name), ".aep"),
                     [t.model_dump() for t in [*texts, *variant.texts]], files, outs))
    outputs, overflow, done, counts = [], [], [], [0, 0]
    for name, path, edits, files, outs in jobs:
        try:
            made, over = await asyncio.to_thread(edit.template_render, template, path, edits, files, outs,
                                                 discard and not done)
        except Exception as error:
            if not done:
                error.args = (f"Variant {name}: {error}", *error.args[1:])
                raise
            raise OperationUnknown(f"Variant {name}: {error}; {', '.join(done)} rendered before it") from error
        outputs += [{"variant": name, **o} for o in made]
        overflow += [{"variant": name, **o} for o in over]
        counts = [counts[0] + len(edits), counts[1] + len(files)]
        done.append(name)
        await ctx.report_progress(len(done), len(jobs), f"{name}: rendered")
    return {"project": str(target), "texts": counts[0], "overflow": overflow, "footage": counts[1],
            "outputs": outputs}


@mcp.tool(annotations=WRITES)
async def ae_essential_graphics(
        project: Project, comp: Comp,
        add: Annotated[list[models.EssentialProperty], Field(description="Layer properties to add, each under a "
                                                                         "name.")] = [],
        template_name: Annotated[str | None, Field(description="Name of the Essential Graphics "
                                                               "template.")] = None
) -> models.EssentialGraphics:
    """Add layer properties (source text, color, slider or effect parameters, position ...) to a comp's Essential Graphics under a name, or a footage or comp layer itself as a media replacement control when property is omitted; optionally name the template, and list the controls the comp has."""
    return await scene("ae_essential_graphics", project, {"comp": comp, "add": [a.model_dump() for a in add],
                                                          "template_name": template_name})


@mcp.tool(annotations=WRITES)
async def ae_essential_override(
        project: Project, comp: Comp, layer: models.Layer,
        values: Annotated[dict[str, Any], Field(min_length=1, description="Values by Essential Property "
                                                                          "name.")]
) -> models.EssentialOverridden:
    """Override Essential Properties on one nested-comp layer by their ae_essential_graphics names: a media replacement control takes an absolute footage path (imported once) or a comp name, a string sets source text, a number, array or color list sets that value. Each instance of the same comp keeps its own values."""
    return await scene("ae_essential_override", project, {"comp": comp, "layer": layer, "values": values})


@mcp.tool(annotations=WRITES)
async def ae_mogrt_export(project: Project, comp: Comp,
                          file: Annotated[str, Field(description="Absolute .mogrt path.")]) -> models.Script:
    """Refused: headless After Effects does not write the .mogrt. Use ae_essential_graphics to prepare the comp."""
    host.absolute(file, ".mogrt")
    raise ValueError("Refused: comp.exportAsMotionGraphicsTemplate returns true in headless After Effects but writes "
                     "no file; it only creates an empty folder at the path (measured). Export the .mogrt from "
                     "an After Effects window instead")
