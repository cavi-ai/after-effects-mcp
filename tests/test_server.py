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
         "ae_footage_replace", "ae_render_queue_set"}


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


if __name__ == "__main__":
    unittest.main()
