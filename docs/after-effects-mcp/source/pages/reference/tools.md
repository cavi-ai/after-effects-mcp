# Tools

Every tool is listed with its parameters and the fields of its result. A parameter marked `*` is required.
Access is what the tool annotations declare: `read-only` changes nothing, `write` changes a project or writes
files, `destructive` can delete or overwrite (a comp, a movie, a layer, unsaved work, or whatever a script
does). A tool that runs a packaged script saves the script's report into its `project`, which is created
when it does not exist, and returns it as `report` with its fields repeated at the top of the result. Paths
are absolute. Layers are a 1-based index or a name. Colors are RGB from 0 to 1.

A tool that fails raises an error with the reason; a script's `errors` field fails the call.

## Session

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `ae_status` | read-only |  | `app`, `version`, `aerender`, `headless_pids`, `ui_pids`, `error` | The installed application, its version and running pids. A missing application is reported in `error`. |
| `ae_launch` | write |  | `app`, `version`, `aerender`, `headless_pids`, `ui_pids`, `error` | Starts headless After Effects and waits until it answers scripts. |
| `ae_script` | destructive | `script`*, `project`*, `args`, `timeout` | `project`, `report` | Runs a `.jsx` with the global `CAVI_ARGS`; it calls `caviReport(obj)`. `timeout` is 10 to 3600 seconds, default 900. |

## Project

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `ae_project` | destructive | `action`*, `path`, `discard`, `overwrite`, `comps` | `project`, `report`, `action`, `removed`, `path`, `previous`, `items`, `comps`, `footage` | Opens, saves, saves as, reports (`info`), reduces to `comps`, removes unused footage or consolidates duplicates. |
| `ae_project_settings` | write | `project`*, `bits_per_channel`, `linear_blending`, `working_space`, `display_start_frame`, `time_display`, `frames_count`, `expression_engine`, `gpu` | `project`, `report`, `settings` | Sets project-wide bit depth, color space, time display, expression engine and GPU mode. |
| `ae_inspect` | read-only | `project`*, `scope`, `comp` | `project`, `report`, `scope` | Lists project items, one comp's layers or the render queue. |
| `ae_import` | write | `project`*, `files`*, `folder`, `sequence`, `import_as`, `alpha`, `conform_fps`, `loop` | `project`, `report`, `items` | Imports footage, an image sequence or a layered file as a comp. |
| `ae_footage_replace` | write | `project`*, `item`*, `file`* | `project`, `report`, `item`, `layers_using` | Replaces a footage item's source file in place. |
| `ae_collect` | write | `project`*, `folder`* | `project`, `folder`, `items`, `copied`, `relinked`, `skipped`, `missing` | Copies used footage into a folder and relinks it. |
| `ae_organize` | write | `project`*, `folders`, `renames`, `moves` | `project`, `report`, `folders`, `renamed`, `moved` | Creates folders, renames items and moves them. |
| `ae_fonts` | read-only | `project`*, `filter`, `limit` | `project`, `report`, `fonts`, `count` | Lists installed fonts by PostScript name. |
| `ae_effects` | read-only | `project`*, `filter`, `category`, `limit` | `project`, `report`, `effects`, `total`, `categories` | Lists installed effects with their match names. |
| `ae_presets` | read-only | `project`*, `filter`, `limit` | `project`, `report`, `render_settings`, `output_modules`, `animation_presets` | Lists render settings and output module templates and installed `.ffx` presets. |

