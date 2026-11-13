"""Release identity and path rules shared by the documentation build and verify commands."""

import hashlib
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ID = "after-effects-mcp"
SOURCE_REL = f"docs/{PRODUCT_ID}/source"
OUTPUT_ROOT = REPO_ROOT / ".tmp" / "docs"
TOKENS = {"{{PRODUCT_VERSION}}": "version", "{{RELEASE_TAG}}": "tag", "{{RELEASE_COMMIT}}": "commit"}
UNRESOLVED_TOKEN = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
STABLE_VERSION = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
COMMIT_SHA = re.compile(r"^[a-f0-9]{40}$")


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.strip()


def default_identity():
    """The release this checkout documents: its newest vX.Y.Z tag and the commit at HEAD."""
    try:
        tag = git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("no vX.Y.Z release tag is reachable; fetch the tags or pass --version") from error
    commit = git("rev-parse", "HEAD")
    return {"version": tag.removeprefix("v"), "tag": tag, "commit": commit,
            "source_date_epoch": int(git("show", "-s", "--format=%ct", commit))}


def resolve_identity(values=None):
    """A checked release identity: ``values`` over the defaults taken from git."""
    values = {k: v for k, v in (values or {}).items() if v is not None}
    if "version" in values:
        values.setdefault("tag", f"v{values['version']}")
    if not {"version", "tag", "commit", "source_date_epoch"} <= values.keys():
        values = {**default_identity(), **values}
    version, tag, commit, epoch = values["version"], values["tag"], values["commit"], values["source_date_epoch"]
    if not STABLE_VERSION.fullmatch(version):
        raise ValueError(f"release version {version} is not X.Y.Z")
    if tag != f"v{version}":
        raise ValueError("release tag must match version")
    if not isinstance(commit, str) or not COMMIT_SHA.fullmatch(commit):
        raise ValueError("release commit must be a full lowercase SHA")
    if type(epoch) is not int or epoch < 0:
        raise ValueError("source date epoch must be a non-negative integer")
    generated = datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"version": version, "tag": tag, "commit": commit, "source_date_epoch": epoch, "generated_at": generated}


def stamp(text, release):
    for token, field in TOKENS.items():
        text = text.replace(token, release[field])
    return text


def parse_options(argv):
    """``--name value`` pairs as a dict; a flag without a value is ignored."""
    values, index = {}, 0
    while index < len(argv):
        if argv[index].startswith("--") and index + 1 < len(argv) and not argv[index + 1].startswith("--"):
            values[argv[index][2:]] = argv[index + 1]
            index += 2
        else:
            index += 1
    return values


def release_input(values):
    result = {key: values[key] for key in ("version", "tag", "commit") if key in values}
    if "source-date-epoch" in values:
        result["source_date_epoch"] = int(values["source-date-epoch"])
    return result


def list_files(root):
    """Every file below ``root`` as a sorted portable path; links and special files are refused."""
    files = []

    def walk(directory, relative):
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            name = f"{relative}/{entry.name}" if relative else entry.name
            path = Path(entry.path)
            if path.is_symlink():
                raise ValueError(f"documentation rejects symlink: {name}")
            if path.is_dir():
                walk(path, name)
            elif path.is_file():
                files.append(name)
            else:
                raise ValueError(f"documentation rejects non-file: {name}")

    walk(root, "")
    return sorted(files)


def content_sha256(root, paths):
    digest = hashlib.sha256()
    for relative in sorted(item for item in paths if item != "manifest.json"):
        digest.update(relative.encode() + b"\0" + (Path(root) / relative).read_bytes() + b"\0")
    return digest.hexdigest()


def navigation_paths(navigation):
    """The page paths of navigation.json, each checked to stay inside the pages folder and to appear once."""
    if not isinstance(navigation, dict) or not isinstance(navigation.get("sections"), list):
        raise ValueError("navigation.json missing sections array")
    pages = []
    for section in navigation["sections"]:
        if not isinstance(section, dict) or not isinstance(section.get("pages"), list):
            raise ValueError("navigation.json sections need pages arrays")
        for page in section["pages"]:
            path = page.get("path") if isinstance(page, dict) else None
            if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
                raise ValueError("navigation.json contains an unsafe page path")
            pages.append(path)
    if len(set(pages)) != len(pages):
        raise ValueError("navigation.json contains duplicate page paths")
    return pages


def manifest_for(release, digest):
    return {"schemaVersion": 2, "package": PRODUCT_ID, "product": PRODUCT_ID, "version": release["version"],
            "contentSha256": digest, "publicBasePath": f"/docs/{PRODUCT_ID}/v{release['version']}",
            "stableAlias": f"/docs/{PRODUCT_ID}", "release": {"tag": release["tag"], "commit": release["commit"]},
            "generatedAt": release["generated_at"]}
