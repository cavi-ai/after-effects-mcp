# Results and errors

Every tool returns the result and error shapes of the
[MCP Core contract](https://github.com/cavi-ai/mcp-core/blob/main/docs/mcp-core/source/pages/reference/results-and-errors.md):
structured content that matches the tool's output schema, and on failure an `error` with `code`, `outcome`
and `next_action`. This page lists what this server adds.

## Recovery tool

An `unknown` outcome names `ae_inspect` as its `next_action`. List the project and its render queue, and check
the output files, before calling again.

## Codes

| `code` | `outcome` | When |
|---|---|---|
| `AE_UI_RUNNING` | `rejected` | After Effects is running with its UI. Quit it, then call `ae_launch`. |
| `AE_PROJECT_UNSAVED` | `rejected` | The open project has unsaved changes and the call targets another project. Save it, or run the tool on the open path. |
| `AE_SCRIPT_REFUSED` | `rejected` | A typed tool's script failed and the project was reloaded as saved before the call. |
| `AE_RENDER_BUSY` | `rejected` | A background render is running. Wait for it with `ae_render_status` or stop it with `ae_render_cancel`. |

Each has `next_action` `inspect_inputs`. An argument the chosen action does not read, such as `time` for
`ae_layer_edit` `delete` or `overwrite` for `ae_project` `open`, is refused as `INVALID_ARGUMENT` before After
Effects is called.
