import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()


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
