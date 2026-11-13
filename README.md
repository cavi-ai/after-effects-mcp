# After Effects MCP

MCP server for headless Adobe After Effects on macOS. It launches After Effects without its UI,
runs ExtendScript files with arguments and returns their JSON reports, and renders saved projects
with `aerender`, checking every output movie's frame count.

## Install

Requires macOS, After Effects 2026 or later, FFmpeg (`ffprobe`) and Python 3.15.

```sh
uv sync
uv run cavi-after-effects-mcp
```

The server speaks MCP over stdio. Client configuration:

```json
{"mcpServers": {"after-effects": {"command": "uv", "args": ["--directory", "/path/to/after-effects-mcp", "run", "cavi-after-effects-mcp"]}}}
```

## Tools

| Tool | What it does |
|---|---|
| `ae_status` | Installed After Effects, its version, and running headless and UI pids. |
| `ae_launch` | Starts one headless instance (`open -n -g -a ... --args -noui`) and waits until it answers `app.project.numItems`. Refuses while After Effects runs with its UI. |
| `ae_script` | Runs a `.jsx` file in the headless instance and returns its report (below). |
| `ae_render_queue` | Runs `aerender` on a saved project's render queue, then checks each declared output movie's frame count with `ffprobe`. A movie that is missing, older than the render or short of frames is deleted and rendered once more on its own with `-comp`. |
| `after_effects_render` | Renders one declared AEP composition range to a new PNG sequence and pins it as an animation media receipt. Paths are relative to `CAVI_ADOBE_WORKSPACE`. |
| `ae_inspect` | Lists project items (comps with size, duration, fps, layer count and renderer; footage with file and missing flag; folders), one comp's layers (type, in/out, 3D, parent, effects by matchName, keyframed properties) or the render queue (status, render flag, label, output file, templates). |
| `ae_comp_new` | Creates a comp with size, duration, fps, background color and renderer; `replace` removes an existing comp of that name. |
| `ae_layer_add` | Adds a solid, text (font, size, tracking, fill, stroke, justification, paragraph box), footage (imported on first use), 3D model (`.glb`, `.gltf`, `.obj`; Advanced 3D comps, note 31), nested comp (`source`), rectangle shape, null, camera, light (point, spot, parallel, ambient, environment) or adjustment layer with transform, 3D, timing, parent, blend mode and track matte. |
| `ae_keyframes` | Sets keyframes `[{time, value}]` on a property path with ease in/out or interpolation type, and/or an expression or an expression preset (wiggle, loop cycle or pingpong, inertial bounce, time-based rotation). Without keyframes, `easy_ease`, `ease`, `hold`, `spatial` (bezier or linear) and `rove` restyle the existing keys; `remove` drops all keys or those in a time range. |
| `ae_effect_add` | Adds an effect by matchName and sets its parameters. |
| `ae_text_animator` | Adds a text animator whose range selector opens over characters, words or lines (opacity, position, tracking, scale, blur, rotation), or `animators` with fill and stroke color, stroke width, skew, character offset and per-character 3D rotation and several selectors per animator: range (shape, ease high and low, based on characters, words or lines), wiggly and expression. `path` sets text on a path from a layer mask with first and last margin (note 28). |
| `ae_footage_replace` | Replaces a footage item's source file in place (`item.replace`); every layer using the item updates. |
| `ae_render_queue_set` | Adds comps to the render queue with render settings and output module templates, file, time span (`work_area`, `comp` or `{start, duration}`) and the output settings scripts can set (resize and quality, crop, audio on/off/auto, sample rate, channels, bit depth); sets render on/off and comp label, duplicates or removes entries, sets render settings (quality, resolution, proxy use, effects, motion blur, frame blending, frame rate; note 32), and lists the queue with each entry's span, output and render settings. `locked` is render off with label 0. Format, channels, depth and color are refused (note 22). |
| `ae_presets` | Lists render settings templates, output module templates (read from a render queue item) and installed `.ffx` animation presets by category and name; `filter` narrows the presets. |
| `ae_preset_apply` | Refuses: `layer.applyPreset` exits headless After Effects (note 12). It still resolves the preset name or path first. |
| `ae_transitions` | Lists the transition kinds and whether this install has each effect. |
| `ae_transition` | Keys Transition Completion of a wipe or dissolve effect, an opacity cross-fade or a dip to a color, between two layers (starting at the second layer's in point) or on one layer's in or out point; duration in seconds or frames. |
| `ae_project` | Opens a saved `.aep` in the headless instance (`app.open`), saves it, saves it under a new path (`overwrite` to replace a file), or reports the open project's path and item counts. Open refuses while the open project has unsaved changes unless `discard`. `reduce` (keep `comps` and what they use), `remove_unused` and `consolidate` rewrite the open project, or save to `path` and leave the file alone; they return the removed count. |
| `ae_layer_set` | Changes an existing layer found by comp and name or index: name, enabled, solo, shy, locked, label, in/out, start time, stretch percent, blend mode, parent (or `no_parent`), 3D, motion blur and track matte (or `none`). `properties` sets static values on any property path (transform, Geometry and Material options, light and camera options, effect parameters) and returns the values read back. |
| `ae_text_set` | Replaces the source text and style (font, size, fill, stroke, stroke width, tracking, leading, justification, paragraph box) of an existing text layer; its animators and keyframes stay. |
| `ae_layer_edit` | Duplicates, deletes, reorders (top, bottom or an index), splits at a time, or precomposes a list of layers into a named comp with all attributes moved. |
| `ae_comp_set` | Sets a comp's name, size, fps, duration, work area, background, renderer and the motion blur and frame blending switches; `duplicate_as` copies the comp first and changes the copy. |
| `ae_import` | Imports files, an image sequence (from its first frame) or a layered PSD/AI as a comp into a named project folder, then sets alpha mode, conform frame rate and loop count. |
| `ae_markers` | Sets comp or layer markers with comment, duration and chapter, and a beat grid from bpm and beats per bar (comment `bar.beat`, chapter `Bar n` on each downbeat); `clear` removes the existing ones. |
| `ae_frame` | Renders the frame at each given time of a comp to PNG through `aerender` and a temporary render queue entry that is removed afterwards; returns the file paths. The comp background color is composited in; `alpha` keeps transparency. |
| `ae_shape_add` | Adds a shape layer, or a group on an existing shape layer: rectangle (roundness), ellipse, polystar (star or polygon) or bezier path, with trim paths, round corners, offset paths, wiggle paths, merge paths, fill, stroke (cap, join, dashes), gradient fill and stroke (linear or radial), repeater and a group transform. |
| `ae_mask` | Adds a mask to a layer or changes an existing one (index or name): rect, ellipse or points path, mode, feather, expansion, opacity, invert and a keyframed path. |
| `ae_effects` | Lists the installed effects (`app.effects`) with category, display name and matchName; `filter` and `category` narrow them. |
| `ae_camera` | Adds or changes a one- or two-node camera (position, point of interest, zoom or focal length, depth of field, focus distance, aperture, blur level), optionally parented to an orbit null at its point of interest, and/or a light (type, intensity, color, cone angle and feather, shadows). |
| `ae_essential_graphics` | Adds layer properties (source text, color, slider or effect parameters, position) to a comp's Essential Graphics under a name, names the template, and lists the controls. |
| `ae_mogrt_export` | Refuses: headless After Effects writes no `.mogrt` (note 23). |
| `ae_template_render` | Opens a template `.aep`, sets text layers by name (text and style), replaces footage items by name, saves to `project`, and renders the named comps with `aerender` and frame checks. Other render queue entries are switched off. |
| `ae_collect` | Copies every used footage file into a folder, relinks each item there with `item.replace`, saves to `project`, and reports the counts and items still missing; solids and image sequences are skipped. |
| `ae_audio` | Sets an audio layer's Audio Levels in dB (static or keyed), fade in and out by duration (from -100 dB) and audio on or off. `convert_to_keyframes` refuses (note 25). |
| `ae_time` | Enables time remap with keys `[{time, source_time}]`, freezes a frame at a source time, reverses a layer (stretch -100, keeping its earlier edge) and sets frame blending to none, mix or pixel motion (the comp switch is turned on). |
| `ae_controls` | Adds named Expression Controls (slider, angle, point, 3D point, color, checkbox, layer, dropdown) to a layer, sets their values, and links properties on any layer to a control with a generated expression, optionally scaled or offset (note 29). |
| `ae_project_settings` | Sets bits per channel (8, 16, 32), working color space, linear blending, display start frame, frames or timecode display, frame count start, expression engine and GPU acceleration (metal or software); reports every setting (note 30). |
| `ae_sequence_layers` | Places existing layers and footage files end to end from a start time with an overlap, earlier items on top, and applies an `ae_transition` kind (default crossfade) at every join. |
| `ae_essential_override` | Overrides the Essential Properties of one nested-comp layer by name (a string sets source text), so two instances of one comp carry different values (note 33). |

`ae_render_queue_set` takes template names exactly as `ae_presets` lists them and refuses others. `clear`
removes only existing entries of the comps named in `add`.

`ae_script`, `ae_render_queue` and the scene tools take absolute paths. The scene tools run packaged
templates in `src/cavi_after_effects_mcp/jsx/` through the script contract below, so each returns the
template's report and fails on its `errors`. They share the open project and save it to `project`.
Property paths are `position`, `scale`, `rotation`, `anchor`, `opacity` or match-name paths joined
with `/`.

## Script contract

`ae_script(script, project, args)` defines the global `CAVI_ARGS` (the `args` object), then runs
`script`. The script sets its report with `caviReport(object)`, which stores the JSON as the
comment of the project folder `cavi-report` and saves the open project to `project`. A script that
never calls `caviReport` reports `{"value": <its last value>}`. A report with a non-empty `errors`
list fails the call with those errors.

Before running the script the runner compiles its text with `new Function` inside `try`, so a
syntax error comes back as a message with its line instead of aborting the script call. Runtime
exceptions the script does not catch also come back as messages with their line.

```js
var comp = app.project.items.addComp("Title", 1920, 1080, 1, 2, 30);
caviReport({comp: comp.name, frames: 60, errors: []});
```

`ae_render_queue(project, outputs)` takes `outputs` as `[{comp, file, frames}]`; the render
settings and output module templates for a second render default to `Best Settings` and
`High Quality`.

The `after_effects_render` recipe:

```json
{
  "version": 1, "name": "SpellLoop", "project": "effects/spell.aep",
  "dependencies": ["effects/source.psd"], "composition": "SpellLoop", "start": 0, "end": 23,
  "fps": {"numerator": 24, "denominator": 1}, "loop": true, "alpha": "straight",
  "output_module": "Game RGBA PNG"
}
```

Start and end are inclusive. The output module must be an existing straight-alpha RGBA PNG
template. Exactly one After Effects `aerender` must be installed. The render runs with a
300-second, 8 GiB process-group and 512 MiB output limit.

## Behavior notes

Measured with After Effects 2026 on macOS.

1. Headless After Effects (`-noui`) has no BridgeTalk. `DoScript` returns only `0` (success) or
   `1` (any failure), and scripts cannot write files. Reports therefore travel inside the saved
   project.
2. Headless After Effects starts with a project open, and `app.newProject()` crashes it. Scripts
   reuse the open project: remove its items and render queue entries instead.
3. `$.evalFile` of a file with a syntax error aborts `DoScript` before any `catch` runs.
   ExtendScript is ES3, so Java-era reserved words such as `final` are syntax errors there while
   `node --check` accepts them. The runner's compile check turns these into messages.
4. With the comp renderer set to Advanced 3D (`ADBE Calder`), adding an effect to a 3D layer, or
   setting `layer.motionBlur` on a 3D shape layer, aborts the script uncatchably. Extrusion depth,
   lights, cameras and rotation work. Renderers listed: `ADBE Advanced 3d` (Classic 3D),
   `ADBE Calder` (Advanced 3D), `ADBE Ernst` (Cinema 4D).
5. A full-frame Glow (`ADBE Glo2`) adjustment lifts dark blues: a dark navy solid gains about +50
   in the blue channel at threshold 70, in 8 and 16 bpc.
6. `ae_effect_add` on a 3D layer and `ae_layer_add` with `motion_blur` on a 3D rectangle shape are
   refused with a message, before the call that would abort After Effects, while the comp renderer
   is `ADBE Calder`.
7. Every script call watches the headless pid: if After Effects exits during the call it fails at
   once with that message instead of waiting for the timeout, and a call with no headless instance
   fails asking for `ae_launch`.
8. `output_module` templates seen: `High Quality`, `High Quality with Alpha`, `Lossless`,
   `Lossless with Alpha`, `Alpha Only`, `H.264 - Match Render Settings - 15 Mbps`, `Photoshop`,
   `TIFF Sequence with Alpha`. Render queue status names are `QUEUED`, `UNQUEUED`, `DONE` and so on.
9. `ae_inspect` reports cameras and lights as 3D although their `threeDLayer` reads false.
10. Completion runs 0 to 100 on the stock transition effects and 0 to 1 on some CC ones (CC Twister).
    CC Line Sweep is not installed here.
11. `aerender` skips a queue entry with render off, and renders the others in the saved project, so a
    queue holding other comps renders them too.
12. `layer.applyPreset` of a `.ffx` animation preset exits the headless instance within two seconds
    (measured with `3D Basic Position Z Cascade In` and `Center Spiral In`); the call fails with the
    exited-during-the-call error of note 7.
13. `aerender` can crash mid-queue and still exit 0, so every output's frame count is checked.
   A ProRes movie with a timecode track lists `nb_frames` twice in `ffprobe`; the first value is
   the video stream's.
14. After Effects opens a saved project headless with `app.open`, and `app.project.dirty` is readable. A call that
    fails saves its report into the open project, so `ae_project` sends refusals to a temporary project and a
    refused open leaves the project on disk untouched.
15. An output module's `Format` is read-only from scripts and no PNG template ships, so `ae_frame` renders the
    `TIFF Sequence with Alpha` template and converts each frame with `sips`. The frames carry alpha, so `ae_frame`
    adds a solid of the comp's background color at the bottom for the render and removes it afterwards unless `alpha`.
16. A sequence output file with no `[#####]` in its name gets the frame number appended after the extension
    (`f0_.tif00015`); `ae_frame` names its files `f<n>_[#####].tif`.
17. A locked layer refuses every other change, so `ae_layer_set`
    unlocks first and locks last. `setTrackMatte` switches the matte layer's video off (`enabled` false).
18. `conformFrameRate` is refused for a still, `boxTextSize` for point text and `setValue` for a keyed property;
    the calls fail with After Effects' message.
19. A shape gradient's color stops (`ADBE Vector Grad Colors`) have no value type, so scripts can neither read nor
    set them: `ae_shape_add` gradients take the default stops (white to black) and set type, start and end.
20. A new shape layer sits at the comp center; `ae_shape_add` moves it to the origin so group positions are comp
    pixels. Wiggle Paths is `ADBE Vector Filter - Roughen`. Stroke dashes exist only after `addProperty` on the
    Dashes group. A camera's point of interest is `ADBE Anchor Point`.
21. Parenting a camera to an orbit null keeps its view: its position reads relative to the null afterwards.
22. `OutputModule.setSettings` refuses `Format`, `Channels`, `Depth` and `Color` as read-only; alpha, depth and color
    come from the template (`High Quality with Alpha` gives `RGB + Alpha`). It accepts `Resize` with `Resize to`
    `[w, h]`, `Resize Quality` `Low` or `High` (not `Medium`), `Crop` with `Crop Top/Left/Bottom/Right`,
    `Output Audio` `On`, `Off` or `Auto`, `Audio Sample Rate`, `Audio Channels` and `Audio Bit Depth` (`16 Bit`).
    A render of one entry with resize, a time span and audio on gave a 320x180 ProRes 4444 movie with alpha,
    30 frames and a mono 44.1 kHz audio stream; an entry with crop and audio off gave 620x340 with no alpha and no
    audio stream.
23. `comp.exportAsMotionGraphicsTemplate` returns true in headless After Effects and writes no file: it creates an
    empty folder at the given path. `addToMotionGraphicsTemplateAs`, `motionGraphicsTemplateName` and the controller
    list work, so `ae_essential_graphics` prepares the comp and the `.mogrt` has to be exported from a window.
24. The scripting method is `app.project.consolidateFootage` (there is no `consolidateAllFootage`);
    `reduceProject` takes an array of comps and returns the number of removed items.
25. `app.findMenuCommandId("Convert Audio to Keyframes")` returns 4218, and `app.executeCommand(4218)` on a selected
    audio layer exits the headless instance (measured twice), so `ae_audio` refuses it.
26. Audio Levels fades and levels are measured with `volumedetect` on a rendered movie with audio on: a 440 Hz tone at
    -21.1 dB gave -27.1 dB in the middle at a -6 dB level, -82.5 dB in the first and last quarter second of a
    0.5 s fade in and out, and -91 dB with the layer's audio off.
27. Removing every key of Time Remap hides the property (`setValueAtTime` then fails), so new keys are set first and the
    old ones dropped. `layer.frameBlending` is read-only; `frameBlendingType` sets the mode (4012 none, 4013 mix,
    4014 pixel motion). A reversed layer shows between its out and in points.
28. Text animator properties and selectors are added with `addProperty` on the animator's property group, and every
    property reference goes invalid once a sibling is added, so the animator is fetched by index each time. Match
    names: `ADBE Text Fill Color`, `ADBE Text Stroke Color`, `ADBE Text Stroke Width`, `ADBE Text Skew`,
    `ADBE Text Character Offset`, `ADBE Text Rotation X`/`Y`; selectors `ADBE Text Selector` (range),
    `ADBE Text Wiggly Selector` and `ADBE Text Expressible Selector` (the expression selector).
29. A dropdown Expression Control is `ADBE Dropdown Control`; `setPropertyParameters` rebuilds the effect, so it is
    fetched again from the end of the effect parade and renamed afterwards. Controls are told apart by their
    parameter name (Slider, Angle, Point, 3D Point, Color, Checkbox, Layer, Menu).
30. Every project setting above is settable, including 32 bits per channel with linear blending. A value other than
    8, 16 or 32 bits is refused by After Effects; an unknown working space name is silently stored as `None`, so
    `ae_project_settings` refuses names not in `listColorProfiles()`. `revision` and `numItems` are read-only. The
    GPU types CUDA, OpenCL, DirectX and Vulkan are not offered; metal and software set.
31. `.glb`, `.gltf` and `.obj` import as footage and `comp.layers.add` makes a 3D model layer (`ADBE 3D Model Layer`)
    in an Advanced 3D comp; other renderers are refused. `fit` (default on) sets the layer centered with scale
    `0.6 * comp height / (largest extent of sourceRectAtTime * sqrt(3))` percent; a 2-unit cube is 1024 px at 100%,
    so it gets 20.3% in a 360 px comp. `fit: false` keeps the raw import, which fills the frame. A model without
    normals renders flat gray whatever the lights; with normals an environment light alone shades the faces. An
    environment light is invisible itself, so a comp holding only one renders like an empty comp. The model layer's
    out point is set to the comp duration.
32. `RQItem.setSettings` accepts Quality (Wireframe, Draft, Best), Resolution (Full, Half, Third, Quarter), Proxy Use
    (Use No Proxies, Use Comp Proxies Only, Use All Proxies), Effects (All On, All Off, Current Settings), Motion
    Blur and Frame Blending (On for Checked Layers, Off for All Layers, Current Settings). `Frame Rate` itself is
    refused; setting the number `Use this frame rate` switches the mode. `RQItem.duplicate()` and `remove()` work.
    An aerender at half resolution and 12 fps wrote 160x90 at 12 fps with 24 frames.
33. A nested comp layer exposes `layer.essentialProperty` as a group named Essential Properties whose properties
    carry the names given in `ae_essential_graphics`; setting a text property takes a `TextDocument`.

## Development

```sh
uv sync --dev
uv run ruff check .
uv run pytest
```
