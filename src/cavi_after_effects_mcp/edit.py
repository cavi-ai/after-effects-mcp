"""Editing helpers: project open/save, beat grids and single-frame renders through aerender."""

import shutil
import tempfile
import time
from pathlib import Path

from cavi_mcp_core.proc import diagnostics, run_sync

from . import host

FRAME_MODULE = "TIFF Sequence with Alpha"
RENDER_ATTEMPTS = 3
RENDER_RETRY_SECONDS = 15
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


def direct_frames(project, comp, frames, alpha):
    """Write the frames with Comp.saveFrameToPng, which needs no aerender; False when After Effects did not write them all."""
    for frame in frames:
        Path(frame["file"]).unlink(missing_ok=True)
    try:
        host.run_template("ae_frame_png", project, {"comp": comp, "frames": frames, "background": not alpha})
    except RuntimeError as error:
        if "No comp named" in str(error):
            raise
        return False
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if all(Path(f["file"]).is_file() and Path(f["file"]).stat().st_size > 0 for f in frames):
            return True
        time.sleep(0.25)
    return False


def render_frames(project, comp, times, directory, alpha=False):
    """Render the frame at each time to ``directory`` as PNG through a temporary queue entry that is removed again; the comp background is composited in unless ``alpha``."""
    project, directory = host.absolute(project, ".aep"), host.absolute(directory)
    directory.mkdir(parents=True, exist_ok=True)
    direct = [{"time": t, "file": str(directory / f"{comp}_{t:g}s.png")} for t in times]
    if direct_frames(project, comp, direct, alpha):
        return direct
    work = Path(tempfile.mkdtemp(prefix="frames-", dir=directory))
    try:
        frames = [{"time": t, "file": str(work / f"f{i}_[#####].tif")} for i, t in enumerate(times)]
        queued = host.run_template("ae_frame_queue", project, {"action": "add", "comp": comp, "frames": frames,
                                                               "output_module": FRAME_MODULE,
                                                               "background": not alpha})
        try:
            for attempt in range(RENDER_ATTEMPTS):
                host.aerender("-project", str(project))
                if all(len(list(work.glob(f"f{i}_*.tif"))) == 1 for i in range(len(times))):
                    break
                if attempt + 1 < RENDER_ATTEMPTS:
                    time.sleep(RENDER_RETRY_SECONDS)
        finally:
            host.run_template("ae_frame_queue", project, {"action": "remove", "comp": comp, "count": len(times),
                                                          "enabled": queued["enabled"]})
        out = []
        for i, t in enumerate(times):
            made = sorted(work.glob(f"f{i}_*.tif"))
            if len(made) != 1:
                raise RuntimeError(f"aerender wrote {len(made)} frames for time {t} after {RENDER_ATTEMPTS} attempts; it "
                                   "exits without rendering when the Adobe Media Encoder service it launches fails")
            png = directory / f"{comp}_{t:g}s.png"
            to_png(made[0], png)
            out.append({"time": t, "file": str(png)})
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def copy_footage(files, folder):
    """Copy each distinct file into ``folder``; a name already taken by another file gets a numeric suffix. Returns {source: copy}."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    copies, taken = {}, set()
    for source in map(Path, files):
        if str(source) in copies:
            continue
        target, count = folder / source.name, 1
        while target.name in taken or (target.exists() and not target.samefile(source)):
            count += 1
            target = folder / f"{source.stem}_{count}{source.suffix}"
        taken.add(target.name)
        if not target.exists():
            shutil.copy2(source, target)
        copies[str(source)] = str(target)
    return copies


def missing_footage(project):
    """Names of footage items whose file is missing, read through ae_inspect."""
    report = host.run_template("ae_inspect", project, {"scope": "project", "comp": None})
    return [f["name"] for f in report["footage"] if f["missing"]]


def collect(project, folder):
    """Copy the used footage files into ``folder`` and relink every item to its copy."""
    found = host.run_template("ae_collect", project, {"mode": "list"})["items"]
    skipped = [f["name"] for f in found if f["used"] and (f["sequence"] or f["missing"])]
    used = [f for f in found if f["used"] and not f["sequence"] and not f["missing"]]
    copies = copy_footage([f["file"] for f in used], folder)
    links = [{"id": f["id"], "file": copies[f["file"]]} for f in used]
    done = host.run_template("ae_collect", project, {"mode": "relink", "links": links})
    still = missing_footage(project)
    return {"project": str(project), "folder": str(folder), "items": len(used), "copied": len(copies),
            "relinked": done["relinked"], "skipped": skipped, "missing": len(still)}


def template_render(template, project, texts, footage, renders, discard):
    """Open ``template``, apply the text and footage edits, save to ``project`` and aerender the named comps."""
    project_op({"action": "open", "path": str(template), "discard": discard, "overwrite": False, "comps": []},
               template)
    for text in texts:
        host.run_template("ae_text_set", project, text)
    for item, file in footage.items():
        host.run_template("ae_footage_replace", project, {"item": item, "file": file})
    names = {r["comp"] for r in renders}
    queue = host.run_template("ae_inspect", project, {"scope": "queue", "comp": None})["queue"]
    off = [{"index": q["index"], "render": False, "label": None, "locked": False}
           for q in queue if q["comp"] not in names and q["render"]]
    add = [{**r, "locked": False, "time_span": None, "output": None} for r in renders]
    host.run_template("ae_render_queue_set", project, {"add": add, "update": off, "clear": True})
    comps = {c["name"]: c for c in host.run_template("ae_inspect", project, {"scope": "project", "comp": None})["comps"]}
    outputs = [{"comp": r["comp"], "file": r["file"], "frames": round(comps[r["comp"]]["duration"] * comps[r["comp"]]["fps"])}
               for r in renders]
    return host.render_queue(project, outputs, renders[0]["render_settings"], renders[0]["output_module"])["outputs"]
