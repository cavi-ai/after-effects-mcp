import shutil
import struct
import subprocess
import tempfile
import threading
import unittest
import zlib
from pathlib import Path
from unittest import mock

from cavi_after_effects_mcp import edit, host
from cavi_after_effects_mcp.models import MaskShape, PathShape


def png(path, width, height):
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    rows = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


class CopyFootageTest(unittest.TestCase):
    def test_files_are_copied_once_and_equal_names_stay_apart(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a").mkdir()
            (root / "b").mkdir()
            (root / "a" / "clip.mov").write_bytes(b"first")
            (root / "b" / "clip.mov").write_bytes(b"second")
            sources = [root / "a" / "clip.mov", root / "b" / "clip.mov", root / "a" / "clip.mov"]
            copies = edit.copy_footage(sources, root / "out")
            self.assertEqual(len(copies), 2)
            self.assertEqual(Path(copies[str(sources[0])]).read_bytes(), b"first")
            self.assertEqual(Path(copies[str(sources[1])]).read_bytes(), b"second")
            self.assertEqual(sorted(p.name for p in (root / "out").iterdir()), ["clip.mov", "clip_2.mov"])

    def test_a_copy_already_in_the_folder_is_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "out").mkdir()
            (root / "out" / "clip.mov").write_bytes(b"x")
            self.assertEqual(edit.copy_footage([root / "out" / "clip.mov"], root / "out"),
                             {str(root / "out" / "clip.mov"): str(root / "out" / "clip.mov")})


class MaskShapeTest(unittest.TestCase):
    def test_rect_mask_is_four_corners_with_straight_edges(self):
        shape = edit.mask_shape(MaskShape(kind="rect", box=[10, 20, 100, 50]))
        self.assertEqual(shape["vertices"], [[10, 20], [110, 20], [110, 70], [10, 70]])
        self.assertEqual(shape["in_tangents"] + shape["out_tangents"], [[0, 0]] * 8)

    def test_ellipse_mask_spans_its_box_with_curved_tangents(self):
        shape = edit.mask_shape(MaskShape(kind="ellipse", box=[0, 0, 200, 100]))
        self.assertEqual(shape["vertices"], [[100, 0], [200, 50], [100, 100], [0, 50]])
        self.assertAlmostEqual(shape["out_tangents"][0][0], 55.22847498)
        self.assertAlmostEqual(shape["in_tangents"][1][1], -27.61423749)

    def test_points_mask_defaults_to_straight_tangents(self):
        shape = edit.mask_shape(MaskShape(kind="points", path=PathShape(vertices=[[0, 0], [5, 5], [0, 9]], closed=False)))
        self.assertEqual(shape["in_tangents"], [[0, 0]] * 3)
        self.assertFalse(shape["closed"])


class ExpressionPresetTest(unittest.TestCase):
    def test_wiggle_and_loops(self):
        self.assertEqual(edit.expression_preset("wiggle", 2, 30, 5, 90), "wiggle(2, 30)")
        self.assertEqual(edit.expression_preset("loop_pingpong", 2, 30, 5, 90), 'loopOut("pingpong")')
        self.assertEqual(edit.expression_preset("time_rotation", 2, 30, 5, 45), "value + time * 45")

    def test_bounce_carries_its_amplitude_frequency_and_decay(self):
        text = edit.expression_preset("inertial_bounce", 4, 12, 7, 0)
        self.assertTrue(text.startswith("amp = 12;\nfreq = 4;\ndecay = 7;"))
        self.assertIn("velocityAtTime", text)


class BeatGridTest(unittest.TestCase):
    def test_beats_are_numbered_by_bar_and_stop_before_the_end(self):
        grid = edit.beat_grid(bpm=120, beats_per_bar=3, start=1.0, end=3.0)
        self.assertEqual([m["time"] for m in grid], [1.0, 1.5, 2.0, 2.5])
        self.assertEqual([m["comment"] for m in grid], ["1.1", "1.2", "1.3", "2.1"])
        self.assertEqual([m["chapter"] for m in grid], ["Bar 1", None, None, "Bar 2"])

    def test_tempo_sets_the_spacing(self):
        grid = edit.beat_grid(bpm=90, beats_per_bar=4, start=0, end=2)
        self.assertEqual([round(m["time"], 4) for m in grid], [0, 0.6667, 1.3333])


