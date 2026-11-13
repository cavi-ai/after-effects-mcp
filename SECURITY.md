# Security Policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's private vulnerability reporting:
<https://github.com/cavi-ai/after-effects-mcp/security/advisories/new>. Do not open a public issue.
Include affected versions, reproduction steps and impact. Do not include Adobe account details or project files.

## Supported versions

Until 1.0, security fixes go to the latest minor release and `main`.

## Scope

- `ae_script` runs a caller-chosen `.jsx` file in After Effects with the user's permissions, and the scene
  tools run packaged scripts the same way. Connect the server only to clients you trust.
- Scripts that call `applyPreset`, `executeCommand` or `findMenuCommandId` are refused because they abort
  headless After Effects. That list protects the application from crashes; it is not a sandbox.
- Tools read and write the absolute paths a caller gives them. `after_effects_render` is confined to the
  workspace folder.
- The server speaks MCP over stdio, sends no telemetry and uses no accounts.
- Adobe applications and their licenses are out of scope; report those to Adobe.
