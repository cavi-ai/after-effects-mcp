"""Drive the real server over stdio against headless After Effects: the README first result."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve()
PROJECT = str(ROOT / "title.aep")
COMP = "Title"


def add(spec):
    return "ae_layer_add", {"project": PROJECT, "layer": {"comp": COMP, **spec}}


def keys(layer, prop, *frames, **options):
    return "ae_keyframes", {"project": PROJECT, "comp": COMP, "layer": layer, "property": prop,
                            "keyframes": [{"time": t, "value": v} for t, v in frames], **options}


def reveal(layer, start, **properties):
    return "ae_text_animator", {"project": PROJECT, "comp": COMP, "layer": layer, "start": start,
                                "duration": 0.6, **properties}


STEPS = [
    ("ae_status", {}),
    ("ae_launch", {}),
    ("ae_comp_new", {"project": PROJECT, "name": COMP, "width": 1280, "height": 720, "duration": 3.5, "fps": 24,
                     "background": [0.02, 0.02, 0.06], "replace": True}),
    add({"kind": "footage", "name": "Aisle", "file": str(HERE / "media" / "aisle.mp4")}),
    keys("Aisle", "scale", (0, [100, 100]), (3.5, [108, 108])),
    add({"kind": "shape_rect", "name": "Bar", "fill": [0.02, 0.03, 0.09], "width": 600, "height": 132,
         "transform": {"position": [380, 590], "opacity": 82}}),
    keys("Bar", "position", (0.2, [-320, 590]), (0.7, [380, 590]), easy_ease=True),
    add({"kind": "shape_rect", "name": "Accent", "fill": [0.35, 0.85, 1], "width": 8, "height": 132,
         "transform": {"position": [84, 590]}}),
    keys("Accent", "scale", (0.6, [100, 0]), (0.9, [100, 100]), easy_ease=True),
    add({"kind": "text", "name": "Headline", "text": "Aisle B", "font": "AvenirNext-Bold", "size": 64,
         "fill": [1, 1, 1], "transform": {"position": [108, 585]}}),
    reveal("Headline", 0.55, opacity=0, position=[0, 24]),
    add({"kind": "text", "name": "Subline", "text": "Racks online at 02:00", "font": "AvenirNext-Medium",
         "size": 28, "tracking": 40, "fill": [0.55, 0.88, 1], "transform": {"position": [110, 630]}}),
    reveal("Subline", 0.9, opacity=0),
    ("ae_frame", {"project": PROJECT, "comp": COMP, "times": [0.5, 1, 2.5], "directory": str(ROOT / "frames")}),
    ("ae_inspect", {"project": PROJECT, "scope": "comp", "comp": COMP}),
]


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"])
    async with stdio_client(params) as (r, w), ClientSession(r, w, read_timeout_seconds=900) as client:
        await client.initialize()
        for name, arguments in STEPS:
            reply = await client.call_tool(name, arguments)
            body = reply.structured_content if not reply.is_error else reply.content[0].text
            print(name, "ERROR" if reply.is_error else "ok", json.dumps(body), flush=True)
            if reply.is_error:
                sys.exit(1)


asyncio.run(main())
