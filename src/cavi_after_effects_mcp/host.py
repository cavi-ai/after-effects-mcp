"""Headless After Effects: launch, scripts over Apple Events, aerender and frame checks."""

import asyncio
import contextlib
import fcntl
import glob
import json
import math
import os
import re
import shutil
import signal
import tempfile
import threading
import time
import uuid
from pathlib import Path

from cavi_mcp_core import apps, files, journal, resident
from cavi_mcp_core.contracts import OperationRejected
from cavi_mcp_core.proc import diagnostics, run, run_sync

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

class Access:
    """Re-entrant lock held by one thread of one server process at a time: every server process of the user
    drives the same headless instance, so the lock is a file lock under the temporary folder."""

    def __init__(self, path):
        self.path = path
        self.thread = threading.RLock()
        self.depth = 0
        self.file = None

    def __enter__(self):
        self.thread.acquire()
        if self.depth == 0:
            try:
                self.file = open(self.path, "a")
                fcntl.flock(self.file, fcntl.LOCK_EX)
            except BaseException:
                if self.file:
                    self.file.close()
                    self.file = None
                self.thread.release()
                raise
        self.depth += 1
        return self

    def __exit__(self, *exc):
        self.depth -= 1
        if self.depth == 0:
            self.file.close()  # closing the file releases the lock
            self.file = None
        self.thread.release()


# One After Effects instance runs one script at a time; a second call, from any server process, waits for the first.
ACCESS = Access(Path(tempfile.gettempdir()) / "cavi-after-effects.lock")


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


async def watched(command, timeout, pid, interval):
    call = asyncio.ensure_future(run(command, timeout))
    while not call.done():
        await asyncio.wait({call}, timeout=interval)
        if not call.done() and not alive(pid):
            call.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await call
            raise RuntimeError(f"After Effects (pid {pid}) exited during the call; the next tool call starts it again")
    try:
        result = call.result()
    except TimeoutError:
        raise RuntimeError(f"After Effects did not answer within {timeout} seconds") from None
    return result.returncode, result.stdout, result.stderr


def run_watched(command, timeout, pid, interval=0.5):
    """Run ``command`` while process ``pid`` lives; stop its process group and raise as soon as ``pid`` exits."""
    return asyncio.run(watched(command, timeout, pid, interval))


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
        # The terminology of DoScript compiles only against a literal application name.
        name = application().stem.replace("\\", "\\\\").replace('"', '\\"')
        command = ["osascript", "-e", "on run argv", "-e", f"with timeout of {timeout} seconds",
                   "-e", f'tell application "{name}" to set answer to DoScript (item 1 of argv)',
                   "-e", "end timeout", "-e", "return answer", "-e", "end run", code]
        returncode, out, err = run_watched(command, timeout + 30, headless[0])
    if returncode or out.strip() != "0":
        raise RuntimeError("After Effects script failed: " + (err.strip() or out.strip() or f"exit {returncode}"))


def launch():
    """Start one headless After Effects (-noui) and wait until it answers scripts."""
    with ACCESS:
        headless, ui = processes()
        if ui:
            raise OperationRejected(f"After Effects is running with its UI (pid {ui[0]}); quit it first",
                                    code="AE_UI_RUNNING")
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
        raise FileNotFoundError(f"No script at {script}")
    text = script.read_text(encoding="utf-8", errors="replace")
    for call, reason in CRASHING_CALLS.items():
        if re.search(rf"\b{call}\s*\(", text):
            raise ValueError(f"Refused: {script.name} calls {call}. {reason}")


