"""Place and time 2D layers in a comp."""

from typing import Annotated, Literal

from cavi_mcp_core.server import WRITES, need, reject_foreign
from pydantic import Field

from .. import host, models
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


@mcp.tool(annotations=WRITES)
async def ae_stagger(
        project: Project, comp: Comp,
        layers: Annotated[list[models.Layer], Field(
            min_length=1, description="Layers in stagger order, by index or name. The first does not move.")],
        frames: Annotated[int, Field(
            description="Whole frames added for each later layer. Negative shifts earlier. 0 is refused.")],
        mode: Annotated[Literal["in_points", "keyframes", "both"], Field(
            description="Shift in and out points, every key time, or both.")]
) -> models.Stagger:
    """Shift each listed layer by whole frames after the one before it, moving in and out points, keyframes or
    both. Cameras, lights, 3D layers and locked layers are refused."""
    if frames == 0:
        raise ValueError("frames must not be 0")
    return await scene("ae_stagger", project,
                       {"comp": comp, "layers": layers, "frames": frames, "mode": mode})


# Frame sizes, written as WIDTHxHEIGHT. The default list is every one of them, in this order.
ASPECTS = ("1920x1080", "1080x1920", "1080x1080", "1080x1350")


def frame_aspects(aspects: list[str]) -> list[str]:
    """Refuse an aspect this tool does not reframe to, and a list that names one twice."""
    seen = set()
    for aspect in aspects:
        if aspect not in ASPECTS:
            raise ValueError(f"Unknown aspect {aspect}")
        if aspect in seen:
            raise ValueError(f"aspects lists {aspect} twice")
        seen.add(aspect)
    return aspects


@mcp.tool(annotations=WRITES)
async def ae_reframe(
        project: Project, comp: Comp,
        aspects: Annotated[list[str], Field(
            min_length=1,
            description="Frame sizes as WIDTHxHEIGHT. One or more of 1920x1080, 1080x1920, 1080x1080 and "
                        "1080x1350; the default is all four.")] = ["1920x1080", "1080x1920", "1080x1080",
                                                                   "1080x1350"],
        time: Annotated[float, Field(description="Seconds at which layer bounds are measured.")] = 0
) -> models.Reframe:
    """Duplicate a comp at each frame size and shift 2D layers so their bounds keep the same offset from the
    center. Cameras, lights, 3D layers and locked layers are left in place."""
    host.absolute(project, ".aep")
    return await scene("ae_reframe", project, {"comp": comp, "aspects": frame_aspects(aspects), "time": time})
