"""Failures that reached After Effects, hid their cause or crashed the server, each driven through the real tools."""

import asyncio
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from mcp.server.mcpserver.exceptions import ToolError

from cavi_after_effects_mcp import host
from cavi_after_effects_mcp.server import mcp


class Reached(AssertionError):
    """Raised by the stand-in for the Apple Event call, so a refused call never touches After Effects."""


def reached(*_args, **_kwargs):
    raise Reached("the call reached After Effects")


def call(name, arguments):
    return asyncio.run(mcp.call_tool(name, arguments))


class NonFiniteNumbersTest(unittest.TestCase):
    def test_nan_and_infinity_are_refused_before_after_effects(self):
        base = {"project": "/x.aep", "comp": "a", "layer": 1}
        nan, inf = float("nan"), float("inf")
        calls = [
            ("ae_layer_set", {**base, "in_point": nan}),
            ("ae_layer_set", {**base, "properties": {"Transform/Opacity": inf}}),
            ("ae_keyframes", {**base, "property": "position", "keyframes": [{"time": 0, "value": [nan, 0]}]}),
            ("ae_effect_add", {**base, "match_name": "ADBE Glo2", "params": {"Glow Radius": -inf}}),
            ("ae_text_set", {**base, "tracking": nan}),
        ]
        with mock.patch.object(host, "do_script", reached):
            for name, arguments in calls:
                with self.subTest(name=name), self.assertRaisesRegex(ToolError, "finite"):
                    call(name, arguments)

    def test_a_script_argument_must_be_finite(self):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "one.jsx"
            script.write_text("1;\n")
            with mock.patch.object(host, "do_script", reached), self.assertRaisesRegex(ToolError, "finite"):
                call("ae_script", {"script": str(script), "project": f"{folder}/x.aep", "args": {"n": float("nan")}})


class BeatGridSizeTest(unittest.TestCase):
    def test_a_beat_grid_with_tens_of_thousands_of_markers_is_refused(self):
        with mock.patch.object(host, "do_script", reached), self.assertRaisesRegex(ToolError, "limit"):
            call("ae_markers", {"project": "/x.aep", "comp": "a", "grid": {"bpm": 1000, "end": 3600}})


class ScriptFileTest(unittest.TestCase):
    def test_a_missing_script_is_named(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ToolError, "No script at"):
            call("ae_script", {"script": f"{folder}/none.jsx", "project": f"{folder}/x.aep"})


class ReportTest(unittest.TestCase):
    def test_a_report_without_its_end_marker_is_named_unreadable(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "cut.aep"
            project.write_bytes(b'junk CAVI_REPORT{"errors":[]')
            with self.assertRaisesRegex(RuntimeError, "unreadable"):
                host.project_report(project)


class ApplicationLookupTest(unittest.TestCase):
    def test_a_wrong_override_is_reported_by_status_not_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = str(Path(folder) / "none.app")
            with mock.patch.dict(os.environ, {"CAVI_AFTER_EFFECTS_APP": missing}):
                status = call("ae_status", {})
        data = status.structured_content
        self.assertIsNone(data["app"])
        self.assertIn("CAVI_AFTER_EFFECTS_APP", data["error"])


class SerializedAccessTest(unittest.TestCase):
    def test_two_calls_never_run_scripts_in_the_application_at_once(self):
        active, most, guard = [0], [0], threading.Lock()

        def application(code, timeout):
            with guard:
                active[0] += 1
                most[0] = max(most[0], active[0])
            time.sleep(0.2)
            target = json.loads(code.split("var CAVI_PROJECT = ")[1].split(";\n")[0])
            Path(target).write_bytes(b'CAVI_REPORT{"errors":[],"value":"1"}CAVI_END')
            with guard:
                active[0] -= 1

        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "one.jsx"
            script.write_text("1;\n")
            with mock.patch.object(host, "do_script", application):
                workers = [threading.Thread(target=host.run_script,
                                            args=(script, Path(folder) / f"{n}.aep", {}, 10)) for n in "ab"]
                for worker in workers:
                    worker.start()
                for worker in workers:
                    worker.join()
        self.assertEqual(most[0], 1)


if __name__ == "__main__":
    sys.exit(unittest.main())
