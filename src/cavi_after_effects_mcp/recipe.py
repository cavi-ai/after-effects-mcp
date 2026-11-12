"""Bounded aerender of one declared AEP composition range to a pinned PNG sequence."""

import os
import re
from pathlib import Path

from cavi_adobe_mcp import art_media as media
from cavi_adobe_mcp.native_media import MediaOutcomeUnknown, run


def ae_render(workspace, recipe, directory):
    """Render an existing selected AEP composition to a new PNG sequence."""
    source, target = media.inside(workspace, recipe), media.inside(workspace, directory)
    spec = media.load(source)
    if (not isinstance(spec, dict) or spec.get("version") != 1
            or set(spec) != {"version", "name", "project", "dependencies", "composition", "start", "end",
                             "fps", "loop", "alpha", "output_module"}
            or type(spec["start"]) is not int or type(spec["end"]) is not int
            or not 0 <= spec["start"] <= spec["end"] or spec["end"] - spec["start"] >= 1000
            or type(spec["loop"]) is not bool or spec["alpha"] != "straight"
            or not isinstance(spec["composition"], str) or not 1 <= len(spec["composition"]) <= 128
            or not isinstance(spec["output_module"], str) or not 1 <= len(spec["output_module"]) <= 128
            or any(ord(c) < 32 for c in spec["composition"] + spec["output_module"])
            or not isinstance(spec["dependencies"], list) or len(spec["dependencies"]) > 64):
        raise ValueError("Declare one bounded composition, inclusive range, rational FPS, dependencies "
                         "and RGBA PNG output module")
    media.name(spec["name"])
    fps = media.rate(spec["fps"])
    if (spec["end"] - spec["start"] + 1) * fps["denominator"] / fps["numerator"] > 300:
        raise ValueError("Render exceeds 300 seconds of animation")
    project = media.inside(workspace, spec["project"])
    if project.suffix.lower() != ".aep":
        raise ValueError("Use an existing AEP project")
    inputs = [source, project, *(media.inside(workspace, p) for p in spec["dependencies"])]
    fingerprints = {str(p): media.digest(p) for p in inputs}
    binaries = sorted(Path("/Applications").glob("Adobe After Effects */aerender"))
    if len(binaries) != 1 or not os.access(binaries[0], os.X_OK):
        raise ValueError("Exactly one executable Adobe After Effects aerender must be installed")
    target.mkdir(parents=True, exist_ok=False)
    command = [str(binaries[0]), "-project", str(project), "-comp", spec["composition"],
               "-s", str(spec["start"]), "-e", str(spec["end"]), "-OMtemplate", spec["output_module"],
               "-output", str(target / "frame_[#####].png")]
    try:
        execution = run(command, target)
        if any(media.digest(p) != sha for p, sha in fingerprints.items()):
            raise MediaOutcomeUnknown("An AEP render input changed during execution")
        output = sorted(target.glob("frame_*.png"))
        numbers = [int(match[1]) for p in output
                   if (match := re.fullmatch(r"frame_\[(\d+)\]\.png", p.name))]
        if not numbers:
            numbers = [int(match[1]) for p in output if (match := re.fullmatch(r"frame_(\d+)\.png", p.name))]
        count = spec["end"] - spec["start"] + 1
        if (len(output) != count or len(numbers) != count
                or numbers != list(range(numbers[0], numbers[0] + count))):
            raise MediaOutcomeUnknown("Render did not produce the complete contiguous declared PNG range")
        ingest = {"version": 1, "name": spec["name"], "fps": fps, "loop": spec["loop"],
                  "alpha": "straight", "sources": [str(p) for p in inputs],
                  "frames": [{"name": f"Frame{i:06}", "path": str(p)} for i, p in enumerate(output)]}
        media.write(target / "frames.json", ingest)
        result = media.ingest(workspace, str(target / "frames.json"), str(target / "handoff"))
        return {**result, "execution": execution, "composition": spec["composition"],
                "timing_authority": "caller_declared", "dependencies_authority": "caller_declared",
                "launches_applications": True}
    except (OSError, ValueError) as exc:
        raise MediaOutcomeUnknown("Render started; inspect its directory before continuing: " + str(exc)) from exc
