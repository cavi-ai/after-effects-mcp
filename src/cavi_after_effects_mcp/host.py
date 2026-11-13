"""Headless After Effects: launch, scripts over Apple Events, aerender and frame checks."""

import json
import os
import plistlib
import re
import shutil
import subprocess
import time
from pathlib import Path

from cavi_mcp_core.proc import diagnostics, run_sync

RUNNER = Path(__file__).with_name("runner.jsx")
JSX = Path(__file__).with_name("jsx")
RENDER_TIMEOUT = 3600
CURRENT = [None]  # the project the last call saved to


def newest(pattern):
    found = sorted(Path("/Applications").glob(pattern))
    if not found:
        raise ValueError(f"No /Applications/{pattern}")
    return found[-1]


def after_effects():
    """The newest installed After Effects folder, which holds the app and aerender."""
    return newest("Adobe After Effects 20*/aerender").parent


def processes():
    """Running After Effects pids, split into headless (-noui) and UI instances."""
    result = run_sync(["pgrep", "-fl", "MacOS/After Effects"], 10)
    headless, ui = [], []
    for line in result.stdout.splitlines():
        pid, _, command = line.partition(" ")
        (headless if "-noui" in command else ui).append(int(pid))
    return headless, ui


def status():
    folder = after_effects()
    app = next(folder.glob("Adobe After Effects 20*.app"))
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    headless, ui = processes()
    return {"app": str(app), "version": info.get("CFBundleShortVersionString", ""),
            "aerender": str(folder / "aerender"), "headless_pids": headless, "ui_pids": ui}


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_watched(command, timeout, pid, interval=0.5):
    """Run ``command`` while process ``pid`` lives; stop it and raise as soon as ``pid`` exits."""
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             start_new_session=True)
    deadline = time.monotonic() + timeout
    while child.poll() is None:
        if not alive(pid):
            child.kill()
            child.wait()
            raise RuntimeError(f"After Effects (pid {pid}) exited during the call; the next tool call starts it again")
        if time.monotonic() > deadline:
            child.kill()
            child.wait()
            raise RuntimeError(f"After Effects did not answer within {timeout} seconds")
        time.sleep(interval)
    out, err = child.communicate()
    return child.returncode, out, err


def do_script(code, timeout):
    """Run ExtendScript in the headless instance; DoScript answers 0 on success, 1 on any failure."""
    headless, _ = processes()
    if not headless:
        launch()
        headless, _ = processes()
    command = ["osascript", "-e", "on run argv", "-e", f"with timeout of {timeout} seconds",
               "-e", f'tell application "{after_effects().name}" to set answer to DoScript '
               "(item 1 of argv)", "-e", "end timeout", "-e", "return answer", "-e", "end run", code]
    returncode, out, err = run_watched(command, timeout + 30, headless[0])
    if returncode or out.strip() != "0":
        raise RuntimeError("After Effects script failed: " + (err.strip() or out.strip() or f"exit {returncode}"))


def launch():
    """Start one headless After Effects (-noui) and wait until it answers scripts."""
    headless, ui = processes()
    if ui:
        raise RuntimeError(f"After Effects is running with its UI (pid {ui[0]}); quit it first")
    if not headless:
        result = run_sync(["open", "-n", "-g", "-a", after_effects().name, "--args", "-noui"], 60)
        if result.returncode:
            raise RuntimeError("After Effects did not launch: " + diagnostics(result))
        for _ in range(120):
            if processes()[0]:
                break
            time.sleep(0.5)
        if not processes()[0]:
            raise RuntimeError("After Effects did not start within 60 seconds")
    do_script("app.project.numItems", 300)
    return status()


# Calls that abort headless After Effects (measured), each with the tool that does the job safely.
CRASHING_CALLS = {
    "applyPreset": "layer.applyPreset aborts After Effects; build the look with ae_effect_add, ae_keyframes and ae_text_animator",
    "executeCommand": "app.executeCommand runs menu commands that abort After Effects without a window (Convert Audio to Keyframes did, twice)",
    "findMenuCommandId": "menu command ids are only useful to app.executeCommand, which is refused",
}


