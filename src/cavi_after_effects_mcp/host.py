"""Headless After Effects: launch, scripts over Apple Events, aerender and frame checks."""

import json
import math
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from cavi_mcp_core import apps
from cavi_mcp_core.proc import diagnostics, run_sync

RUNNER = Path(__file__).with_name("runner.jsx")
JSX = Path(__file__).with_name("jsx")
RENDER_TIMEOUT = 3600
LAUNCH_WAIT = 60
# More markers than this in one call would make a script too large for After Effects to run.
MAX_MARKERS = 5000
# Where Homebrew and the system keep FFmpeg when the client starts the server with a short PATH.
TOOL_PATH = ":/opt/homebrew/bin:/usr/local/bin"

# (name, bundle identifier, glob under /Applications, environment override)
AFTER_EFFECTS = ("Adobe After Effects", "com.adobe.AfterEffects.application",
                 "Adobe After Effects 20*/Adobe After Effects 20*.app", "CAVI_AFTER_EFFECTS_APP")

# One After Effects instance runs one script at a time; a second call waits for the first.
ACCESS = threading.RLock()


class Session:
    """What the last call left behind: the project it saved to."""

    project = None


session = Session()


def application():
    """The installed After Effects .app: the override in CAVI_AFTER_EFFECTS_APP, else the newest installed."""
    return apps.bundle(*AFTER_EFFECTS).path


def after_effects():
    """The folder that holds the application, aerender and the Presets folder."""
    return application().parent


def processes():
    """Pids of the running After Effects, split into headless (-noui) and UI instances.

    Only the application's own executable counts; its render engine and other helpers do not.
    """
    headless, ui = [], []
    for process in apps.processes(apps.bundle(*AFTER_EFFECTS).executable):
        result = run_sync(["/bin/ps", "-o", "args=", "-p", str(process.pid)], 10)
        if result.returncode:
            continue  # the process ended meanwhile
        (headless if "-noui" in result.stdout.split() else ui).append(process.pid)
    return headless, ui


def status():
    """What is installed and running; an application that is not installed is reported, never raised."""
    try:
        found = apps.bundle(*AFTER_EFFECTS)
    except (apps.AppUnavailable, apps.AppMismatch) as failure:
        return {"app": None, "version": "", "aerender": None, "headless_pids": [], "ui_pids": [],
                "error": str(failure)}
    aerender = found.path.parent / "aerender"
    headless, ui = processes()
    return {"app": str(found.path), "version": found.info.get("CFBundleShortVersionString", ""),
            "aerender": str(aerender) if aerender.is_file() else None, "headless_pids": headless,
            "ui_pids": ui, "error": None if aerender.is_file() else f"No aerender next to {found.path}"}


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


