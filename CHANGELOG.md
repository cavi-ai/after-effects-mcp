# Changelog

Versions come from git tags; a pull request adds its lines under Unreleased and never edits a version.

## Unreleased

### Added

- `ae_project` `new` saves an empty project at a path.

### Fixed

- A call on a project path with no file starts it only from an untitled, empty project; otherwise it is refused, so
  a new project no longer inherits the items of the project open before it.
- `ae_template_render` saves the opened template to `project` before filling it, so an existing `project` file is
  replaced by the filled template instead of being edited, and its queue entries no longer fail on missing render
  settings.
- Reports escape every control character, so a text, marker comment or other value holding one is returned as it is
  in the project instead of without it.

## 0.1.1 - 2026-11-16

### Changed

- No longer depends on `cavi-adobe-mcp`; `after_effects_render` writes its receipt through `cavi-mcp-core`.

## 0.1.0 - 2026-11-14

### Added

- `CAVI_AFTER_EFFECTS_APP` chooses the application bundle.
- `ae_status` reports an application that is not installed in `error` instead of failing.
- LICENSE, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, a release workflow, documentation under
  `docs/after-effects-mcp`, evaluations and package metadata.
- Issue and pull request templates; CI runs the evaluations.
- `examples/first-result` builds an animated lower third over real footage in headless After Effects.

### Changed

- Depends on `cavi-adobe-mcp` and `cavi-mcp-core` by version range; the application is found through
  `cavi-mcp-core`.
- Tools live in `tools/` modules, the server object and shared helpers in `app.py`.
- `after_effects_render` uses the implementation in `cavi-adobe-mcp`.
- FFmpeg is found the same way for encoding and for frame checks.

### Fixed

- NaN and infinite numbers are refused before After Effects is called.
- A beat grid or marker list of more than 5000 markers is refused instead of building an unbounded list.
- A missing script file is named; a report without its end marker is reported as unreadable.
- The application's render engine and other helpers are no longer counted as a running After Effects.
- Two simultaneous calls take turns instead of interleaving scripts in the same instance.
- A `shape_rect` layer with neither fill nor stroke is refused instead of being added invisible.
