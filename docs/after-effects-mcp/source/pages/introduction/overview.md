# Overview

`cavi-after-effects-mcp` is an MCP server that drives Adobe After Effects without its window. It starts one
headless instance (`-noui`), sends it ExtendScript over Apple Events, and reads back a JSON report for every
call. Renders go through `aerender`, with a frame-by-frame fallback when `aerender` leaves no movie.

It runs on macOS with After Effects installed and licensed by you. The server does not supply a license,
sign in or accept terms.

## What it does

- Runs your own `.jsx` file with `ae_script`, or one of the typed tools that build and change a project:
  comps, layers, text, shapes, masks, cameras and lights, keyframes, expressions, effects, text animators,
  transitions, time remapping, audio levels, markers and project settings.
- Inspects what is there: project items, a comp's layers, any layer's property tree, installed effects,
  fonts, render templates and animation presets.
- Fills templates: opens a template project, sets text layers by name, swaps footage and renders the named
  comps.
- Delivers: aerender of a saved render queue with frame counts checked, single frames, frame sequences and
  H.264 or ProRes movies written without `aerender`.

## How a call works

1. A tool call carries the project path (`.aep`, absolute) and the arguments.
2. The server makes sure the project is the one open in the headless instance, runs the packaged script and
   saves the project. The script's report is stored inside the saved project, and the server reads it back.
3. A report with `errors` fails the call. A script that throws leaves the project as it was on disk.

One instance runs one script at a time, so two simultaneous calls take turns.

## What it refuses

Three calls abort headless After Effects when they run: `layer.applyPreset`, `app.executeCommand` and
`app.findMenuCommandId`. A script that contains one is refused before it runs. `ae_preset_apply`,
`ae_mogrt_export` and the audio-to-keyframes option of `ae_audio` exist to say so with the supported
alternative. See [Troubleshooting](../guides/troubleshooting.md).

## Where to go next

- [Setup](../guides/setup.md), then [Your first comp](../guides/first-comp.md).
- The [tool reference](../reference/tools.md) lists every tool with its parameters and results.
- [Version and support](../release/version-and-support.md) says what was checked natively.
