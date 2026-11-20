import json
import os
import shutil
import signal
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

    def test_a_container_without_a_frame_count_counts_its_packets(self):
        # MXF, which an After Effects output module can write, and Matroska keep no nb_frames.
        for name, codec in (("end.mxf", ["-c:v", "mpeg2video", "-pix_fmt", "yuv422p"]), ("end.mkv", [])):
            with self.subTest(name=name):
                movie = self.root / name
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                                "testsrc=s=320x180:r=30:d=3", *codec, str(movie)], check=True)
                self.assertTrue(host.rendered(movie, 90))


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


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required")
class CutTest(unittest.TestCase):
    def test_cuts_are_the_first_frames_of_new_shots(self):
        root = Path(tempfile.mkdtemp(prefix="ae-cuts-"))
        self.addCleanup(shutil.rmtree, root)
        shots = root / "shots.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=d=1:s=320x180:r=30", "-f", "lavfi", "-i", "smptebars=d=1:s=320x180:r=30", "-f",
                        "lavfi", "-i", "rgbtestsrc=d=1:s=320x180:r=30", "-filter_complex",
                        "[0][1][2]concat=n=3:v=1:a=0,format=yuv420p", str(shots)], check=True)
        self.assertEqual(host.cuts(shots), [1.0, 2.0])
        self.assertEqual(host.cuts(shots, threshold=0.8), [1.0])
        tone = root / "tone.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=d=1", str(tone)],
                       check=True)
        with self.assertRaisesRegex(ValueError, "tone.wav has no video stream"):
            host.cuts(tone)


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
class MenuValueTest(unittest.TestCase):
    FRACTAL = ["Basic", "(-", "Turbulent Smooth", "Turbulent Basic", "Turbulent Sharp", "(-", "Dynamic"]

    def menu_value(self, items, value, version="26.5"):
        """caviMenuValue from lib.jsx on a property whose menu is ``items`` (None: not a menu)."""
        source = (host.JSX / "lib.jsx").read_text()
        functions = ""
        for name in ("caviMenuItems", "caviMenuValue"):
            start = source.index(f"function {name}(")
            functions += source[start:source.index("\n}\n", start) + 3]
        script = (f"const app = {{version: {json.dumps(version)}}};\n"
                  "function caviFail(message) { throw new Error(message); }\n" + functions +
                  "const [items, value] = JSON.parse(process.argv[1]);\n"
                  "const prop = {name: 'Fractal Type', get propertyParameters() {\n"
                  "  if (items === null) { throw new Error('This property does not have dropdown menu options.'); }\n"
                  "  return items; }};\n"
                  "try { process.stdout.write(JSON.stringify(caviMenuValue(prop, value))); }\n"
                  "catch (error) { process.stdout.write(JSON.stringify({error: error.message})); }")
        out = subprocess.run(["node", "-e", script, json.dumps([items, value])], capture_output=True, text=True,
                             check=True)
        return json.loads(out.stdout)

    def test_an_item_is_set_by_its_text_and_separators_keep_their_index(self):
        self.assertEqual(self.menu_value(self.FRACTAL, "Dynamic"), 7)
        self.assertEqual(self.menu_value(self.FRACTAL, "Turbulent Smooth"), 3)
        self.assertEqual(self.menu_value(self.FRACTAL, 4), 4)

    def test_an_unknown_item_names_the_items(self):
        self.assertEqual(self.menu_value(self.FRACTAL, "(-"), {
            "error": "Fractal Type has no item (-; its items are Basic, Turbulent Smooth, Turbulent Basic, "
                     "Turbulent Sharp, Dynamic"})

    def test_text_for_a_property_without_a_menu_is_refused(self):
        self.assertEqual(self.menu_value(None, "Dynamic"), {"error": "Fractal Type is not a menu; it takes no text "
                                                                     "Dynamic"})
        self.assertIn("need After Effects 26.0", self.menu_value(None, "Dynamic", "25.4")["error"])