## Comps and layers

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `ae_comp_new` | destructive | `project`*, `name`*, `width`*, `height`*, `duration`*, `fps`, `background`, `renderer`, `replace` | `project`, `report`, `comp`, `renderer`, `replaced` | Creates a comp; `replace` removes an existing comp of that name. |
| `ae_comp_set` | write | `project`*, `comp`*, `name`, `width`, `height`, `duration`, `fps`, `work_area`, `background`, `renderer`, `motion_blur`, `frame_blending`, `duplicate_as` | `project`, `report`, `comp`, `source`, `duplicated`, `width`, `height`, `duration`, `fps` | Changes a comp, or a copy of it with `duplicate_as`. |
| `ae_layer_add` | write | `project`*, `layer`* | `project`, `report`, `layer` | Adds a solid, text, footage, 3D model, nested comp, rectangle, null, camera, light or adjustment layer. |
| `ae_layer_set` | write | `project`*, `comp`*, `layer`*, `name`, `enabled`, `solo`, `shy`, `locked`, `label`, `in_point`, `out_point`, `start_time`, `stretch`, `blend_mode`, `parent`, `no_parent`, `three_d`, `motion_blur`, `track_matte`, `properties` | `project`, `report`, `comp`, `layer`, `properties_set`, `values` | Changes switches, timing, blend mode, parent, matte and static property values. |
| `ae_layer_edit` | destructive | `project`*, `comp`*, `layers`*, `action`*, `time`, `move_to`, `name` | `project`, `report`, `comp`, `action`, `layers`, `layer_count` | Duplicates, deletes, reorders, splits or precomposes layers. |
| `ae_text_set` | write | `project`*, `comp`*, `layer`*, `text`, `font`, `size`, `fill`, `stroke`, `stroke_width`, `tracking`, `leading`, `justification`, `box` | `project`, `report`, `comp`, `layer`, `text`, `animators` | Replaces the text or style of a text layer. |
| `ae_shape_add` | write | `project`*, `comp`*, `shape`*, `name`, `layer`, `group_name`, `fill`, `stroke`, `gradient_fill`, `gradient_stroke`, `operators`, `transform` | `project`, `report`, `comp`, `layer`, `group`, `contents` | Adds a shape layer, or a group on one, with operators and paint. |
| `ae_mask` | write | `project`*, `comp`*, `layer`*, `shape`, `mask`, `name`, `mode`, `feather`, `expansion`, `opacity`, `invert`, `path_keys` | `project`, `report`, `comp`, `layer`, `mask`, `mask_count`, `path_keys` | Adds or changes a mask, including a keyframed path. |
| `ae_camera` | write | `project`*, `comp`*, `camera`, `rig`, `light` | `project`, `report`, `comp` | Adds or changes a camera, an orbit rig and a light. |
| `ae_material` | write | `project`*, `comp`*, `layer`*, `material`* | `project`, `report`, `comp`, `layer`, `renderer`, `material` | Sets a 3D layer's material options. |
| `ae_markers` | write | `project`*, `comp`*, `layer`, `markers`, `grid`, `clear` | `project`, `report`, `comp`, `count`, `markers` | Sets markers and a beat grid; at most 5000 markers per call. |