def refuse_crashing_calls(script):
    """Refuse a script file that contains a call known to abort headless After Effects."""
    text = Path(script).read_text(encoding="utf-8", errors="replace")
    for call, reason in CRASHING_CALLS.items():
        if re.search(rf"\b{call}\s*\(", text):
            raise ValueError(f"Refused: {script.name} calls {call}. {reason}")


def ensure_open(project):
    """Make ``project`` the open project when it exists on disk, so a restarted instance never saves its empty project over it."""
    if not Path(project).is_file():
        return
    code = (f"var t = new File({json.dumps(str(project))}), c = app.project.file;\n"
            "if (!c || c.fsName !== t.fsName) {\n"
            "    if (app.project.dirty) { throw new Error('unsaved changes'); }\n"
            "    app.open(t);\n}")
    try:
        do_script(code, 300)
    except RuntimeError as error:
        if "unsaved changes" in str(error):
            raise RuntimeError(f"The open project has unsaved changes; save it, or run the tool on its own path, "
                               f"before opening {project}") from error
        raise


def script_call(script, project, args):
    """DoScript code that runs ``script`` through runner.jsx with CAVI_ARGS."""
    return (f"var CAVI_ARGS = {json.dumps(args)};\nvar CAVI_LIB = {json.dumps(str(JSX / 'lib.jsx'))};\nvar CAVI_SCRIPT = {json.dumps(str(script))};\n"
            f"var CAVI_PROJECT = {json.dumps(str(project))};\n"
            f"$.evalFile(new File({json.dumps(str(RUNNER))}));")


def project_report(path):
    """The JSON report stored between CAVI_REPORT and CAVI_END in a saved project."""
    raw = Path(path).read_bytes()
    for encoding in ("utf-8", "utf-16-be"):
        start, end = "CAVI_REPORT".encode(encoding), "CAVI_END".encode(encoding)
        if start in raw:
            body = raw[raw.index(start) + len(start):raw.index(end, raw.index(start))]
            return json.loads(body.decode(encoding))
    raise RuntimeError(f"{path} holds no report")


def absolute(path, suffix=None):
    path = Path(path).expanduser()
    if not path.is_absolute():
        raise ValueError(f"Use an absolute path: {path}")
    if suffix and path.suffix.lower() != suffix:
        raise ValueError(f"Expected a {suffix} file: {path}")
    return path


def fingerprint(path):
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_mtime_ns, stat.st_size, stat.st_ino


def run_script(script, project, args, timeout):
    """Run a .jsx file and return the report it saved in ``project``."""
    script, project = absolute(script, ".jsx"), absolute(project, ".aep")
    if not script.is_file():
        raise ValueError(f"No script at {script}")
    project.parent.mkdir(parents=True, exist_ok=True)
    before = fingerprint(project)
    ensure_open(project)
    do_script(script_call(script, project, args), timeout)
    if fingerprint(project) in (None, before):
        raise RuntimeError(f"The script saved no report to {project}")
    report = project_report(project)
    if report.get("errors"):
        raise RuntimeError("After Effects script: " + "; ".join(map(str, report["errors"])))
    CURRENT[0] = project
    return report


def run_template(name, project, args, timeout=300):
    """Run the packaged template ``jsx/<name>.jsx`` and return its report."""
    return run_script(JSX / f"{name}.jsx", project, args, timeout)


