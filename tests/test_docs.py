import asyncio
import hashlib
import json
import posixpath
import re
import tempfile
import unittest
from pathlib import Path

from cavi_after_effects_mcp.server import mcp
from scripts.docs.build import build_documentation
from scripts.docs.lib import REPO_ROOT, SOURCE_REL, list_files, navigation_paths
from scripts.docs.verify import verify_documentation

IDENTITY = {"version": "1.2.3", "tag": "v1.2.3", "commit": "0123456789abcdef0123456789abcdef01234567",
            "source_date_epoch": 1700000000}
PAGES = Path(REPO_ROOT) / SOURCE_REL / "pages"
ROW = re.compile(r"^\| `([a-z_]+)` \| (read-only|write|destructive) \| (.*?) \| (.*?) \| .+ \|$")


def digest(root):
    result = hashlib.sha256()
    for relative in list_files(root):
        result.update(relative.encode() + b"\0" + (Path(root) / relative).read_bytes() + b"\0")
    return result.hexdigest()


def names(cell):
    return {match[0] for match in re.findall(r"`(\w+)`(\*?)", cell)}


def required(cell):
    return {match[0] for match in re.findall(r"`(\w+)`(\*?)", cell) if match[1]}


def access(tool):
    if tool.annotations.read_only_hint:
        return "read-only"
    return "destructive" if tool.annotations.destructive_hint else "write"


class DocumentationBuildTest(unittest.TestCase):
    def test_build_is_stamped_complete_and_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "first", Path(temp) / "second"
            build_documentation({**IDENTITY, "output_root": first})
            build_documentation({**IDENTITY, "output_root": second})
            self.assertEqual(digest(first), digest(second))
            manifest = json.loads((first / "manifest.json").read_text())
            self.assertEqual(manifest["version"], "1.2.3")
            self.assertEqual(manifest["release"], {"tag": "v1.2.3", "commit": IDENTITY["commit"]})
            self.assertEqual(manifest["generatedAt"], "2023-11-14T22:13:20.000Z")
            text = (first / "release/version-and-support.md").read_text()
            self.assertIn("`v1.2.3`", text)
            self.assertNotRegex(text, r"\{\{[A-Z_]+\}\}")
            verify_documentation({**IDENTITY, "output_root": first})

    def test_a_changed_page_fails_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            built = Path(temp) / "built"
            build_documentation({**IDENTITY, "output_root": built})
            (built / "introduction/overview.md").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                verify_documentation({**IDENTITY, "output_root": built})

    def test_a_malformed_release_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            for bad in ({"version": "1.2"}, {"commit": "abc"}, {"tag": "v9.9.9"}):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    build_documentation({**IDENTITY, **bad, "output_root": Path(temp) / "out"})

    def test_navigation_lists_every_page_once(self):
        navigation = json.loads((Path(REPO_ROOT) / SOURCE_REL / "navigation.json").read_text())
        self.assertEqual(sorted(navigation_paths(navigation)), sorted(list_files(PAGES)))

    def test_relative_page_links_resolve(self):
        pages = list_files(PAGES)
        broken = []
        for page in pages:
            for target in re.findall(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)", (PAGES / page).read_text()):
                if re.match(r"^[a-z]+:", target):
                    continue
                if posixpath.normpath(posixpath.join(posixpath.dirname(page), target)) not in pages:
                    broken.append(f"{page} -> {target}")
        self.assertEqual(broken, [])

    def test_readme_links_resolve(self):
        readme = (Path(REPO_ROOT) / "README.md").read_text()
        broken = [target for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", readme)
                  if not re.match(r"^[a-z]+:", target) and not (Path(REPO_ROOT) / target).exists()]
        self.assertEqual(broken, [])


class ToolReferenceTest(unittest.TestCase):
    def test_every_registered_tool_is_documented_exactly(self):
        registered = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}
        documented = {}
        for line in (PAGES / "reference/tools.md").read_text().splitlines():
            if match := ROW.match(line):
                self.assertNotIn(match[1], documented, f"{match[1]} is listed twice")
                documented[match[1]] = match.groups()[1:]
        self.assertEqual(set(documented), set(registered))
        for name, (kind, parameters, results) in documented.items():
            tool = registered[name]
            schema = tool.input_schema
            with self.subTest(tool=name):
                self.assertEqual(kind, access(tool))
                self.assertEqual(names(parameters), set(schema.get("properties", {})))
                self.assertEqual(required(parameters), set(schema.get("required", [])))
                self.assertEqual(names(results), set(tool.output_schema.get("properties", {})))


if __name__ == "__main__":
    unittest.main()
