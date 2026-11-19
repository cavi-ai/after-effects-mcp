"""Failures that reached After Effects, hid their cause or crashed the server, each driven through the real tools."""

import asyncio
import base64
import io
import json
import os
import plistlib
import re
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from cavi_mcp_core import resident
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image

from cavi_after_effects_mcp import host, render
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


class InvisibleShapeTest(unittest.TestCase):
    def test_a_rectangle_without_fill_or_stroke_is_refused(self):
        layer = {"comp": "a", "kind": "shape_rect", "name": "Bar", "color": [0, 0, 0.1], "width": 600, "height": 132}
        with mock.patch.object(host, "do_script", reached), self.assertRaisesRegex(ToolError, "fill or stroke"):
            call("ae_layer_add", {"project": "/x.aep", "layer": layer})


class BeatGridSizeTest(unittest.TestCase):
    def test_a_beat_grid_with_tens_of_thousands_of_markers_is_refused(self):
        with mock.patch.object(host, "do_script", reached), self.assertRaisesRegex(ToolError, "limit"):
            call("ae_markers", {"project": "/x.aep", "comp": "a", "grid": {"bpm": 1000, "end": 3600}})


class ScriptFileTest(unittest.TestCase):
    def test_a_missing_script_is_named(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ToolError, "No script at"):
            call("ae_script", {"script": f"{folder}/none.jsx", "project": f"{folder}/x.aep"})


def report_file(code):
    """The file the runner writes its report to, as named in the DoScript code."""
    return Path(json.loads(code.split("var CAVI_REPORT_FILE = ")[1].split(";\n")[0]))


class ReportTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name) / "a.aep"
        self.project.write_bytes(b"RIFX saved before the call")

    def inspect(self, report):
        def application(code, timeout):
            if "CAVI_PROJECT" in code:
                report_file(code).write_text(report, encoding="utf-8")

        with mock.patch.object(host, "do_script", application):
            return call("ae_inspect", {"project": str(self.project)})

    def test_a_read_returns_the_report_and_leaves_the_project_file(self):
        report = {"scope": "project", "comps": [], "footage": [], "folders": [], "errors": []}
        result = self.inspect(json.dumps(report))
        self.assertEqual(result.structured_content["report"], report)
        self.assertEqual(self.project.read_bytes(), b"RIFX saved before the call")

    def test_a_cut_report_is_named_unreadable(self):
        with self.assertRaisesRegex(ToolError, "unreadable report"):
            self.inspect('{"errors": [')


class ApplicationLookupTest(unittest.TestCase):
    def test_a_wrong_override_is_reported_by_status_not_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = str(Path(folder) / "none.app")
            with mock.patch.dict(os.environ, {"CAVI_AFTER_EFFECTS_APP": missing}):
                status = call("ae_status", {})
        data = status.structured_content
        self.assertIsNone(data["app"])
        self.assertIn("CAVI_AFTER_EFFECTS_APP", data["error"])


class RenderApplicationTest(unittest.TestCase):
    def test_after_effects_render_uses_the_application_the_override_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            app = root / "Other" / "Adobe After Effects 2099.app"
            (app / "Contents" / "MacOS").mkdir(parents=True)
            (app / "Contents" / "MacOS" / "After Effects").write_bytes(b"")
            with (app / "Contents" / "Info.plist").open("wb") as stream:
                plistlib.dump({"CFBundleIdentifier": "com.adobe.AfterEffects.application",
                               "CFBundleExecutable": "After Effects", "CFBundleShortVersionString": "99.0"}, stream)
            (root / "cut.aep").write_bytes(b"RIFX")
            (root / "recipe.json").write_text(json.dumps({
                "version": 1, "name": "shot", "project": "cut.aep", "dependencies": [], "composition": "Main",
                "start": 0, "end": 9, "fps": {"numerator": 30, "denominator": 1}, "loop": False,
                "alpha": "straight", "output_module": "PNG"}))
            scan = Path.glob

            def installed(self, pattern, *args, **kwargs):
                # The installs on this machine stay out of the test.
                return iter(()) if self == Path("/Applications") else scan(self, pattern, *args, **kwargs)

            with mock.patch.dict(os.environ, {"CAVI_AFTER_EFFECTS_APP": str(app)}), \
                    mock.patch.object(Path, "glob", installed), \
                    self.assertRaisesRegex(ValueError, f"No aerender at {re.escape(str(root / 'Other'))}"):
                render.ae_render(str(root), "recipe.json", "frames")
            self.assertFalse((root / "frames").exists())


