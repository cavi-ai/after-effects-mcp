"""Build the versioned documentation tree from docs/after-effects-mcp/source."""

import json
import shutil
import sys
from pathlib import Path

from .lib import (
    OUTPUT_ROOT,
    REPO_ROOT,
    SOURCE_REL,
    UNRESOLVED_TOKEN,
    content_sha256,
    list_files,
    manifest_for,
    navigation_paths,
    parse_options,
    release_input,
    resolve_identity,
    stamp,
)


def expected_files(source_root, release):
    """Output path to stamped text for every source file; pages sit at the root of the output."""
    values = {}
    for source in list_files(source_root):
        text = stamp((Path(source_root) / source).read_text(encoding="utf-8"), release)
        if UNRESOLVED_TOKEN.search(text):
            raise ValueError(f"unresolved template token in {source}")
        values[source.removeprefix("pages/")] = text
    for page in navigation_paths(json.loads(values["navigation.json"])):
        if page not in values:
            raise ValueError(f"navigation path missing: {page}")
    return values


def build_documentation(values=None):
    values = values or {}
    release = resolve_identity(values)
    source_root = Path(values.get("source_root") or REPO_ROOT / SOURCE_REL).resolve()
    output_root = Path(values.get("output_root") or OUTPUT_ROOT / f"v{release['version']}").resolve()
    if source_root == output_root or output_root.is_relative_to(source_root):
        raise ValueError("documentation output must be outside the source tree")
    expected = expected_files(source_root, release)
    if output_root.exists():
        shutil.rmtree(output_root)
    for relative, text in expected.items():
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    manifest = manifest_for(release, content_sha256(output_root, list(expected)))
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"output_root": output_root, "manifest": manifest}


def main(argv=None):
    values = parse_options(sys.argv[1:] if argv is None else argv)
    try:
        result = build_documentation({**release_input(values),
                                      **({"output_root": values["output"]} if "output" in values else {})})
    except (ValueError, OSError, KeyError) as error:
        sys.stderr.write(f"{error}\n")
        return 1
    print(result["output_root"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
