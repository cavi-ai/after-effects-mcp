import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TOOLS = {"ae_status", "ae_launch", "ae_script", "ae_render_queue", "after_effects_render"}


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


if __name__ == "__main__":
    unittest.main()
