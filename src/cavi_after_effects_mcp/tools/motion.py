"""Animation: keyframes, expressions, effects, text animators, controls, audio levels and time."""

import asyncio
from typing import Annotated, Any, Literal

from cavi_mcp_core.server import READ_ONLY, WRITES
from pydantic import Field

from .. import edit, host, models
from ..app import Comp, Project, given, mcp, scene
from ..models import Ease, ExpressionPreset, Keyframe


@mcp.tool(annotations=WRITES)
async def ae_keyframes(
        project: Project, comp: Comp, layer: models.Layer,
        property: Annotated[str, Field(description="Property path, such as position, Transform/Opacity or a "
                                                   "match-name path.")],
        keyframes: Annotated[list[Keyframe], Field(description="Keyframes to set.")] = [],
        ease: Annotated[Ease | None, Field(description="Temporal ease for the keys.")] = None,
        expression: Annotated[str | None, Field(description="Expression to set.")] = None,
        preset: Annotated[ExpressionPreset | None, Field(description="wiggle, loop_cycle, loop_pingpong, "
                                                                     "inertial_bounce or time_rotation.")] = None,
        replace: Annotated[bool, Field(description="Remove the existing keys before setting new ones.")] = True,
        easy_ease: Annotated[bool, Field(description="Easy ease the keys.")] = False,
        hold: Annotated[bool, Field(description="Make the keys hold keys.")] = False,
        spatial: Annotated[Literal["bezier", "linear"] | None, Field(description="Spatial interpolation of a "
                                                                                 "position path.")] = None,
        rove: Annotated[bool, Field(description="Rove the keys across time.")] = False,
        remove: Annotated[Literal["all"] | Annotated[list[float], Field(min_length=2, max_length=2)] | None,
                          Field(description="Drop all keys, or those in [start, end] seconds.")] = None
) -> models.Keyframed:
    """Set keyframes, an expression or an expression preset on a layer property. Without keyframes, easy_ease,
    ease, hold, spatial and rove restyle the existing keys."""
    if expression is not None and preset is not None:
        raise ValueError("Give an expression or a preset, not both")
    if easy_ease and ease is None:
        ease = Ease(speed=0, influence=33.333)
    restyle = hold or spatial is not None or rove or (ease is not None and not keyframes)
    if not (keyframes or expression is not None or preset or remove or restyle):
        raise ValueError("Give keyframes or an expression (or a preset, remove, easy_ease, hold, spatial or rove)")
    if preset:
        expression = edit.expression_preset(preset.kind, preset.freq, preset.amp, preset.decay, preset.speed)
    args = {"comp": comp, "layer": layer, "property": property, "expression": expression, "remove": remove,
            "replace": replace and bool(keyframes or (expression is not None and preset is None)),
            "keyframes": [k.model_dump() for k in keyframes], "ease": ease.model_dump() if ease else None,
            "restyle": restyle, "hold": hold, "spatial": spatial, "rove": rove}
    return await scene("ae_keyframes", project, args)


@mcp.tool(annotations=WRITES)
async def ae_expressions(
        project: Project, comp: Comp,
        layer: Annotated[models.Layer | None, Field(description="List only this layer's expressions.")] = None,
        remove_broken: Annotated[bool, Field(description="Clear the expressions that have an error.")] = False
) -> models.Expressions:
    """List every expression in a comp as {layer, property path, expression, enabled, error}; broken counts the
    expressions After Effects reports an error for."""
    return await scene("ae_expressions", project, {"comp": comp, "layer": layer, "remove_broken": remove_broken})


@mcp.tool(annotations=WRITES)
async def ae_effect_add(
        project: Project, comp: Comp, layer: models.Layer,
        match_name: Annotated[str, Field(description="Effect matchName, as ae_effects lists it.")],
        params: Annotated[dict[str, Any] | None, Field(description="Parameter values by name or "
                                                                   "matchName.")] = None,
        name: Annotated[str | None, Field(description="Name for the effect instance.")] = None
) -> models.EffectAdded:
    """Add an effect by matchName (e.g. ADBE Glo2) and set parameters by name or matchName."""
    return await scene("ae_effect_add", project, {"comp": comp, "layer": layer, "match_name": match_name,
                                                  "params": params or {}, "name": name})


