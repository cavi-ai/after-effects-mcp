# Building and animating

The examples work on one project, `/path/to/promo.aep`, whose comp `Main` holds a footage layer `Shot`, a text
layer `Title` and a solid `Card`. [Your first comp](first-comp.md) builds such a comp; the
[tool reference](../reference/tools.md) lists every parameter.

## Effects

`ae_effects` lists the installed effects with their match names. `ae_effect_add` adds one by match name and
sets its parameters by name; a menu takes its item text.

```json
{"tool": "ae_effects", "arguments": {"project": "/path/to/promo.aep", "filter": "glow"}}
```

```json
{"tool": "ae_effect_add", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Title",
 "match_name": "ADBE Glo2", "params": {"Glow Radius": 40}}}
```

## Layer switches, timing and parts

`ae_layer_set` changes switches, timing, parent, blend mode and track matte, and sets any static property by
its path. `ae_layer_parts` removes, turns on or off, or moves an effect, mask, shape group or text animator.

```json
{"tool": "ae_layer_set", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Title",
 "parent": "Card", "blend_mode": "add", "in_point": 1, "properties": {"Transform/Opacity": 80}}}
```

```json
{"tool": "ae_layer_parts", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Title",
 "edits": [{"path": "Effects/Glow", "action": "disable"}]}}
```

## Masks

`ae_mask` adds a rectangle, ellipse or point mask, or changes one by name, with mode, feather, expansion,
opacity and keyed paths. A box is `[x, y, width, height]`.

```json
{"tool": "ae_mask", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Shot",
 "shape": {"kind": "ellipse", "box": [460, 140, 1000, 800]}, "feather": [60, 60]}}
```

## Controls and expressions

`ae_controls` adds Expression Controls to a layer and links properties to them. `ae_keyframes` sets an
expression on any property, and `ae_expressions` lists a comp's expressions with their errors.

```json
{"tool": "ae_controls", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Card",
 "controls": [{"kind": "slider", "name": "Fade", "value": 60}],
 "links": [{"control": "Fade", "property": "Transform/Opacity", "layer": "Title"}]}}
```

```json
{"tool": "ae_keyframes", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Card",
 "property": "Transform/Position", "expression": "wiggle(2, 20)"}}
```

```json
{"tool": "ae_expressions", "arguments": {"project": "/path/to/promo.aep", "comp": "Main"}}
```

## Time

`ae_time` turns on time remapping with keys that map comp time to source time, freezes a frame, reverses a
layer or sets frame blending.

```json
{"tool": "ae_time", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Shot",
 "time_remap": true, "remap_keys": [{"time": 0, "source_time": 0}, {"time": 4, "source_time": 2}]}}
```

## Edits, transitions and markers

`ae_sequence_layers` places layers or footage files end to end, with a transition at each join.
`ae_transitions` lists the kinds this install has, and `ae_transition` adds one on a layer's in or out point
or between two layers.

```json
{"tool": "ae_sequence_layers", "arguments": {"project": "/path/to/promo.aep", "comp": "Main",
 "items": [{"file": "/path/to/a.mp4"}, {"file": "/path/to/b.mp4"}], "start": 4, "overlap": 0.5,
 "transition": {"kind": "crossfade"}}}
```

```json
{"tool": "ae_transition", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "kind": "linear_wipe",
 "layer": "Card", "edge": "in", "seconds": 0.5}}
```

`ae_markers` sets comp or layer markers, a beat grid, and markers at an audio file's onsets or a video file's
cuts.

```json
{"tool": "ae_markers", "arguments": {"project": "/path/to/promo.aep", "comp": "Main",
 "grid": {"bpm": 120, "end": 10}, "cuts": {"file": "/path/to/a.mp4", "offset": 4}}}
```

## 3D

`ae_layer_set` with `three_d` makes a layer 3D. `ae_camera` adds or changes a camera, optionally on an orbit
rig, and a light; `ae_material` sets a 3D layer's material options. Extruded text and shapes, parametric
meshes and environment lights are in the [tool reference](../reference/tools.md), and `.c4d` scenes in
[Rendering and the fallback](rendering.md).

```json
{"tool": "ae_layer_set", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Shot",
 "three_d": true}}
```

```json
{"tool": "ae_camera", "arguments": {"project": "/path/to/promo.aep", "comp": "Main",
 "camera": {"nodes": 2, "position": [960, 540, -1500], "point_of_interest": [960, 540, 0], "focal_length": 35},
 "rig": true, "light": {"type": "spot", "intensity": 120, "casts_shadows": true}}}
```

```json
{"tool": "ae_material", "arguments": {"project": "/path/to/promo.aep", "comp": "Main", "layer": "Shot",
 "material": {"casts_shadows": "on", "accepts_lights": true}}}
```

## Comp and project settings

`ae_comp_set` changes a comp's size, length, frame rate, work area, background, renderer, motion blur and frame
blending, or does so on a copy with `duplicate_as`. `ae_project_settings` sets bit depth, color space, time
display, expression engine and GPU mode.

```json
{"tool": "ae_comp_set", "arguments": {"project": "/path/to/promo.aep", "comp": "Main",
 "duplicate_as": "Main 9x16", "width": 1080, "height": 1920}}
```

```json
{"tool": "ae_project_settings", "arguments": {"project": "/path/to/promo.aep", "bits_per_channel": 16}}
```
