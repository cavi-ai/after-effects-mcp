"""The project: open, save, inspect, import, organize, and what the installation offers."""

import asyncio
from typing import Annotated, Literal

from cavi_mcp_core.server import DESTRUCTIVE, READ_ONLY, WRITES, need, reject_foreign
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from .. import edit, host, models
from ..app import BATCH, Project, given, mcp, scene


def folder_path(path):
    """Refuse a project folder path that is not non-empty names separated by single slashes."""
    if not path.strip("/") or "//" in path:
        raise ValueError(f"A folder path has non-empty names separated by single slashes: {path}")


@mcp.tool(annotations=READ_ONLY)
async def ae_inspect(
        project: Project,
        scope: Annotated[Literal["project", "comp", "queue"], Field(description="What to list.")] = "project",
        comp: Annotated[str | None, Field(description="Comp to list; required for scope comp.")] = None
) -> models.Inspect:
    """List project items (comps, footage with missing flag, folders), one comp's layers, or the render queue."""
    if scope == "comp" and not comp:
        raise ValueError("scope comp needs a comp name")
    return await scene("ae_inspect", project, {"scope": scope, "comp": comp})


# The flags each ae_project action reads; path is read by every action.
PROJECT_USES = {"new": {"discard", "overwrite"}, "open": {"discard"}, "save_as": {"overwrite"}, "reduce": {"comps"}}


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_project(
        action: Annotated[Literal["new", "open", "save", "save_as", "info", "reduce", "remove_unused", "consolidate"],
                          Field(description="What to do with the project.")],
        path: Annotated[str | None, Field(description="Absolute .aep path; required for new, open and "
                                                      "save_as.")] = None,
        discard: Annotated[bool, Field(description="Let new and open drop unsaved changes.")] = False,
        overwrite: Annotated[bool, Field(description="Let new and save_as replace an existing file.")] = False,
        comps: Annotated[list[str], Field(description="Comps reduce keeps.")] = []) -> models.ProjectState:
    """Create an empty .aep (new), open, save or save as a .aep in the headless instance, or report the open
    project's path. reduce keeps only comps and what they use, remove_unused drops unused footage, consolidate
    merges duplicate footage; each rewrites the open project, or saves to path when given. removed reports the
    count."""
    reject_foreign(action, {"discard": discard or None, "overwrite": overwrite or None, "comps": comps or None},
                   PROJECT_USES.get(action, set()))
    if action in ("new", "open", "save_as"):
        need(path or None, "path", action)
    if action == "reduce":
        need(comps or None, "comps", action)
    target =host.absolute(path, ".aep") if path else host.session.project
    if action == "open" and not target.is_file():
        raise FileNotFoundError(f"No project at {target}")
    if action == "new" and target.exists() and not overwrite:
        raise ValueError(f"{target} exists; set overwrite to replace it")
    if action in ("save", "info", "reduce", "remove_unused", "consolidate") and target is None:
        raise ValueError(f"{action} needs a path until a project has been used in this session")
    args = {"action": action, "path": str(target) if target else None, "discard": discard, "overwrite": overwrite,
            "comps": comps}
    report = await asyncio.to_thread(edit.project_op, args)
    return {"project": report["path"] or "", "report": report, **{k: v for k, v in report.items() if k != "errors"}}


@mcp.tool(annotations=WRITES)
async def ae_project_settings(
        project: Project,
        bits_per_channel: Annotated[Literal[8, 16, 32] | None, Field(description="Color bit depth.")] = None,
        linear_blending: Annotated[bool | None, Field(description="Blend colors using 1.0 gamma.")] = None,
        working_space: Annotated[str | None, Field(description="Working color space, a name from the install's "
                                                               "color profile list.")] = None,
        display_start_frame: Annotated[Annotated[int, Field(ge=0)] | None,
                                       Field(description="Frame number the time display starts at.")] = None,
        time_display: Annotated[Literal["frames", "timecode"] | None, Field(description="Time display "
                                                                                       "style.")] = None,
        frames_count: Annotated[Literal["start_0", "start_1", "timecode_conversion"] | None,
                                Field(description="How frames are counted.")] = None,
        expression_engine: Annotated[Literal["javascript-1.0", "extendscript"] | None,
                                     Field(description="Expression engine.")] = None,
        gpu: Annotated[Literal["metal", "software"] | None, Field(description="GPU acceleration.")] = None
) -> models.ProjectSettings:
    """Set project-wide color, time display, expression engine and GPU settings; the report lists every setting
    after the change. Unset fields stay as they are."""
    args = {"bits_per_channel": bits_per_channel, "linear_blending": linear_blending,
            "working_space": working_space, "display_start_frame": display_start_frame,
            "time_display": time_display, "frames_count": frames_count,
            "expression_engine": expression_engine, "gpu": gpu}
    given(**args)
    return await scene("ae_project_settings", project, args)