## Animation

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `ae_keyframes` | write | `project`*, `comp`*, `layer`*, `property`*, `keyframes`, `ease`, `expression`, `preset`, `replace`, `easy_ease`, `hold`, `spatial`, `rove`, `remove` | `project`, `report`, `keys` | Sets or restyles keyframes, sets an expression or an expression preset, removes keys. |
| `ae_expressions` | write | `project`*, `comp`*, `layer`, `remove_broken` | `project`, `report`, `comp`, `expressions`, `broken`, `removed` | Lists a comp's expressions with their errors; `remove_broken` clears the broken ones. |
| `ae_effect_add` | write | `project`*, `comp`*, `layer`*, `match_name`*, `params`, `name` | `project`, `report`, `effect` | Adds an effect by match name and sets parameters. |
| `ae_preset_apply` | write | `project`*, `comp`*, `layer`*, `preset`*, `time` | `project`, `report` | Always refused: applying an animation preset aborts headless After Effects. |
| `ae_text_animator` | write | `project`*, `comp`*, `layer`*, `unit`, `opacity`, `position`, `tracking`, `scale`, `blur`, `rotation`, `start`, `duration`, `ease`, `name`, `animators`, `path` | `project`, `report`, `comp`, `layer`, `animators`, `animator_count` | Adds text animators with range, wiggly or expression selectors, and text on a path. |
| `ae_controls` | write | `project`*, `comp`*, `layer`*, `controls`, `links` | `project`, `report`, `comp`, `layer`, `controls`, `links` | Adds Expression Controls and links properties to them. |
| `ae_audio` | write | `project`*, `comp`*, `layer`*, `enabled`, `level`, `level_keys`, `fade_in`, `fade_out`, `convert_to_keyframes` | `project`, `report`, `comp`, `layer`, `audio_enabled`, `keys` | Sets audio levels in dB, fades and audio on or off. `convert_to_keyframes` is refused. |
| `ae_time` | write | `project`*, `comp`*, `layer`*, `time_remap`, `remap_keys`, `freeze_at`, `reverse`, `frame_blending` | `project`, `report`, `comp`, `layer`, `time_remap`, `keys`, `stretch`, `in_point`, `out_point`, `visible_start`, `visible_end` | Time remap, freeze frame, reverse and frame blending. |
| `ae_properties` | read-only | `project`*, `comp`*, `layer`*, `path`, `depth`, `max_nodes`, `time` | `project`, `report`, `comp`, `layer`, `count`, `truncated`, `properties` | Reads a layer's property tree, optionally the animated value at a time. |

## Transitions

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `ae_transitions` | read-only | `project`* | `kinds` | Lists the transition kinds this install has. |
| `ae_transition` | write | `project`*, `comp`*, `kind`*, `layer`, `edge`, `from_layer`, `to_layer`, `seconds`, `frames`, `color`, `ease` | `project`, `report` | Adds a transition on one layer's in or out point, or between two layers. |
| `ae_sequence_layers` | write | `project`*, `comp`*, `items`*, `start`, `overlap`, `transition` | `project`, `report`, `layers`, `joins` | Places layers or footage files end to end, with a transition at each join. |

## Delivery

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `ae_render_queue_set` | write | `project`*, `add`, `update`, `clear` | `project`, `report`, `queue` | Fills and edits the render queue and lists it. |
| `ae_render_queue` | destructive | `project`*, `outputs`*, `render_settings`, `output_module` | `project`, `outputs` | Renders the saved queue with `aerender`, renders short movies again and falls back to frames and FFmpeg. |
| `ae_template_render` | destructive | `template`*, `project`*, `renders`*, `texts`, `footage`, `discard` | `project`, `texts`, `footage`, `outputs` | Fills a template and renders the named comps. |
| `ae_frame` | write | `project`*, `comp`*, `times`*, `directory`*, `alpha`, `method` | `project`, `comp`, `frames` | Writes PNG frames at given times. |
| `ae_export_frames` | destructive | `project`*, `comp`*, `directory`*, `start`, `duration`, `step`, `alpha`, `movie`, `codec`, `max_frames` | `project`, `comp`, `directory`, `frames`, `fps`, `first`, `last`, `movie` | Writes a frame range as PNGs and optionally a movie, without `aerender`. |
| `after_effects_render` | write | `recipe`*, `directory`* | `status`, `receipt`, `sha256`, `frame_count`, `fps`, `execution`, `composition`, `timing_authority`, `dependencies_authority`, `launches_applications` | Renders one declared comp range of a workspace project to a new PNG directory. |
| `ae_essential_graphics` | write | `project`*, `comp`*, `add`, `template_name` | `project`, `report`, `comp`, `name`, `added`, `controls` | Adds properties to a comp's Essential Graphics. |
| `ae_essential_override` | write | `project`*, `comp`*, `layer`*, `values`* | `project`, `report`, `layer`, `source`, `available`, `overridden` | Overrides Essential Properties on a nested-comp layer. |
| `ae_mogrt_export` | write | `project`*, `comp`*, `file`* | `project`, `report` | Always refused: headless After Effects writes no `.mogrt`. |