@mcp.tool(annotations=WRITES)
async def ae_preset_apply(
        project: Project, comp: Comp, layer: models.Layer,
        preset: Annotated[str, Field(description="Animation preset name or absolute .ffx path.")],
        time: Annotated[float, Field(ge=0, description="Comp time in seconds.")] = 0) -> models.Script:
    """Refused: layer.applyPreset exits headless After Effects. Resolves `preset` first, so bad names fail clearly."""
    await asyncio.to_thread(host.resolve_preset, preset)
    raise ValueError("Refused: applying an animation preset (layer.applyPreset) exits headless After Effects "
                     "(measured with two presets); build the look with ae_effect_add, ae_keyframes and "
                     "ae_text_animator instead")


@mcp.tool(annotations=WRITES)
async def ae_text_animator(
        project: Project, comp: Comp, layer: models.Layer,
        unit: Annotated[Literal["characters", "words", "lines"], Field(description="What the range selector "
                                                                                   "steps over.")] = "characters",
        opacity: Annotated[float | None, Field(description="Animated opacity in percent.")] = None,
        position: Annotated[models.Vector | None, Field(description="Animated position offset.")] = None,
        tracking: Annotated[float | None, Field(description="Animated tracking.")] = None,
        scale: Annotated[models.Vector | None, Field(description="Animated scale in percent.")] = None,
        blur: Annotated[models.Vector | None, Field(description="Animated blur.")] = None,
        rotation: Annotated[float | None, Field(description="Animated rotation in degrees.")] = None,
        start: Annotated[float, Field(ge=0, description="When the range selector starts opening, comp "
                                                        "seconds.")] = 0,
        duration: Annotated[float, Field(gt=0, description="How long it takes to open, in seconds.")] = 1,
        ease: Annotated[Ease | None, Field(description="Ease of the selector keys.")] = Ease(),
        name: Annotated[str | None, Field(description="Animator name.")] = None,
        animators: Annotated[list[models.TextAnimator],
                             Field(description="Full animators, each with properties and selectors.")] = [],
        path: Annotated[models.TextPath | None, Field(description="Text on a path from a layer mask.")] = None
) -> models.TextAnimated:
    """Add a text animator whose range selector opens over the text, or full animators with several selectors
    (range, wiggly, expression), and/or put the text on a mask path."""
    properties = {"opacity": opacity, "position": position, "tracking": tracking, "scale": scale,
                  "blur": blur, "rotation": rotation}
    listed = [a.model_dump() for a in animators]
    if not listed and any(v is not None for v in properties.values()):
        listed = [{"name": name, "properties": properties, "selectors": [
            models.TextSelector(unit=unit, animate=models.RangeAnimation(start=start, duration=duration,
                                                                         ease=ease)).model_dump()]}]
    if not listed and path is None:
        raise ValueError("Give at least one animator property")
    args = {"comp": comp, "layer": layer, "animators": listed, "path": path.model_dump() if path else None}
    return await scene("ae_text_animator", project, args)


@mcp.tool(annotations=WRITES)
async def ae_controls(
        project: Project, comp: Comp, layer: models.Layer,
        controls: Annotated[list[models.ControlSpec], Field(description="Expression Controls to add to the "
                                                                        "layer, with values.")] = [],
        links: Annotated[list[models.ControlLink], Field(description="Properties to drive from a control.")] = []
) -> models.ControlsSet:
    """Add named Expression Controls (slider, angle, point, point3d, color, checkbox, layer, dropdown) to a layer
    and link properties on any layer to a control with a generated expression (scale, offset, one axis)."""
    if not controls and not links:
        raise ValueError("Give controls or links")
    args = {"comp": comp, "layer": layer, "controls": [c.model_dump() for c in controls],
            "links": [link.model_dump() for link in links]}
    return await scene("ae_controls", project, args)


