"""Drive the real server over stdio against headless After Effects: the README first result."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(sys.argv[1]).resolve()
PROJECT = str(ROOT / "hello.aep")
STEPS = [
    ("ae_status", {}),
    ("ae_launch", {}),
    ("ae_comp_new", {"project": PROJECT, "name": "Title", "width": 1280, "height": 720, "duration": 3,
                     "fps": 30, "background": [0.05, 0.07, 0.12], "replace": True}),
    ("ae_layer_add", {"project": PROJECT, "layer": {
        "comp": "Title", "kind": "text", "name": "Headline", "text": "Hello, After Effects", "size": 90,
        "fill": [1, 1, 1], "justification": "center",
        "transform": {"position": [640, 380]}}}),
    ("ae_text_animator", {"project": PROJECT, "comp": "Title", "layer": "Headline", "opacity": 0,
                          "duration": 1.2}),
    ("ae_markers", {"project": PROJECT, "comp": "Title", "grid": {"bpm": 120, "end": 3}}),
    ("ae_frame", {"project": PROJECT, "comp": "Title", "times": [0.2, 2.5], "directory": str(ROOT / "frames")}),
    ("ae_inspect", {"project": PROJECT, "scope": "comp", "comp": "Title"}),
]


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"])
    async with stdio_client(params) as (r, w), ClientSession(r, w, read_timeout_seconds=900) as client:
        await client.initialize()
        for name, arguments in STEPS:
            reply = await client.call_tool(name, arguments)
            body = reply.structured_content if not reply.is_error else reply.content[0].text
            print(name, "ERROR" if reply.is_error else "ok", json.dumps(body)[:600], flush=True)


asyncio.run(main())
