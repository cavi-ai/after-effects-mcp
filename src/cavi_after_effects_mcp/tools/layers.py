"""Comps and layers: create, change, text, shapes, masks, cameras, materials and markers."""

from typing import Annotated, Any, Literal

from cavi_mcp_core.server import DESTRUCTIVE, WRITES
from pydantic import Field

from .. import edit, host, models
from ..app import Comp, Project, given, mcp, scene
from ..models import (
    BeatGrid,
    CameraSpec,
    Color,
    Fill,
    Gradient,
    GroupTransform,
    LayerSpec,
    LightSpec,
    MarkerSpec,
    MaskKey,
    MaskShape,
    Operator,
    ShapeSpec,
    Stroke,
    TrackMatte,
)


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_comp_new(
        project: Project, name: Annotated[str, Field(description="Name of the new comp.")],
        width: Annotated[int, Field(ge=4, le=30000, description="Width in pixels.")],
        height: Annotated[int, Field(ge=4, le=30000, description="Height in pixels.")],
        duration: Annotated[float, Field(gt=0, le=10800, description="Duration in seconds.")],
        fps: Annotated[float, Field(gt=0, le=240, description="Frame rate.")] = 30,
        background: Annotated[Color, Field(description="Background color, RGB 0 to 1.")] = [0, 0, 0],
        renderer: Annotated[str | None, Field(description="ADBE Advanced 3d, ADBE Calder or ADBE Ernst.")] = None,
        replace: Annotated[bool, Field(description="Remove an existing comp of that name first.")] = False
) -> models.CompNew:
    """Create a comp with its size, duration, frame rate, background and 3D renderer."""
    return await scene("ae_comp_new", project, {"name": name, "width": width, "height": height,
                                                "duration": duration, "fps": fps, "background": background,
                                                "renderer": renderer, "replace": replace})


@mcp.tool(annotations=WRITES)
async def ae_comp_set(
        project: Project, comp: Comp, name: Annotated[str | None, Field(description="New comp name.")] = None,
        width: Annotated[Annotated[int, Field(ge=4, le=30000)] | None,
                         Field(description="Width in pixels.")] = None,
        height: Annotated[Annotated[int, Field(ge=4, le=30000)] | None,
                          Field(description="Height in pixels.")] = None,
        duration: Annotated[Annotated[float, Field(gt=0, le=10800)] | None,
                            Field(description="Duration in seconds.")] = None,
        fps: Annotated[Annotated[float, Field(gt=0, le=240)] | None, Field(description="Frame rate.")] = None,
        work_area: Annotated[Annotated[list[float], Field(min_length=2, max_length=2)] | None,
                             Field(description="Work area as [start, duration] in seconds.")] = None,
        background: Annotated[Color | None, Field(description="Background color, RGB 0 to 1.")] = None,
        renderer: Annotated[str | None, Field(description="3D renderer match name.")] = None,
        motion_blur: Annotated[bool | None, Field(description="Comp motion blur switch.")] = None,
        frame_blending: Annotated[bool | None, Field(description="Comp frame blending switch.")] = None,
        duplicate_as: Annotated[str | None, Field(description="Copy the comp under this name and change the "
                                                              "copy.")] = None) -> models.CompChanged:
    """Change a comp's name, size, frame rate, duration, work area, background, renderer and switches."""
    given(name=name, width=width, height=height, duration=duration, fps=fps, work_area=work_area,
          background=background, renderer=renderer, motion_blur=motion_blur, frame_blending=frame_blending,
          duplicate_as=duplicate_as)
    args = {"comp": comp, "name": name, "width": width, "height": height, "duration": duration, "fps": fps,
            "work_area": work_area, "background": background, "renderer": renderer, "motion_blur": motion_blur,
            "frame_blending": frame_blending, "duplicate_as": duplicate_as}
    return await scene("ae_comp_set", project, args)


@mcp.tool(annotations=WRITES)
async def ae_layer_add(project: Project,
                       layer: Annotated[LayerSpec, Field(description="The layer to add and its settings.")]
                       ) -> models.LayerAdded:
    """Add a solid, text, footage, 3D model (.glb, .gltf, .obj; Advanced 3D comps only), nested comp (`source`), rectangle, null, camera, light (point, spot, parallel, ambient, environment) or adjustment layer with transform, 3D, timing, parent, blend mode and matte."""
    if layer.kind == "comp" and not layer.source:
        raise ValueError("A comp layer needs source, the name of the comp to nest")
    if layer.kind in ("footage", "model"):
        path = host.absolute(layer.file or "")
        if layer.kind == "model" and path.suffix.lower() not in (".glb", ".gltf", ".obj"):
            raise ValueError("A 3D model file is .glb, .gltf or .obj")
    return await scene("ae_layer_add", project, {**layer.model_dump(), "file": layer.file})


