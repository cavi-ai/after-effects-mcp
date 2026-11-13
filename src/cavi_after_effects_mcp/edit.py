"""Editing helpers: project open/save, beat grids and single-frame renders through aerender."""

import shutil
import tempfile
from pathlib import Path

from cavi_mcp_core.proc import diagnostics, run_sync

from . import host

FRAME_MODULE = "TIFF Sequence with Alpha"


def beat_grid(bpm, beats_per_bar, start, end):
    """Markers on every beat from ``start`` up to (not including) ``end``, commented bar.beat, chapter on each downbeat."""
    spacing = 60.0 / bpm
    markers, beat = [], 0
    while start + beat * spacing < end - 1e-9:
        bar, number = divmod(beat, beats_per_bar)
        markers.append({"time": start + beat * spacing, "comment": f"{bar + 1}.{number + 1}", "duration": 0,
                        "chapter": f"Bar {bar + 1}" if number == 0 else None})
        beat += 1
    return markers


def to_png(source, destination):
    """Convert one image to PNG with sips."""
    result = run_sync(["sips", "-s", "format", "png", str(source), "--out", str(destination)], 60)
    if result.returncode or not Path(destination).is_file():
        raise RuntimeError("Could not convert the frame to PNG: " + diagnostics(result))


def project_op(args, target):
    """Run ae_project.jsx; its report is saved in the project it names, or in a temporary one when refused."""
    fallback = Path(tempfile.gettempdir()) / "cavi-ae-project.aep"
    candidates = [p for p in (target, host.CURRENT[0], fallback) if p]
    before = {p: host.fingerprint(p) for p in candidates}
    host.do_script(host.script_call(host.JSX / "ae_project.jsx", fallback, {**args, "fallback": str(fallback)}), 300)
    for path in candidates:
        if host.fingerprint(path) not in (None, before[path]):
            report = host.project_report(path)
            if report.get("errors"):
                raise RuntimeError("After Effects script: " + "; ".join(map(str, report["errors"])))
            host.CURRENT[0] = Path(report["path"]) if report.get("path") else None
            return report
    raise RuntimeError(f"The project call saved no report; the open project is not {target}")


def render_frames(project, comp, times, directory):
    """Render the frame at each time to ``directory`` as PNG through a temporary queue entry that is removed again."""
    project, directory = host.absolute(project, ".aep"), host.absolute(directory)
    directory.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="frames-", dir=directory))
    try:
        frames = [{"time": t, "file": str(work / f"f{i}_[#####].tif")} for i, t in enumerate(times)]
        queued = host.run_template("ae_frame_queue", project, {"action": "add", "comp": comp, "frames": frames,
                                                               "output_module": FRAME_MODULE})
        try:
            host.aerender("-project", str(project))
        finally:
            host.run_template("ae_frame_queue", project, {"action": "remove", "count": len(times),
                                                          "enabled": queued["enabled"]})
        out = []
        for i, t in enumerate(times):
            made = sorted(work.glob(f"f{i}_*.tif"))
            if len(made) != 1:
                raise RuntimeError(f"aerender wrote {len(made)} frames for time {t}")
            png = directory / f"{comp}_{t:g}s.png"
            to_png(made[0], png)
            out.append({"time": t, "file": str(png)})
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)
