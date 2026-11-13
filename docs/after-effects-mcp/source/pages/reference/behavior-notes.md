# Measured behavior

What headless After Effects does, measured with After Effects 2026 on macOS. Tool descriptions and error
messages refer to these notes by number.

1. Headless After Effects (`-noui`) has no BridgeTalk. `DoScript` returns only `0` (success) or `1` (any failure),
   and scripts cannot write files (`Comp.saveFrameToPng` aside, note 34). Reports travel inside the saved project.
2. Headless After Effects starts with a project open, and `app.newProject()` crashes it. Scripts reuse the open
   project: remove its items and render queue entries instead.
3. `$.evalFile` of a file with a syntax error aborts `DoScript` before any `catch` runs. ExtendScript is ES3, so
   Java-era reserved words such as `final` are syntax errors there while `node --check` accepts them. The runner's
   compile check turns these into messages.
4. With the comp renderer set to Advanced 3D (`ADBE Calder`), adding an effect to a 3D layer, or setting
   `layer.motionBlur` on a 3D shape layer, aborts the script uncatchably. Extrusion depth, lights, cameras and
   rotation work. Renderers listed: `ADBE Advanced 3d` (Classic 3D), `ADBE Calder` (Advanced 3D), `ADBE Ernst`
   (Cinema 4D).
5. A full-frame Glow (`ADBE Glo2`) adjustment lifts dark blues: a dark navy solid gains about +50 in the blue
   channel at threshold 70, in 8 and 16 bpc.
6. `ae_effect_add` on a 3D layer and `ae_layer_add` with `motion_blur` on a 3D rectangle shape are refused with a
   message, before the call that would abort After Effects, while the comp renderer is `ADBE Calder`.
7. Every script call watches the headless pid: if After Effects exits during the call it fails at once with that
   message instead of waiting for the timeout. A call with no headless instance starts one.
8. `output_module` templates seen: `High Quality`, `High Quality with Alpha`, `Lossless`, `Lossless with Alpha`,
   `Alpha Only`, `H.264 - Match Render Settings - 15 Mbps`, `Photoshop`, `TIFF Sequence with Alpha`. Render queue
   status names are `QUEUED`, `UNQUEUED`, `DONE` and so on.
9. `ae_inspect` reports cameras and lights as 3D although their `threeDLayer` reads false.
10. Completion runs 0 to 100 on the stock transition effects and 0 to 1 on some CC ones (CC Twister). CC Line Sweep
    was not installed on the measured machine.
11. `aerender` skips a queue entry with render off, and renders the others in the saved project, so a queue holding
    other comps renders them too.
12. `layer.applyPreset` of a `.ffx` animation preset exits the headless instance within two seconds (measured with
    `3D Basic Position Z Cascade In` and `Center Spiral In`); the call fails with the exited-during-the-call error
    of note 7.
13. `aerender` can crash mid-queue and still exit 0, so every output's frame count is checked. A ProRes movie with
    a timecode track lists `nb_frames` twice in `ffprobe`; the first value is the video stream's.
14. After Effects opens a saved project headless with `app.open`, and `app.project.dirty` is readable. A call that
    fails saves its report into the open project, so `ae_project` sends refusals to a temporary project and a
    refused open leaves the project on disk untouched.
15. An output module's `Format` is read-only from scripts and no PNG template ships, so `ae_frame` renders the
    `TIFF Sequence with Alpha` template and converts each frame with `sips`. The frames carry alpha, so `ae_frame`
    adds a solid of the comp's background color at the bottom for the render and removes it afterwards unless
    `alpha`.
16. A sequence output file with no `[#####]` in its name gets the frame number appended after the extension
    (`f0_.tif00015`); `ae_frame` names its files `f<n>_[#####].tif`.
17. A locked layer refuses every other change, so `ae_layer_set` unlocks first and locks last. `setTrackMatte`
    switches the matte layer's video off (`enabled` false).
