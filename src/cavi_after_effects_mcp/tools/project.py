"""The project: open, save, inspect, import, organize, and what the installation offers."""

import asyncio
from typing import Annotated, Literal

from cavi_mcp_core.server import DESTRUCTIVE, READ_ONLY, WRITES
from pydantic import Field

from .. import edit, host, models
from ..app import given, mcp, scene


@mcp.tool(annotations=READ_ONLY)
async def ae_inspect(project: str, scope: Literal["project", "comp", "queue"] = "project",
                     comp: str | None = None) -> models.Inspect:
    """List project items (comps, footage with missing flag, folders), one comp's layers, or the render queue."""
    if scope == "comp" and not comp:
        raise ValueError("scope comp needs a comp name")
    return await scene("ae_inspect", project, {"scope": scope, "comp": comp})


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_project(action: Literal["open", "save", "save_as", "info", "reduce", "remove_unused", "consolidate"],
                     path: str | None = None, discard: bool = False, overwrite: bool = False,
                     comps: list[str] = []) -> models.ProjectState:
    """Open a saved .aep in the headless instance, save it, save it under a new path, or report the open project's path. Open refuses unsaved changes unless discard; save_as refuses an existing file unless overwrite. reduce keeps only `comps` and what they use, remove_unused drops unused footage, consolidate merges duplicate footage; each rewrites the open project, or saves to `path` instead when given. removed reports the count."""
    if action in ("open", "save_as") and not path:
        raise ValueError(f"{action} needs a path")
    if action == "reduce" and not comps:
        raise ValueError("reduce needs comps")
    target = host.absolute(path, ".aep") if path else host.session.project
    if action == "open" and not target.is_file():
        raise ValueError(f"No project at {target}")
    if action in ("save", "info", "reduce", "remove_unused", "consolidate") and target is None:
        raise ValueError(f"{action} needs a path until a project has been used in this session")
    args = {"action": action, "path": str(target) if target else None, "discard": discard, "overwrite": overwrite,
            "comps": comps}
    report = await asyncio.to_thread(edit.project_op, args, target)
    return {"project": report["path"] or "", "report": report, **{k: v for k, v in report.items() if k != "errors"}}


@mcp.tool(annotations=WRITES)
async def ae_project_settings(project: str, bits_per_channel: Literal[8, 16, 32] | None = None,
                              linear_blending: bool | None = None, working_space: str | None = None,
                              display_start_frame: Annotated[int, Field(ge=0)] | None = None,
                              time_display: Literal["frames", "timecode"] | None = None,
                              frames_count: Literal["start_0", "start_1", "timecode_conversion"] | None = None,
                              expression_engine: Literal["javascript-1.0", "extendscript"] | None = None,
                              gpu: Literal["metal", "software"] | None = None) -> models.ProjectSettings:
    """Set project-wide bit depth, working color space (a name from the install's color profile list), linear blending, display start frame, time display and frame count, expression engine and GPU acceleration; the report lists every setting after the change. Unset fields stay as they are."""
    args = {"bits_per_channel": bits_per_channel, "linear_blending": linear_blending,
            "working_space": working_space, "display_start_frame": display_start_frame,
            "time_display": time_display, "frames_count": frames_count,
            "expression_engine": expression_engine, "gpu": gpu}
    given(**args)
    return await scene("ae_project_settings", project, args)


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
async def ae_footage_replace(project: str, item: str, file: str) -> models.Footage:
    """Replace a footage item's source file in place; every layer using it updates."""
    return await scene("ae_footage_replace", project, {"item": item, "file": str(host.absolute(file))})


@mcp.tool(annotations=WRITES)
async def ae_collect(project: str, folder: str) -> models.Collected:
    """Copy every used footage file into `folder`, relink each item there with item.replace, save to `project`, and report counts and items still missing. Solids and image sequences are skipped by name."""
    return await asyncio.to_thread(edit.collect, host.absolute(project, ".aep"), host.absolute(folder))


@mcp.tool(annotations=WRITES)
async def ae_organize(project: str, folders: list[str] = [], renames: list[models.ItemRename] = [],
                      moves: list[models.ItemMove] = []) -> models.Organized:
    """Tidy the project panel: create folders (nested paths such as Comps/Titles), rename items, then move items (by their new names) into folders. An item name shared by two items is refused."""
    if not (folders or renames or moves):
        raise ValueError("Give at least one of: folders, renames, moves")
    if any(not f.strip("/") or "//" in f for f in folders):
        raise ValueError("A folder path has non-empty names separated by single slashes")
    return await scene("ae_organize", project, {"folders": folders, "renames": [r.model_dump() for r in renames],
                                                "moves": [m.model_dump() for m in moves]})


@mcp.tool(annotations=READ_ONLY)
async def ae_fonts(project: str, filter: str = "", limit: Annotated[int, Field(ge=1, le=2000)] = 200) -> models.Fonts:
    """List installed fonts as {postscript, family, style}; filter matches any of the three. Text tools take the PostScript name and refuse names that are not installed."""
    return await scene("ae_fonts", project, {"filter": filter, "limit": limit}, 120)


@mcp.tool(annotations=READ_ONLY)
async def ae_effects(project: str, filter: str = "", category: str | None = None,
                     limit: Annotated[int, Field(ge=1, le=1000)] = 200) -> models.EffectList:
    """List installed effects (app.effects) with category, display name and matchName; `filter` matches all three. The categories field counts the matches per category."""
    return await scene("ae_effects", project, {"filter": filter, "category": category, "limit": limit}, 120)


@mcp.tool(annotations=READ_ONLY)
async def ae_presets(project: str, filter: str = "", limit: Annotated[int, Field(ge=1, le=1000)] = 200
                     ) -> models.Presets:
    """List render settings templates, output module templates and installed .ffx animation presets (filter matches category and name)."""
    report = await asyncio.to_thread(host.run_template, "ae_presets", project, {}, 120)
    found = await asyncio.to_thread(host.animation_presets, None, filter)
    return {"project": project, "report": report, "render_settings": report["render_settings"],
            "output_modules": report["output_modules"], "animation_presets": found[:limit],
            "preset_count": len(found)}
