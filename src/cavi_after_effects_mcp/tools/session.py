"""Start After Effects and run scripts in it."""

import asyncio
from typing import Annotated, Any

from cavi_mcp_core.server import DESTRUCTIVE, READ_ONLY, WRITES
from pydantic import Field

from .. import host, models
from ..app import mcp


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
async def ae_script(script: str, project: str, args: dict[str, Any] | None = None,
                    timeout: Annotated[int, Field(ge=10, le=3600)] = 900) -> models.Script:
    """Run a .jsx with global CAVI_ARGS; it calls caviReport(obj) and the project saves to `project` (.aep).

    Paths are absolute. Returns the report; report.errors fails the call.
    """
    host.refuse_crashing_calls(script)
    report = await asyncio.to_thread(host.run_script, script, project, args or {}, timeout)
    return {"project": project, "report": report}
