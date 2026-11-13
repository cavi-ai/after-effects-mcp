# Templates and Essential Graphics

## Fill a template

`ae_template_render` turns a template project into finished movies in one call:

1. It opens the `template` `.aep`. Unsaved changes in the instance stop the call unless `discard` is true.
2. It sets each entry of `texts` on its text layer (`comp`, `layer`, and any of `text`, `font`, `size`, `fill`,
   `stroke`, `stroke_width`, `tracking`, `leading`, `justification`, `box`). The layer's animators and keyframes
   stay.
3. It replaces each `footage` item, by item name, with the file you give.
4. It saves the result to `project` (a new path, so the template is untouched).
5. It queues the comps named in `renders` (`comp`, `file`, and optionally `output_module` and
   `render_settings`), turns every other queue entry off, and renders through
   [the render queue path](rendering.md) with frame counts checked.

```json
{"tool": "ae_template_render", "arguments": {"template": "/path/to/lower-third.aep",
 "project": "/path/to/out/ada.aep",
 "texts": [{"comp": "Lower third", "layer": "Name", "text": "Ada Lovelace"}],
 "footage": {"Logo": "/path/to/ada-logo.png"},
 "renders": [{"comp": "Lower third", "file": "/path/to/out/ada.mov"}]}}
```

The first render's `output_module` and `render_settings` apply to the whole call. Call the tool once per
distinct setting.

The text and footage tools it uses are available on their own: `ae_text_set` and `ae_footage_replace`.

## Essential Graphics

`ae_essential_graphics` exposes layer properties as controls of a comp. Each entry of `add` names a layer, a
property path (`Text/Source Text`, `Transform/Position`, an effect parameter) and the control name. Properties
that cannot be added are refused by name. `template_name` names the template. The result lists every control the
comp has.

`ae_essential_override` sets those controls on one nested-comp layer by name: a string sets source text; a
number, array or color list sets that value. Each instance of the same comp keeps its own values, so one
template comp can carry many titles:

```json
{"tool": "ae_essential_override", "arguments": {"project": "/path/to/titles.aep", "comp": "Main",
 "layer": "Title A", "values": {"Headline": "Spring sale"}}}
```

## Exporting a `.mogrt`

Headless After Effects returns success from `comp.exportAsMotionGraphicsTemplate` but writes no file, so
`ae_mogrt_export` refuses and says so. Prepare the comp with `ae_essential_graphics`, then export the
`.mogrt` from an After Effects window.

## Collecting a project

`ae_collect` copies every used footage file into a folder, relinks each item to its copy and saves the project.
Solids and image sequences are skipped by name, and items whose files are already missing are reported in
`skipped` and counted in `missing`.
