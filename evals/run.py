"""Exercise the server over stdio without After Effects.

Every call is one the server must answer without starting the application: the application path points at a
folder that does not exist, so a call that reached After Effects would fail instead of launching it. The run
checks that each tool is listed with a description and its access annotation, that each tool rejects an unknown
argument, and the cases in cases.json.

    uv run --locked python evals/run.py
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
TOOL_COUNT = 45


def pointer(value, path):
    for key in path.strip("/").split("/"):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def fill(value, work):
    if isinstance(value, str):
        return value.replace("{work}", str(work))
    if isinstance(value, dict):
        return {key: fill(item, work) for key, item in value.items()}
    return value


def text(reply):
    return "\n".join(getattr(item, "text", "") for item in reply.content)


async def check_case(session, case, work):
    reply = await session.call_tool(case["tool"], fill(case["arguments"], work))
    if case["expect"] == "error":
        assert reply.is_error, "expected a tool error"
        if case.get("error"):
            assert case["error"].lower() in text(reply).lower(), text(reply)
        return
    assert not reply.is_error, text(reply)
    for path, expected in case.get("equals", {}).items():
        assert pointer(reply.structured_content, path) == expected, reply.structured_content
    for path in case.get("required", []):
        assert pointer(reply.structured_content, path), path


async def main():
    work = Path(tempfile.mkdtemp(prefix="ae-evals-", dir=ROOT / ".tmp" if (ROOT / ".tmp").is_dir() else None))
    (work / "workspace").mkdir()
    env = {**os.environ, "CAVI_AFTER_EFFECTS_APP": str(work / "Missing" / "Adobe After Effects.app"),
           "CAVI_ADOBE_WORKSPACE": str(work / "workspace")}
    params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_after_effects_mcp.server"], env=env)
    failures = []
    async with stdio_client(params) as (reader, writer), ClientSession(reader, writer, read_timeout_seconds=90) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        if len(tools) != TOOL_COUNT:
            failures.append(f"listing: {len(tools)} tools, expected {TOOL_COUNT}")
        for tool in tools:
            if not tool.description or tool.annotations is None:
                failures.append(f"listing: {tool.name} has no description or annotations")
            reply = await session.call_tool(tool.name, {"unexpected_argument": 1})
            if not reply.is_error:
                failures.append(f"unknown-argument {tool.name}: accepted")
        for case in json.loads((ROOT / "evals/cases.json").read_text()):
            try:
                await check_case(session, case, work)
            except AssertionError as error:
                failures.append(f"{case['id']}: {error}")
    for line in failures:
        print("FAIL", line)
    print(f"{len(tools)} tools, {len(failures)} failures")
    return 1 if failures else 0


sys.exit(asyncio.run(main()))
