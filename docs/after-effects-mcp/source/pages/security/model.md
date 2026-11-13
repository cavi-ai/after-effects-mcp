# Security model

## Scripts run with your permissions

`ae_script` runs a `.jsx` file you choose inside After Effects, and the scene tools run packaged scripts the
same way. ExtendScript can read and write any file you can. Connect the server only to clients you trust.
`ae_script` is annotated destructive for that reason.

Scripts that call `applyPreset`, `executeCommand` or `findMenuCommandId` are refused before they run, because
those calls abort headless After Effects. The list protects the application from crashes; it does not limit
what other script code can do.

## Files

Tools read and write the absolute paths a caller gives them: projects, footage, output movies and frame
folders. They are not confined to a workspace. Relative paths are refused. `after_effects_render` is the
exception: its recipe and output directory must stay inside `CAVI_ADOBE_WORKSPACE`, it writes only to a new
directory, and it checks that no input changed while the render ran.

Scripts cannot write files while After Effects runs headless, so each call's report travels inside the saved
project (a folder item named `cavi-report`). Call reports are not sent anywhere.

## Applications

The server starts one headless After Effects (`-noui`) and never attaches to a window you have open. It
does not start any other Adobe application. `aerender`, which After Effects' own render path launches, may start
its helper services.

## No background activity

The server speaks MCP over stdio. It makes no network connections, sends no telemetry, uses no accounts and
does not install software, accept terms or dismiss license prompts. It does not retry a call by itself.

## Reporting a problem

Report vulnerabilities privately as described in the repository's `SECURITY.md`.
