"""Start After Effects and run scripts in it."""

import asyncio
from typing import Annotated, Any

from cavi_mcp_core.server import DESTRUCTIVE, READ_ONLY, WRITES
from pydantic import Field

from .. import host, models
from ..app import Project, mcp


@mcp.tool(annotations=READ_ONLY)
async def ae_status() -> models.Status:
    """Installed After Effects and its running headless and UI pids. An application that is not installed is
    reported in `error`."""
    return await asyncio.to_thread(host.status)


@mcp.tool(annotations=WRITES)
async def ae_launch() -> models.Status:
    """Start headless After Effects (-noui) and wait until it answers scripts."""
    return await asyncio.to_thread(host.launch)


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_script(
        script: Annotated[str, Field(description="Absolute path of the .jsx to run.")],
        project: Project,
        args: Annotated[dict[str, Any] | None, Field(description="Values the script reads as CAVI_ARGS.")] = None,
        timeout: Annotated[int, Field(ge=10, le=3600, description="Seconds to wait before the call fails.")] = 900
) -> models.Script:
    """Run a .jsx that calls caviReport(obj); returns the report, and report.errors fails the call."""
    host.refuse_crashing_calls(script)
    report = await asyncio.to_thread(host.run_script, script, project, args or {}, timeout)
    return {"project": project, "report": report}