@unittest.skipUnless(shutil.which("node"), "node is required")
class MeshOptionsTest(unittest.TestCase):
    def mesh_options(self, kind, mesh, bevel):
        """caviMeshOptions from lib.jsx on a ``kind`` mesh layer: its report and the streams' values afterwards."""
        source = (host.JSX / "lib.jsx").read_text()
        start = source.index("var CAVI_SLICE")
        end = source.index("\n}\n", source.index("function caviMeshSet(")) + 3
        script = ("function caviFail(message) { throw new Error(message); }\n"
                  "const TYPES = ['CUBE', 'SPHERE', 'PLANE', 'CYLINDER', 'CONE', 'TORUS'];\n"
                  "const ParametricMeshType = Object.fromEntries(TYPES.map((t, i) => [t, 6812 + i]));\n"
                  "class ParametricMeshLayer {}\n" + source[start:end] +
                  "const [kind, mesh, bevel] = JSON.parse(process.argv[1]);\n"
                  "const streams = {};\n"
                  "function group() { return {property(name) {\n"
                  "  if (!streams[name]) { streams[name] = {value: 0, setValue(v) { this.value = v; }}; }\n"
                  "  return streams[name]; }}; }\n"
                  "const layer = Object.assign(new ParametricMeshLayer(), {name: 'M',\n"
                  "  parametricMeshType: ParametricMeshType[kind], parametricMeshOptions: group(),\n"
                  "  parametricBevelOptions: group()});\n"
                  "let out;\n"
                  "try { out = caviMeshOptions(layer, mesh, bevel); } catch (error) { out = {error: error.message}; }\n"
                  "const values = Object.fromEntries(Object.entries(streams).map(([k, s]) => [k, s.value]));\n"
                  "process.stdout.write(JSON.stringify({out, values}));")
        run = subprocess.run(["node", "-e", script, json.dumps([kind, mesh, bevel])], capture_output=True, text=True,
                             check=True)
        return json.loads(run.stdout)

    def test_options_set_the_streams_of_the_layers_own_mesh_type(self):
        self.assertEqual(self.mesh_options("SPHERE", {"radius": 150, "slice_end": 270}, None), {
            "out": {"type": "sphere", "mesh": {"radius": 150, "slice_end": 270}, "bevel": {}},
            "values": {"ADBE SphereRadiusStrm": 150, "ADBE SphereEndAngleStrm": 270}})
        self.assertEqual(self.mesh_options("CONE", {"top_cap": False}, {"bottom_radius": 12}), {
            "out": {"type": "cone", "mesh": {"top_cap": False}, "bevel": {"bottom_radius": 12}},
            "values": {"ADBE ConeTopCapStrm": 0, "ADBE ConeBevelBottomRadiusStrm": 12}})

    def test_an_option_the_mesh_type_lacks_is_refused_before_any_change(self):
        self.assertEqual(self.mesh_options("SPHERE", {"radius": 150, "width": 400}, None), {
            "out": {"error": "A sphere mesh has no mesh option width; it has radius, sides, slice_caps, slice_start, "
                             "slice_end, invert_slice, smoothing_angle"}, "values": {}})
        self.assertEqual(self.mesh_options("TORUS", {"caps": False}, {"radius": 5}), {
            "out": {"error": "A torus mesh has no Bevel Options"}, "values": {}})