18. `conformFrameRate` is refused for a still, `boxTextSize` for point text and `setValue` for a keyed property;
    the calls fail with After Effects' message.
19. A shape gradient's color stops (`ADBE Vector Grad Colors`) have no value type, so scripts can neither read nor
    set them: `ae_shape_add` gradients take the default stops (white to black) and set type, start and end.
20. A new shape layer sits at the comp center; `ae_shape_add` moves it to the origin so group positions are comp
    pixels. Wiggle Paths is `ADBE Vector Filter - Roughen`. Stroke dashes exist only after `addProperty` on the
    Dashes group. A camera's point of interest is `ADBE Anchor Point`.
21. Parenting a camera to an orbit null keeps its view: its position reads relative to the null afterwards.
22. `OutputModule.setSettings` refuses `Format`, `Channels`, `Depth` and `Color` as read-only; alpha, depth and
    color come from the template (`High Quality with Alpha` gives `RGB + Alpha`). It accepts `Resize` with
    `Resize to` `[w, h]`, `Resize Quality` `Low` or `High` (not `Medium`), `Crop` with
    `Crop Top/Left/Bottom/Right`, `Output Audio` `On`, `Off` or `Auto`, `Audio Sample Rate`, `Audio Channels` and
    `Audio Bit Depth` (`16 Bit`). A render of one entry with resize, a time span and audio on gave a 320x180
    ProRes 4444 movie with alpha, 30 frames and a mono 44.1 kHz audio stream; an entry with crop and audio off
    gave 620x340 with no alpha and no audio stream.
23. `comp.exportAsMotionGraphicsTemplate` returns true in headless After Effects and writes no file: it creates an
    empty folder at the given path. `addToMotionGraphicsTemplateAs`, `motionGraphicsTemplateName` and the
    controller list work, so `ae_essential_graphics` prepares the comp and the `.mogrt` has to be exported from a
    window.
24. The scripting method is `app.project.consolidateFootage` (there is no `consolidateAllFootage`); `reduceProject`
    takes an array of comps and returns the number of removed items.
25. `app.findMenuCommandId("Convert Audio to Keyframes")` returns 4218, and `app.executeCommand(4218)` on a
    selected audio layer exits the headless instance (measured twice), so `ae_audio` refuses it.
26. Audio Levels fades and levels are measured with `volumedetect` on a rendered movie with audio on: a 440 Hz tone
    at -21.1 dB gave -27.1 dB in the middle at a -6 dB level, -82.5 dB in the first and last quarter second of a
    0.5 s fade in and out, and -91 dB with the layer's audio off.
27. Removing every key of Time Remap hides the property (`setValueAtTime` then fails), so new keys are set first
    and the old ones dropped. `layer.frameBlending` is read-only; `frameBlendingType` sets the mode (4012 none,
    4013 mix, 4014 pixel motion). A reversed layer shows between its out and in points.
28. Text animator properties and selectors are added with `addProperty` on the animator's property group, and every
    property reference goes invalid once a sibling is added, so the animator is fetched by index each time. Match
    names: `ADBE Text Fill Color`, `ADBE Text Stroke Color`, `ADBE Text Stroke Width`, `ADBE Text Skew`,
    `ADBE Text Character Offset`, `ADBE Text Rotation X`/`Y`; selectors `ADBE Text Selector` (range),
    `ADBE Text Wiggly Selector` and `ADBE Text Expressible Selector` (the expression selector).
29. A dropdown Expression Control is `ADBE Dropdown Control`; `setPropertyParameters` rebuilds the effect, so it is
    fetched again from the end of the effect parade and renamed afterwards. Controls are told apart by their
    parameter name (Slider, Angle, Point, 3D Point, Color, Checkbox, Layer, Menu).