@unittest.skipUnless(shutil.which("sips"), "sips is required")
class FrameFileTest(unittest.TestCase):
    def test_a_tiff_frame_becomes_a_png_of_the_same_size(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            png(root / "source.png", 6, 4)
            subprocess.run(["sips", "-s", "format", "tiff", str(root / "source.png"), "--out", str(root / "f.tif")],
                           check=True, capture_output=True)
            edit.to_png(root / "f.tif", root / "out.png")
            self.assertEqual((root / "out.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            size = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(root / "out.png")],
                                  check=True, capture_output=True, text=True).stdout
            self.assertIn("pixelWidth: 6", size)
            self.assertIn("pixelHeight: 4", size)

    def test_a_missing_frame_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError):
                edit.to_png(Path(folder) / "none.tif", Path(folder) / "out.png")


class CrashingCallsTest(unittest.TestCase):
    def test_scripts_calling_known_aborting_functions_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            for call in ("layer.applyPreset(new File('/x.ffx'))", "app.executeCommand(4218)",
                         "app.findMenuCommandId('Drop Shadow')"):
                script = Path(folder) / "bad.jsx"
                script.write_text(f"var l = app.project.item(1);\n{call};\n")
                with self.assertRaisesRegex(ValueError, "Refused"):
                    host.refuse_crashing_calls(script)

    def test_an_ordinary_script_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "ok.jsx"
            script.write_text("var comp = app.project.items.addComp('a', 100, 100, 1, 1, 30);\n")
            host.refuse_crashing_calls(script)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is required")
class EncodeFramesTest(unittest.TestCase):
    def probe(self, movie):
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-count_frames", "-show_entries",
                              "stream=codec_name,width,height,nb_read_frames,r_frame_rate", "-of", "csv=p=0", str(movie)],
                             check=True, capture_output=True, text=True).stdout.strip()
        return out.split(",")

    def test_numbered_frames_become_an_even_sized_h264_movie(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for n in range(1, 5):
                png(root / f"frame_{n:05d}.png", 21, 11)
            movie = root / "out.mp4"
            made = subprocess.run(edit.encode_command(root, movie, 12, "h264", False), capture_output=True, text=True)
            self.assertEqual(made.returncode, 0, made.stderr)
            codec, width, height, rate, frames = self.probe(movie)
            self.assertEqual((codec, int(width), int(height), rate, int(frames)), ("h264", 20, 10, "12/1", 4))

    def test_prores_with_alpha_keeps_the_size_and_frame_count(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for n in range(1, 4):
                png(root / f"frame_{n:05d}.png", 21, 11)
            movie = root / "out.mov"
            made = subprocess.run(edit.encode_command(root, movie, 6, "prores", True), capture_output=True, text=True)
            self.assertEqual(made.returncode, 0, made.stderr)
            codec, width, height, rate, frames = self.probe(movie)
            self.assertEqual((codec, int(width), int(height), int(frames)), ("prores", 21, 11, 3))


class FrameNameTest(unittest.TestCase):
    def test_each_time_gets_its_own_file_in_the_folder(self):
        def application(name, project, args, timeout=300):
            for frame in args["frames"]:
                png(Path(frame["file"]), 4, 4)
            return {"errors": []}

        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "frames"
            with mock.patch.object(host, "run_template", application):
                frames = edit.render_frames(Path(folder) / "p.aep", "A/B", [1.0, 1.0000001, 1.5], directory)
            files = [Path(f["file"]) for f in frames]
            self.assertEqual(len(set(files)), 3)
            self.assertEqual({f.parent for f in files}, {directory})
            self.assertTrue(all(f.is_file() for f in files))

    def test_the_render_scratch_folder_is_removed_with_a_read_only_folder_in_it(self):
        def application(name, project, args, timeout=300):
            return {"enabled": []}

        def aerender(*args):
            for work in directory.glob("frames-*"):
                locked = work / "cache"
                locked.mkdir(exist_ok=True)
                (locked / "entry").touch()
                locked.chmod(0o500)

        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "frames"
            with (mock.patch.object(host, "run_template", application), mock.patch.object(host, "aerender", aerender),
                  mock.patch.object(edit, "RENDER_RETRY_SECONDS", 0)):
                with self.assertRaisesRegex(RuntimeError, "aerender wrote 0 frames"):
                    edit.render_frames(Path(folder) / "p.aep", "A", [1.0], directory, use_direct=False)
            self.assertEqual(list(directory.glob("frames-*")), [])


class DirectFramesTest(unittest.TestCase):
    def test_a_missing_comp_is_raised_and_aerender_is_not_called(self):
        def application(name, project, args, timeout=300):
            if name != "ae_frame_png":
                raise AssertionError(name)
            raise RuntimeError("After Effects script: No comp named Shot")

        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "frames"
            aerender = mock.Mock()
            with (mock.patch.object(host, "run_template", application),
                  mock.patch.object(host, "aerender", aerender)):
                with self.assertRaisesRegex(RuntimeError, "No comp named"):
                    edit.render_frames(Path(folder) / "p.aep", "Shot", [1.0], directory)
            aerender.assert_not_called()

    def test_any_other_direct_error_falls_through_to_aerender(self):
        def application(name, project, args, timeout=300):
            if name == "ae_frame_png":
                raise RuntimeError("After Effects script: saveFrameToPng failed")
            return {"enabled": []}

        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "frames"
            aerender = mock.Mock()
            with (mock.patch.object(host, "run_template", application),
                  mock.patch.object(host, "aerender", aerender),
                  mock.patch.object(edit, "RENDER_RETRY_SECONDS", 0)):
                with self.assertRaisesRegex(RuntimeError, "aerender wrote 0 frames"):
                    edit.render_frames(Path(folder) / "p.aep", "A", [1.0], directory)
            self.assertEqual(aerender.call_count, edit.RENDER_ATTEMPTS)

    def test_cavi_comp_still_fails_with_no_comp_named(self):
        lib = (host.JSX / "lib.jsx").read_text()
        start = lib.index("function caviComp(")
        body = lib[start:lib.index("\n}\n", start)]
        self.assertIn("No comp named ", body)


class ExportFramesTest(unittest.TestCase):
    def test_frames_created_empty_and_written_later_are_returned(self):
        """After Effects creates each PNG before it writes its bytes."""
        fills = []

        def application(name, project, args, timeout=300):
            files = [Path(args["directory"]) / f"frame_{n:05d}.png" for n in range(1, 4)]
            for f in files:
                f.touch()
            fills.append(threading.Timer(0.5, lambda: [png(f, 4, 4) for f in files]))
            fills[-1].start()
            return {"count": 3, "fps": 30, "errors": []}

        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "frames"
            try:
                with mock.patch.object(host, "run_template", application):
                    result = edit.export_frames(Path(folder) / "p.aep", "A", directory, 0, None, 1, False, None,
                                                "h264", 10)
            finally:
                for fill in fills:
                    fill.join()
            self.assertEqual(result["frames"], 3)
            self.assertEqual(result["last"], str(directory / "frame_00003.png"))


class WarmedTest(unittest.TestCase):
    def test_a_warming_report_waits_for_bytes_then_runs_the_script_again(self):
        """The warm file stays empty until its bytes arrive; the second call has no warm path."""
        order = []
        calls = []
        fills = []

        def application(name, project, args, timeout=300):
            calls.append((name, project, args, timeout))
            if args["warm"] is not None:
                warm = Path(args["warm"])
                warm.touch()

                def fill():
                    order.append("filled")
                    warm.write_bytes(b"png")

                fills.append(threading.Timer(0.5, fill))
                fills[-1].start()
                return {"warming": True, "errors": []}
            order.append("second")
            return {"errors": [], "frames": 1}

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            warm = root / ".cineware-warm.png"
            project = root / "p.aep"
            sent = {"comp": "A", "frames": [{"time": 1.0, "file": str(root / "a.png")}]}
            try:
                with mock.patch.object(host, "run_template", application):
                    report = edit.warmed("ae_frame_png", project, sent, warm, 40)
            finally:
                for fill in fills:
                    fill.join()
            self.assertEqual(order, ["filled", "second"])
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][0], "ae_frame_png")
            self.assertEqual(calls[0][1], project)
            self.assertEqual(calls[0][2], {**sent, "warm": str(warm)})
            self.assertEqual(calls[0][3], 40)
            self.assertIsNone(calls[1][2]["warm"])
            self.assertEqual(calls[1], ("ae_frame_png", project, {**sent, "warm": None}, 40))
            self.assertEqual(report, {"errors": [], "frames": 1})
            self.assertFalse(warm.exists())

    def test_a_report_without_warming_runs_the_script_once(self):
        calls = []

        def application(name, project, args, timeout=300):
            calls.append((name, project, args, timeout))
            return {"errors": [], "frames": 2}

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            warm = root / ".cineware-warm.png"
            project = root / "p.aep"
            sent = {"comp": "A"}
            with mock.patch.object(host, "run_template", application):
                report = edit.warmed("ae_frame_range", project, sent, warm)
            self.assertEqual(calls, [("ae_frame_range", project, {**sent, "warm": str(warm)}, 300)])
            self.assertEqual(report, {"errors": [], "frames": 2})
            self.assertFalse(warm.exists())