@mcp.tool(annotations=WRITES)
async def ae_import(
        project: Project,
        files: Annotated[list[str], Field(min_length=1, description="Absolute paths of the files to import.")],
        folder: Annotated[str | None, Field(description="Project folder path to import into, such as "
                                                        "Footage/Audio, created level by level from the root "
                                                        "when missing.")] = None,
        sequence: Annotated[bool, Field(description="Import an image sequence from its first frame.")] = False,
        import_as: Annotated[Literal["footage", "comp", "comp_cropped"],
                             Field(description="Import a layered PSD or AI as footage or as a comp.")] = "footage",
        alpha: Annotated[Literal["ignore", "straight", "premultiplied"] | None,
                         Field(description="Alpha interpretation.")] = None,
        conform_fps: Annotated[Annotated[float, Field(gt=0, le=240)] | None,
                               Field(description="Frame rate to conform the footage to.")] = None,
        loop: Annotated[Annotated[int, Field(ge=1)] | None, Field(description="Times the footage loops.")] = None
) -> models.Imported:
    """Import files into the project, then set their alpha mode, conform frame rate and loop count. An .aep arrives as one folder, reported with type project and the names of its comps."""
    paths = [str(host.absolute(f)) for f in files]
    if folder is not None:
        folder_path(folder)
    args = {"files": paths, "folder": folder, "sequence": sequence, "as": import_as, "alpha": alpha,
            "conform_fps": conform_fps, "loop": loop}
    return await scene("ae_import", project, args)


@mcp.tool(annotations=WRITES)
async def ae_footage_replace(project: Project, item: Annotated[str, Field(description="Footage item name.")],
                             file: Annotated[str, Field(description="Absolute path of the new source file.")]
                             ) -> models.Footage:
    """Replace a footage item's source file in place; every layer using it updates."""
    return await scene("ae_footage_replace", project, {"item": item, "file": str(host.absolute(file))})


@mcp.tool(annotations=WRITES)
async def ae_collect(project: Project,
                     folder: Annotated[str, Field(description="Absolute path of the folder to copy footage into.")]
                     ) -> models.Collected:
    """Copy every used footage file into a folder, relink each item there and report counts and items still
    missing. Solids and image sequences are skipped by name."""
    return await asyncio.to_thread(edit.collect, host.absolute(project, ".aep"), host.absolute(folder))


@mcp.tool(annotations=WRITES)
async def ae_organize(
        project: Project,
        folders: Annotated[list[str], Field(description="Folder paths to create, such as Comps/Titles.")] = [],
        renames: Annotated[list[models.ItemRename], Field(description="Items to rename.")] = [],
        moves: Annotated[list[models.ItemMove], Field(description="Items to move into folders, by their new "
                                                                  "names.")] = []) -> models.Organized:
    """Tidy the project panel: create folders, rename items, then move items into folders. An item name shared
    by two items is refused; pass the item's id from ae_inspect instead."""
    if not (folders or renames or moves):
        raise ValueError("Give at least one of: folders, renames, moves")
    for path in folders + [m.folder for m in moves]:
        folder_path(path)
    return await scene("ae_organize", project, {"folders": folders, "renames": [r.model_dump() for r in renames],
                                                "moves": [m.model_dump() for m in moves]})


