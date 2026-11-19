# Changelog

Versions come from git tags; a pull request adds its lines under Unreleased and never edits a version.

## Unreleased

### Added

- `ae_layer_add` `kind` `mesh` adds a parametric cube, sphere, plane, cylinder, cone or torus (`mesh_type`), sized
  by scale, in After Effects 26.3 or later; `ae_inspect` lists such layers as `mesh`.
- `ae_camera` `light` `source` sets the 2D layer whose image an environment light uses, and the result reports it.
- `ae_text_set` and `ae_template_render` `texts` set a paragraph box's `box_fit`, `box_align` and `box_inset`, and
  report `overflow` when the text does not fit its box; `ae_template_render` lists those layers.
- `ae_fonts` `used` lists the fonts the project's text uses, with `missing` and the layers that use each, and
  `ae_font_replace` replaces a font everywhere with an installed one.
- `ae_layer_set` and the tool reference name `Geometry Options/Extrusion Depth` and `Bevel Depth` for extruded 3D
  text and shapes.
- `ae_frame` returns its first `previews` frames (default 4) as PNG images at most 768 px on the long side,
  beside their paths.
- A menu property, such as an effect's popup or a Dropdown Menu Control, takes its item text in `ae_layer_set`
  `properties`, `ae_effect_add` `params`, `ae_controls` and `ae_keyframes`, and `ae_properties` lists its `items`
  and selected `text`.
- `ae_layer_edit` `copy` copies layers with their keyframes, effects and masks into `to_comp`.
- `ae_essential_graphics` makes a footage or comp layer a media replacement control when `property` is omitted,
  and `ae_essential_override` sets it from an absolute footage path or a comp name.
- `ae_markers` `cuts` adds a marker at each cut of a video file, found with FFmpeg's scene score.
- `ae_template_render` `variants` fills and renders a template once per variant in one call, each variant's
  `name` replacing `{name}` in `project` and the `renders` files.

### Changed

- `ae_layer_edit` and `ae_project` refuse an argument the action does not read, such as `time` for `delete` or
  `overwrite` for `open`, and name a missing one as `<name> is required for action=<action>`, through
  `cavi-mcp-core` `need` and `reject_foreign`.
- The documentation lists the server's error codes and links the `cavi-mcp-core` results and errors contract.
- The rendering guide covers `.c4d` layers and their Cineware settings.
- A Building and animating guide covers effects, layer switches and parts, masks, controls and expressions,
  time, edits and markers, 3D, and comp and project settings; the README and overview list every tool area.
- With After Effects running with its window, tools run in it instead of being refused as `AE_UI_RUNNING`; a call
  made while a dialog is open in it is refused as `AE_DIALOG_OPEN`. Every script runs inside a `catch`, so an
  error never opens a dialog in the window.
- The lock that runs one script at a time, the FFmpeg lookup and the `ae_frame` previews use `cavi-mcp-core` 0.1.7
  `lock.FileLock`, `apps.program` and `media.png_content`.

### Fixed

- A background render's job record is created once and readable only by its user, through `cavi-mcp-core`
  `journal.create_json`, and read back through `files.load_json`.
- `ae_template_render` with `texts` sets them instead of failing with `TypeError: undefined is not an object`, and
  each entry takes `ranges` as `ae_text_set` does.
- `ae_import` lists an imported `.aep` as `type` `project` with its `comps` instead of as footage with no size.
- `ae_frame` and `ae_export_frames` show a Cineware scene from the first frame instead of a black one.
- `ae_properties` with `path` reports each property's full path, such as `Layer/Effects/Cineware/Renderer`,
  instead of dropping the groups above the one read.
- A rendered MXF or Matroska movie counts its frames from its packets, since it keeps no frame count, instead of
  being reported short of its frames.
- The scratch folder of an aerender frame render or a fallback movie is removed even when it holds read-only
  folders, through `cavi-mcp-core` `workspace.remove_scratch`; what cannot be removed is reported as a warning.

## 0.2.0 - 2026-11-18

### Added

- `ae_project` `new` saves an empty project at a path.
- `ae_properties` `keyframes` lists each animated property's keys: time, value, in and out interpolation, temporal
  ease, and spatial tangents, continuity and roving.
- `ae_layer_set` sets collapse transformations, guide, auto-orient, quality, sampling and adjustment switches.
- `ae_comp_new` `footage` builds a comp from a video or still: its size, pixel aspect, duration and frame rate,
  with the file as layer 1.
- `ae_layer_parts` removes, switches on or off and moves a layer's effects, masks, shape groups and text animators
  by path.
- `ae_batch` runs typed write tools in order in one After Effects call with one save, and rolls every step back
  when one fails: six steps take 1.7 s instead of 10.2 s as six calls.
- `ae_markers` `onsets` adds a marker where the level of an audio or video file jumps, found with FFmpeg.
- `ae_text_set` `ranges` styles character ranges: font, size, fill, stroke, tracking, faux bold and italic, and
  baseline shift.
- `ae_render_start`, `ae_render_status` and `ae_render_cancel` render one queue entry in the background under a
  `cavi-mcp-core` resident owner, report its frames as progress and stop it with its `aerendercore`.

### Changed

- Tool results are built on the `cavi-mcp-core` `Result` model instead of a local copy.
- The tests parse every packaged script with Node.js.
- CI runs the MCP Eval probes in `evals/manifest.json`: catalog budgets, pagination, declared surfaces and
  protocol negotiation.
- The footage lookup, property setter, path shape, frame backdrop, renderer check and light types live once in
  `lib.jsx` instead of in two or three scripts each.
