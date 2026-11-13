# First result

`run.py` starts the server over stdio, then calls `ae_status`, `ae_launch`, `ae_comp_new`, `ae_layer_add`,
`ae_text_animator`, `ae_markers`, `ae_frame` and `ae_inspect` against headless After Effects. It builds a
3-second 1280 x 720 comp `Title` whose text "Hello, After Effects" types on, sets 6 beat markers at 120 bpm and
writes two frames.

```sh
uv run python examples/first-result/run.py /path/to/an/empty/folder
```

The folder receives `hello.aep` and `frames/`. Each call prints its name, `ok` or `ERROR`, and the start of its
result. The script starts After Effects without its UI; quit it afterwards.

The frames from a run on After Effects 26.5.0 are next to this file: `Title_0.2s.png` shows the first letter and
`Title_2.5s.png` the whole line.
