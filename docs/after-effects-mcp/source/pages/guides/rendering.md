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
 "outputs": [{"comp": "Main", "file": "/path/to/out/main.mov", "frames": 150}]}}
```

`frames` is the frame count the finished movie must have. The tool works through three steps and reports which
one produced each movie in `path`:

1. `aerender` renders the saved project's queue.
2. Each movie that is missing, older than the call, unreadable or not exactly `frames` frames long is deleted
   and rendered again by itself, with the `render_settings` and `output_module` arguments.
3. A movie that is still wrong is made from `saveFrameToPng` frames and FFmpeg: `.mp4` as H.264, `.mov` as
   ProRes, from frame 0 at the comp's frame rate. Its `path` is `saveFrameToPng`. Any other extension is an
   error.

Frame counts are read with `ffprobe`. A render that ends with the wrong count after the fallback is an error that
names the comp, the count it has and the failure `aerender` reported.

The `rerendered` flag of each output says whether step 2 ran.

## Frames without a render

- `ae_frame` writes one PNG per time. `method: "auto"` uses `saveFrameToPng` and falls back to `aerender`
  through a temporary queue entry that is removed again; `method: "aerender"` uses only `aerender`. The comp
  background is in the frame; `alpha` keeps transparency instead. Up to 50 times per call.
- `ae_export_frames` writes `frame_00001.png` and on for a time range without `aerender`, and encodes a movie
  with FFmpeg when `movie` is given. `step` keeps every n-th frame, `max_frames` (default 1800, at most 5000)
  stops a range that is too long, and `alpha` with `codec: "prores"` writes a `.mov` with alpha. H.264 has no
  alpha.

## PNG sequences in a workspace

`after_effects_render` is the other render tool. It takes a recipe file in the workspace that declares the
project, its dependencies, one composition, an inclusive frame range of at most 1000 frames and 300 seconds,
a rational frame rate and an RGBA PNG output module. It renders into a new directory and returns a receipt of
the inputs and the contiguous frames. It never uses an instance you have open. It is provided by
`cavi-adobe-mcp`.
