# Troubleshooting

## "After Effects is running with its UI (pid N); quit it first"

The server only drives a headless instance it starts. Quit the After Effects window, then call `ae_launch`.

## "After Effects (pid N) exited during the call"

After Effects ended while a script ran. The next tool call starts it again, and the project is reopened from
disk, so an empty project is never saved over yours. If it happens on every call, look for the script that
caused it: calls into `layer.applyPreset`, `app.executeCommand` and `app.findMenuCommandId` end headless
After Effects, which is why they are refused.

## "Refused: ... calls applyPreset"

`ae_script` refuses a script that contains one of the three aborting calls and names the tool that does the job:
`ae_effect_add`, `ae_keyframes` and `ae_text_animator` for a look, `ae_keyframes` with an expression or keys
instead of Convert Audio to Keyframes. The same applies to `ae_preset_apply`, `ae_mogrt_export` and
`convert_to_keyframes` of `ae_audio`.

## "The open project has unsaved changes"

The instance holds edits that were not saved and the call targets a different project. Save them (`ae_project`
with `save`), or run the tool on the path that is open.

## "After Effects script failed" or "After Effects script: ..."

The first form means the Apple Event call itself failed or timed out: the message has the system error. The second
carries the errors the script reported, such as `No comp named X`. The project is reloaded from disk when it was
open and had changed.

## "The script saved no report" or "... holds an unreadable report"

The script ended without calling `caviReport`, or the saved project does not hold a complete report. For
`ae_script`, call `caviReport(object)` once at the end; otherwise its last value becomes the report.

## "numbers must be finite"

The arguments contain NaN or an infinite number. After Effects cannot take those; the call is refused before
anything runs.

## aerender leaves no movie

`aerender` exits without rendering when the Adobe Media Encoder service it starts fails. `ae_render_queue` and
`ae_frame` then use the frame fallback; see [Rendering and the fallback](rendering.md). Run `ae_status` to check
that `aerender` is next to the application.

## "Install ffprobe (FFmpeg)" or "Install ffmpeg"

Frame counts need `ffprobe`; movies written without `aerender` need `ffmpeg`. Install FFmpeg
(`brew install ffmpeg`). Both are found on `PATH` and in the Homebrew locations.

## Things After Effects does not allow from scripts

Gradient color stops (`ae_shape_add` uses the default stops), the output module's format, channels, depth and
color (`ae_render_queue_set`) and the `.mogrt` file written headless are not available. Each tool refuses or
says so where it applies.
