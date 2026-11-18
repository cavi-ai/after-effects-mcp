import json
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

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


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is required")
class RenderedAudioTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ae-audio-"))
        self.addCleanup(shutil.rmtree, self.root)
        self.audio = self.root / "mix.aif"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=3:sample_rate=48000", str(self.audio)], check=True)

    def test_an_audio_output_counts_its_duration_in_frames(self):
        self.assertEqual(host.written(self.audio, 0, 30), 90)
        self.assertTrue(host.rendered(self.audio, 90, 0, 30))
        self.assertFalse(host.rendered(self.audio, 150, 0, 30))

    def test_a_movie_with_audio_counts_its_video_frames(self):
        movie = self.root / "end.mov"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=s=320x180:r=30:d=2", "-i", str(self.audio), "-c:v", "prores_ks", "-shortest",
                        str(movie)], check=True)
        self.assertEqual(host.written(movie, 0, 30), 60)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required")
class OnsetTest(unittest.TestCase):
    def test_onsets_fall_within_one_hop_of_each_hit(self):
        root = Path(tempfile.mkdtemp(prefix="ae-onsets-"))
        self.addCleanup(shutil.rmtree, root)
        hits = root / "hits.wav"
        bursts = "+".join(f"between(t,{t},{t + 0.1})" for t in (0.5, 1.0, 1.75, 2.5))
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"aevalsrc='0.5*sin(2*PI*440*t)*({bursts})':s=48000:d=3", str(hits)], check=True)
        found = host.onsets(hits)
        self.assertEqual(len(found), 4, found)
        for onset, hit in zip(found, (0.5, 1.0, 1.75, 2.5)):
            self.assertLess(abs(onset - hit), host.ONSET_HOP / host.ONSET_RATE, found)
        self.assertEqual(host.onsets(hits, gap=0.6), found[:1] + found[2:])


class RenderedSequenceTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ae-sequence-"))
        self.addCleanup(shutil.rmtree, self.root)
        self.output = self.root / "shot [v2]_[#####].tif"
        for frame in (15, 16, 17):
            (self.root / f"shot [v2]_{frame:05d}.tif").write_bytes(b"II*\x00")
        (self.root / "shot [v2]_00018.tif").write_bytes(b"")

    def test_an_image_sequence_counts_its_written_frames(self):
        self.assertTrue(host.rendered(self.output, 3))
        self.assertFalse(host.rendered(self.output, 4))

    def test_frames_from_before_the_render_do_not_count(self):
        self.assertFalse(host.rendered(self.output, 3, time.time() + 60))


class QueueEntryTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.project = self.root / "p.aep"
        self.project.write_bytes(b"RIFX")
        self.entry = {"index": 1, "comp": "R", "file": str(self.root / "work.mov"), "render": True,
                      "span_start": 0.5, "span_duration": 0.5, "fps": 30, "comp_fps": 30, "frames": 15}

    def render(self, frames):
        def queue(name, project, args, timeout=300):
            return {"queue": [self.entry], "errors": []}

        def aerender(*args):
            raise AssertionError("aerender ran")

        output = {"comp": "R", "file": str(self.root / "work.mov"), "frames": frames}
        with mock.patch.object(host, "run_template", queue), mock.patch.object(host, "aerender", aerender):
            return host.render_queue(self.project, [output])

    def test_frames_that_differ_from_the_queue_entry_are_refused_before_rendering(self):
        with self.assertRaisesRegex(ValueError, r"R: the queue entry renders 15 frames \(0\.5 s from 0\.5 s at 30 fps\)"):
            self.render(60)

    def test_an_output_with_no_queue_entry_is_refused_before_rendering(self):
        self.entry["file"] = str(self.root / "other.mov")
        with self.assertRaisesRegex(ValueError, "No queue entry renders R to"):
            self.render(None)


class ScriptPathTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ae-report-"))
        self.addCleanup(shutil.rmtree, self.root)

    def test_relative_script_path_is_refused(self):
        with self.assertRaisesRegex(ValueError, "absolute path"):
            host.run_script("build.jsx", self.root / "out.aep", {}, 60)


@unittest.skipUnless(shutil.which("node"), "node is required")
class ReportJsonTest(unittest.TestCase):
    def stringify(self, value):
        source = host.RUNNER.read_text()
        start = source.index("function caviStringify")
        stop = source.index("\n}\n", start) + 3
        script = source[start:stop] + "process.stdout.write(caviStringify(JSON.parse(process.argv[1])));"
        out = subprocess.run(["node", "-e", script, json.dumps(value)], capture_output=True, text=True, check=True)
        return out.stdout

    def test_control_characters_round_trip(self):
        value = {"text": "one\u0003two", "name": "a\"b\\c\nd\te\u0000\u001f"}
        out = self.stringify(value)
        self.assertTrue(out.isprintable())
        self.assertEqual(json.loads(out), value)


@unittest.skipUnless(shutil.which("node"), "node is required")
class ScriptSyntaxTest(unittest.TestCase):
    PARSE = ("const vm = require('vm'), fs = require('fs'); let bad = 0;\n"
             "for (const file of process.argv.slice(1)) {\n"
             "  try { new vm.Script(fs.readFileSync(file, 'utf8'), {filename: file}); }\n"
             "  catch (error) { bad += 1; console.log(file + ': ' + error.message); }\n"
             "}\nprocess.exit(bad ? 1 : 0);")

    def parse(self, files):
        return subprocess.run(["node", "-e", self.PARSE, *map(str, files)], capture_output=True, text=True)

    def test_every_script_parses(self):
        files = sorted(host.JSX.glob("*.jsx")) + [host.RUNNER]
        self.assertGreater(len(files), 30)
        result = self.parse(files)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_script_that_does_not_parse_is_named(self):
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "broken.jsx"
            broken.write_text("(function () { var a = ; })();\n")
            result = self.parse([host.RUNNER, broken])
        self.assertEqual(result.returncode, 1)
        self.assertIn("broken.jsx: Unexpected token", result.stdout)


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


class PresetTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ae-presets-"))
        self.addCleanup(shutil.rmtree, self.root)
        for path in ("Text/Fade Up.ffx", "Transitions - Wipes/Iris.ffx", "Legacy/Iris.ffx", "Text/readme.txt"):
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_bytes(b"")

    def test_presets_are_listed_by_category_and_name(self):
        found = host.animation_presets(self.root)
        self.assertEqual([(p["category"], p["name"]) for p in found],
                         [("Legacy", "Iris"), ("Text", "Fade Up"), ("Transitions - Wipes", "Iris")])

    def test_presets_are_filtered_by_text(self):
        self.assertEqual([p["name"] for p in host.animation_presets(self.root, "wipes")], ["Iris"])

    def test_preset_name_resolves_to_its_file(self):
        self.assertEqual(host.resolve_preset("Fade Up", self.root), self.root / "Text/Fade Up.ffx")
        self.assertEqual(host.resolve_preset("Legacy/Iris", self.root), self.root / "Legacy/Iris.ffx")

    def test_ambiguous_or_unknown_preset_is_refused(self):
        with self.assertRaisesRegex(ValueError, "matches 2"):
            host.resolve_preset("Iris", self.root)
        with self.assertRaisesRegex(ValueError, "matches 0"):
            host.resolve_preset("Nope", self.root)

    def test_absolute_preset_path_is_used_as_given(self):
        path = self.root / "Text/Fade Up.ffx"
        self.assertEqual(host.resolve_preset(str(path), self.root), path)


if __name__ == "__main__":
    unittest.main()