@unittest.skipUnless(shutil.which("node"), "node is required")
class FontAxesTest(unittest.TestCase):
    KEFA = [{"min": 300, "max": 800, "default": 400, "name": "Weight", "tag": "wght"}]

    def font_axes(self, font, data, axes, api=True):
        """addFontAxes from ae_text_animator.jsx on text in ``font``: its report and the axes added with values."""
        source = (host.JSX / "ae_text_animator.jsx").read_text()
        functions = ""
        for name in ("animatorAt", "addFontAxes"):
            start = source.index(f"function {name}(")
            functions += source[start:source.index("\n}\n", start) + 3]
        script = ("function caviFail(message) { throw new Error(message); }\n" + functions +
                  "const [font, data, axes, api] = JSON.parse(process.argv[1]);\n"
                  "const added = [];\n"
                  "const props = {};\n"
                  "if (api) { props.addVariableFontAxis = tag => {\n"
                  "  const p = {value: 400, setValue(v) { this.value = v; }}; added.push([tag, p]); return p; }; }\n"
                  "const doc = {fontObject: {postScriptName: font, designAxesData: data === null ? undefined : data}};\n"
                  "const animator = {property: n => n === 'ADBE Text Animator Properties' ? props : null};\n"
                  "const text = {property: n => n === 'ADBE Text Document' ? {value: doc}\n"
                  "  : n === 'ADBE Text Animators' ? {property: i => i === 1 ? animator : null} : null};\n"
                  "const layer = {property: n => n === 'ADBE Text Properties' ? text : null};\n"
                  "let out;\n"
                  "try { out = addFontAxes(layer, 1, axes); } catch (error) { out = {error: error.message}; }\n"
                  "process.stdout.write(JSON.stringify({out, added: added.map(([t, p]) => [t, p.value])}));")
        run = subprocess.run(["node", "-e", script, json.dumps([font, data, axes, api])], capture_output=True,
                             text=True, check=True)
        return json.loads(run.stdout)

    def test_an_axis_of_the_font_is_added_and_set(self):
        self.assertEqual(self.font_axes("KefaIII-Regular", self.KEFA, {"wght": 800}),
                         {"out": {"wght": 800}, "added": [["wght", 800]]})

    def test_an_axis_the_font_lacks_is_refused_with_the_fonts_axes(self):
        self.assertEqual(self.font_axes("KefaIII-Regular", self.KEFA, {"wght": 800, "wdth": 100}), {
            "out": {"error": "Font KefaIII-Regular has no variable axis wdth; its axes are wght 300 to 800"},
            "added": []})
        self.assertEqual(self.font_axes("ArialMT", None, {"wght": 800}), {
            "out": {"error": "Font ArialMT is not a variable font; it has no axis wght"}, "added": []})

    def test_axes_before_after_effects_26_are_refused(self):
        self.assertEqual(self.font_axes("KefaIII-Regular", self.KEFA, {"wght": 800}, api=False)["out"],
                         {"error": "Variable font axes need After Effects 26.0 or later"})


@unittest.skipUnless(shutil.which("node"), "node is required")
class LayerInputTest(unittest.TestCase):
    def layer_input(self, value, limit=-1, layer_param=True, api=True):
        """caviSetLayerInput from lib.jsx on Displacement Map Layer of layer 1 in a comp of Target and Map, whose
        cycle-safe stage limit is ``limit``: what it reads back and the setInputLayerAndStage calls."""
        source = (host.JSX / "lib.jsx").read_text()
        layer = source.index("function caviLayer(")
        start = source.index("var CAVI_STAGES")
        end = source.index("\n}\n", source.index("function caviIsInput(")) + 3
        script = ("function caviFail(message) { throw new Error(message); }\n"
                  "const PropertyValueType = {OneD: 1, LAYER_INDEX: 7};\n" +
                  source[layer:source.index("\n}\n", layer) + 3] + source[start:end] +
                  "const [value, limit, layerParam, api] = JSON.parse(process.argv[1]);\n"
                  "const comp = {name: 'C', numLayers: 2, layer: i => layers[i - 1]};\n"
                  "const layers = [{name: 'Target', index: 1, containingComp: comp},\n"
                  "  {name: 'Map', index: 2, containingComp: comp}];\n"
                  "const calls = [];\n"
                  "const prop = {name: 'Displacement Map Layer', propertyValueType: layerParam ? 7 : 1,\n"
                  "  propertyDepth: 2, propertyGroup: d => d === 2 ? layers[0] : null, inputLayerAndStage: [1, 0],\n"
                  "  LayerInputStageType: {SOURCE: 0, ALL_EFFECTS: -1, ONLY_MASKS: -2},\n"
                  "  getInputStageCycleSafeLimit: () => limit};\n"
                  "if (api) { prop.setInputLayerAndStage = (l, s) => { calls.push([l, s]); prop.inputLayerAndStage = [l, s]; }; }\n"
                  "let out;\n"
                  "try { caviSetLayerInput(prop, value); out = caviLayerInput(prop); }\n"
                  "catch (error) { out = {error: error.message}; }\n"
                  "process.stdout.write(JSON.stringify({out, calls}));")
        run = subprocess.run(["node", "-e", script, json.dumps([value, limit, layer_param, api])],
                             capture_output=True, text=True, check=True)
        return json.loads(run.stdout)

    def test_a_layer_by_name_is_set_at_its_stage(self):
        self.assertEqual(self.layer_input({"layer": "Map", "stage": "masks"}),
                         {"out": {"layer": 2, "stage": "masks"}, "calls": [[2, 0], [2, -2]]})
        self.assertEqual(self.layer_input({"layer": None, "stage": "source"})["out"], {"layer": 0, "stage": "source"})

    def test_a_stage_past_the_cycle_safe_limit_is_refused(self):
        self.assertEqual(self.layer_input({"layer": 1, "stage": "effects"}, limit=-2)["out"], {
            "error": "Displacement Map Layer at stage effects makes a render cycle; its highest safe stage is masks"})

    def test_a_bad_stage_a_property_that_is_not_a_layer_and_old_after_effects_are_refused(self):
        self.assertEqual(self.layer_input({"layer": 2, "stage": "comp"}), {"out": {
            "error": "Displacement Map Layer has no stage comp; its stages are source, masks and effects"},
            "calls": []})
        self.assertEqual(self.layer_input({"layer": 2, "stage": "masks"}, layer_param=False)["out"], {
            "error": "Displacement Map Layer is not a layer parameter; {layer, stage} sets one"})
        self.assertEqual(self.layer_input({"layer": 2, "stage": "masks"}, api=False)["out"], {
            "error": "A layer parameter's stage needs After Effects 26.5 or later"})