class FallbackMovieTest(unittest.TestCase):
    def test_a_format_ffmpeg_cannot_make_from_frames_is_refused_before_any_work(self):
        with tempfile.TemporaryDirectory() as folder:
            movie = Path(folder) / "out.avi"
            with self.assertRaisesRegex(RuntimeError, r"\.mp4 \(H\.264\) or \.mov \(ProRes\), not \.avi"):
                edit.fallback_movie(Path(folder) / "x.aep", {"comp": "a", "file": str(movie), "frames": 3},
                                    {"span_start": 0, "span_duration": 0.1, "fps": 30, "comp_fps": 30, "frames": 3})
            self.assertEqual(list(Path(folder).iterdir()), [])


class RenderOutputsTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.project = self.root / "p.aep"
        self.project.write_bytes(b"RIFX")
        self.movie = self.root / "work.mov"
        self.entry = {"index": 4, "comp": "R", "file": str(self.movie), "render": True, "span_start": 0.0,
                      "span_duration": 0.5, "fps": 30, "comp_fps": 30, "frames": 15}
        self.output = {"comp": "R", "file": str(self.movie), "frames": None}

    def render(self, counts, fallback):
        calls = []

        def queue(name, project, args, timeout=300):
            return {"queue": [self.entry], "errors": []}

        def aerender(*args):
            calls.append(args)

        with (mock.patch.object(host, "run_template", queue), mock.patch.object(host, "aerender", aerender),
              mock.patch.object(host, "written", side_effect=counts),
              mock.patch.object(edit, "fallback_movie", fallback)):
            result = edit.render_outputs(self.project, [self.output])
        return result, calls

    def made(self, frames, rerendered, path):
        return {"comp": "R", "file": str(self.movie), "frames": frames, "rerendered": rerendered, "path": path}

    def test_a_complete_count_stays_on_aerender(self):
        fallback = mock.Mock(side_effect=AssertionError("fallback ran"))
        result, calls = self.render([15], fallback)
        fallback.assert_not_called()
        self.assertEqual(calls, [("-project", str(self.project))])
        self.assertEqual(result, {"project": str(self.project), "outputs": [self.made(15, False, "aerender")]})

    def test_a_short_count_renders_that_entry_again(self):
        fallback = mock.Mock(side_effect=AssertionError("fallback ran"))
        result, calls = self.render([5, 15], fallback)
        fallback.assert_not_called()
        self.assertEqual(calls, [("-project", str(self.project)),
                                 ("-project", str(self.project), "-rqindex", "4")])
        self.assertEqual(result, {"project": str(self.project), "outputs": [self.made(15, True, "aerender")]})

    def test_a_count_still_short_uses_save_frame_to_png(self):
        fallback = mock.Mock(return_value=15)
        result, calls = self.render([5, 5], fallback)
        fallback.assert_called_once_with(self.project, self.output, self.entry)
        self.assertEqual(calls[1], ("-project", str(self.project), "-rqindex", "4"))
        self.assertEqual(result, {"project": str(self.project), "outputs": [self.made(15, True, "saveFrameToPng")]})

    def test_a_fallback_error_names_the_frames_aerender_left(self):
        def fallback(*args):
            raise RuntimeError("encoder broke")

        with self.assertRaisesRegex(RuntimeError, r"^R: aerender left 5 of 15 frames \(no error\); "
                                    r"the fallback failed: encoder broke$"):
            self.render([5, 5], fallback)

    def test_retries_all_short_outputs_before_fallback_failure(self):
        second = {**self.entry, "index": 5, "comp": "S", "file": str(self.root / "second.mov")}
        outputs = [self.output, {"comp": "S", "file": second["file"], "frames": None}]
        made = [{"file": entry["file"], "frames": 5} for entry in (self.entry, second)]
        report = {"project": str(self.project), "entries": [self.entry, second], "outputs": made,
                  "since": 0, "failure": None}
        calls = []

        def fallback(*args):
            calls.append("fallback")
            raise RuntimeError("encoder broke")

        with (mock.patch.object(host, "render_queue", return_value=report),
              mock.patch.object(host, "discard"),
              mock.patch.object(host, "aerender", side_effect=lambda *args: calls.append(args)),
              mock.patch.object(host, "written", side_effect=[5, 15]),
              mock.patch.object(edit, "fallback_movie", side_effect=fallback),
              self.assertRaisesRegex(RuntimeError, "encoder broke")):
            edit.render_outputs(self.project, outputs)
        self.assertEqual(calls, [("-project", str(self.project), "-rqindex", "4"),
                                 ("-project", str(self.project), "-rqindex", "5"), "fallback"])
