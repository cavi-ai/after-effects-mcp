# Templates and Essential Graphics

## Fill a template

`ae_template_render` turns a template project into finished movies in one call:

1. It opens the `template` `.aep`. Unsaved changes in the instance stop the call unless `discard` is true.
2. It sets each entry of `texts` on its text layer (`comp`, `layer`, and any of `text`, `font`, `size`, `fill`,
   `stroke`, `stroke_width`, `tracking`, `leading`, `justification`, `box`, `box_fit`, `box_align`,
   `box_inset`, and `ranges` as in `ae_text_set`). The layer's animators and keyframes stay. The result's
   `overflow` lists each filled layer whose paragraph text does not fit its box; `box_fit: "cursor"` grows the
   box down instead.
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

Each render is its own queue entry with its own `output_module` and `render_settings`, and is checked and, when
short, rendered again from that entry.

The text and footage tools it uses are available on their own: `ae_text_set` and `ae_footage_replace`.

### Many versions in one call

`variants` fills and renders the template once per entry, one after another. Each variant has a `name` (letters,
digits, spaces, `_`, `.` and `-`, up to 64 characters), its own `texts` and its own `footage`. The `name`
replaces `{name}` in `project` and in every `renders` file, so both need `{name}`. The call's own `texts` and
`footage` apply to every variant first, then the variant's own. Each entry of `outputs` and `overflow` carries
its `variant`, and the call reports progress after each one.

```json
{"tool": "ae_template_render", "arguments": {"template": "/path/to/lower-third.aep",
 "project": "/path/to/out/{name}.aep",
 "footage": {"Logo": "/path/to/logo.png"},
 "renders": [{"comp": "Lower third", "file": "/path/to/out/{name}.mov"}],
 "variants": [{"name": "ada", "texts": [{"comp": "Lower third", "layer": "Name", "text": "Ada Lovelace"}]},
              {"name": "alan", "texts": [{"comp": "Lower third", "layer": "Name", "text": "Alan Turing"}]}]}}
```

When the first variant fails, the error names it and keeps its code. When a later one fails, the call stops
with `OUTCOME_UNKNOWN`, names the variant, and lists the variants rendered before it; their projects and movies
stay on disk.

A template opened on a machine without one of its fonts shows a substitute. `ae_fonts` with `used: true` lists
the fonts its text uses with `missing: true` for those, and `ae_font_replace` swaps a font for an installed one
in every layer, mixed styles included.

## Essential Graphics

`ae_essential_graphics` exposes layer properties as controls of a comp. Each entry of `add` names a layer, a
property path (`Text/Source Text`, `Transform/Position`, an effect parameter) and the control name. Properties
that cannot be added are refused by name. An entry without `property` makes a footage or comp layer a media
replacement control; a text layer, or a layer that is already one, is refused. `template_name`
names the template. The result lists every control the comp has.

`ae_essential_override` sets those controls on one nested-comp layer by name: a media replacement control takes
an absolute footage path, imported once, or a comp name; a string sets source text; a number, array or color list
sets that value. Each instance of the same comp keeps its own values, so one template comp can carry many titles:

```json
{"tool": "ae_essential_override", "arguments": {"project": "/path/to/titles.aep", "comp": "Main",
 "layer": "Title A", "values": {"Headline": "Spring sale", "Photo": "/path/to/spring.png"}}}
```

## Building from template packs

`ae_import` brings in another `.aep` as one folder and lists its comps. `ae_layer_edit` `copy` copies layers
with their keyframes, effects and masks into `to_comp`, on top and in order. A comp name the pack shares with the
project is refused by name until `ae_organize` renames one of the two.

## Exporting a `.mogrt`

Headless After Effects returns success from `comp.exportAsMotionGraphicsTemplate` but writes no file, so
`ae_mogrt_export` refuses and says so. Prepare the comp with `ae_essential_graphics`, then export the
`.mogrt` from an After Effects window.

## Collecting a project

`ae_collect` copies every used footage file into a folder, relinks each item to its copy and saves the project.
Solids and image sequences are skipped by name, and items whose files are already missing are reported in
`skipped` and counted in `missing`.