@mcp.tool(annotations=WRITES)
async def ae_layer_set(
        project: Project, comp: Comp, layer: models.Layer,
        name: Annotated[str | None, Field(description="New layer name.")] = None,
        enabled: Annotated[bool | None, Field(description="Video switch.")] = None,
        solo: Annotated[bool | None, Field(description="Solo switch.")] = None,
        shy: Annotated[bool | None, Field(description="Shy switch.")] = None,
        locked: Annotated[bool | None, Field(description="Lock switch.")] = None,
        label: Annotated[Annotated[int, Field(ge=0, le=16)] | None,
                         Field(description="Label color index, 0 to 16.")] = None,
        in_point: Annotated[float | None, Field(description="In point, comp seconds.")] = None,
        out_point: Annotated[float | None, Field(description="Out point, comp seconds.")] = None,
        start_time: Annotated[float | None, Field(description="Start time, comp seconds.")] = None,
        stretch: Annotated[Annotated[float, Field(ge=-9900, le=9900)] | None,
                           Field(description="Time stretch in percent; negative reverses, 0 is refused.")] = None,
        blend_mode: Annotated[str | None, Field(description="Blending mode name.")] = None,
        parent: Annotated[models.Layer | None, Field(description="Parent layer, index or name.")] = None,
        no_parent: Annotated[bool, Field(description="Remove the parent.")] = False,
        three_d: Annotated[bool | None, Field(description="3D layer switch.")] = None,
        motion_blur: Annotated[bool | None, Field(description="Motion blur switch.")] = None,
        track_matte: Annotated[TrackMatte | Literal["none"] | None,
                               Field(description="Track matte layer and type; none removes it.")] = None,
        properties: Annotated[dict[str, Any] | None,
                              Field(description="Static values by property path, such as Transform/Opacity or "
                                                "Effects/Glow/Glow Threshold.")] = None) -> models.LayerChanged:
    """Change an existing layer: switches, label, timing, stretch, blend mode, parent, 3D, motion blur, track
    matte and static property values."""
    given(name=name, enabled=enabled, solo=solo, shy=shy, locked=locked, label=label, in_point=in_point,
          out_point=out_point, start_time=start_time, stretch=stretch, blend_mode=blend_mode, parent=parent,
          three_d=three_d, motion_blur=motion_blur, track_matte=track_matte, properties=properties,
          no_parent=True if no_parent else None)
    if stretch == 0:
        raise ValueError("stretch cannot be 0")
    if no_parent and parent is not None:
        raise ValueError("Give parent or no_parent, not both")
    args = {"comp": comp, "layer": layer, "name": name, "enabled": enabled, "solo": solo, "shy": shy,
            "locked": locked, "label": label, "in_point": in_point, "out_point": out_point,
            "start_time": start_time, "stretch": stretch, "blend_mode": blend_mode, "parent": parent,
            "no_parent": no_parent, "three_d": three_d, "motion_blur": motion_blur,
            "track_matte": track_matte.model_dump() if isinstance(track_matte, TrackMatte) else track_matte,
            "properties": properties or {}}
    return await scene("ae_layer_set", project, args)


@mcp.tool(annotations=DESTRUCTIVE)
async def ae_layer_edit(
        project: Project, comp: Comp,
        layers: Annotated[list[models.Layer], Field(min_length=1, description="Layers to edit, by index or "
                                                                              "name.")],
        action: Annotated[Literal["duplicate", "delete", "reorder", "split", "precompose"],
                          Field(description="What to do with the layers.")],
        time: Annotated[Annotated[float, Field(ge=0)] | None, Field(description="Split time, comp "
                                                                               "seconds.")] = None,
        move_to: Annotated[Literal["top", "bottom"] | Annotated[int, Field(ge=1)] | None,
                           Field(description="Reorder target: top, bottom or a 1-based index.")] = None,
        name: Annotated[str | None, Field(description="Precompose comp name, or the name of a single "
                                                      "duplicate.")] = None) -> models.LayersEdited:
    """Duplicate, delete, reorder, split or precompose layers; precompose moves all attributes."""
    if action == "split" and time is None:
        raise ValueError("split needs a time")
    if action == "reorder" and move_to is None:
        raise ValueError("reorder needs move_to")
    if action == "precompose" and not name:
        raise ValueError("precompose needs a name")
    args = {"comp": comp, "layers": layers, "action": action, "time": time, "move_to": move_to, "name": name}
    return await scene("ae_layer_edit", project, args)


