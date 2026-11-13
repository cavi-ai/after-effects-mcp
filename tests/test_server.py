import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TOOLS = {"ae_status", "ae_launch", "ae_script", "ae_render_queue", "after_effects_render", "ae_inspect",
         "ae_comp_new", "ae_layer_add", "ae_keyframes", "ae_effect_add", "ae_text_animator",
         "ae_footage_replace", "ae_render_queue_set", "ae_presets", "ae_preset_apply", "ae_transition",
         "ae_transitions", "ae_project", "ae_layer_set", "ae_text_set", "ae_layer_edit", "ae_comp_set",
         "ae_import", "ae_markers", "ae_frame", "ae_shape_add", "ae_mask", "ae_effects", "ae_camera", "ae_essential_graphics", "ae_mogrt_export",
         "ae_template_render", "ae_collect"}


class ProtocolTest(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_and_refused_recipe(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "recipe.json").write_text(json.dumps({"version": 2}))
            params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"],
                                           env={**os.environ, "CAVI_ADOBE_WORKSPACE": str(root)})
            async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
                await client.initialize()
                catalog = {tool.name: tool for tool in (await client.list_tools()).tools}
                self.assertEqual(set(catalog), TOOLS)
                for tool in catalog.values():
                    self.assertTrue(tool.output_schema["required"], tool.name)
                reply = await client.call_tool("after_effects_render",
                                               {"recipe": "recipe.json", "directory": "frames"})
                self.assertTrue(reply.is_error)
                self.assertFalse((root / "frames").exists())
                reply = await client.call_tool("ae_render_queue", {"project": "/x.aep", "outputs": []})
                self.assertTrue(reply.is_error)

    async def test_scene_tools_refuse_bad_input_before_calling_after_effects(self):
        params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"])
        async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
            await client.initialize()
            calls = {
                "ae_inspect": {"project": "/x.aep", "scope": "comp"},
                "ae_footage_replace": {"project": "/x.aep", "item": "a", "file": "relative.png"},
                "ae_render_queue_set": {"project": "/x.aep", "add": [{"comp": "a", "file": "out.mov"}]},
                "ae_layer_add": {"project": "/x.aep", "layer": {"comp": "a", "kind": "footage", "name": "p",
                                                                 "file": "relative.png"}},
                "ae_keyframes": {"project": "/x.aep", "comp": "a", "layer": 1, "property": "position"},
                "ae_text_animator": {"project": "/x.aep", "comp": "a", "layer": 1},
            }
            expected = {"ae_inspect": "comp name", "ae_footage_replace": "absolute path",
                        "ae_render_queue_set": "absolute path", "ae_layer_add": "absolute path",
                        "ae_keyframes": "keyframes or an expression", "ae_text_animator": "animator property"}
            for name, arguments in calls.items():
                reply = await client.call_tool(name, arguments)
                self.assertTrue(reply.is_error, name)
                self.assertIn(expected[name], reply.content[0].text, name)

    async def test_transition_preset_and_queue_inputs_are_refused_before_calling_after_effects(self):
        params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"])
        base = {"project": "/x.aep", "comp": "a"}
        calls = [
            ("ae_transition", {**base, "kind": "spin", "layer": 1, "seconds": 1}, "Unknown transition"),
            ("ae_transition", {**base, "kind": "crossfade", "layer": 1}, "seconds or frames"),
            ("ae_transition", {**base, "kind": "crossfade", "layer": 1, "frames": 5, "seconds": 1},
             "seconds or frames"),
            ("ae_transition", {**base, "kind": "crossfade", "seconds": 1, "from_layer": 1}, "from_layer and to_layer"),
            ("ae_preset_apply", {**base, "layer": 1, "preset": "/nope.ffx"}, "No .ffx preset"),
            ("ae_render_queue_set", {"project": "/x.aep", "clear": True}, "clear removes"),
        ]
        async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
            await client.initialize()
            for name, arguments, message in calls:
                reply = await client.call_tool(name, arguments)
                self.assertTrue(reply.is_error, name)
                self.assertIn(message, reply.content[0].text, name)

    async def test_edit_tools_refuse_bad_input_before_calling_after_effects(self):
        params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"])
        base = {"project": "/x.aep", "comp": "a", "layer": 1}
        calls = [
            ("ae_project", {"action": "open", "path": "/nope/missing.aep"}, "No project at"),
            ("ae_project", {"action": "save_as"}, "needs a path"),
            ("ae_project", {"action": "save_as", "path": "relative.aep"}, "absolute path"),
            ("ae_layer_set", base, "at least one"),
            ("ae_layer_set", {**base, "parent": 2, "no_parent": True}, "parent or no_parent"),
            ("ae_text_set", base, "at least one"),
            ("ae_layer_edit", {"project": "/x.aep", "comp": "a", "layers": [1], "action": "split"}, "needs a time"),
            ("ae_layer_edit", {"project": "/x.aep", "comp": "a", "layers": [1], "action": "reorder"}, "needs move_to"),
            ("ae_layer_edit", {"project": "/x.aep", "comp": "a", "layers": [1], "action": "precompose"}, "needs a name"),
            ("ae_comp_set", {"project": "/x.aep", "comp": "a"}, "at least one"),
            ("ae_import", {"project": "/x.aep", "files": ["relative.png"]}, "absolute path"),
            ("ae_markers", {"project": "/x.aep", "comp": "a"}, "markers or a beat grid"),
            ("ae_markers", {"project": "/x.aep", "comp": "a", "grid": {"bpm": 120, "end": 4, "start": 4}}, "after start"),
            ("ae_frame", {"project": "/x.aep", "comp": "a", "times": [0], "directory": "relative"}, "absolute path"),
        ]
        async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
            await client.initialize()
            for name, arguments, message in calls:
                reply = await client.call_tool(name, arguments)
                self.assertTrue(reply.is_error, (name, arguments))
                self.assertIn(message, reply.content[0].text, (name, arguments))

    async def test_motion_tools_refuse_bad_input_before_calling_after_effects(self):
        params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"])
        base = {"project": "/x.aep", "comp": "a"}
        calls = [
            ("ae_shape_add", {**base, "shape": {"kind": "path"}}, "needs path"),
            ("ae_shape_add", {**base, "shape": {"kind": "rect"}, "operators": [{"type": "round_corners"}]},
             "round_corners needs radius"),
            ("ae_shape_add", {**base, "shape": {"kind": "rect"}, "operators": [{"type": "trim"}]}, "trim needs"),
            ("ae_mask", {**base, "layer": 1}, "needs a shape"),
            ("ae_mask", {**base, "layer": 1, "mask": 1}, "at least one"),
            ("ae_mask", {**base, "layer": 1, "shape": {"kind": "ellipse"}}, "needs box"),
            ("ae_camera", base, "camera or a light"),
            ("ae_camera", {**base, "light": {"type": "spot"}, "rig": True}, "rig needs a camera"),
            ("ae_keyframes", {**base, "layer": 1, "property": "rotation", "expression": "1",
                              "preset": {"kind": "wiggle"}}, "not both"),
        ]
        async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
            await client.initialize()
            for name, arguments, message in calls:
                reply = await client.call_tool(name, arguments)
                self.assertTrue(reply.is_error, (name, arguments))
                self.assertIn(message, reply.content[0].text, (name, arguments))

    async def test_delivery_tools_refuse_bad_input_before_calling_after_effects(self):
        params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"])
        add = {"comp": "a", "file": "/x/out.mov", "output": {"channels": "RGB+Alpha", "format": "PNG"}}
        calls = [
            ("ae_render_queue_set", {"project": "/x.aep", "add": [add]}, "format, channels cannot be set"),
            ("ae_render_queue_set", {"project": "/x.aep", "add": [{"comp": "a", "file": "/x/o.mov",
                                                                    "time_span": {"start": 0, "duration": 0}}]}, "duration"),
            ("ae_mogrt_export", {"project": "/x.aep", "comp": "a", "file": "/x/t.mogrt"}, "writes no file"),
            ("ae_template_render", {"template": "relative.aep", "project": "/x.aep",
                                    "renders": [{"comp": "a", "file": "/x/o.mov"}]}, "absolute path"),
            ("ae_project", {"action": "reduce", "path": "/x.aep"}, "reduce needs comps"),
            ("ae_project", {"action": "remove_unused"}, "needs a path"),
            ("ae_collect", {"project": "/x.aep", "folder": "relative"}, "absolute path"),
        ]
        async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
            await client.initialize()
            for name, arguments, message in calls:
                reply = await client.call_tool(name, arguments)
                self.assertTrue(reply.is_error, (name, arguments))
                self.assertIn(message, reply.content[0].text, (name, arguments))

    async def test_preset_apply_is_refused_for_an_existing_preset(self):
        with tempfile.TemporaryDirectory() as folder:
            preset = Path(folder) / "look.ffx"
            preset.write_bytes(b"")
            params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"])
            async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
                await client.initialize()
                reply = await client.call_tool("ae_preset_apply", {"project": "/x.aep", "comp": "a",
                                                                   "layer": 1, "preset": str(preset)})
                self.assertTrue(reply.is_error)
                self.assertIn("exits headless After Effects", reply.content[0].text)


if __name__ == "__main__":
    unittest.main()
