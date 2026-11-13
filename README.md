# After Effects MCP

[![CI](https://github.com/cavi-ai/after-effects-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/cavi-ai/after-effects-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

MCP server for headless Adobe After Effects on macOS. It starts After Effects without its UI, runs
ExtendScript with arguments and returns the script's JSON report, and renders saved projects with `aerender`,
checking every output movie's frame count. 45 tools cover comps, layers, shapes, masks, text, keyframes,
effects, 3D, transitions, templates, Essential Graphics and delivery.

Built on [`cavi-adobe-mcp`](https://pypi.org/project/cavi-adobe-mcp/) and
[`cavi-mcp-core`](https://pypi.org/project/cavi-mcp-core/). Every tool fails with a readable reason and
never takes the server down.

## First result

A 3-second title comp whose text types on, with a beat grid of markers and two frames to look at. This is the
sequence the server ran against After Effects 26.5.0 for this README:

| Call | Arguments | Result |
|---|---|---|
| `ae_status` | none | the installed app, its version and the running pids |
| `ae_launch` | none | headless After Effects is up and answers scripts |
| `ae_comp_new` | `project`, `name: "Title"`, 1280 x 720, 3 s, 30 fps, `replace: true` | the comp `Title` in a new `hello.aep` |
| `ae_layer_add` | a text layer `Headline`, "Hello, After Effects", size 90, centered | the layer |
| `ae_text_animator` | `layer: "Headline"`, `opacity: 0`, `duration: 1.2` | one animator |
| `ae_markers` | `grid: {"bpm": 120, "end": 3}` | 6 markers, `bar.beat` comments |
| `ae_frame` | `times: [0.2, 2.5]` | `Title_0.2s.png` and `Title_2.5s.png` |

At 0.2 seconds the frame shows the first letter, at 2.5 seconds the whole line. Run it yourself with
[examples/first-result](examples/first-result/README.md); the calls with their full arguments are in
[Your first comp](docs/after-effects-mcp/source/pages/guides/first-comp.md).

## Install

Requires macOS, After Effects 2026 or later, FFmpeg (`ffmpeg` and `ffprobe` on `PATH`) and Python 3.15 or
later.

```sh
uv tool install cavi-after-effects-mcp
```

or from a checkout:

```sh
uv sync
uv run cavi-after-effects-mcp
```

The server speaks MCP over stdio. Client configuration:

```json
{
  "mcpServers": {
    "after-effects": {
      "command": "uvx",
      "args": ["cavi-after-effects-mcp"]
    }
  }
}
```

## Quickstart

1. Call `ae_status`. It reports the After Effects it found and its version, or the reason it found none.
2. Call `ae_launch`. It starts one headless instance and waits until it answers.
3. Create a comp with `ae_comp_new`, passing an absolute path for `project`. The project is created and saved.
4. Add layers, animation and effects, then look with `ae_frame` or write a movie with `ae_export_frames`.
5. Render a queue with `ae_render_queue_set` and `ae_render_queue`.

Every tool that edits a project takes the project's absolute path and saves it. After Effects runs with no UI,
so nothing is open on screen; a call that fails leaves the project as it was.

## Tools

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
result fields, and a test fails when it and the server's registry differ. Three tools refuse by design
because headless After Effects aborts on the underlying call: `ae_preset_apply`, `ae_mogrt_export` and
`convert_to_keyframes` of `ae_audio`. See [Measured behavior](docs/after-effects-mcp/source/pages/reference/behavior-notes.md).

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
and writes a receipt:

```json
{
  "version": 1, "name": "SpellLoop", "project": "effects/spell.aep",
  "dependencies": ["effects/source.psd"], "composition": "SpellLoop", "start": 0, "end": 23,
  "fps": {"numerator": 24, "denominator": 1}, "loop": true, "alpha": "straight",
  "output_module": "Game RGBA PNG"
}
```

Start and end are inclusive. The output module must be an existing straight-alpha RGBA PNG template, and
exactly one `aerender` must be installed.

## Documentation

| Page | What it covers |
|---|---|
| [Overview](docs/after-effects-mcp/source/pages/introduction/overview.md) | What the server does and how a call travels |
| [Setup](docs/after-effects-mcp/source/pages/guides/setup.md) | Requirements, installation, client configuration |
| [Your first comp](docs/after-effects-mcp/source/pages/guides/first-comp.md) | The first result, call by call |
| [Templates and Essential Graphics](docs/after-effects-mcp/source/pages/guides/templates-and-essential-graphics.md) | Filling a template and rendering it |
| [Rendering and the fallback](docs/after-effects-mcp/source/pages/guides/rendering.md) | `aerender`, frame checks, the frame fallback |
| [Troubleshooting](docs/after-effects-mcp/source/pages/guides/troubleshooting.md) | Errors and what to do |
| [Tools](docs/after-effects-mcp/source/pages/reference/tools.md) | Every tool, parameter and result |
| [Configuration](docs/after-effects-mcp/source/pages/reference/configuration.md) | Environment variables and fixed limits |
| [Measured behavior](docs/after-effects-mcp/source/pages/reference/behavior-notes.md) | What headless After Effects does |
| [Security model](docs/after-effects-mcp/source/pages/security/model.md) | What the server can touch |

## Configuration

| Variable | Meaning |
|---|---|
| `CAVI_AFTER_EFFECTS_APP` | Absolute path of the After Effects `.app` to use. A wrong path is reported, never replaced by another install. Default: the newest `Adobe After Effects 20*` in `/Applications`. |
| `CAVI_ADOBE_WORKSPACE` | Workspace folder for `after_effects_render`; its recipe and output must stay inside it. |
| `CAVI_ADOBE_DATA` | Private state directory of the shared Adobe package. |

## Security

The server runs ExtendScript with the permissions of the user who started it. Only `after_effects_render` is
confined to a workspace folder; the other tools take any absolute path and can write there, and `ae_script` runs
arbitrary ExtendScript. Run it only for clients you trust. See the
[security model](docs/after-effects-mcp/source/pages/security/model.md) and [SECURITY.md](SECURITY.md) to report
a vulnerability.

## Tests

```sh
uv run --locked ruff check .
uv run --locked pytest -q
```

The tests drive the registered tools through the server and never start After Effects. A test fails when the
tool reference and the registry differ, when the documentation build is not reproducible, or when a link in
the README or the pages is broken. See [Testing and evaluation](docs/after-effects-mcp/source/pages/reference/testing.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md). Release history is in
[CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE).

## Trademarks

Adobe and After Effects are trademarks of Adobe Inc. This project is not affiliated with or endorsed by Adobe.