@unittest.skipUnless(shutil.which("node"), "node is required")
class PropertyPathTest(unittest.TestCase):
    def paths(self, path):
        """The paths ae_properties.jsx reports for ``path`` on a layer Scene > Effects > Cineware > Renderer."""
        lib = (host.JSX / "lib.jsx").read_text()
        start = lib.index("function caviProp(")
        script = ("const $ = {evalFile() {}}; function File() {} const CAVI_LIB = ''; const CAVI_TRANSFORM = {};\n"
                  "const PropertyType = {PROPERTY: 1, NAMED_GROUP: 3};\n"
                  "const PropertyValueType = {NO_VALUE: 0, CUSTOM_VALUE: 1, SHAPE: 2, MARKER: 3, TEXT_DOCUMENT: 4};\n"
                  "function make(name, kids, parent) {\n"
                  "  const p = {name, matchName: name, parentProperty: parent,\n"
                  "    propertyDepth: parent ? parent.propertyDepth + 1 : 0,\n"
                  "    propertyType: kids ? PropertyType.NAMED_GROUP : PropertyType.PROPERTY, propertyValueType: 9,\n"
                  "    value: 2, numKeys: 0, canSetExpression: false, expression: ''};\n"
                  "  p.kids = (kids || []).map(k => make(k[0], k[1], p));\n"
                  "  p.numProperties = p.kids.length;\n"
                  "  p.property = ref => (typeof ref === 'number' ? p.kids[ref - 1] : p.kids.find(k => k.name === ref)) || null;\n"
                  "  return p;\n"
                  "}\n"
                  "const layer = make('Scene', [['Effects', [['Cineware', [['Renderer']]]]]], null);\n"
                  "let report = null;\n"
                  "function caviFail(message) { throw new Error(message); }\n"
                  "function caviComp() { return {name: 'C'}; }\n"
                  "function caviLayer() { return layer; }\n"
                  "function caviMenuItems() { return null; }\n"
                  "function caviLayerInput() { return null; }\n"
                  "function caviReport(r) { report = r; }\n"
                  "const CAVI_ARGS = JSON.parse(process.argv[1]);\n"
                  + lib[start:lib.index("\n}\n", start) + 3] + (host.JSX / "ae_properties.jsx").read_text() +
                  "\nprocess.stdout.write(JSON.stringify(report.properties.map(p => p.path)));")
        arguments = {"comp": "C", "layer": "Scene", "path": path, "depth": 4, "max_nodes": 100, "time": None,
                     "keyframes": False}
        out = subprocess.run(["node", "-e", script, json.dumps(arguments)], capture_output=True, text=True,
                             check=True)
        return json.loads(out.stdout)

    def test_a_read_from_a_group_reports_paths_from_the_layer(self):
        for path in (None, "Effects", "Effects/Cineware", "Effects/Cineware/Renderer"):
            with self.subTest(path=path):
                self.assertEqual(self.paths(path), ["Scene/Effects/Cineware/Renderer"])