# Write tools whose call runs one packaged script and returns its report.
BATCHABLE = frozenset({
    "ae_comp_new", "ae_comp_set", "ae_layer_add", "ae_layer_set", "ae_layer_edit", "ae_layer_parts", "ae_text_set",
    "ae_shape_add", "ae_mask", "ae_camera", "ae_material", "ae_markers", "ae_keyframes", "ae_expressions",
    "ae_effect_add", "ae_text_animator", "ae_controls", "ae_audio", "ae_time", "ae_transition",
    "ae_essential_graphics", "ae_essential_override", "ae_render_queue_set", "ae_project_settings", "ae_import",
    "ae_footage_replace", "ae_organize"})


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_batch(
        project: Project,
        steps: Annotated[list[models.BatchStep], Field(min_length=1, max_length=200, description="Typed write "
                                                       "tool calls in order, each {tool, args} without project.")],
        timeout: Annotated[int, Field(ge=10, le=3600, description="Seconds for the whole batch.")] = 600
) -> models.Batched:
    """Run typed write tools in order in one After Effects call. Each step's arguments are checked as its tool
    checks them before anything runs; the project is saved once after the last step, and a failing step leaves
    the project as it was before the batch. Returns each step's report in order."""
    planned = []
    token = BATCH.set(planned)
    try:
        for number, step in enumerate(steps, 1):
            label = f"Step {number} ({step.tool})"
            if step.tool not in BATCHABLE:
                raise ValueError(f"{label} is not a batchable tool; use one of {', '.join(sorted(BATCHABLE))}")
            if "project" in step.args:
                raise ValueError(f"{label}: project is given once, for the batch")
            try:
                await mcp._tool_manager.get_tool(step.tool).run({"project": project, **step.args}, None)
            except ToolError as error:
                raise ValueError(f"{label}: {str(error).removeprefix(f'Error executing tool {step.tool}: ')}") from error
            if len(planned) != number:
                raise RuntimeError(f"{label} ran {len(planned) - number + 1} scripts instead of one")
    finally:
        BATCH.reset(token)
    return await scene("ae_batch", project, {"steps": planned}, timeout)


@mcp.tool(annotations=READ_ONLY)
async def ae_fonts(
        project: Project,
        filter: Annotated[str, Field(description="Text the PostScript name, family or style contains.")] = "",
        limit: Annotated[int, Field(ge=1, le=2000, description="Most fonts to return.")] = 200,
        used: Annotated[bool, Field(description="List the fonts the project's text uses instead, each with missing "
                                                "and the layers that use it.")] = False) -> models.Fonts:
    """List installed fonts as {postscript, family, style}. Text tools take the PostScript name and refuse names
    that are not installed. With used, missing is true for a font that was not installed when the project opened;
    ae_font_replace swaps it."""
    return await scene("ae_fonts", project, {"filter": filter, "limit": limit, "used": used}, 120)


@mcp.tool(annotations=WRITES)
async def ae_font_replace(
        project: Project,
        font: Annotated[str, Field(min_length=1, description="PostScript name of a font the project's text uses, "
                                                             "as ae_fonts with used lists it.")],
        to: Annotated[str, Field(min_length=1, description="PostScript name of the installed font to use "
                                                           "instead.")],
        fallback: Annotated[bool, Field(description="Use a fallback font for characters the new font has no "
                                                    "glyphs for.")] = True) -> models.FontReplaced:
    """Replace every use of a font in the project's text, mixed styles included, with an installed font; the
    layers that used it are listed. Also relinks a missing font once it is installed under the same name."""
    return await scene("ae_font_replace", project, {"font": font, "to": to, "fallback": fallback})


@mcp.tool(annotations=READ_ONLY)
async def ae_effects(
        project: Project,
        filter: Annotated[str, Field(description="Text the category, display name or matchName contains.")] = "",
        category: Annotated[str | None, Field(description="List only this category.")] = None,
        limit: Annotated[int, Field(ge=1, le=1000, description="Most effects to return.")] = 200
) -> models.EffectList:
    """List installed effects with category, display name and matchName. The categories field counts the
    matches per category."""
    return await scene("ae_effects", project, {"filter": filter, "category": category, "limit": limit}, 120)


@mcp.tool(annotations=READ_ONLY)
async def ae_presets(
        project: Project,
        filter: Annotated[str, Field(description="Text an animation preset's category or name contains.")] = "",
        limit: Annotated[int, Field(ge=1, le=1000, description="Most animation presets to return.")] = 200
) -> models.Presets:
    """List render settings templates, output module templates and installed .ffx animation presets."""
    report = await asyncio.to_thread(host.run_template, "ae_presets", project, {}, 120)
    found = await asyncio.to_thread(host.animation_presets, None, filter)
    return {"project": project, "report": report, "render_settings": report["render_settings"],
            "output_modules": report["output_modules"], "animation_presets": found[:limit],
            "preset_count": len(found)}
