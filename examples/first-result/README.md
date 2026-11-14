# First result

A lower third over a shot, built and rendered by headless After Effects through the server. The frames are
from 0.5, 1 and 2.5 seconds: the name bar sliding in, the headline rising in, and the finished title.

![Three frames of a server aisle: a dark name bar sliding in from the left, the headline "Aisle B" rising in, and the finished lower third with "Racks online at 02:00"](title-sequence.png)

## The input

[media/aisle.mp4](media/aisle.mp4) is a forward dolly down a server aisle, 3.75 seconds, 1280 by 720 at 24
fps. It was generated with Wan 2.1 text-to-video; it is part of this repository and covered by its
[MIT license](../../LICENSE).

## Reproduce it

```sh
uv run --locked python examples/first-result/run.py /path/to/an/empty/folder
```

[run.py](run.py) starts the server over stdio and calls `ae_status`, `ae_launch`, `ae_comp_new`,
`ae_layer_add`, `ae_keyframes`, `ae_text_animator`, `ae_frame` and `ae_inspect`. The folder receives
`title.aep` and `frames/`. Each call prints its name, `ok` or `ERROR`, and its result; the script stops at
the first error. After Effects runs without its UI; quit it afterwards. The calls with their arguments are
explained in [Your first comp](../../docs/after-effects-mcp/source/pages/guides/first-comp.md).

## What it returned

The comp `Title` is 1280 by 720, 3.5 seconds at 24 fps, with five layers: the `Aisle` footage with keyed
scale, the `Bar` and `Accent` rectangles with keyed position and scale, and the `Headline` and `Subline` text
layers, each with one animator. [Title_2.5s.png](Title_2.5s.png) is the full-size finished frame from a run
on After Effects 26.5.0.
