"""The server object and the helpers every tool module shares."""

import asyncio
from typing import Any

from cavi_mcp_core.server import Server

from . import host

mcp = Server("cavi-after-effects", package="cavi-after-effects-mcp",
             instructions="Headless After Effects: ae_launch, then ae_script or the typed ae_* scene tools; "
                         "ae_render_queue renders. Paths are absolute.")


async def scene(name: str, project: str, args: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
    """Run the packaged script ``name`` on ``project`` and return its report with the report's fields lifted."""
    report = await asyncio.to_thread(host.run_template, name, project, args, timeout)
    return {"project": project, "report": report, **{k: v for k, v in report.items() if k != "errors"}}


def given(**fields):
    """Refuse a call that sets none of ``fields``."""
    if all(v is None for v in fields.values()):
        raise ValueError("Give at least one of: " + ", ".join(fields))
