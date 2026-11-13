"""Comps and layers: create, change, text, shapes, masks, cameras, materials and markers."""

from typing import Annotated, Any, Literal

from cavi_mcp_core.server import WRITES
from pydantic import Field

from .. import edit, host, models
from ..app import given, mcp, scene
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


@mcp.tool(annotations=WRITES)
async def ae_comp_new(project: str, name: str, width: Annotated[int, Field(ge=4, le=30000)],
                      height: Annotated[int, Field(ge=4, le=30000)],
                      duration: Annotated[float, Field(gt=0, le=10800)],
                      fps: Annotated[float, Field(gt=0, le=240)] = 30, background: Color = [0, 0, 0],
                      renderer: str | None = None, replace: bool = False) -> models.CompNew:
    """Create a comp; replace removes an existing comp of that name. renderer: ADBE Advanced 3d, ADBE Calder, ADBE Ernst."""
    return await scene("ae_comp_new", project, {"name": name, "width": width, "height": height,
                                                "duration": duration, "fps": fps, "background": background,
                                                "renderer": renderer, "replace": replace})


@mcp.tool(annotations=WRITES)
async def ae_comp_set(project: str, comp: str, name: str | None = None,
                      width: Annotated[int, Field(ge=4, le=30000)] | None = None,
                      height: Annotated[int, Field(ge=4, le=30000)] | None = None,
                      duration: Annotated[float, Field(gt=0, le=10800)] | None = None,
                      fps: Annotated[float, Field(gt=0, le=240)] | None = None,
                      work_area: Annotated[list[float], Field(min_length=2, max_length=2)] | None = None,
                      background: Color | None = None, renderer: str | None = None,
                      motion_blur: bool | None = None, frame_blending: bool | None = None,
                      duplicate_as: str | None = None) -> models.CompChanged:
    """Change a comp's name, size, fps, duration, work area [start, duration], background, renderer and motion blur and frame blending switches. duplicate_as copies the comp first and changes the copy."""
    given(name=name, width=width, height=height, duration=duration, fps=fps, work_area=work_area,
          background=background, renderer=renderer, motion_blur=motion_blur, frame_blending=frame_blending,
          duplicate_as=duplicate_as)
    args = {"comp": comp, "name": name, "width": width, "height": height, "duration": duration, "fps": fps,
            "work_area": work_area, "background": background, "renderer": renderer, "motion_blur": motion_blur,
            "frame_blending": frame_blending, "duplicate_as": duplicate_as}
    return await scene("ae_comp_set", project, args)


@mcp.tool(annotations=WRITES)
async def ae_layer_add(project: str, layer: LayerSpec) -> models.LayerAdded:
    """Add a solid, text, footage, 3D model (.glb, .gltf, .obj; Advanced 3D comps only), nested comp (`source`), rectangle, null, camera, light (point, spot, parallel, ambient, environment) or adjustment layer with transform, 3D, timing, parent, blend mode and matte."""
    if layer.kind == "comp" and not layer.source:
        raise ValueError("A comp layer needs source, the name of the comp to nest")
    if layer.kind in ("footage", "model"):
        path = host.absolute(layer.file or "")
        if layer.kind == "model" and path.suffix.lower() not in (".glb", ".gltf", ".obj"):
            raise ValueError("A 3D model file is .glb, .gltf or .obj")
    return await scene("ae_layer_add", project, {**layer.model_dump(), "file": layer.file})


@mcp.tool(annotations=WRITES)
async def ae_layer_set(project: str, comp: str, layer: models.Layer, name: str | None = None,
                       enabled: bool | None = None, solo: bool | None = None, shy: bool | None = None,
                       locked: bool | None = None, label: Annotated[int, Field(ge=0, le=16)] | None = None,
                       in_point: float | None = None, out_point: float | None = None,
                       start_time: float | None = None, stretch: Annotated[float, Field(ge=-9900, le=9900)] | None = None,
                       blend_mode: str | None = None, parent: models.Layer | None = None, no_parent: bool = False,
                       three_d: bool | None = None, motion_blur: bool | None = None,
                       track_matte: TrackMatte | Literal["none"] | None = None,
                       properties: dict[str, Any] | None = None) -> models.LayerChanged:
    """Change an existing layer: switches, label, timing, stretch percent, blend mode, parent, 3D, motion blur, track matte. `properties` sets static values by path ("position", "Transform/Opacity", "Geometry Options/Extrusion Depth", "Effects/Glow/Glow Threshold" or match names)."""
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


