"""Place 2D layers in a comp by their bounds."""

from typing import Annotated, Literal

from cavi_mcp_core.server import WRITES, need, reject_foreign
from pydantic import Field

from .. import models
from ..app import Comp, Project, mcp, scene

# Optional arguments each ae_layout action reads. time is the instant the bounds are measured.
LAYOUT_USES = {
    "align": {"edge", "to", "time"},
    "distribute": {"axis", "gap", "time"},
    "anchor": {"time"},
}


@mcp.tool(annotations=WRITES)
async def ae_layout(
        project: Project, comp: Comp,
        layers: Annotated[list[models.Layer], Field(
            min_length=1, description="Layers to move, by index or name.")],
        action: Annotated[Literal["align", "distribute", "anchor"], Field(
            description="align lines up an edge, distribute spaces boxes, anchor centers the anchor.")],
        edge: Annotated[
            Literal["left", "right", "top", "bottom", "hcenter", "vcenter", "center"] | None,
            Field(description="align: left, right, top, bottom, hcenter, vcenter or center.")] = None,
        to: Annotated[Literal["comp", "selection"], Field(
            description="align: the comp frame, or the combined bounds of these layers.")] = "comp",
        axis: Annotated[Literal["horizontal", "vertical"] | None,
                        Field(description="distribute: horizontal or vertical.")] = None,
        gap: Annotated[float | None, Field(description="distribute: pixels between boxes. Omit it to pin the "
                                                       "first and last and space the gaps evenly.")] = None,
        time: Annotated[float, Field(description="Seconds at which the bounds are measured.")] = 0
) -> models.Layout:
    """Align, distribute or recenter the anchor of 2D layers by their bounds, including scale, rotation and
    parents. Cameras, lights, 3D layers and locked layers are refused."""
    given = {"edge": edge, "to": None if to == "comp" else to, "axis": axis, "gap": gap, "time": time}
    reject_foreign(action, given, LAYOUT_USES[action])
    if action == "align":
        need(edge, "edge", action)
    elif action == "distribute":
        need(axis, "axis", action)
    return await scene("ae_layout", project, {"comp": comp, "layers": layers, "action": action, "edge": edge,
                                              "to": to, "axis": axis, "gap": gap, "time": time})
