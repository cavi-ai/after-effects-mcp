# Changelog

Versions come from git tags; a pull request adds its lines under Unreleased and never edits a version.

## Unreleased

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

### Changed

- Tool results are built on the `cavi-mcp-core` `Result` model instead of a local copy.
- The tests parse every packaged script with Node.js.
- The footage lookup, property setter, path shape, frame backdrop, renderer check and light types live once in
  `lib.jsx` instead of in two or three scripts each.

### Fixed

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
