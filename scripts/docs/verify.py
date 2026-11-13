"""Verify that built documentation is complete and matches its manifest."""

import json
import sys
from pathlib import Path

from .lib import (
    OUTPUT_ROOT,
    UNRESOLVED_TOKEN,
    content_sha256,
    list_files,
    manifest_for,
    navigation_paths,
    parse_options,
    release_input,
    resolve_identity,
)


def verify_documentation(values=None):
    values = values or {}
    release = resolve_identity(values)
    root = Path(values.get("output_root") or OUTPUT_ROOT / f"v{release['version']}").resolve()
    paths = list_files(root)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("documentation manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest != manifest_for(release, content_sha256(root, paths)):
        raise ValueError("documentation manifest is inconsistent with built content")
    for page in navigation_paths(json.loads((root / "navigation.json").read_text(encoding="utf-8"))):
        if not (root / page).is_file():
            raise ValueError(f"navigation path is not a file: {page}")
    for relative in paths:
        if UNRESOLVED_TOKEN.search((root / relative).read_text(encoding="utf-8")):
            raise ValueError(f"unresolved template token in {relative}")
    return manifest


def main(argv=None):
    values = parse_options(sys.argv[1:] if argv is None else argv)
    try:
        manifest = verify_documentation({**release_input(values),
                                         **({"output_root": values["output"]} if "output" in values else {})})
    except (ValueError, OSError, KeyError) as error:
        sys.stderr.write(f"{error}\n")
        return 1
    print(json.dumps(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