class SerializedAccessTest(unittest.TestCase):
    def test_two_calls_never_run_scripts_in_the_application_at_once(self):
        active, most, guard = [0], [0], threading.Lock()

        def application(code, timeout):
            if "CAVI_PROJECT" not in code:
                return  # the check that a new project starts from an empty one
            with guard:
                active[0] += 1
                most[0] = max(most[0], active[0])
            time.sleep(0.2)
            report_file(code).write_text('{"errors": [], "value": "1"}', encoding="utf-8")
            with guard:
                active[0] -= 1

        reports = []

        def run(project):
            reports.append(host.run_script(script, project, {}, 10))

        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "one.jsx"
            script.write_text("1;\n")
            with mock.patch.object(host, "do_script", application):
                workers = [threading.Thread(target=run, args=(Path(folder) / f"{n}.aep",)) for n in "ab"]
                for worker in workers:
                    worker.start()
                for worker in workers:
                    worker.join()
        self.assertEqual(most[0], 1)
        self.assertEqual(reports, [{"errors": [], "value": "1"}] * 2)


class ProcessAccessTest(unittest.TestCase):
    def test_two_server_processes_never_hold_the_application_at_once(self):
        code = ("import time\nfrom cavi_after_effects_mcp import host\n"
                "with host.ACCESS:\n    start = time.time()\n    time.sleep(0.5)\n    print(start, time.time())\n")
        with tempfile.TemporaryDirectory() as folder:
            env = {**os.environ, "TMPDIR": folder}
            children = [subprocess.Popen([sys.executable, "-c", code], env=env, stdout=subprocess.PIPE, text=True)
                        for _ in range(2)]
            spans = sorted(tuple(map(float, child.communicate(timeout=60)[0].split())) for child in children)
        self.assertLessEqual(spans[0][1], spans[1][0])


