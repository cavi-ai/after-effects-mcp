# Version and support

This documentation is for `cavi-after-effects-mcp` {{PRODUCT_VERSION}}, released as
`{{RELEASE_TAG}}` from commit `{{RELEASE_COMMIT}}`.

Versions follow Semantic Versioning and come from git tags. Before 1.0, the tool surface and result fields can
still change. Every change is recorded in the repository
[CHANGELOG.md](https://github.com/cavi-ai/after-effects-mcp/blob/main/CHANGELOG.md).

## Checked application

After Effects 27.0.0 on macOS, headless: launch, `ae_project` `new`, creating a comp, adding a text layer, a text
animator and its variable font axes, a beat grid of markers, a parametric mesh layer and its mesh and bevel
options, an effect layer parameter's source layer and stage, PNG frames, inspecting a comp, writing an H.264 movie
from frames, `ae_script` and reporting the open project. Checked in 26.5.0: the same,
and `ae_template_render` with and without `variants`, `ae_render_queue` against its queue
entries (movies, image sequences and a re-render), `ae_render_start`, `ae_render_status` and `ae_render_cancel`,
`ae_batch`, crossfade and dip transitions, `ae_text_set` on keyed Source Text and character ranges, `ae_audio`
fades, `ae_sequence_layers`, `ae_import` and `ae_organize` folder paths, `ae_controls` links, `ae_expressions`,
`ae_properties` keyframes, `ae_layer_set` switches and extrusion, parametric mesh layers, environment light
sources, text box fit and overflow, `ae_fonts` `used` and `ae_font_replace`, menu items by name, `ae_layer_edit`
`copy`, media replacement controls, `.aep` import, `.c4d` layers with Cineware settings and frames, `ae_comp_new`
from footage, `ae_layer_parts`, `ae_markers` onsets and cuts, a call that ends when After Effects exits during
it, and calls in After Effects running with its window, refused ones included. The
other tools are covered by their input checks; a tool that fails in your install is a bug to report.

Requires Python 3.15 or newer. Only macOS is supported, because the server addresses After Effects over Apple
Events.

## License and trademarks

MIT licensed.

Adobe and After Effects are either registered trademarks or trademarks of Adobe in the United States and/or
other countries. This project is not affiliated with, endorsed by, or sponsored by Adobe. It does not include
or redistribute Adobe software, templates, presets or project files; you supply your own licensed application.