def ensure_open(project):
    """Make ``project`` the open project when it exists on disk, so a restarted instance never saves its empty project over it.

    A path with no file yet is saved from the open project, so only an untitled, empty project may start it.
    """
    if not Path(project).is_file():
        try:
            do_script("if (app.project.file || app.project.numItems > 0) { throw new Error('open project in use'); }", 300)
        except RuntimeError as error:
            # DoScript answers 1 when the script throws; the thrown message does not reach the caller.
            if str(error) == "After Effects script failed: 1":
                raise FileNotFoundError(f"No project at {project}; create it with ae_project action new") from error
            raise
        return
    other = (f"var t = new File({json.dumps(str(project))}), c = app.project.file;\n"
             "var other = !c || c.fsName !== t.fsName;\n")
    try:
        do_script(other + "if (other && app.project.dirty) { throw new Error('unsaved changes'); }", 300)
    except RuntimeError as error:
        # DoScript answers 1 when the script throws, and this check throws only on unsaved changes.
        if str(error) == "After Effects script failed: 1":
            raise OperationRejected(f"The open project has unsaved changes; save it, or run the tool on its own "
                                    f"path, before opening {project}", code="AE_PROJECT_UNSAVED") from error
        raise
    do_script(other + "if (other) { app.open(t); }", 300)


def script_call(script, project, args, report):
    """DoScript code that runs ``script`` through runner.jsx with CAVI_ARGS and writes its report to ``report``."""
    require_finite(args)
    return (f"var CAVI_ARGS = {json.dumps(args, allow_nan=False)};\nvar CAVI_LIB = {json.dumps(str(JSX / 'lib.jsx'))};\n"
            f"var CAVI_SCRIPT = {json.dumps(str(script))};\n"
            f"var CAVI_PROJECT = {json.dumps(str(project) if project else None)};\n"
            f"var CAVI_REPORT_FILE = {json.dumps(str(report))};\n"
            f"$.evalFile(new File({json.dumps(str(RUNNER))}));")


def scripted(script, project, args, timeout):
    """Run ``script`` through runner.jsx on the open project and return the report it wrote."""
    with tempfile.TemporaryDirectory(prefix="cavi-ae-") as folder:
        path = Path(folder) / "report.json"
        do_script(script_call(script, project, args, path), timeout)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise RuntimeError(f"{Path(script).name} wrote no report") from None
    try:
        return json.loads(text)
    except ValueError as error:
        raise RuntimeError(f"{Path(script).name} wrote an unreadable report: {error}") from error


def absolute(path, suffix=None):
    path = Path(path).expanduser()
    if not path.is_absolute():
        raise ValueError(f"Use an absolute path: {path}")
    if suffix and path.suffix.lower() != suffix:
        raise ValueError(f"Expected a {suffix} file: {path}")
    return path


def run_script(script, project, args, timeout, contained=False):
    """Run a .jsx file on ``project`` and return its report; the project is saved only when the script changed it.

    ``contained`` scripts change nothing but the project, so an error the runner rolled back is a refusal.
    """
    script, project = absolute(script, ".jsx"), absolute(project, ".aep")
    if not script.is_file():
        raise FileNotFoundError(f"No script at {script}")
    require_finite(args)
    project.parent.mkdir(parents=True, exist_ok=True)
    with ACCESS:
        ensure_open(project)
        report = scripted(script, project, args, timeout)
    if report.get("errors"):
        message = "After Effects script: " + "; ".join(map(str, report["errors"]))
        if contained and report.get("restored"):
            raise OperationRejected(message + "; the project was left as it was", code="AE_SCRIPT_REFUSED")
        raise RuntimeError(message)
    session.project = project
    return report


# Templates that write files beside the project or switch projects, so a rolled-back error may still have effects.
UNCONTAINED = {"ae_frame_png", "ae_frame_range", "ae_project"}


def run_template(name, project, args, timeout=300):
    """Run the packaged template ``jsx/<name>.jsx`` and return its report."""
    return run_script(JSX / f"{name}.jsx", project, args, timeout, contained=name not in UNCONTAINED)


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


def audio_frames(path, fps):
    """Frames at ``fps`` that an output with audio and no video stream lasts; None for any other file."""
    result = run_sync([tool("ffprobe", "to verify rendered audio"), "-v", "error", "-show_entries",
                       "stream=codec_type,duration", "-of", "json", str(path)], 60)
    try:
        streams = json.loads(result.stdout)["streams"]
    except (ValueError, KeyError):
        return None
    if any(s.get("codec_type") == "video" for s in streams):
        return None
    durations = [s["duration"] for s in streams if s.get("codec_type") == "audio" and "duration" in s]
    return round(float(durations[0]) * fps) if durations else None


