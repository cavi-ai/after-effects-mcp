"""MCP server for headless Adobe After Effects."""

import asyncio
from typing import Annotated, Any, Literal

from cavi_adobe_mcp.config import workspace
from cavi_adobe_mcp.contracts import Result
from cavi_mcp_core.server import READ_ONLY, WRITES, Server
from pydantic import BaseModel, ConfigDict, Field

from . import host
from . import recipe as recipes

mcp = Server("cavi-after-effects", package="cavi-after-effects-mcp",
             instructions="Headless After Effects: ae_launch, then ae_script; ae_render_queue renders.")


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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
