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

Call `ae_launch` to start the headless instance. Every other tool starts it when it is not running, so this is
only needed to see the start-up cost on its own.

## One instance at a time

The server drives a headless instance it starts itself. If After Effects is already running with its window,
`ae_launch` stops with the pid and asks you to quit it first; the server never takes over a window. Quit the
headless instance from Activity Monitor when you are done, or leave it running for the next call.