class ErrorContractTest(unittest.TestCase):
    """The error a client receives: rejected only when After Effects kept nothing, else unknown with ae_inspect next."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.project = Path(folder.name) / "a.aep"
        self.project.write_bytes(b"RIFX")

    def error(self, name, arguments, application):
        with mock.patch.object(host, "do_script", application):
            try:
                call(name, arguments)
            except ToolError as error:
                return str(error), mcp.failure(name, error).structured_content["error"]
        self.fail(f"{name} succeeded")

    def reporting(self, report):
        def application(code, timeout):
            if "CAVI_PROJECT" in code:
                report_file(code).write_text(json.dumps(report), encoding="utf-8")
        return application

    def test_a_script_error_after_a_rollback_is_rejected(self):
        report = {"errors": ["Error: Comp C has no layer named Missing (line 8)"], "restored": True}
        arguments = {"project": str(self.project), "comp": "C", "layer": "Missing", "name": "x"}
        message, error = self.error("ae_layer_set", arguments, self.reporting(report))
        self.assertIn("no layer named Missing", message)
        self.assertEqual((error["outcome"], error["code"], error["next_action"]),
                         ("rejected", "AE_SCRIPT_REFUSED", "inspect_inputs"))

    def test_a_script_error_without_a_rollback_points_at_ae_inspect(self):
        report = {"errors": ["Error: Comp C has no layer named Missing (line 8)"], "restored": False}
        arguments = {"project": str(self.project), "comp": "C", "layer": "Missing", "name": "x"}
        _, error = self.error("ae_layer_set", arguments, self.reporting(report))
        self.assertEqual((error["outcome"], error["code"], error["next_action"]),
                         ("unknown", "OUTCOME_UNKNOWN", "ae_inspect"))

    def test_an_unsaved_open_project_is_refused_by_name(self):
        def application(code, timeout):
            if "app.project.dirty" in code:
                raise RuntimeError("After Effects script failed: 1")  # DoScript's answer to a thrown error
            raise Reached("the call went past the unsaved-changes check")

        message, error = self.error("ae_inspect", {"project": str(self.project)}, application)
        self.assertIn("unsaved changes", message)
        self.assertEqual((error["outcome"], error["code"]), ("rejected", "AE_PROJECT_UNSAVED"))

    def test_launching_beside_an_instance_with_its_ui_is_rejected(self):
        with mock.patch.object(host, "processes", lambda: ([], [4242])):
            message, error = self.error("ae_launch", {}, reached)
        self.assertIn("pid 4242", message)
        self.assertEqual((error["outcome"], error["code"]), ("rejected", "AE_UI_RUNNING"))


class ForeignArgumentsTest(unittest.TestCase):
    def test_an_argument_the_action_does_not_use_is_refused_before_after_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "a.aep"
            project.write_bytes(b"RIFX")
            edit = {"project": str(project), "comp": "a", "layers": [1]}
            calls = [
                ("ae_layer_edit", {**edit, "action": "delete", "time": 2}, "Not valid for action=delete: time"),
                ("ae_layer_edit", {**edit, "action": "duplicate", "move_to": "top"},
                 "Not valid for action=duplicate: move_to"),
                ("ae_project", {"action": "open", "path": str(project), "overwrite": True},
                 "Not valid for action=open: overwrite"),
            ]
            with mock.patch.object(host, "do_script", reached):
                for name, arguments, message in calls:
                    with self.subTest(arguments=arguments), self.assertRaisesRegex(ToolError, message):
                        call(name, arguments)


class RenderJobRecordTest(unittest.TestCase):
    def test_a_background_render_keeps_a_private_job_record(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            project = root / "a.aep"
            project.write_bytes(b"RIFX")
            install = root / "install"
            install.mkdir()
            (install / "aerender").write_text("#!/bin/sh\nexit 0\n")
            (install / "aerender").chmod(0o755)
            output = root / "out" / "o.mov"
            entry = {"index": 1, "comp": "C", "file": str(output), "frames": 3, "fps": 30}
            with (mock.patch.object(host, "RENDER_JOBS", root / "jobs"),
                  mock.patch.object(host, "after_effects", lambda: install),
                  mock.patch.object(host, "queue_entries", lambda _project, _outputs: [entry])):
                job = host.render_start(project, {"comp": "C", "file": str(output)})["job"]
                resident.wait(root / "jobs" / job, timeout=30)
                record = root / "jobs" / f"{job}.json"
                self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
                self.assertEqual((host.render_job(job)["comp"], host.render_job(job)["frames"]), ("C", 3))


class FramePreviewTest(unittest.TestCase):
    def frames(self, **options):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name).resolve()
        project = root / "a.aep"
        project.write_bytes(b"RIFX")

        def application(code, timeout):
            if "ae_frame_png" in code:
                args = json.loads(code.split("var CAVI_ARGS = ")[1].split(";\n")[0])
                for i, frame in enumerate(args["frames"]):
                    Image.new("RGB", (1920, 1080), (40 * i, 30, 30)).save(frame["file"])
                report_file(code).write_text(json.dumps({"comp": "C", "frames": len(args["frames"]), "errors": []}))

        with mock.patch.object(host, "do_script", application):
            return call("ae_frame", {"project": str(project), "comp": "C", "times": [0, 0.5, 1, 1.5, 2],
                                     "directory": str(root / "frames"), **options})

    def test_the_first_frames_come_back_as_images(self):
        result = self.frames()
        images = [block for block in result.content if block.type == "image"]
        self.assertEqual(len(images), 4)
        self.assertEqual(len(result.structured_content["frames"]), 5)
        for i, (block, frame) in enumerate(zip(images, result.structured_content["frames"])):
            preview = Image.open(io.BytesIO(base64.b64decode(block.data)))
            self.assertEqual((block.mime_type, preview.size), ("image/png", (768, 432)))
            self.assertEqual(preview.convert("RGB").getpixel((0, 0)), (40 * i, 30, 30))
            self.assertEqual(Image.open(frame["file"]).size, (1920, 1080))

    def test_no_previews_returns_only_the_paths(self):
        result = self.frames(previews=0)
        self.assertEqual([block.type for block in result.content], ["text"])
        self.assertEqual(len(result.structured_content["frames"]), 5)


if __name__ == "__main__":
    sys.exit(unittest.main())
