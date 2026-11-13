# Your first comp

This builds a 3-second title comp with a text layer that types on, a beat grid of markers, and two PNG frames.
Every path is absolute; replace `/path/to` with a folder you own. The calls are the ones in the
repository README's first result.

## 1. Create the comp

```json
{"tool": "ae_comp_new", "arguments": {"project": "/path/to/hello.aep", "name": "Title", "width": 1280,
 "height": 720, "duration": 3, "fps": 30, "background": [0.05, 0.07, 0.12], "replace": true}}
```

The project is created and saved on the first call. `background` is RGB from 0 to 1.

## 2. Add a text layer

```json
{"tool": "ae_layer_add", "arguments": {"project": "/path/to/hello.aep", "layer": {"comp": "Title",
 "kind": "text", "name": "Headline", "text": "Hello, After Effects", "size": 90, "fill": [1, 1, 1],
 "justification": "center", "transform": {"position": [640, 380]}}}}
```

A layer is addressed later by its 1-based index or its name.

## 3. Animate it

```json
{"tool": "ae_text_animator", "arguments": {"project": "/path/to/hello.aep", "comp": "Title",
 "layer": "Headline", "opacity": 0, "duration": 1.2}}
```

The animator's range selector opens over characters for 1.2 seconds, so the letters appear one by one.

## 4. Mark the beats

```json
{"tool": "ae_markers", "arguments": {"project": "/path/to/hello.aep", "comp": "Title",
 "grid": {"bpm": 120, "end": 3}}}
```

This sets a marker on every beat before 3 seconds, commented bar.beat, with a chapter on each downbeat.

## 5. Look at it

```json
{"tool": "ae_frame", "arguments": {"project": "/path/to/hello.aep", "comp": "Title", "times": [0.2, 2.5],
 "directory": "/path/to/frames"}}
```

The result lists `Title_0.2s.png` and `Title_2.5s.png`. At 0.2 seconds only the first letter shows; at 2.5
seconds the whole line does.

## Next

`ae_inspect` with `scope: "comp"` lists the layers and their keyframed properties. `ae_properties` reads one
layer's whole property tree. See the [tool reference](../reference/tools.md) for the rest, and
[Rendering and the fallback](rendering.md) to write a movie.
