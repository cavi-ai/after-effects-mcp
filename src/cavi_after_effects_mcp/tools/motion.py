"""Animation: keyframes, expressions, effects, text animators, controls, audio levels and time."""

import asyncio
from typing import Annotated, Any, Literal

from cavi_mcp_core.server import READ_ONLY, WRITES
from pydantic import Field

from .. import edit, host, models
from ..app import given, mcp, scene
from ..models import Ease, ExpressionPreset, Keyframe


@mcp.tool(annotations=WRITES)
async def ae_keyframes(project: str, comp: str, layer: models.Layer, property: str,
                       keyframes: list[Keyframe] = [], ease: Ease | None = None, expression: str | None = None,
                       preset: ExpressionPreset | None = None, replace: bool = True, easy_ease: bool = False,
                       hold: bool = False, spatial: Literal["bezier", "linear"] | None = None, rove: bool = False,
                       remove: Literal["all"] | Annotated[list[float], Field(min_length=2, max_length=2)] | None = None
                       ) -> models.Keyframed:
    """Set keyframes on a layer property ("position", "Transform/Opacity" or match-name path), an expression or an expression preset (wiggle, loop_cycle, loop_pingpong, inertial_bounce, time_rotation). Without keyframes, easy_ease, ease, hold, spatial (position paths) and rove restyle the existing keys; remove drops all keys or those in [start, end]."""
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
async def ae_expressions(project: str, comp: str, layer: models.Layer | None = None,
                         remove_broken: bool = False) -> models.Expressions:
    """List every expression in a comp (or one layer) as {layer, property path, expression, enabled, error}; `broken` counts expressions After Effects reports an error for. remove_broken clears those expressions."""
    return await scene("ae_expressions", project, {"comp": comp, "layer": layer, "remove_broken": remove_broken})


@mcp.tool(annotations=WRITES)
async def ae_effect_add(project: str, comp: str, layer: models.Layer, match_name: str,
                        params: dict[str, Any] | None = None, name: str | None = None) -> models.EffectAdded:
    """Add an effect by matchName (e.g. ADBE Glo2) and set parameters by name or matchName."""
    return await scene("ae_effect_add", project, {"comp": comp, "layer": layer, "match_name": match_name,
                                                  "params": params or {}, "name": name})


@mcp.tool(annotations=WRITES)
async def ae_preset_apply(project: str, comp: str, layer: models.Layer, preset: str,
                          time: Annotated[float, Field(ge=0)] = 0) -> models.Script:
    """Refused: layer.applyPreset exits headless After Effects. Resolves `preset` first, so bad names fail clearly."""
    await asyncio.to_thread(host.resolve_preset, preset)
    raise ValueError("Refused: applying an animation preset (layer.applyPreset) exits headless After Effects "
                     "(measured with two presets); build the look with ae_effect_add, ae_keyframes and "
                     "ae_text_animator instead")


@mcp.tool(annotations=WRITES)
async def ae_text_animator(project: str, comp: str, layer: models.Layer,
                           unit: Literal["characters", "words", "lines"] = "characters",
                           opacity: float | None = None, position: models.Vector | None = None,
                           tracking: float | None = None, scale: models.Vector | None = None,
                           blur: models.Vector | None = None, rotation: float | None = None,
                           start: Annotated[float, Field(ge=0)] = 0,
                           duration: Annotated[float, Field(gt=0)] = 1, ease: Ease | None = Ease(),
                           name: str | None = None, animators: list[models.TextAnimator] = [],
                           path: models.TextPath | None = None) -> models.TextAnimated:
    """Add a text animator whose range selector opens over characters, words or lines from `start` for `duration`; or `animators`, each with properties (fill and stroke color, stroke width, skew, character offset, per-character 3D rotation ...) and several selectors (range with shape, ease high and low, wiggly, expression); and/or text on a path from a layer mask (`path`, first and last margin)."""
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
async def ae_controls(project: str, comp: str, layer: models.Layer, controls: list[models.ControlSpec] = [],
                      links: list[models.ControlLink] = []) -> models.ControlsSet:
    """Add named Expression Controls (slider, angle, point, point3d, color, checkbox, layer, dropdown) to `layer` and set their values, and link target properties on any layer to a control with a generated expression (scale, offset, one axis of a vector)."""
    if not controls and not links:
        raise ValueError("Give controls or links")
    args = {"comp": comp, "layer": layer, "controls": [c.model_dump() for c in controls],
            "links": [link.model_dump() for link in links]}
    return await scene("ae_controls", project, args)


@mcp.tool(annotations=WRITES)
async def ae_audio(project: str, comp: str, layer: models.Layer, enabled: bool | None = None,
                   level: float | Annotated[list[float], Field(min_length=2, max_length=2)] | None = None,
                   level_keys: list[Keyframe] = [], fade_in: Annotated[float, Field(gt=0)] | None = None,
                   fade_out: Annotated[float, Field(gt=0)] | None = None, convert_to_keyframes: bool = False
                   ) -> models.AudioSet:
    """Set an audio layer's Audio Levels in dB (static `level`, or keyed `level_keys` with [left, right] or one value), fade in and out by seconds (from -100 dB), and audio on or off."""
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
async def ae_time(project: str, comp: str, layer: models.Layer, time_remap: bool | None = None,
                  remap_keys: list[models.RemapKey] = [], freeze_at: Annotated[float, Field(ge=0)] | None = None,
                  reverse: bool | None = None, frame_blending: Literal["none", "mix", "pixel_motion"] | None = None
                  ) -> models.TimeSet:
    """Time remap on or off with keys [{time, source_time}], a freeze frame at a source time, reverse (stretch -100, keeping the in point), and the layer's frame blending (none, mix, pixel_motion; the comp switch is turned on)."""
    given(time_remap=time_remap, remap_keys=remap_keys or None, freeze_at=freeze_at, reverse=reverse,
          frame_blending=frame_blending)
    if freeze_at is not None and remap_keys:
        raise ValueError("Give freeze_at or remap_keys, not both")
    args = {"comp": comp, "layer": layer, "time_remap": time_remap, "remap_keys": [k.model_dump() for k in remap_keys],
            "freeze_at": freeze_at, "reverse": reverse, "frame_blending": frame_blending}
    return await scene("ae_time", project, args)


@mcp.tool(annotations=READ_ONLY)
async def ae_properties(project: str, comp: str, layer: models.Layer, path: str | None = None,
                        depth: Annotated[int, Field(ge=1, le=8)] = 4,
                        max_nodes: Annotated[int, Field(ge=1, le=5000)] = 1000,
                        time: Annotated[float, Field(ge=0)] | None = None) -> models.Properties:
    """Read a layer's properties as {path, match name, value, key count, expression}: the whole tree to `depth` groups, or one property or group by `path` ("Transform", "Effects/Glow", "Text/Source Text" or a match name). Values are the stored value, or with `time` (comp seconds) the animated value at that time with expressions evaluated."""
    return await scene("ae_properties", project, {"comp": comp, "layer": layer, "path": path, "depth": depth,
                                                  "max_nodes": max_nodes, "time": time}, 120)