@mcp.tool(annotations=WRITES)
async def ae_text_set(
        project: Project, comp: Comp, layer: models.Layer,
        text: Annotated[str | None, Field(description="New source text.")] = None,
        font: Annotated[str | None, Field(description="PostScript font name, as ae_fonts lists it.")] = None,
        size: Annotated[Annotated[float, Field(gt=0)] | None, Field(description="Font size in pixels.")] = None,
        fill: Annotated[Color | None, Field(description="Fill color, RGB 0 to 1.")] = None,
        stroke: Annotated[Color | None, Field(description="Stroke color, RGB 0 to 1.")] = None,
        stroke_width: Annotated[Annotated[float, Field(ge=0)] | None,
                                Field(description="Stroke width in pixels.")] = None,
        tracking: Annotated[float | None, Field(description="Tracking in thousandths of an em.")] = None,
        leading: Annotated[float | None, Field(description="Line spacing in pixels.")] = None,
        justification: Annotated[Literal["left", "center", "right", "full"] | None,
                                 Field(description="Paragraph alignment.")] = None,
        box: Annotated[Annotated[list[float], Field(min_length=2, max_length=2)] | None,
                       Field(description="Paragraph box size [width, height] in pixels.")] = None
) -> models.TextChanged:
    """Replace the source text and/or style of an existing text layer; its animators and keyframes stay."""
    style = {"text": text, "font": font, "size": size, "fill": fill, "stroke": stroke, "stroke_width": stroke_width,
             "tracking": tracking, "leading": leading, "justification": justification, "box": box}
    given(**style)
    return await scene("ae_text_set", project, {"comp": comp, "layer": layer, **style})


@mcp.tool(annotations=WRITES)
async def ae_shape_add(
        project: Project, comp: Comp,
        shape: Annotated[ShapeSpec, Field(description="Rect, ellipse, polystar or bezier path.")],
        name: Annotated[str, Field(description="Name of a new shape layer.")] = "Shape",
        layer: Annotated[models.Layer | None, Field(description="Existing shape layer to add the group "
                                                                "to.")] = None,
        group_name: Annotated[str, Field(description="Name of the shape group.")] = "Group",
        fill: Annotated[Fill | None, Field(description="Solid fill.")] = None,
        stroke: Annotated[Stroke | None, Field(description="Solid stroke.")] = None,
        gradient_fill: Annotated[Gradient | None, Field(description="Gradient fill with default stops.")] = None,
        gradient_stroke: Annotated[Gradient | None, Field(description="Gradient stroke with default "
                                                                      "stops.")] = None,
        operators: Annotated[list[Operator], Field(description="Trim, round corners, offset, wiggle, merge and "
                                                               "repeater operators.")] = [],
        transform: Annotated[GroupTransform | None, Field(description="Group transform.")] = None
) -> models.ShapeAdded:
    """Add a shape layer, or a group on an existing shape layer: the path, operators, paint and finally
    repeaters. A new layer sits at the comp origin, so positions are comp pixels. Gradient color stops cannot
    be set from scripts; a gradient takes After Effects' default stops."""
    spec = shape.model_dump()
    if shape.kind == "path":
        spec = {**spec, **shape.path.model_dump()}
    grad = {"gradient_fill": gradient_fill, "gradient_stroke": gradient_stroke}
    args = {"comp": comp, "layer": layer, "name": name, "group_name": group_name, "shape": spec,
            "fill": fill.model_dump() if fill else None, "stroke": stroke.model_dump() if stroke else None,
            **{k: v.model_dump() if v else None for k, v in grad.items()},
            "operators": [o.model_dump() for o in operators],
            "transform": (transform or GroupTransform()).model_dump()}
    return await scene("ae_shape_add", project, args)


