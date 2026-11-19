# Setup

## Requirements

- macOS with Adobe After Effects installed under `/Applications` and licensed. The server finds the newest
  `Adobe After Effects 20*` install; `CAVI_AFTER_EFFECTS_APP` names a specific `.app` instead.
- Python 3.15 or newer and [uv](https://docs.astral.sh/uv/).
- FFmpeg (`ffmpeg` and `ffprobe`) for frame checks and for movies written without `aerender`. It is looked up
  on `PATH`, then in `/opt/homebrew/bin` and `/usr/local/bin`.

## Install

```sh
uv tool install cavi-after-effects-mcp
```

Upgrade with `uv tool upgrade cavi-after-effects-mcp`. The command is `cavi-after-effects-mcp`.

## Register the server

```json
{
  "mcpServers": {
    "after-effects": {"command": "cavi-after-effects-mcp"}
  }
}
```

A desktop client that does not inherit your shell's `PATH` needs the absolute path that
`command -v cavi-after-effects-mcp` prints.

`after_effects_render` reads its recipe from a workspace folder. Add
`"env": {"CAVI_ADOBE_WORKSPACE": "/absolute/path"}` to the entry to use it. No other tool needs a workspace.

## Check the install

Call `ae_status`. It reports the application path, its version, the `aerender` path and the pids of any
running After Effects, split into headless and UI instances. An application that is not installed is reported
in `error` rather than raised.

Call `ae_launch` to start the headless instance. Every other tool starts it when no After Effects is running, so
this is only needed to see the start-up cost on its own.

## One instance at a time

The server runs its scripts in one After Effects: a headless instance when one runs, else After Effects running
with its window, else a headless instance it starts. With the window open you watch each change happen in the
project open there. A call that targets another project opens it in the window, and is refused while the open
project has unsaved changes, so save your work first. While a dialog is open in the window, calls are refused
until you close it. Quit the headless instance from Activity Monitor when you are done, or leave it running for
the next call.
