# Cavi After Effects MCP

[![PyPI version](https://img.shields.io/pypi/v/cavi-after-effects-mcp)](https://pypi.org/project/cavi-after-effects-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MCP server for headless Adobe After Effects on macOS. It starts After Effects without its UI, runs
ExtendScript with arguments and returns the script's JSON report, and renders saved projects with `aerender`,
checking every output movie's frame count. 45 tools cover comps, layers, shapes, masks, text, keyframes,
effects, 3D, transitions, templates, Essential Graphics and delivery.

## Try one title

Put a lower third over a shot: the footage pushes in, a name bar slides in, and two lines of text rise in.
The frame below was rendered by headless After Effects from that comp at 2.5 seconds.

![A server aisle in blue and magenta light with a lower third reading "Aisle B" and "Racks online at 02:00"](examples/first-result/Title_2.5s.png)

The calls are in [run.py](examples/first-result/run.py) and the shot is in
[examples/first-result/media](examples/first-result/media). The comp is 1280 by 720, 3.5 seconds at 24 fps,
with five layers. [Reproduce the title](examples/first-result/README.md) with one command; the calls are
explained in [Your first comp](docs/after-effects-mcp/source/pages/guides/first-comp.md).

## Install

Requires macOS, After Effects 2026 or later, FFmpeg (`ffmpeg` and `ffprobe` on `PATH`) and Python 3.15 or
later with [uv](https://docs.astral.sh/uv/). You supply your own licensed Adobe applications.

```sh
uv tool install cavi-after-effects-mcp
```

Upgrade with `uv tool upgrade cavi-after-effects-mcp`. To work from a checkout instead, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Quickstart

Register the stdio server with your MCP client:

```json
{"mcpServers": {"after-effects": {"command": "cavi-after-effects-mcp"}}}
```

If your client does not inherit your shell's `PATH`, use the absolute path that
`command -v cavi-after-effects-mcp` prints. Then ask your agent to:

1. Call `ae_status`. It reports the After Effects it found and its version, or the reason it found none.
2. Call `ae_launch`. It starts one headless instance and waits until it answers.
3. Create a comp with `ae_comp_new`, passing an absolute path for `project`. The project is created and saved.
4. Add layers, animation and effects, then look with `ae_frame` or write a movie with `ae_export_frames`.
5. Render a queue with `ae_render_queue_set` and `ae_render_queue`.

Every tool that edits a project takes the project's absolute path and saves it. After Effects runs with no UI,
so nothing is open on screen; a call that fails leaves the project as it was.

## What it does

| Area | Tools |
|---|---|
| Session | `ae_status`, `ae_launch`, `ae_script` |
| Project | `ae_inspect`, `ae_project`, `ae_project_settings`, `ae_import`, `ae_footage_replace`, `ae_collect`, `ae_organize`, `ae_fonts`, `ae_effects`, `ae_presets` |
| Comps and layers | `ae_comp_new`, `ae_comp_set`, `ae_layer_add`, `ae_layer_set`, `ae_layer_edit`, `ae_text_set`, `ae_shape_add`, `ae_mask`, `ae_camera`, `ae_material`, `ae_markers` |
| Animation | `ae_keyframes`, `ae_expressions`, `ae_effect_add`, `ae_preset_apply`, `ae_text_animator`, `ae_controls`, `ae_audio`, `ae_time`, `ae_properties` |
| Transitions | `ae_transitions`, `ae_transition`, `ae_sequence_layers` |
| Delivery | `ae_render_queue_set`, `ae_render_queue`, `after_effects_render`, `ae_frame`, `ae_export_frames`, `ae_template_render`, `ae_essential_graphics`, `ae_essential_override`, `ae_mogrt_export` |

Each tool carries its access in its annotations: read-only, write, or destructive. The
[tool reference](docs/after-effects-mcp/source/pages/reference/tools.md) lists every tool's parameters and
result fields, and a test fails when it and the server's registry differ. Three calls always refuse, because
headless After Effects aborts on the underlying operation, and name the supported alternative instead:
`ae_preset_apply`, `ae_mogrt_export` and `convert_to_keyframes` of `ae_audio`. See
[Measured behavior](docs/after-effects-mcp/source/pages/reference/behavior-notes.md).

## Script contract

`ae_script(script, project, args)` defines the global `CAVI_ARGS` (the `args` object), then runs the script. The
script sets its report with `caviReport(object)`, which stores the JSON in the saved project. A script that
never calls `caviReport` reports `{"value": <its last value>}`. A report with a non-empty `errors` list fails
the call with those errors. Before running, the runner compiles the script inside `try`, so a syntax error
comes back as a message with its line. A script that fails leaves no partial edits.

```js
var comp = app.project.items.addComp("Title", 1920, 1080, 1, 2, 30);
caviReport({comp: comp.name, frames: 60, errors: []});
```

`ae_script` refuses scripts that call `applyPreset`, `executeCommand` or `findMenuCommandId`, which abort
headless After Effects.

## Rendering

`ae_render_queue` runs `aerender` on a saved project's queue and checks each declared output's frame count with
`ffprobe`. A movie that is missing, older than the render or short of frames is rendered again on its own. If
that still fails, the movie is encoded from `saveFrameToPng` frames with `ffmpeg` and the output reports which
path produced it. `ae_export_frames` writes a frame range without `aerender` at all. See
[Rendering and the fallback](docs/after-effects-mcp/source/pages/guides/rendering.md).

`after_effects_render` renders one declared composition range of a workspace project to a new PNG directory
and writes a receipt. The recipe:

```json
{
  "version": 1, "name": "Title", "project": "titles/title.aep",
  "dependencies": ["titles/aisle.mp4"], "composition": "Title", "start": 0, "end": 83,
  "fps": {"numerator": 24, "denominator": 1}, "loop": false, "alpha": "straight",
  "output_module": "RGBA PNG"
}
```

Start and end are inclusive frames. The output module must be an existing straight-alpha RGBA PNG template,
and exactly one `aerender` must be installed.

## Documentation

The documentation source is in `docs/after-effects-mcp/source`:

- [Overview](docs/after-effects-mcp/source/pages/introduction/overview.md) and
  [setup](docs/after-effects-mcp/source/pages/guides/setup.md)
- Guides: [your first comp](docs/after-effects-mcp/source/pages/guides/first-comp.md),
  [templates and Essential Graphics](docs/after-effects-mcp/source/pages/guides/templates-and-essential-graphics.md),
  [rendering and the fallback](docs/after-effects-mcp/source/pages/guides/rendering.md) and
  [troubleshooting](docs/after-effects-mcp/source/pages/guides/troubleshooting.md)
- Reference: [tools](docs/after-effects-mcp/source/pages/reference/tools.md),
  [configuration](docs/after-effects-mcp/source/pages/reference/configuration.md),
  [measured behavior](docs/after-effects-mcp/source/pages/reference/behavior-notes.md) and
  [testing and evaluation](docs/after-effects-mcp/source/pages/reference/testing.md)
- [Security model](docs/after-effects-mcp/source/pages/security/model.md) and
  [version and support](docs/after-effects-mcp/source/pages/release/version-and-support.md)

## Configuration

| Variable | Meaning |
|---|---|
| `CAVI_AFTER_EFFECTS_APP` | Absolute path of the After Effects `.app` to use. A wrong path is reported, never replaced by another install. Default: the newest `Adobe After Effects 20*` in `/Applications`. |
| `CAVI_ADOBE_WORKSPACE` | Workspace folder for `after_effects_render`; its recipe and output must stay inside it. |
| `CAVI_ADOBE_DATA` | Private state directory of the shared Adobe package. |

## Security

The server speaks MCP over stdio, sends no telemetry and uses no accounts. It runs ExtendScript with the
permissions of the user who started it. Only `after_effects_render` is confined to a workspace folder; the
other tools take any absolute path and can write there, and `ae_script` runs arbitrary ExtendScript. Run it
only for clients you trust. See the [security model](docs/after-effects-mcp/source/pages/security/model.md) and
[SECURITY.md](SECURITY.md).

## Tests

```sh
uv sync --locked --dev
uv run --locked ruff check .
uv run --locked pytest -q
uv run --locked python evals/run.py
```

The unit tests and the evaluations drive the registered tools through the server and never start After
Effects; tests that need FFmpeg skip without it. A test fails when the tool reference and the registry differ,
when the documentation build is not reproducible, or when a link in the README or the pages is broken. The
evaluations play each case in `evals/cases.json` against the server over stdio. See
[Testing and evaluation](docs/after-effects-mcp/source/pages/reference/testing.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and the rules for changes. This project follows
the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).

## Trademarks

Adobe and After Effects are either registered trademarks or trademarks of Adobe in the United States and/or
other countries. This project is not affiliated with, endorsed by, or sponsored by Adobe. It does not include
or redistribute Adobe software, templates or presets; you supply your own licensed applications.