@mcp.tool(annotations=WRITES)
async def ae_mask(
        project: Project, comp: Comp, layer: models.Layer,
        shape: Annotated[MaskShape | None, Field(description="Rect, ellipse or points path.")] = None,
        mask: Annotated[models.Layer | None, Field(description="Existing mask to change, by index or "
                                                               "name.")] = None,
        name: Annotated[str | None, Field(description="Mask name.")] = None,
        mode: Annotated[Literal["none", "add", "subtract", "intersect", "lighten", "darken", "difference"] | None,
                        Field(description="Mask mode.")] = None,
        feather: Annotated[models.Point | None, Field(description="Feather [x, y] in pixels.")] = None,
        expansion: Annotated[float | None, Field(description="Expansion in pixels.")] = None,
        opacity: Annotated[Annotated[float, Field(ge=0, le=100)] | None,
                           Field(description="Mask opacity in percent.")] = None,
        invert: Annotated[bool | None, Field(description="Invert the mask.")] = None,
        path_keys: Annotated[list[MaskKey], Field(description="Keyframed path as [{time, shape}].")] = []
) -> models.MaskSet:
    """Add a mask to a layer, or change an existing one: path, mode, feather, expansion, opacity, invert and a
    keyframed path."""
    if mask is None and shape is None and not path_keys:
        raise ValueError("A new mask needs a shape or path_keys")
    given(shape=shape, name=name, mode=mode, feather=feather, expansion=expansion, opacity=opacity, invert=invert,
          path_keys=path_keys or None)
    args = {"comp": comp, "layer": layer, "mask": mask, "name": name, "mode": mode, "feather": feather,
            "expansion": expansion, "opacity": opacity, "invert": invert,
            "shape": edit.mask_shape(shape) if shape else None,
            "path_keys": [{"time": k.time, "shape": edit.mask_shape(k.shape)} for k in path_keys]}
    return await scene("ae_mask", project, args)


@mcp.tool(annotations=WRITES)
async def ae_camera(
        project: Project, comp: Comp,
        camera: Annotated[CameraSpec | None, Field(description="Camera to add or change.")] = None,
        rig: Annotated[bool, Field(description="Parent the camera to an orbit null at its point of "
                                               "interest.")] = False,
        light: Annotated[LightSpec | None, Field(description="Light to add or change.")] = None
) -> models.CameraSet:
    """Add or change a one- or two-node camera (position, point of interest, zoom or focal length, depth of field, focus distance, aperture, blur level), optionally parented to an orbit null at its point of interest (`rig`), and/or a light (type, intensity, color, cone angle and feather, shadows)."""
    if camera is None and light is None:
        raise ValueError("Give a camera or a light")
    if rig and camera is None:
        raise ValueError("rig needs a camera")
    return await scene("ae_camera", project, {"comp": comp, "rig": rig, "camera": camera.model_dump() if camera else None,
                                              "light": light.model_dump() if light else None})


@mcp.tool(annotations=WRITES)
async def ae_material(project: Project, comp: Comp, layer: models.Layer,
                      material: Annotated[models.Material, Field(description="Material options to set.")]
                      ) -> models.Materialed:
    """Set a 3D layer's material options: casts shadows (off, on, only), accepts shadows and lights, light transmission, ambient, diffuse, specular, shininess, metal, reflection, glossiness, fresnel, transparency, rolloff, index of refraction. Refuses 2D layers; the report lists every option after the change."""
    values = {k: v for k, v in material.model_dump().items() if v is not None}
    if not values:
        raise ValueError("Give at least one material option")
    return await scene("ae_material", project, {"comp": comp, "layer": layer, "values": values})


@mcp.tool(annotations=WRITES)
async def ae_markers(
        project: Project, comp: Comp,
        layer: Annotated[models.Layer | None, Field(description="Set this layer's markers instead of the "
                                                                "comp's.")] = None,
        markers: Annotated[list[MarkerSpec], Field(max_length=host.MAX_MARKERS,
                                                   description="Markers with comment, duration and "
                                                               "chapter.")] = [],
        grid: Annotated[BeatGrid | None, Field(description="One marker per beat from bpm and beats per "
                                                           "bar.")] = None,
        clear: Annotated[bool, Field(description="Remove the existing markers first.")] = False
) -> models.MarkerList:
    """Set comp or layer markers and/or a beat grid. A call sets at most 5000 markers."""
    if not markers and grid is None:
        raise ValueError("Give markers or a beat grid")
    if grid is not None and grid.end <= grid.start:
        raise ValueError("The beat grid end must be after start")
    listed = [m.model_dump() for m in markers]
    if grid is not None:
        listed += edit.beat_grid(grid.bpm, grid.beats_per_bar, grid.start, grid.end)
    if len(listed) > host.MAX_MARKERS:
        raise ValueError(f"{len(listed)} markers in one call; the limit is {host.MAX_MARKERS}")
    return await scene("ae_markers", project, {"comp": comp, "layer": layer, "markers": listed, "clear": clear})
