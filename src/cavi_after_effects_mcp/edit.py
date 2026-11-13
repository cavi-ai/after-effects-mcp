"""Editing helpers: project open/save, beat grids and single-frame renders through aerender."""

import shutil
import tempfile
from pathlib import Path

from cavi_mcp_core.proc import diagnostics, run_sync

from . import host

FRAME_MODULE = "TIFF Sequence with Alpha"
KAPPA = 0.5522847498


def expression_preset(kind, freq, amp, decay, speed):
    """The expression text of a preset."""
    if kind == "wiggle":
        return f"wiggle({freq:g}, {amp:g})"
    if kind == "loop_cycle":
        return 'loopOut("cycle")'
    if kind == "loop_pingpong":
        return 'loopOut("pingpong")'
    if kind == "time_rotation":
        return f"value + time * {speed:g}"
    return (f"amp = {amp:g};\nfreq = {freq:g};\ndecay = {decay:g};\nn = 0;\n"
            "if (numKeys > 0) {\n  n = nearestKey(time).index;\n  if (key(n).time > time) n--;\n}\n"
            "if (n == 0) {\n  value;\n} else {\n  t = time - key(n).time;\n"
            "  v = velocityAtTime(key(n).time - thisComp.frameDuration / 10);\n"
            "  value + v * (amp / 100) * Math.sin(freq * t * 2 * Math.PI) / Math.exp(decay * t);\n}")


def mask_shape(spec):
    """Vertices and tangents (relative to each vertex) of a rect, ellipse or points mask."""
    if spec.kind == "points":
        return {"vertices": spec.path.vertices, "in_tangents": spec.path.in_tangents,
                "out_tangents": spec.path.out_tangents, "closed": spec.path.closed}
    x, y, w, h = spec.box
    if spec.kind == "rect":
        zero = [[0, 0]] * 4
        return {"vertices": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], "in_tangents": zero,
                "out_tangents": zero, "closed": True}
    rx, ry, kx, ky = w / 2, h / 2, w / 2 * KAPPA, h / 2 * KAPPA
    return {"vertices": [[x + rx, y], [x + w, y + ry], [x + rx, y + h], [x, y + ry]],
            "in_tangents": [[-kx, 0], [0, -ky], [kx, 0], [0, ky]],
            "out_tangents": [[kx, 0], [0, ky], [-kx, 0], [0, -ky]], "closed": True}


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


def render_frames(project, comp, times, directory, alpha=False):
    """Render the frame at each time to ``directory`` as PNG through a temporary queue entry that is removed again; the comp background is composited in unless ``alpha``."""
    project, directory = host.absolute(project, ".aep"), host.absolute(directory)
    directory.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="frames-", dir=directory))
    try:
        frames = [{"time": t, "file": str(work / f"f{i}_[#####].tif")} for i, t in enumerate(times)]
        queued = host.run_template("ae_frame_queue", project, {"action": "add", "comp": comp, "frames": frames,
                                                               "output_module": FRAME_MODULE,
                                                               "background": not alpha})
        try:
            host.aerender("-project", str(project))
        finally:
            host.run_template("ae_frame_queue", project, {"action": "remove", "comp": comp, "count": len(times),
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
