# Cavi After Effects MCP

![An illustrated red panda conducting a luminous animated sculpture](assets/after-effects-mcp-hero.png)

## Make an entrance.

Turn a direction into motion with an animation partner in After Effects. Build compositions with text, shapes and layers, animate them with keyframes, review frames and render the result. Your work is saved in an editable After Effects project.

The server runs After Effects without its UI on macOS. Bring your own licensed application.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![PyPI weekly downloads](https://img.shields.io/pypi/dw/cavi-after-effects-mcp?label=PyPI%20downloads%2Fweek)](https://pypi.org/project/cavi-after-effects-mcp/)

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

If your client does not inherit your shell's `PATH`, use the absolute path that `command -v cavi-after-effects-mcp` prints. Then try a request like:

> Create a lower third for this shot. Animate the name and title into place, show me a frame, and render the composition.

The [setup guide](docs/after-effects-mcp/source/pages/guides/setup.md) and [first comp](docs/after-effects-mcp/source/pages/guides/first-comp.md) walk through the workflow. Project paths are absolute; edits are saved to the project.

## Try one title

This example adds an animated lower third over a shot and saves the composition as a project.

![A frame from the example title: a server aisle with an animated lower third](examples/first-result/Title_2.5s.png)

[Explore the example](examples/first-result/README.md) or follow the [first comp guide](docs/after-effects-mcp/source/pages/guides/first-comp.md).

## What you can do

- Create and inspect projects, compositions and layers.
- Add text, shapes and masks, then animate properties with keyframes.
- Review frames and render saved compositions.

See the [tool reference](docs/after-effects-mcp/source/pages/reference/tools.md) for operations and parameters, [measured behavior](docs/after-effects-mcp/source/pages/reference/behavior-notes.md) for supported behavior, and the [rendering guide](docs/after-effects-mcp/source/pages/guides/rendering.md) for delivery.

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and the rules for changes. This project follows
the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).

## Trademarks

Adobe and After Effects are either registered trademarks or trademarks of Adobe in the United States and/or
other countries. This project is not affiliated with, endorsed by, or sponsored by Adobe. It does not include
or redistribute Adobe software, templates or presets; you supply your own licensed applications.
