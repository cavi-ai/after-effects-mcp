"""Run the MCP Eval probes in evals/manifest.json against the server over stdio, without After Effects.

The application path points at a folder that does not exist, so no probe can start After Effects. The run fails
when a probe fails: the catalog over its tool, schema or token budget, broken pagination, an undeclared surface or
a wrong answer to an unknown protocol version. The report and the evaluator's version and checksum are written to
.tmp/evals/<run>/.

    MCPEVAL_EXECUTABLE=/path/to/mcpeval uv run --locked python evals/probe.py
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    executable = shutil.which(os.environ.get("MCPEVAL_EXECUTABLE", str(ROOT / "node_modules/.bin/mcpeval")))
    if executable is None:
        raise SystemExit("Install MCP Eval with npm install or set MCPEVAL_EXECUTABLE")
    evaluator = Path(executable).resolve()
    reports = ROOT / ".tmp/evals"
    reports.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="probe-", dir=reports))
    version = subprocess.run([str(evaluator), "--version"], capture_output=True, text=True, timeout=30, check=True)
    (output / "metadata.json").write_text(json.dumps({
        "evaluator_version": version.stdout.strip(),
        "evaluator_sha256": hashlib.sha256(evaluator.read_bytes()).hexdigest(),
        "source_revision": os.environ.get("MCPEVAL_SOURCE_REVISION"),
    }, indent=2) + "\n")
    with tempfile.TemporaryDirectory(prefix="ae-eval-") as work:
        env = {**os.environ, "MCPEVAL_HOME": str(Path(work) / "store"),
               "CAVI_AFTER_EFFECTS_APP": str(Path(work) / "Missing" / "Adobe After Effects.app")}
        with (output / "after-effects.json").open("w") as stream:
            result = subprocess.run([str(evaluator), "probe", "--server", "after-effects",
                                     "--manifest", str(ROOT / "evals/manifest.json"), "--format", "json",
                                     "--gate-only", "--", sys.executable, "-m", "cavi_after_effects_mcp.server"],
                                    cwd=ROOT, env=env, stdout=stream, check=False, timeout=300)
    report = json.loads((output / "after-effects.json").read_text())
    for case in report["cases"]:
        print("PASS" if case["passed"] else "FAIL", case["id"], case["reason"] or "")
    print(f"mcpeval exit {result.returncode}, report {output / 'after-effects.json'}")
    return result.returncode


sys.exit(main())