@mcp.tool(annotations=WRITES)
async def ae_layer_edit(project: str, comp: str, layers: Annotated[list[models.Layer], Field(min_length=1)],
                        action: Literal["duplicate", "delete", "reorder", "split", "precompose"],
                        time: Annotated[float, Field(ge=0)] | None = None,
                        move_to: Literal["top", "bottom"] | Annotated[int, Field(ge=1)] | None = None,
                        name: str | None = None) -> models.LayersEdited:
    """Duplicate (name renames a single copy), delete, reorder (move_to top, bottom or a 1-based index), split at `time`, or precompose the layers into a comp called `name` with all attributes moved."""
    if action == "split" and time is None:
        raise ValueError("split needs a time")
    if action == "reorder" and move_to is None:
        raise ValueError("reorder needs move_to")
    if action == "precompose" and not name:
        raise ValueError("precompose needs a name")
    args = {"comp": comp, "layers": layers, "action": action, "time": time, "move_to": move_to, "name": name}
    return await scene("ae_layer_edit", project, args)


@mcp.tool(annotations=WRITES)
async def ae_text_set(project: str, comp: str, layer: models.Layer, text: str | None = None,
                      font: str | None = None, size: Annotated[float, Field(gt=0)] | None = None,
                      fill: Color | None = None, stroke: Color | None = None,
                      stroke_width: Annotated[float, Field(ge=0)] | None = None, tracking: float | None = None,
                      leading: float | None = None,
                      justification: Literal["left", "center", "right", "full"] | None = None,
                      box: Annotated[list[float], Field(min_length=2, max_length=2)] | None = None
                      ) -> models.TextChanged:
    """Replace the source text and/or style of an existing text layer; its animators and keyframes stay."""
    style = {"text": text, "font": font, "size": size, "fill": fill, "stroke": stroke, "stroke_width": stroke_width,
             "tracking": tracking, "leading": leading, "justification": justification, "box": box}
    given(**style)
    return await scene("ae_text_set", project, {"comp": comp, "layer": layer, **style})


@mcp.tool(annotations=WRITES)
async def ae_shape_add(project: str, comp: str, shape: ShapeSpec, name: str = "Shape", layer: models.Layer | None = None,
                       group_name: str = "Group", fill: Fill | None = None, stroke: Stroke | None = None,
                       gradient_fill: Gradient | None = None, gradient_stroke: Gradient | None = None,
                       operators: list[Operator] = [], transform: GroupTransform | None = None) -> models.ShapeAdded:
    """Add a shape layer, or a group on the existing shape `layer`: a rect, ellipse, polystar or bezier path, then operators (trim, round_corners, offset, wiggle, merge), paint and finally repeaters, with a group transform; a new layer sits at the comp origin, so positions are comp pixels. Gradient color stops cannot be set from scripts (note 19): a gradient takes After Effects' default stops."""
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
async def ae_mask(project: str, comp: str, layer: models.Layer, shape: MaskShape | None = None,
                  mask: models.Layer | None = None, name: str | None = None,
                  mode: Literal["none", "add", "subtract", "intersect", "lighten", "darken", "difference"] | None = None,
                  feather: models.Point | None = None, expansion: float | None = None,
                  opacity: Annotated[float, Field(ge=0, le=100)] | None = None, invert: bool | None = None,
                  path_keys: list[MaskKey] = []) -> models.MaskSet:
    """Add a mask to a layer, or change the existing `mask` (index or name): rect, ellipse or points path, mode, feather, expansion, opacity, invert, and a keyframed path as [{time, shape}]."""
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
async def ae_camera(project: str, comp: str, camera: CameraSpec | None = None, rig: bool = False,
                    light: LightSpec | None = None) -> models.CameraSet:
    """Add or change a one- or two-node camera (position, point of interest, zoom or focal length, depth of field, focus distance, aperture, blur level), optionally parented to an orbit null at its point of interest (`rig`), and/or a light (type, intensity, color, cone angle and feather, shadows)."""
    if camera is None and light is None:
        raise ValueError("Give a camera or a light")
    if rig and camera is None:
        raise ValueError("rig needs a camera")
    return await scene("ae_camera", project, {"comp": comp, "rig": rig, "camera": camera.model_dump() if camera else None,
                                              "light": light.model_dump() if light else None})


@mcp.tool(annotations=WRITES)
async def ae_material(project: str, comp: str, layer: models.Layer, material: models.Material) -> models.Materialed:
    """Set a 3D layer's material options: casts shadows (off, on, only), accepts shadows and lights, light transmission, ambient, diffuse, specular, shininess, metal, reflection, glossiness, fresnel, transparency, rolloff, index of refraction. Refuses 2D layers; the report lists every option after the change."""
    values = {k: v for k, v in material.model_dump().items() if v is not None}
    if not values:
        raise ValueError("Give at least one material option")
    return await scene("ae_material", project, {"comp": comp, "layer": layer, "values": values})


@mcp.tool(annotations=WRITES)
async def ae_markers(project: str, comp: str, layer: models.Layer | None = None,
                     markers: Annotated[list[MarkerSpec], Field(max_length=host.MAX_MARKERS)] = [],
                     grid: BeatGrid | None = None, clear: bool = False) -> models.MarkerList:
    """Set comp markers (or `layer` markers) with comment, duration and chapter, and/or a beat grid from bpm and beats per bar. clear removes the existing ones first. A call sets at most 5000 markers."""
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