def require_finite(value, where="arguments"):
    """Raise ValueError naming the first NaN or infinite number in ``value``, which After Effects cannot take."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{where} holds {value}; numbers must be finite")
    elif isinstance(value, dict):
        for key, item in value.items():
            require_finite(item, f"{where}.{key}")
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            require_finite(item, f"{where}[{index}]")


def do_script(code, timeout):
    """Run ExtendScript in the headless instance; DoScript answers 0 on success, 1 on any failure."""
    with ACCESS:
        headless, _ = processes()
        if not headless:
            launch()
            headless, _ = processes()
        command = ["osascript", "-e", "on run argv", "-e", f"with timeout of {timeout} seconds",
                   "-e", 'tell application (item 2 of argv) to set answer to DoScript (item 1 of argv)',
                   "-e", "end timeout", "-e", "return answer", "-e", "end run", code, application().stem]
        returncode, out, err = run_watched(command, timeout + 30, headless[0])
    if returncode or out.strip() != "0":
        raise RuntimeError("After Effects script failed: " + (err.strip() or out.strip() or f"exit {returncode}"))


def launch():
    """Start one headless After Effects (-noui) and wait until it answers scripts."""
    with ACCESS:
        headless, ui = processes()
        if ui:
            raise RuntimeError(f"After Effects is running with its UI (pid {ui[0]}); quit it first")
        if not headless:
            result = run_sync(["open", "-n", "-g", str(application()), "--args", "-noui"], 60)
            if result.returncode:
                raise RuntimeError("After Effects did not launch: " + diagnostics(result))
            for _ in range(LAUNCH_WAIT * 2):
                if processes()[0]:
                    break
                time.sleep(0.5)
            if not processes()[0]:
                raise RuntimeError(f"After Effects did not start within {LAUNCH_WAIT} seconds")
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
    script = absolute(script, ".jsx")
    if not script.is_file():
        raise ValueError(f"No script at {script}")
    text = script.read_text(encoding="utf-8", errors="replace")
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
    require_finite(args)
    return (f"var CAVI_ARGS = {json.dumps(args, allow_nan=False)};\nvar CAVI_LIB = {json.dumps(str(JSX / 'lib.jsx'))};\n"
            f"var CAVI_SCRIPT = {json.dumps(str(script))};\n"
            f"var CAVI_PROJECT = {json.dumps(str(project))};\n"
            f"$.evalFile(new File({json.dumps(str(RUNNER))}));")


def project_report(path):
    """The JSON report stored between CAVI_REPORT and CAVI_END in a saved project."""
    raw = Path(path).read_bytes()
    for encoding in ("utf-8", "utf-16-be"):
        start, end = "CAVI_REPORT".encode(encoding), "CAVI_END".encode(encoding)
        if start in raw:
            begin = raw.index(start) + len(start)
            stop = raw.find(end, begin)
            if stop < 0:
                raise RuntimeError(f"{path} holds an unreadable report: its end marker is missing")
            try:
                return json.loads(raw[begin:stop].decode(encoding))
            except ValueError as error:
                raise RuntimeError(f"{path} holds an unreadable report: {error}") from error
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
    require_finite(args)
    project.parent.mkdir(parents=True, exist_ok=True)
    with ACCESS:
        before = fingerprint(project)
        ensure_open(project)
        do_script(script_call(script, project, args), timeout)
        if fingerprint(project) in (None, before):
            raise RuntimeError(f"The script saved no report to {project}")
        report = project_report(project)
    if report.get("errors"):
        raise RuntimeError("After Effects script: " + "; ".join(map(str, report["errors"])))
    session.project = project
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


def tool(name, purpose):
    """The path of an FFmpeg program, found on PATH or where Homebrew installs it."""
    found = shutil.which(name, path=os.environ.get("PATH", "") + TOOL_PATH)
    if not found:
        raise ValueError(f"Install {name} (FFmpeg) {purpose}")
    return found


def frame_count(movie):
    """Video frames of a movie; a movie with a timecode track lists nb_frames twice, so take the first."""
    result = run_sync([tool("ffprobe", "to verify rendered frames"), "-v", "error", "-select_streams", "v:0",
                       "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(movie)], 60)
    counts = result.stdout.split()
    if result.returncode or not counts or not counts[0].isdigit():
        return None
    return int(counts[0])


def rendered(movie, frames, since=0.0):
    """A finished movie: written after ``since``, readable, with exactly ``frames`` frames."""
    path = Path(movie)
    return path.is_file() and path.stat().st_mtime >= since and frame_count(path) == frames


def aerender(*args):
    program = after_effects() / "aerender"
    if not program.is_file():
        raise RuntimeError(f"No aerender at {program}")
    result = run_sync([str(program), *args, "-v", "ERRORS_AND_PROGRESS", "-close", "DO_NOT_SAVE_CHANGES"],
                      RENDER_TIMEOUT)
    if result.returncode:
        raise RuntimeError("aerender failed: " + diagnostics(result))


def render_queue(project, outputs, settings, module):
    """Render a saved project's queue, then render once more each movie left incomplete."""
    project = absolute(project, ".aep")
    if not project.is_file():
        raise ValueError(f"No project at {project}")
    files = [absolute(item["file"]) for item in outputs]
    since = time.time() - 1
    failure = None
    try:
        aerender("-project", str(project))
    except RuntimeError as error:
        failure = error
    results = []
    for item, file in zip(outputs, files, strict=True):
        again = not rendered(file, item["frames"], since)
        # aerender can exit 0 after a crash mid-queue; a short movie renders once more on its own.
        if again:
            file.unlink(missing_ok=True)
            try:
                aerender("-project", str(project), "-comp", item["comp"], "-output", str(file),
                         "-RStemplate", settings, "-OMtemplate", module)
            except RuntimeError as error:
                failure = error
        results.append({"comp": item["comp"], "file": str(file),
                        "frames": frame_count(file) if file.is_file() else None, "rerendered": again,
                        "path": "aerender"})
    return {"project": str(project), "outputs": results, "failure": str(failure) if failure else None}