- The README, overview, template guide and checked-application list describe batches, background renders,
  temporary reports and per-entry render templates.

### Fixed

- A script call that ends because After Effects exited or did not answer stops the whole process group of its
  command through `cavi-mcp-core` `proc.run`, so no process it started is left running.
- A call on a project path with no file starts it only from an untitled, empty project; otherwise it is refused, so
  a new project no longer inherits the items of the project open before it.
- `ae_template_render` saves the opened template to `project` before filling it, so an existing `project` file is
  replaced by the filled template instead of being edited, and its queue entries no longer fail on missing render
  settings.
- Reports escape every control character, so a text, marker comment or other value holding one is returned as it is
  in the project instead of without it.
- A typed tool whose script failed and was rolled back is `rejected` with `AE_SCRIPT_REFUSED` instead of `unknown`;
  unknown outcomes name `ae_inspect` as the next action.
- An open project with unsaved changes is refused as `AE_PROJECT_UNSAVED` with its message instead of
  `After Effects script failed: 1`, and an instance running with its UI as `AE_UI_RUNNING`.
- A missing project or script file is reported as `INPUT_NOT_FOUND`.
- `ae_text_set` on a layer with Source Text keyframes styles each key and keeps its text, instead of writing the
  current text to every key.
- A crossfade between two layers fades only the upper one, so the background no longer shows through at the
  midpoint, and a dip between two layers trims both to its midpoint, so its second half shows the incoming layer.
  A transition whose outgoing layer ends before it is refused, and `ae_sequence_layers` refuses a transition longer
  than the overlap (twice the overlap for a dip).
- `after_effects_render` runs the `aerender` next to the application `CAVI_AFTER_EFFECTS_APP` names, or the newest
  install, instead of refusing when `/Applications` holds two installs and ignoring the override.
- `ae_frame` names each PNG `<comp>_<position>_<time>s.png` with `/` and `:` in the comp name replaced, so close
  times no longer share a file and a comp name with `/` no longer fails the call.
- `ae_render_queue` checks each output against its queue entry: the entry's time span at its frame rate sets the
  expected frames (a different `frames` is refused), a short output renders again from its entry with
  `aerender -rqindex`, the fallback renders the entry's time span, image sequences count their frame files, and
  output folders are created first. `frames` is optional; `render_settings` and `output_module` are removed, since
  the entry's templates are used. An output with no queue entry is refused.
- `ae_audio` fades follow a gain linear in amplitude, -6 dB at the midpoint, instead of a line in dB that stayed
  below -40 dB for the first 60% of the fade; `fade_in` and `fade_out` longer together than the layer are refused.
- `ae_render_queue` counts an audio-only output's duration in frames at its entry's frame rate, instead of
  deleting it as unreadable, rendering it again and failing.
- `ae_sequence_layers` refuses an item `duration` longer than its source, instead of ending the layer at the end of
  its source and leaving a gap before the next item.
- `ae_keyframes`, `ae_audio`, `ae_time` and `ae_mask` refuse a key list that repeats a time, which After Effects
  merged into one key with the last value and the first key's interpolation.
- Calls from two server processes take turns through a file lock, instead of running on whichever project the other
  process opened last and saving it over their own.
- A comp or layer name two of them share is refused with their item ids or layer indices, instead of resolving to
  the first; `ae_inspect` lists item ids and `ae_organize` renames or moves an item by id.
- `ae_import` `folder` is a folder path from the root, as in `ae_organize`, instead of a root folder whose name
  holds the slashes; folder paths with an empty name are refused for `ae_import` and `ae_organize` moves too.
- `ae_controls` links read a control's parameter by index, `effect("name")(1)`, instead of by its English display
  name, and a link to an effect that is not an Expression Control is refused by name instead of failing with a
  `TypeError`.
- `ae_expressions` on one layer looks the layer up once instead of once per layer of the comp: 1.7 s instead of
  2.2 s on a 400-layer comp.
- Read-only tools leave the `.aep` untouched: reports are written to a temporary JSON file, and a project is saved
  only when the call changed it or names another file. No `cavi-report` folder is added to projects.

## 0.1.1 - 2026-11-16

### Changed

- No longer depends on `cavi-adobe-mcp`; `after_effects_render` writes its receipt through `cavi-mcp-core`.

## 0.1.0 - 2026-11-14

### Added

- `CAVI_AFTER_EFFECTS_APP` chooses the application bundle.
- `ae_status` reports an application that is not installed in `error` instead of failing.
- LICENSE, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, a release workflow, documentation under
  `docs/after-effects-mcp`, evaluations and package metadata.
- Issue and pull request templates; CI runs the evaluations.
- `examples/first-result` builds an animated lower third over real footage in headless After Effects.

### Changed

- Depends on `cavi-adobe-mcp` and `cavi-mcp-core` by version range; the application is found through
  `cavi-mcp-core`.
- Tools live in `tools/` modules, the server object and shared helpers in `app.py`.
- `after_effects_render` uses the implementation in `cavi-adobe-mcp`.
- FFmpeg is found the same way for encoding and for frame checks.

### Fixed

- NaN and infinite numbers are refused before After Effects is called.
- A beat grid or marker list of more than 5000 markers is refused instead of building an unbounded list.
- A missing script file is named; a report without its end marker is reported as unreadable.
- The application's render engine and other helpers are no longer counted as a running After Effects.
- Two simultaneous calls take turns instead of interleaving scripts in the same instance.
- A `shape_rect` layer with neither fill nor stroke is refused instead of being added invisible.