30. Every project setting is settable, including 32 bits per channel with linear blending. A value other than
    8, 16 or 32 bits is refused by After Effects; an unknown working space name is silently stored as `None`, so
    `ae_project_settings` refuses names not in `listColorProfiles()`. `revision` and `numItems` are read-only. The
    GPU types CUDA, OpenCL, DirectX and Vulkan are not offered; metal and software set.
31. `.glb`, `.gltf` and `.obj` import as footage and `comp.layers.add` makes a 3D model layer
    (`ADBE 3D Model Layer`) in an Advanced 3D comp; other renderers are refused. `fit` (default on) sets the layer
    centered with scale `0.6 * comp height / (largest extent of sourceRectAtTime * sqrt(3))` percent; a 2-unit cube
    is 1024 px at 100%, so it gets 20.3% in a 360 px comp. `fit: false` keeps the raw import, which fills the
    frame. A model without normals renders flat gray whatever the lights; with normals an environment light alone
    shades the faces. An environment light is invisible itself, so a comp holding only one renders like an empty
    comp. The model layer's out point is set to the comp duration.
32. `RQItem.setSettings` accepts Quality (Wireframe, Draft, Best), Resolution (Full, Half, Third, Quarter), Proxy
    Use (Use No Proxies, Use Comp Proxies Only, Use All Proxies), Effects (All On, All Off, Current Settings),
    Motion Blur and Frame Blending (On for Checked Layers, Off for All Layers, Current Settings). `Frame Rate`
    itself is refused; setting the number `Use this frame rate` switches the mode. `RQItem.duplicate()` and
    `remove()` work. An aerender at half resolution and 12 fps wrote 160x90 at 12 fps with 24 frames.
33. A nested comp layer exposes `layer.essentialProperty` as a group named Essential Properties whose properties
    carry the names given in `ae_essential_graphics`; setting a text property takes a `TextDocument`.
34. `Comp.saveFrameToPng` writes a PNG from a headless script, so `ae_frame` uses it first and falls back to
    aerender, which exits without rendering (no error, no frames) while another Adobe application holds Dynamic
    Link. A temporary background solid is added for the composite and removed again; `alpha` keeps transparency.
35. Layer styles (drop shadow, stroke, glow ...) stay hidden until enabled: `canSetEnabled` is false,
    `addProperty` refuses, and `findMenuCommandId` returns no usable id, so no layer style tool is offered.
36. Material options that accept a value, per renderer. Classic 3D (`ADBE Advanced 3d`): casts shadows, light
    transmission, accepts shadows and lights, ambient, diffuse, specular intensity and shininess, metal. Advanced
    3D (`ADBE Calder`): the same without light transmission, plus shadow color. Cinema 4D (`ADBE Ernst`): no light
    transmission or shadow color, plus appears in reflections and reflection intensity, sharpness and rolloff.
    Transparency, transparency rolloff and index of refraction are hidden for solids in all three.
37. A script that fails leaves no partial edits: the runner reloads the project from disk when the target was
    changed. Every call first opens its target project when another one, or none, is open (a restarted instance has
    an empty project) and refuses when the open project has unsaved changes. A tool call starts the headless
    instance when none runs. `ae_script` refuses scripts calling `applyPreset`, `executeCommand` and
    `findMenuCommandId`, which abort After Effects (crash reports show `ApplyPreset` and `DoCommandIfEnabled`).
38. `ae_export_frames` calls `Comp.saveFrameToPng` once per frame in one script, then waits for the files, because
    the PNGs land after the script returns. A comp whose frames are 161x91 encodes to H.264 at 160x90 (even sizes
    only); ProRes 4444 keeps odd sizes and alpha.
39. `saveFrameToPng` frames match aerender frames: the same frame of a classic 3D comp and of an Advanced 3D comp
    (3D solids and a light) is pixel-identical (PSNR infinite), and a glb model layer under an environment light
    differs by under one level (PSNR 78.6 dB). The queue fallback encodes the comp from frame 0 for the declared
    frame count, so it matches an aerender movie only for a render of the comp's start; a work area elsewhere is
    not honored.
