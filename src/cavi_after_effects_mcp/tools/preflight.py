"""Read-only checks for missing media, substitute fonts, broken expressions and odd frame sizes."""

from typing import Annotated

from cavi_mcp_core.server import READ_ONLY
from pydantic import Field

from .. import models
from ..app import Project, mcp, scene


@mcp.tool(annotations=READ_ONLY)
async def ae_preflight(
        project: Project,
        comp: Annotated[str | None, Field(description="Comp to scan. Omit to scan the whole project.")] = None
) -> models.Preflight:
    """Report missing footage, substitute fonts and broken expressions, and warn on an odd comp frame size.
    verdict is fail when any of those lists is non-empty; an odd size does not change it. Substitute fonts
    need After Effects 24.5 or later."""
    return await scene("ae_preflight", project, {"comp": comp})