@mcp.tool(annotations=WRITES)
async def ae_audio(
        project: Project, comp: Comp, layer: models.Layer,
        enabled: Annotated[bool | None, Field(description="Audio switch.")] = None,
        level: Annotated[float | Annotated[list[float], Field(min_length=2, max_length=2)] | None,
                         Field(description="Static level in dB, one value or [left, right].")] = None,
        level_keys: Annotated[list[Keyframe], Field(description="Keyed levels in dB.")] = [],
        fade_in: Annotated[Annotated[float, Field(gt=0)] | None,
                           Field(description="Fade in from -100 dB, in seconds.")] = None,
        fade_out: Annotated[Annotated[float, Field(gt=0)] | None,
                            Field(description="Fade out to -100 dB, in seconds.")] = None,
        convert_to_keyframes: Annotated[bool, Field(description="Refused: exits headless After "
                                                                "Effects.")] = False
) -> models.AudioSet:
    """Set an audio layer's Audio Levels, fades and audio switch."""
    if convert_to_keyframes:
        raise ValueError("Refused: Convert Audio to Keyframes (app.executeCommand of the menu command 4218) exits "
                         "headless After Effects (measured twice); use ae_keyframes with an expression or keys")
    given(enabled=enabled, level=level, level_keys=level_keys or None, fade_in=fade_in, fade_out=fade_out)
    if level is not None and level_keys:
        raise ValueError("Give level or level_keys, not both")

    def both(value):
        return [value, value] if isinstance(value, int | float) else value

    keys = [{**k.model_dump(), "value": both(k.value)} for k in level_keys]
    args = {"comp": comp, "layer": layer, "enabled": enabled, "level": both(level), "level_keys": keys,
            "fade_in": fade_in, "fade_out": fade_out}
    return await scene("ae_audio", project, args)


@mcp.tool(annotations=WRITES)
async def ae_time(
        project: Project, comp: Comp, layer: models.Layer,
        time_remap: Annotated[bool | None, Field(description="Time remapping on or off.")] = None,
        remap_keys: Annotated[list[models.RemapKey], Field(description="Remap keys as [{time, "
                                                                       "source_time}].")] = [],
        freeze_at: Annotated[Annotated[float, Field(ge=0)] | None,
                             Field(description="Freeze on this source time, in seconds.")] = None,
        reverse: Annotated[bool | None, Field(description="Play backwards (stretch -100), keeping the in "
                                                          "point.")] = None,
        frame_blending: Annotated[Literal["none", "mix", "pixel_motion"] | None,
                                  Field(description="Layer frame blending; turns the comp switch on.")] = None
) -> models.TimeSet:
    """Time remap with keys, a freeze frame, reverse playback and the layer's frame blending."""
    given(time_remap=time_remap, remap_keys=remap_keys or None, freeze_at=freeze_at, reverse=reverse,
          frame_blending=frame_blending)
    if freeze_at is not None and remap_keys:
        raise ValueError("Give freeze_at or remap_keys, not both")
    args = {"comp": comp, "layer": layer, "time_remap": time_remap, "remap_keys": [k.model_dump() for k in remap_keys],
            "freeze_at": freeze_at, "reverse": reverse, "frame_blending": frame_blending}
    return await scene("ae_time", project, args)


@mcp.tool(annotations=READ_ONLY)
async def ae_properties(
        project: Project, comp: Comp, layer: models.Layer,
        path: Annotated[str | None, Field(description="One property or group, such as Transform, Effects/Glow "
                                                      "or a match name; the whole tree when omitted.")] = None,
        depth: Annotated[int, Field(ge=1, le=8, description="Group levels to descend.")] = 4,
        max_nodes: Annotated[int, Field(ge=1, le=5000, description="Most properties to return.")] = 1000,
        time: Annotated[Annotated[float, Field(ge=0)] | None,
                        Field(description="Comp seconds to read animated values at, expressions "
                                          "evaluated.")] = None
) -> models.Properties:
    """Read a layer's properties as {path, match name, value, key count, expression}; values are the stored
    ones unless time is given."""
    return await scene("ae_properties", project, {"comp": comp, "layer": layer, "path": path, "depth": depth,
                                                  "max_nodes": max_nodes, "time": time}, 120)