ONSET_RATE, ONSET_HOP, ONSET_LOOKBACK = 22050, 256, 6


def onsets(path, rise=6.0, floor=-50.0, gap=0.1):
    """Seconds into ``path`` where its level jumps.

    FFmpeg measures the RMS level of every 256 samples at 22.05 kHz (11.6 ms). A frame is an onset when its level
    is at least ``floor`` dB and ``rise`` dB above the quietest of the six frames before it (70 ms), and at least
    ``gap`` seconds after the previous onset.
    """
    path = absolute(path)
    if not path.is_file():
        raise FileNotFoundError(f"No audio file at {path}")
    result = run_sync([tool("ffmpeg", "to find onsets"), "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                       f"aresample={ONSET_RATE},asetnsamples=n={ONSET_HOP}:p=0,astats=metadata=1:reset=1,"
                       "ametadata=mode=print:key=lavfi.astats.Overall.RMS_level:file=-", "-f", "null", "-"],
                      600, stdout_limit=256 * 1024 * 1024)
    if result.returncode != 0 or result.truncated:
        raise RuntimeError(f"FFmpeg could not measure {path.name}: {diagnostics(result)}")
    times, levels = [], []
    for line in result.stdout.splitlines():
        if line.startswith("frame:"):
            times.append(float(line.split("pts_time:")[1]))
        elif line.startswith("lavfi.astats.Overall.RMS_level="):
            level = float(line.split("=", 1)[1])
            levels.append(level if math.isfinite(level) else -math.inf)
    if not levels:
        raise ValueError(f"{path.name} has no audio stream")
    found = []
    for n, level in enumerate(levels):
        before = min(levels[max(0, n - ONSET_LOOKBACK):n], default=-math.inf)
        if level >= floor and level - before >= rise and (not found or times[n] - found[-1] >= gap):
            found.append(times[n])
    return found


def cuts(path, threshold=0.4):
    """Seconds into ``path`` where a new shot starts: frames whose FFmpeg scene score, the change from the frame
    before from 0 to 1, is at least ``threshold``."""
    path = absolute(path)
    if not path.is_file():
        raise FileNotFoundError(f"No video file at {path}")
    result = run_sync([tool("ffmpeg", "to find cuts"), "-hide_banner", "-nostats", "-i", str(path), "-an", "-vf",
                       f"select='gte(scene,{threshold})',metadata=mode=print:file=-", "-f", "null", "-"],
                      600, stdout_limit=64 * 1024 * 1024)
    if "does not contain any stream" in result.stderr:
        raise ValueError(f"{path.name} has no video stream")
    if result.returncode != 0 or result.truncated:
        raise RuntimeError(f"FFmpeg could not read the video of {path.name}: {diagnostics(result)}")
    return [float(line.split("pts_time:")[1]) for line in result.stdout.splitlines() if line.startswith("frame:")]


SEQUENCE = re.compile(r"\[(#+)\]")


def frame_files(output):
    """The files of an image sequence output whose name holds [###]; None for a movie."""
    path = Path(output)
    mark = SEQUENCE.search(path.name)
    if not mark:
        return None
    name = (glob.escape(path.name[:mark.start()]) + "[0-9]" * len(mark.group(1))
            + glob.escape(path.name[mark.end():]))
    return sorted(path.parent.glob(name))


def written(output, since=0.0, fps=None):
    """Frames of ``output`` written after ``since``: a movie's frame count, an image sequence's non-empty files, or
    an audio file's duration at ``fps``."""
    files = frame_files(output)
    if files is not None:
        return sum(1 for f in files if f.stat().st_mtime >= since and f.stat().st_size > 0) or None
    path = Path(output)
    if not path.is_file() or path.stat().st_mtime < since:
        return None
    frames = frame_count(path)
    return audio_frames(path, fps) if frames is None and fps else frames