TRANSITIONS = {
    "linear_wipe": "ADBE Linear Wipe", "radial_wipe": "ADBE Radial Wipe", "block_dissolve": "ADBE Block Dissolve",
    "gradient_wipe": "ADBE Gradient Wipe", "venetian_blinds": "ADBE Venetian Blinds",
    "cc_radial_scale_wipe": "CC Radial ScaleWipe", "cc_twister": "CC Twister", "cc_glass_wipe": "CC Glass Wipe",
    "cc_image_wipe": "CC Image Wipe", "cc_jaws": "CC Jaws", "cc_light_wipe": "CC Light Wipe",
    "cc_line_sweep": "CC Line Sweep", "cc_grid_wipe": "CC Grid Wipe", "cc_page_turn": "CC Page Turn",
    "cc_warpomatic": "CC WarpoMatic",
}
BUILT_IN_TRANSITIONS = ("crossfade", "dip")


def animation_presets(root=None, text=""):
    """Installed .ffx animation presets as {category, name, path}, optionally filtered by ``text``."""
    root = Path(root) if root else after_effects() / "Presets"
    found = []
    for path in sorted(root.rglob("*.ffx")):
        category = path.parent.relative_to(root).as_posix()
        if text.lower() in f"{category} {path.stem}".lower():
            found.append({"category": category, "name": path.stem, "path": str(path)})
    return found


def resolve_preset(preset, root=None):
    """An absolute .ffx path, or a preset name (optionally "Category/Name") found in the presets folder."""
    if Path(preset).expanduser().is_absolute():
        path = Path(preset).expanduser()
        if path.suffix.lower() != ".ffx" or not path.is_file():
            raise ValueError(f"No .ffx preset at {path}")
        return path
    matches = [p for p in animation_presets(root)
               if preset in (p["name"], f"{p['category']}/{p['name']}")]
    if len(matches) != 1:
        raise ValueError(f"Preset {preset!r} matches {len(matches)} installed presets; "
                         "use Category/Name or an absolute path (see ae_presets)")
    return Path(matches[0]["path"])


def ffprobe():
    found = shutil.which("ffprobe", path=os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin")
    if not found:
        raise ValueError("Install ffprobe (FFmpeg) to verify rendered frames")
    return found


def frame_count(movie):
    """Video frames of a movie; a movie with a timecode track lists nb_frames twice, so take the first."""
    result = run_sync([ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries",
                       "stream=nb_frames", "-of", "csv=p=0", str(movie)], 60)
    counts = result.stdout.split()
    if result.returncode or not counts or not counts[0].isdigit():
        return None
    return int(counts[0])


def rendered(movie, frames, since=0.0):
    """A finished movie: written after ``since``, readable, with exactly ``frames`` frames."""
    path = Path(movie)
    return path.is_file() and path.stat().st_mtime >= since and frame_count(path) == frames


def aerender(*args):
    result = run_sync([str(after_effects() / "aerender"), *args, "-v", "ERRORS_AND_PROGRESS",
                       "-close", "DO_NOT_SAVE_CHANGES"], RENDER_TIMEOUT)
    if result.returncode:
        raise RuntimeError("aerender failed: " + diagnostics(result))


def render_queue(project, outputs, settings, module):
    """Render a saved project's queue, then render once more each movie left incomplete."""
    project = absolute(project, ".aep")
    if not project.is_file():
        raise ValueError(f"No project at {project}")
    files = [absolute(item["file"]) for item in outputs]
    since = time.time() - 1
    aerender("-project", str(project))
    results = []
    for item, file in zip(outputs, files, strict=True):
        again = not rendered(file, item["frames"], since)
        # aerender can exit 0 after a crash mid-queue; a short movie renders once more on its own.
        if again:
            file.unlink(missing_ok=True)
            aerender("-project", str(project), "-comp", item["comp"], "-output", str(file),
                     "-RStemplate", settings, "-OMtemplate", module)
        results.append({"comp": item["comp"], "file": str(file), "frames": frame_count(file),
                        "rerendered": again})
    incomplete = [r["comp"] for r, item in zip(results, outputs, strict=True) if r["frames"] != item["frames"]]
    if incomplete:
        raise RuntimeError("aerender left incomplete movies for " + ", ".join(incomplete))
    return {"project": str(project), "outputs": results}
