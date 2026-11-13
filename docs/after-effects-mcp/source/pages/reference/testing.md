# Testing and evaluation

No Adobe application is needed for the checks below.

## Unit tests

```sh
uv run --locked ruff check .
uv run --locked pytest -q
```

The tests drive the real server over stdio and the real host and edit functions. They cover:

- the catalog: the registered tools match the list in the tests and the [tool reference](tools.md), each with
  the same parameters, result fields and access;
- refusals: the server lists every tool, and a recipe outside the workspace or an empty render list is refused
  without creating output;
- failures: non-finite numbers, oversized marker lists, missing scripts, unreadable reports, a wrong application
  override and simultaneous calls, each stopped before After Effects is called;
- documentation: the build is reproducible, the navigation lists every page once and every relative link
  resolves;
- FFmpeg movie checks, which skip when FFmpeg is not installed.

## Evaluations

```sh
uv run --locked python evals/run.py
```

The run starts the server over stdio with the application path pointing at a folder that does not exist, so no
call can start After Effects. It checks that the server lists 45 tools, each with a description and its access
annotation, that every tool rejects an unknown argument, and the cases in `evals/cases.json`: a missing script,
an out-of-range timeout and comp size, a non-finite frame rate, an oversized beat grid, the refused tools and a
recipe outside the workspace. It prints each failure and exits non-zero when there is one.

## Checked against After Effects

Behavior that needs the application is checked by hand: launch, scripts, frames and movies. See
[Version and support](../release/version-and-support.md) for the version and what was run.