def rendered(output, frames, since=0.0, fps=None):
    """A finished output: written after ``since``, readable, with exactly ``frames`` frames."""
    return written(output, since, fps) == frames


def discard(output):
    """Delete a movie, or every frame of an image sequence."""
    files = frame_files(output)
    for file in files if files is not None else [Path(output)]:
        file.unlink(missing_ok=True)


def aerender(*args):
    program = after_effects() / "aerender"
    if not program.is_file():
        raise RuntimeError(f"No aerender at {program}")
    result = run_sync([str(program), *args, "-v", "ERRORS_AND_PROGRESS", "-close", "DO_NOT_SAVE_CHANGES"],
                      RENDER_TIMEOUT)
    if result.returncode:
        raise RuntimeError("aerender failed: " + diagnostics(result))


def queue_entries(project, outputs):
    """The render queue entry of each output, matched by comp and file; refuses a frame count the entry does not render."""
    queue = run_template("ae_inspect", project, {"scope": "queue", "comp": None})["queue"]
    entries = []
    for item in outputs:
        file = absolute(item["file"]).resolve()
        found = [q for q in queue if q["comp"] == item["comp"] and q["file"] and Path(q["file"]).resolve() == file]
        if not found:
            raise ValueError(f"No queue entry renders {item['comp']} to {file}; add it with ae_render_queue_set")
        entry = found[-1]
        if item.get("frames") is not None and item["frames"] != entry["frames"]:
            raise ValueError(f"{item['comp']}: the queue entry renders {entry['frames']} frames "
                             f"({entry['span_duration']:g} s from {entry['span_start']:g} s at {entry['fps']:g} fps); "
                             f"frames says {item['frames']}")
        entries.append(entry)
    return entries


def render_queue(project, outputs):
    """Render a saved project's queue, then render once more by itself each queued output left incomplete."""
    project = absolute(project, ".aep")
    if not project.is_file():
        raise FileNotFoundError(f"No project at {project}")
    entries = queue_entries(project, outputs)
    files = [absolute(item["file"]) for item in outputs]
    for file in files:
        # After Effects does not create a missing output folder; the entry then renders nothing.
        file.parent.mkdir(parents=True, exist_ok=True)
    since = time.time() - 1
    failure = None
    try:
        aerender("-project", str(project))
    except RuntimeError as error:
        failure = error
    results = []
    for item, entry, file in zip(outputs, entries, files, strict=True):
        again = not rendered(file, entry["frames"], since, entry["fps"])
        # aerender can exit 0 after a crash mid-queue; a short output renders once more with its entry's settings.
        if again:
            discard(file)
            try:
                aerender("-project", str(project), "-rqindex", str(entry["index"]))
            except RuntimeError as error:
                failure = error
        results.append({"comp": item["comp"], "file": str(file), "frames": written(file, since, entry["fps"]),
                        "rerendered": again, "path": "aerender"})
    return {"project": str(project), "outputs": results, "entries": entries,
            "failure": str(failure) if failure else None}


RENDER_JOBS = Path(tempfile.gettempdir()).resolve() / "cavi-after-effects-renders"
JOB_ID = re.compile(r"[0-9a-f]{12}")
# aerender -v ERRORS_AND_PROGRESS logs each frame as "<timecode> (<frame number>): <seconds> Seconds".
FRAME_DONE = re.compile(r"\((\d+)\): \d+ Seconds")


def render_jobs():
    """The private folder holding each background render's job file and resident directory."""
    RENDER_JOBS.mkdir(mode=0o700, exist_ok=True)
    info = RENDER_JOBS.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError(f"{RENDER_JOBS} must belong to this user alone")
    return RENDER_JOBS


