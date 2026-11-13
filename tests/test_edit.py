import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

from cavi_after_effects_mcp import edit


def png(path, width, height):
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    rows = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


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
