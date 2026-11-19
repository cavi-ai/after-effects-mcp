# Rendering and the fallback

## Queue a render

`ae_render_queue_set` fills the project's render queue: each entry of `add` names a comp, an absolute output
`file`, an `output_module` and `render_settings` template (as `ae_presets` lists them), a `time_span`
(`work_area`, `comp` or `{start, duration}`), render `settings` (quality, resolution, proxy use, effects, motion
blur, frame blending, frame rate) and the `output` settings scripts can set (resize, crop, audio). `update`
entries turn items on or off, label them, change their settings, duplicate or remove them. `clear` first removes
the entries of the comps in `add`. The queue is listed afterwards.

Output format, channels, depth and color cannot be set from scripts. Pick an output module template such as
`High Quality with Alpha` instead.

## Render it

```json
{"tool": "ae_render_queue", "arguments": {"project": "/path/to/cut.aep",
 "outputs": [{"comp": "Main", "file": "/path/to/out/main.mov"}]}}
```

Each output names a queue entry by its comp and output `file`; an output with no entry is refused. The entry's
time span at its frame rate sets the frame count the output must have. `frames`, when given, must equal it, or
the call is refused before anything renders. Output folders are created first, since After Effects renders
nothing into a missing one. The tool works through three steps and reports which one produced each output in
`path`:

1. `aerender` renders the saved project's queue.
2. Each output that is missing, older than the call, unreadable or short of its frames is deleted and rendered
   again by itself from its entry (`aerender -rqindex`), with the entry's templates, time span and settings.
3. A movie that is still wrong is made from `saveFrameToPng` frames of the entry's time span and FFmpeg: `.mp4`
   as H.264, `.mov` as ProRes. Its `path` is `saveFrameToPng`. Any other extension, and an entry with its own
   frame rate, is an error.

Movie frame counts are read with `ffprobe`. An image sequence output keeps its `[#####]` in `file` and counts the
non-empty frame files written during the call. An audio-only output, such as the `AIFF 48kHz` template, counts
its duration in frames at the entry's frame rate. A render that ends with the wrong count after the fallback is an
error that names the comp, the count it has and the failure `aerender` reported.

The `rerendered` flag of each output says whether step 2 ran.

## Render in the background

```json
{"tool": "ae_render_start", "arguments": {"project": "/path/to/cut.aep",
 "output": {"comp": "Main", "file": "/path/to/out/main.mov"}}}
```

`ae_render_start` checks the output against its queue entry as `ae_render_queue` does, starts
`aerender -rqindex` for that entry and returns its `job` at once. The render runs under a resident owner from
`cavi-mcp-core`, so it continues if the server exits; its files live in `cavi-after-effects-renders` in the
temporary folder. One render runs at a time: a second start while one runs is refused as `AE_RENDER_BUSY`.

`ae_render_status` reads a job: `running`, `done` (aerender exited 0 and the output has every frame), `failed`,
`cancelled` or `unresolved`, with `done` frames from the aerender log and, once it ended, `written` frames read
from the output. With `wait`, it waits up to that many seconds for the render to end and reports the frames as
MCP progress. `ae_render_cancel` stops the render and waits up to 30 s for it; the output is left as aerender
wrote it. A job that ends without its frames also stops its `aerendercore`, which aerender starts outside its
own process group and which ignores SIGTERM. There is no fallback to `saveFrameToPng` frames.

## Frames without a render

- `ae_frame` writes one PNG per time. `method: "auto"` uses `saveFrameToPng` and falls back to `aerender`
  through a temporary queue entry that is removed again; `method: "aerender"` uses only `aerender`. The comp
  background is in the frame; `alpha` keeps transparency instead. Up to 50 times per call. The first
  `previews` frames (default 4, at most 16, 0 for none) also come back in the result as PNG images at most
  768 px on the long side, so the client sees them without opening the files.
- `ae_export_frames` writes `frame_00001.png` and on for a time range without `aerender`, and encodes a movie
  with FFmpeg when `movie` is given. `step` keeps every n-th frame, `max_frames` (default 1800, at most 5000)
  stops a range that is too long, and `alpha` with `codec: "prores"` writes a `.mov` with alpha. H.264 has no
  alpha.

## PNG sequences in a workspace

`after_effects_render` is the other render tool. It takes a recipe file in the workspace that declares the
project, its dependencies, one composition, an inclusive frame range of at most 1000 frames and 300 seconds,
a rational frame rate and an RGBA PNG output module. It renders into a new directory and returns a receipt of
the inputs and the contiguous frames. It never uses an instance you have open.
