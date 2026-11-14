# Your first comp

This builds a 3.5-second lower third over a shot: the footage pushes in, a name bar slides in from the left,
an accent line grows, and two lines of text rise in. Every path is absolute; replace `/path/to` with a folder
you own. The shot is `examples/first-result/media/aisle.mp4` in the repository, and the calls are the ones
`examples/first-result/run.py` makes.

## 1. Create the comp

```json
{"tool": "ae_comp_new", "arguments": {"project": "/path/to/title.aep", "name": "Title", "width": 1280,
 "height": 720, "duration": 3.5, "fps": 24, "background": [0.02, 0.02, 0.06], "replace": true}}
```

The project is created and saved on the first call. `background` is RGB from 0 to 1.

## 2. Add the shot and push in

```json
{"tool": "ae_layer_add", "arguments": {"project": "/path/to/title.aep", "layer": {"comp": "Title",
 "kind": "footage", "name": "Aisle", "file": "/path/to/aisle.mp4"}}}
{"tool": "ae_keyframes", "arguments": {"project": "/path/to/title.aep", "comp": "Title", "layer": "Aisle",
 "property": "scale", "keyframes": [{"time": 0, "value": [100, 100]}, {"time": 3.5, "value": [108, 108]}]}}
```

The footage is imported on first use. A layer is addressed later by its 1-based index or its name.

## 3. Slide in the name bar

```json
{"tool": "ae_layer_add", "arguments": {"project": "/path/to/title.aep", "layer": {"comp": "Title",
 "kind": "shape_rect", "name": "Bar", "fill": [0.02, 0.03, 0.09], "width": 600, "height": 132,
 "transform": {"position": [380, 590], "opacity": 82}}}}
{"tool": "ae_keyframes", "arguments": {"project": "/path/to/title.aep", "comp": "Title", "layer": "Bar",
 "property": "position", "keyframes": [{"time": 0.2, "value": [-320, 590]}, {"time": 0.7, "value": [380, 590]}],
 "easy_ease": true}}
```

A `shape_rect` is centered on its position and needs `fill` or `stroke`; `color` applies only to solids. The
accent is a second rectangle, 8 by 132 at `[84, 590]` with a cyan `fill`, whose `scale` goes from `[100, 0]`
at 0.6 seconds to `[100, 100]` at 0.9.

## 4. Add the text and reveal it

```json
{"tool": "ae_layer_add", "arguments": {"project": "/path/to/title.aep", "layer": {"comp": "Title",
 "kind": "text", "name": "Headline", "text": "Aisle B", "font": "AvenirNext-Bold", "size": 64,
 "fill": [1, 1, 1], "transform": {"position": [108, 585]}}}}
{"tool": "ae_text_animator", "arguments": {"project": "/path/to/title.aep", "comp": "Title",
 "layer": "Headline", "opacity": 0, "position": [0, 24], "start": 0.55, "duration": 0.6}}
```

The animator's range selector opens over the characters from 0.55 seconds for 0.6 seconds, so each letter
fades in and rises 24 pixels into place. The second line, "Racks online at 02:00" in `AvenirNext-Medium` at
size 28, fades in the same way from 0.9 seconds.

## 5. Look at it

```json
{"tool": "ae_frame", "arguments": {"project": "/path/to/title.aep", "comp": "Title", "times": [0.5, 1, 2.5],
 "directory": "/path/to/frames"}}
```

The result lists `Title_0.5s.png`, `Title_1s.png` and `Title_2.5s.png`. At 0.5 seconds the bar is sliding in;
at 1 second the headline is rising in and the second line has started; at 2.5 seconds the title is complete.

## Next

`ae_inspect` with `scope: "comp"` lists the layers and their keyframed properties. `ae_properties` reads one
layer's whole property tree. See the [tool reference](../reference/tools.md) for the rest, and
[Rendering and the fallback](rendering.md) to write a movie.
