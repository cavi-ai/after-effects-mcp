# Contributing

## Setup

Install Python 3.15 or newer and [uv](https://docs.astral.sh/uv/), then:

```bash
git clone https://github.com/cavi-ai/after-effects-mcp.git
cd after-effects-mcp
uv sync --locked --dev
```

No Adobe application is required for the unit tests or the evaluations. Tests that need FFmpeg skip without it.

## Checks

```bash
uv run --locked ruff check .
uv run --locked pytest -q
uv run --locked python evals/run.py
```

A change to a script under `src/cavi_after_effects_mcp/jsx` is also tried in After Effects, headless (`ae_launch`
starts it). Quit it afterwards.

## Where changes go

- `app.py` holds the server object and the helpers every tool module shares.
- A tool lives in a module under `tools/` and imports `mcp` from `app.py`; `tools/__init__.py` imports the module.
- `host.py` starts After Effects, sends scripts over Apple Events and runs `aerender`. `edit.py` holds the
  helpers behind the frame, movie, project and template tools.
- `models.py` holds the typed inputs and results. Tool pages under `docs/after-effects-mcp/source/pages/reference`
  list every tool; a test fails when they differ from the registered tools.

Add a line under Unreleased in `CHANGELOG.md`. Versions come from git tags and are never edited in a pull request.