def render_start(project, item):
    """Start ``aerender -rqindex`` for one queue entry under a resident owner that outlives this process."""
    project = absolute(project, ".aep")
    if not project.is_file():
        raise FileNotFoundError(f"No project at {project}")
    program = after_effects() / "aerender"
    if not program.is_file():
        raise RuntimeError(f"No aerender at {program}")
    with ACCESS:
        root = render_jobs()
        for path in sorted(root.glob("*.json")):
            if JOB_ID.fullmatch(path.stem) and render_status(path.stem)["state"] == "running":
                raise OperationRejected(f"Render job {path.stem} is running; wait for it with ae_render_status or "
                                        "stop it with ae_render_cancel", code="AE_RENDER_BUSY")
        entry = queue_entries(project, [item])[0]
        file = absolute(item["file"])
        file.parent.mkdir(parents=True, exist_ok=True)
        job = uuid.uuid4().hex[:12]
        journal.create_json(root / f"{job}.json", {
            "project": str(project), "comp": item["comp"], "file": str(file), "frames": entry["frames"],
            "fps": entry["fps"], "index": entry["index"], "since": time.time() - 1})
        env = {k: os.environ[k] for k in ("HOME", "USER", "LOGNAME", "PATH", "TMPDIR", "LANG") if k in os.environ}
        resident.start([str(program), "-project", str(project), "-rqindex", str(entry["index"]),
                        "-v", "ERRORS_AND_PROGRESS", "-close", "DO_NOT_SAVE_CHANGES"],
                       cwd=str(project.parent.resolve()), env=env, directory=root / job, max_seconds=RENDER_TIMEOUT,
                       max_rss_kib=os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") // 1024,
                       minimum_available_kib=0)
    return render_status(job)


CORE_PARENT = re.compile(r"-aerenderpid (\d+)$")


def stop_render_core(aerender_pid, project):
    """Kill the aerendercore an aerender started: it runs outside aerender's process group, outlives a stopped
    aerender and ignores SIGTERM."""
    result = run_sync(["/bin/ps", "-axww", "-o", "pid=,args="], 10)
    for line in result.stdout.splitlines():
        pid, _, args = line.strip().partition(" ")
        parent = CORE_PARENT.search(args)
        if "aerendercore" in args and parent and int(parent.group(1)) == aerender_pid and f"-project {project} " in args:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass


def render_job(job):
    """The job file of a background render."""
    path = render_jobs() / f"{job}.json"
    if not JOB_ID.fullmatch(job) or not path.is_file():
        raise ValueError(f"No render job {job}")
    return files.load_json(path)


def render_status(job):
    """A background render's state, the frames aerender logged and, once it ended, the frames its output has."""
    meta = render_job(job)
    directory = render_jobs() / job
    value = resident.inspect(directory)
    log = directory / "processes" / "worker.log"
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    done = max((int(n) for n in FRAME_DONE.findall(text)), default=0)
    status = {"job": job, "state": value["state"], "comp": meta["comp"], "file": meta["file"],
              "frames": meta["frames"], "done": min(done, meta["frames"])}
    if value["state"] == "running":
        return status
    status["written"] = written(meta["file"], meta["since"], meta["fps"]) or 0
    receipt = value["receipt"] or {}
    if value["state"] == "finished":
        if receipt.get("exit_code") == 0 and status["written"] == meta["frames"]:
            status["state"] = "done"
        else:
            status["state"] = "cancelled" if (directory / "cancel.json").exists() else "failed"
    if status["state"] != "done":
        if receipt.get("pid"):
            stop_render_core(receipt["pid"], meta["project"])
        errors = [line.strip() for line in text.splitlines() if "error" in line.lower()]
        status["error"] = (receipt.get("error") or receipt.get("cleanup_error") or (errors[-1] if errors else None)
                           or f"aerender exited {receipt.get('exit_code')} after writing {status['written']} of "
                              f"{meta['frames']} frames")
    return status


def render_cancel(job):
    """Have the resident owner of a background render stop aerender, wait up to 30 s for it, and report the job;
    reading the ended job stops its aerendercore."""
    render_job(job)
    directory = render_jobs() / job
    resident.cancel(directory)
    try:
        resident.wait(directory, timeout=30)
    except TimeoutError:
        pass
    return render_status(job)
