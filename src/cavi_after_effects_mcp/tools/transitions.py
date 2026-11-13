"""Transitions between and on layers, and laying layers end to end."""

import asyncio
from typing import Annotated, Literal

from cavi_mcp_core.server import READ_ONLY, WRITES
from pydantic import Field

from .. import host, models
from ..app import Comp, Project, mcp, scene
from ..models import Color, Ease


@mcp.tool(annotations=READ_ONLY)
async def ae_transitions(project: Project) -> models.Transitions:
    """List the transition kinds this install has: effect-based wipes and dissolves, crossfade and dip."""
    report = await asyncio.to_thread(host.run_template, "ae_transitions", project,
                                     {"match_names": list(host.TRANSITIONS.values())}, 120)
    have = {e["match_name"]: e["available"] for e in report["effects"]}
    kinds = [{"kind": k, "match_name": m, "available": have.get(m, False)} for k, m in host.TRANSITIONS.items()]
    kinds += [{"kind": k, "match_name": None, "available": True} for k in host.BUILT_IN_TRANSITIONS]
    return {"project": project, "kinds": kinds}


def known(kind):
    if kind not in host.TRANSITIONS and kind not in host.BUILT_IN_TRANSITIONS:
        raise ValueError(f"Unknown transition {kind}; see ae_transitions")


@mcp.tool(annotations=WRITES)
async def ae_transition(
        project: Project, comp: Comp,
        kind: Annotated[str, Field(description="Transition kind, as ae_transitions lists it.")],
        layer: Annotated[models.Layer | None, Field(description="Layer to transition in or out.")] = None,
        edge: Annotated[Literal["in", "out"], Field(description="Which end of layer.")] = "out",
        from_layer: Annotated[models.Layer | None, Field(description="Outgoing layer of a transition between "
                                                                     "two layers.")] = None,
        to_layer: Annotated[models.Layer | None, Field(description="Incoming layer; the transition starts at its "
                                                                   "in point.")] = None,
        seconds: Annotated[Annotated[float, Field(gt=0)] | None, Field(description="Length in seconds.")] = None,
        frames: Annotated[Annotated[int, Field(ge=1)] | None, Field(description="Length in frames.")] = None,
        color: Annotated[Color, Field(description="Dip color, RGB 0 to 1.")] = [0, 0, 0],
        ease: Annotated[Ease | None, Field(description="Ease of the transition keys.")] = Ease()
) -> models.Script:
    """Transition on one layer's in or out point, or between two layers."""
    known(kind)
    if (seconds is None) == (frames is None):
        raise ValueError("Give seconds or frames, not both")
    if layer is None and (from_layer is None or to_layer is None):
        raise ValueError("Give layer, or from_layer and to_layer")
    if layer is not None and (from_layer is not None or to_layer is not None):
        raise ValueError("Give layer, or from_layer and to_layer, not both")
    args = {"comp": comp, "kind": kind, "layer": layer, "edge": edge, "from_layer": from_layer,
            "to_layer": to_layer, "seconds": seconds, "frames": frames, "color": color,
            "match_name": host.TRANSITIONS.get(kind), "ease": ease.model_dump() if ease else None}
    return await scene("ae_transition", project, args)


@mcp.tool(annotations=WRITES)
async def ae_sequence_layers(
        project: Project, comp: Comp,
        items: Annotated[list[models.SequenceItem], Field(min_length=1, description="Existing layers or footage "
                                                                                    "files, in order.")],
        start: Annotated[float, Field(ge=0, description="Comp time the first item starts at, in "
                                                        "seconds.")] = 0,
        overlap: Annotated[float, Field(ge=0, description="Seconds each item overlaps the previous one.")] = 0,
        transition: Annotated[models.SequenceTransition | None,
                              Field(description="Transition at every join; its length defaults to the "
                                                "overlap.")] = None
) -> models.Sequenced:
    """Place layers and footage end to end; earlier items sit above later ones. Refuses a sequence that runs
    past the comp."""
    for item in items:
        if (item.layer is None) == (item.file is None):
            raise ValueError("Each item needs a layer or a file, not both")
        if item.file:
            host.absolute(item.file)
    if transition is not None:
        known(transition.kind)
        if transition.seconds is None and overlap == 0:
            raise ValueError("A transition needs seconds when there is no overlap")
    result = await scene("ae_sequence_layers", project, {"comp": comp, "start": start, "overlap": overlap,
                                                         "items": [i.model_dump() for i in items]})
    if transition is not None:
        for join in result["joins"]:
            await ae_transition(project, comp, transition.kind, from_layer=join["from_layer"],
                                to_layer=join["to_layer"], seconds=transition.seconds or overlap,
                                color=transition.color, ease=transition.ease)
    return result
