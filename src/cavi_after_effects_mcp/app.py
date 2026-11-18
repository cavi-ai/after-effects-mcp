"""The server object and the helpers every tool module shares."""

import asyncio
from typing import Annotated, Any

from cavi_mcp_core.contracts import failure
from cavi_mcp_core.server import Server
from pydantic import Field

from . import host


class AfterEffectsServer(Server):
    def failure(self, name, error):
        """An unknown outcome points at ae_inspect, which lists the project and its render queue."""
        return failure(name, error, unknown_next_action="ae_inspect")


mcp = AfterEffectsServer("cavi-after-effects", package="cavi-after-effects-mcp",
             instructions="Headless After Effects: ae_launch, then ae_script or the typed ae_* scene tools; "
                         "ae_render_queue renders. Paths are absolute.")
Project = Annotated[str, Field(description="Absolute path of the .aep the call works in and saves.")]
Comp = Annotated[str, Field(description="Comp name.")]


async def scene(name: str, project: str, args: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
    """Run the packaged script ``name`` on ``project`` and return its report with the report's fields lifted."""
    report = await asyncio.to_thread(host.run_template, name, project, args, timeout)
    return {"project": project, "report": report, **{k: v for k, v in report.items() if k != "errors"}}


def distinct_times(name, keys):
    """Refuse a key list that repeats a time: After Effects keeps one key there, mixing the repeats' settings."""
    seen = set()
    for key in keys:
        if key.time in seen:
            raise ValueError(f"{name} lists time {key.time:g} twice; give one key per time")
        seen.add(key.time)


def given(**fields):
    """Refuse a call that sets none of ``fields``."""
    if all(v is None for v in fields.values()):
        raise ValueError("Give at least one of: " + ", ".join(fields))
