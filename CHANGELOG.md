# Changelog

Versions come from git tags; a pull request adds its lines under Unreleased and never edits a version.

## Unreleased

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
