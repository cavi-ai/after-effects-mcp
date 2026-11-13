import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from cavi_after_effects_mcp import host


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is required")
class RenderedMovieTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ae-render-"))
        self.addCleanup(shutil.rmtree, self.root)
        # aerender writes a timecode track, which makes ffprobe list the video stream twice.
        self.movie = self.root / "end.mov"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=s=320x180:r=30:d=3", "-c:v", "prores_ks", "-profile:v", "2",
                        "-timecode", "00:00:00:00", str(self.movie)], check=True)

    def test_complete_movie_is_rendered(self):
        self.assertEqual(host.frame_count(self.movie), 90)
        self.assertTrue(host.rendered(self.movie, 90))

    def test_movie_cut_off_by_a_crash_is_not_rendered(self):
        # A crashed render leaves the frames it wrote and no index.
        data = self.movie.read_bytes()
        self.movie.write_bytes(data[:len(data) // 2])
        self.assertFalse(host.rendered(self.movie, 90))

    def test_movie_short_of_its_frames_is_not_rendered(self):
        self.assertFalse(host.rendered(self.movie, 150))

    def test_movie_from_before_the_render_is_not_rendered(self):
        since = self.movie.stat().st_mtime + 60
        self.assertFalse(host.rendered(self.movie, 90, since))


class ProjectReportTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ae-report-"))
        self.addCleanup(shutil.rmtree, self.root)

    def project(self, encoding):
        path = self.root / f"{encoding}.aep"
        text = 'CAVI_REPORT{"comps": ["end"], "errors": []}CAVI_END'
        path.write_bytes(b"RIFX\x00\x01" + text.encode(encoding) + b"\x00\xff")
        return path

    def test_report_is_read_from_a_utf8_project(self):
        self.assertEqual(host.project_report(self.project("utf-8")), {"comps": ["end"], "errors": []})

    def test_report_is_read_from_a_utf16_project(self):
        self.assertEqual(host.project_report(self.project("utf-16-be")), {"comps": ["end"], "errors": []})

    def test_project_without_a_report_is_refused(self):
        path = self.root / "empty.aep"
        path.write_bytes(b"RIFX\x00\x01")
        with self.assertRaisesRegex(RuntimeError, "holds no report"):
            host.project_report(path)

    def test_relative_script_path_is_refused(self):
        with self.assertRaisesRegex(ValueError, "absolute path"):
            host.run_script("build.jsx", self.root / "out.aep", {}, 60)


class WatchedCallTest(unittest.TestCase):
    def test_call_returns_its_output_while_after_effects_lives(self):
        app = subprocess.Popen(["sleep", "30"])
        self.addCleanup(app.kill)
        self.assertEqual(host.run_watched(["echo", "0"], 30, app.pid), (0, "0\n", ""))

    def test_call_ends_with_an_error_when_after_effects_dies_mid_call(self):
        app = subprocess.Popen(["sleep", "30"])
        self.addCleanup(app.kill)
        threading.Timer(1, lambda: (app.kill(), app.wait())).start()
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "exited during the call"):
            host.run_watched(["sleep", "30"], 60, app.pid, interval=0.1)
        self.assertLess(time.monotonic() - started, 10)


if __name__ == "__main__":
    unittest.main()