@unittest.skipUnless(shutil.which("node"), "node is required")
class CinewareFrameTest(unittest.TestCase):
    def frames(self, cineware):
        """The files ae_frame_png.jsx writes when it is called as edit.warmed calls it, on a comp that renders black
        at the first time of the first call when it holds a Cineware layer, as After Effects 26.5 does."""
        lib = (host.JSX / "lib.jsx").read_text()
        functions = ""
        for name in ("caviWarmCineware", "caviHasCineware"):
            if f"function {name}(" in lib:
                start = lib.index(f"function {name}(")
                functions += lib[start:lib.index("\n}\n", start) + 3]
        script = ("const $ = {evalFile() {}}; function File(path) { this.path = path; } const CAVI_LIB = '';\n"
                  "function CompItem() {}\n"
                  "const [cineware, args, source] = JSON.parse(process.argv[1]);\n"
                  "const written = {};\n"
                  "let CAVI_ARGS = null, report = null, calls = 0, first = null;\n"
                  "const effects = {property: name => (cineware && name === 'CINEMA 4D Effect' ? {} : null)};\n"
                  "const layer = {property: name => (name === 'ADBE Effect Parade' ? effects : null), source: null};\n"
                  "const comp = Object.assign(new CompItem(), {id: 1, name: 'C', numLayers: 1, layer: () => layer,\n"
                  "  saveFrameToPng(time, file) {\n"
                  "    if (first === null) { first = time; }\n"
                  "    written[file.path] = cineware && calls === 1 && time === first ? 'black' : 'scene at ' + time;\n"
                  "  }});\n"
                  "function caviComp() { return comp; }\n"
                  "function caviFail(message) { throw new Error(message); }\n"
                  "function caviReport(r) { report = r; }\n"
                  + functions +
                  "function call(a) { CAVI_ARGS = a; calls++; eval(source); }\n"
                  "call(args);\n"
                  "if (report.warming) { call(Object.assign({}, args, {warm: null})); }\n"
                  "process.stdout.write(JSON.stringify(written));")
        arguments = {"comp": "C", "background": False, "warm": "/out/.warm.png",
                     "frames": [{"time": 0.5, "file": "/out/a.png"}, {"time": 0.6, "file": "/out/b.png"}]}
        payload = json.dumps([cineware, arguments, (host.JSX / "ae_frame_png.jsx").read_text()])
        out = subprocess.run(["node", "-e", script, payload], capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def test_the_first_frame_of_a_cineware_comp_shows_the_scene(self):
        self.assertEqual(self.frames(True), {"/out/.warm.png": "black", "/out/a.png": "scene at 0.5",
                                             "/out/b.png": "scene at 0.6"})

    def test_a_comp_without_cineware_renders_each_frame_once(self):
        self.assertEqual(self.frames(False), {"/out/a.png": "scene at 0.5", "/out/b.png": "scene at 0.6"})


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

    def test_a_call_stopped_by_an_exit_leaves_no_process_it_started(self):
        app = subprocess.Popen(["sleep", "30"])
        self.addCleanup(app.kill)
        folder = Path(tempfile.mkdtemp(prefix="ae-watched-"))
        self.addCleanup(shutil.rmtree, folder)
        marker = folder / "pid"
        threading.Timer(1, lambda: (app.kill(), app.wait())).start()
        with self.assertRaisesRegex(RuntimeError, "exited during the call"):
            host.run_watched(["sh", "-c", f'sleep 60 & echo $! > "{marker}"; wait'], 60, app.pid, interval=0.1)
        started = int(marker.read_text())
        self.addCleanup(lambda: host.alive(started) and os.kill(started, signal.SIGKILL))
        deadline = time.monotonic() + 5
        while host.alive(started) and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertFalse(host.alive(started), f"pid {started} outlived the call")


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
