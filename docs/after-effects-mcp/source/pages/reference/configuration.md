# Configuration

The server is configured with environment variables, set in the `env` of its entry in the MCP client.

| Variable | Used by | Meaning |
|---|---|---|
| `CAVI_AFTER_EFFECTS_APP` | every tool that starts or finds After Effects | Absolute path of the `.app` to use. It must be After Effects (bundle identifier `com.adobe.AfterEffects.application`); a wrong path is reported, never replaced by another install. `aerender` and the `Presets` folder are taken from the folder that holds the app. Default: the newest `Adobe After Effects 20*` under `/Applications`. |
| `CAVI_ADOBE_WORKSPACE` | `after_effects_render` | Absolute workspace folder; the recipe and the output directory are relative to it and must stay inside it. |
| `CAVI_ADOBE_DATA` | `cavi-adobe-mcp` | Private state directory of the shared Adobe package; default `~/.local/share/cavi-adobe-mcp`. |

## Fixed limits

| Limit | Value |
|---|---|
| Script call timeout (`ae_script`) | 10 to 3600 seconds, default 900 |
| Scene tool timeout | 300 seconds (120 for the listing tools) |
| `aerender` timeout | 3600 seconds |
| Markers per call | 5000 |
| Times per `ae_frame` call | 50 |
| `max_frames` of `ae_export_frames` | 5000, default 1800 |
| Comp size | 4 to 30000 pixels per side, up to 10800 seconds, up to 240 fps |

## Dependencies

The server depends on `cavi-adobe-mcp` (the `after_effects_render` implementation and the result base type) and
`cavi-mcp-core` (application lookup, bounded subprocesses, the server type), each by version range.
