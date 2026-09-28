#!/usr/bin/env python3
"""Shotcut AI media analysis: an MCP server that lets an AI see and hear media files.

It answers MCP (JSON-RPC 2.0) over standard input and output, like the bridge next to
it, and needs only the Python standard library (Python 3.8 or later) plus the programs
that come with Shotcut AI: ffprobe and ffmpeg (bin/) and whisper-cli for speech. Nothing
leaves the computer; only the Whisper models are downloaded once (download_model).

Tools: check_setup, probe_media, describe_clip, detect_scenes, contact_sheet,
analyze_audio (loudness, silences, tempo and beats), transcribe (words and phrases with
times), analyze_folder, download_model, get_jobs and cancel_job. Long work runs as a job:
a call waits up to "wait" seconds and otherwise answers with the job id, and the result is
cached, so calling the tool again later returns it at once.

Client configuration (Claude Desktop, Antigravity and other stdio clients):

    {"mcpServers": {"shotcut-analysis": {"command": "python",
                                         "args": ["<path>/shotcut_analysis.py"]}}}

Environment variables: SHOTCUT_FFMPEG, SHOTCUT_FFPROBE and SHOTCUT_WHISPER (programs),
SHOTCUT_WHISPER_MODEL (a ggml model file), SHOTCUT_WHISPER_MODELS (the models folder)
and SHOTCUT_ANALYSIS_CACHE (the cache folder).
"""

import array
import base64
import hashlib
import itertools
import json
import math
import operator
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

SERVER_NAME = "shotcut-analysis"
SERVER_TITLE = "Shotcut AI media analysis"
VERSION = "1.0"
PROTOCOL_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
CACHE_VERSION = 1
HERE = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"
# Programs started from a GUI client must not open console windows on Windows.
NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".m2ts", ".mpg",
                    ".mpeg", ".wmv", ".flv", ".3gp", ".mxf", ".ts", ".vob", ".dv"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".opus", ".wma", ".aif",
                    ".aiff"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}
IMAGE_CODECS = {"mjpeg", "png", "bmp", "tiff", "webp", "gif", "jpeg2000", "ppm", "pgm"}

INSTRUCTIONS = (
    "Media analysis for Shotcut AI: it lets you see and hear media before editing. Start with "
    "describe_clip (or analyze_folder for a whole folder of material), look at contact_sheet "
    "images to see the shots, and use transcribe for speech (cut on word boundaries, not in "
    "the middle of a word). analyze_audio gives loudness, silences and the beats of music "
    "for cutting to the rhythm. Times are in seconds from the start of the file, the same "
    "as in/out points of Shotcut AI clips. Long work runs as a job: when a call answers "
    "with a job id, call the same tool again later or get_jobs; results are cached. Edit the "
    "project with the shotcut-ai server.")


def log(*parts):
    print("shotcut-analysis:", *parts, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------------------
# Folders and programs.

def app_data_dir():
    """The data folder of Shotcut (Settings.appDataLocation())."""
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Meltytech" / "Shotcut"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Meltytech" / "Shotcut"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "Meltytech" / "Shotcut"


def cache_dir():
    if os.environ.get("SHOTCUT_ANALYSIS_CACHE"):
        return Path(os.environ["SHOTCUT_ANALYSIS_CACHE"])
    if IS_WINDOWS:
        return app_data_dir() / "analysis"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "Meltytech" / "Shotcut" / "analysis"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "Meltytech" / "Shotcut" / "analysis"


def models_dir():
    """Where Shotcut downloads Whisper models (Subtitles > Speech to Text)."""
    if os.environ.get("SHOTCUT_WHISPER_MODELS"):
        return Path(os.environ["SHOTCUT_WHISPER_MODELS"])
    return app_data_dir() / "extensions" / "whispermodel"


def program_folders():
    """The bin folder of the installation this script belongs to (share/shotcut/mcp), then
    the folder of the script, then the repository layout used by the tests."""
    folders = [HERE.parent.parent.parent / "bin", HERE, HERE.parent.parent.parent / "MacOS"]
    return [folder for folder in folders if folder.is_dir()]


def program_command(name, variable):
    """The command that runs a program, or None. A variable pointing to a .py file runs it
    with this Python, which the tests use."""
    value = os.environ.get(variable)
    if value:
        if value.lower().endswith(".py"):
            return [sys.executable, value]
        return [value]
    exe = name + (".exe" if IS_WINDOWS else "")
    for folder in program_folders():
        candidate = folder / exe
        if candidate.is_file():
            return [str(candidate)]
    found = shutil.which(name)
    return [found] if found else None


def ffmpeg():
    return program_command("ffmpeg", "SHOTCUT_FFMPEG")


def ffprobe():
    return program_command("ffprobe", "SHOTCUT_FFPROBE")


def whisper():
    return (program_command("whisper-cli", "SHOTCUT_WHISPER")
            or program_command("whisper-command", "SHOTCUT_WHISPER"))


def shotcut_setting(group, key):
    """A setting of Shotcut: the registry on Windows, else the QSettings file."""
    if IS_WINDOWS:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                "Software\\Meltytech\\Shotcut\\" + group) as handle:
                return str(winreg.QueryValueEx(handle, key)[0])
        except OSError:
            return None
    if sys.platform == "darwin":
        return None
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    try:
        text = (config / "Meltytech" / "Shotcut.conf").read_text(encoding="utf-8")
    except OSError:
        return None
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif section == group and line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


# The models that Shotcut offers (its whispermodel extension); read from the installed
# extension when possible so that the names stay the same.
BUILTIN_MODELS = [
    ("tiny", "ggml-tiny.bin", 77.7), ("tiny-q5_1", "ggml-tiny-q5_1.bin", 32.2),
    ("base", "ggml-base.bin", 148.0), ("base-q5_1", "ggml-base-q5_1.bin", 59.7),
    ("small", "ggml-small.bin", 488.0), ("small-q5_1", "ggml-small-q5_1.bin", 190.0),
    ("medium-q5_0", "ggml-medium-q5_1.bin", 539.0), ("medium", "ggml-medium.bin", 1530.0),
    ("large-v3-q5_0", "ggml-large-v3-q5_0.bin", 1080.0), ("large-v3", "ggml-large-v3.bin", 3100.0),
    ("tiny.en", "ggml-tiny.en.bin", 77.7), ("base.en", "ggml-base.en.bin", 148.0),
    ("small.en", "ggml-small.en.bin", 488.0),
]
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{}.bin"


def known_models():
    """[{name, file, url, size_mb}] like Shotcut's model list."""
    models = []
    # Installed (share/shotcut/qml) or in the source tree (src/qml).
    for extension in (HERE.parent / "qml" / "extensions" / "whispermodel.qml",
                      HERE.parent / "src" / "qml" / "extensions" / "whispermodel.qml"):
        if extension.is_file():
            break
    try:
        text = extension.read_text(encoding="utf-8")
        for file_name, url, size in re.findall(
                r'file:\s*"([^"]+)"\s*url:\s*"([^"]+)"\s*size:\s*"(\d+)"', text):
            name = re.sub(r"^ggml-|\.bin$", "", url.rsplit("/", 1)[-1])
            models.append({"name": name, "file": file_name, "url": url,
                           "size_mb": round(int(size) / 1048576, 1)})
    except OSError:
        pass
    if not models:
        models = [{"name": name, "file": file_name, "url": MODEL_URL.format(name),
                   "size_mb": size} for name, file_name, size in BUILTIN_MODELS]
    return models


def installed_models():
    folder = models_dir()
    try:
        return sorted(str(path) for path in folder.glob("ggml-*.bin") if path.is_file())
    except OSError:
        return []


def default_model():
    """The model chosen in Shotcut, else the best downloaded multilingual one up to small."""
    for candidate in (os.environ.get("SHOTCUT_WHISPER_MODEL"),
                      shotcut_setting("subtitles", "whisperModel")):
        if candidate and Path(candidate).is_file():
            return candidate
    installed = installed_models()
    preference = ["small-q5_1", "small", "base", "base-q5_1", "medium-q5", "medium", "large",
                  "tiny", "tiny-q5_1"]
    for wanted in preference:
        for path in installed:
            if Path(path).name.startswith("ggml-" + wanted) and ".en" not in Path(path).name:
                return path
    return installed[0] if installed else None


def resolve_model(value):
    """A model name (base, small-q5_1...) or path to its file, or raises ToolError."""
    if not value:
        model = default_model()
        if model:
            return model
        raise ToolError(
            "No Whisper model is installed. Call download_model (\"base\" is a good start, "
            "\"small-q5_1\" is more accurate for Spanish) or download one in Shotcut AI: "
            "Subtitles > Speech to Text.")
    if Path(value).is_file():
        return str(Path(value))
    for model in known_models():
        if value in (model["name"], model["file"]):
            path = models_dir() / model["file"]
            if path.is_file():
                return str(path)
            raise ToolError("The model \"%s\" is not downloaded yet: call download_model with "
                            "name \"%s\" (%s MB)." % (value, model["name"], model["size_mb"]))
    raise ToolError("Unknown model \"%s\". Models: %s." % (
        value, ", ".join(model["name"] for model in known_models())))


# ---------------------------------------------------------------------------------------
# Errors, jobs and programs.

class ToolError(Exception):
    """An error that the model can read and fix (a tool execution error)."""


class Cancelled(Exception):
    pass


class Job:
    def __init__(self, job_id, kind, target, key):
        self.id = job_id
        self.kind = kind
        self.target = target
        self.key = key
        self.status = "running"
        self.progress = 0.0
        self.message = ""
        self.result = None
        self.error = None
        self.started = time.time()
        self.finished = None
        self.cancelled = threading.Event()
        self.done = threading.Event()

    def update(self, progress=None, message=None):
        if self.cancelled.is_set():
            raise Cancelled()
        if progress is not None:
            self.progress = max(self.progress, min(1.0, progress))
        if message is not None:
            self.message = message

    def json(self, with_result=False):
        info = {"job": self.id, "kind": self.kind, "target": self.target, "status": self.status,
                "progress": round(self.progress * 100)}
        if self.message:
            info["message"] = self.message
        info["seconds"] = round((self.finished or time.time()) - self.started, 1)
        if self.error:
            info["error"] = self.error
        if with_result and self.result is not None:
            info["result"] = self.result
        return info


class SubJob:
    """A part of a job: its progress fills one slice of the job's progress."""

    def __init__(self, job, start, size):
        self.job = job
        self.start = start
        self.size = size
        self.cancelled = job.cancelled
        self.progress = 0.0

    def update(self, progress=None, message=None):
        if progress is not None:
            self.progress = max(self.progress, min(1.0, progress))
        self.job.update(self.start + self.size * self.progress, message)


class Jobs:
    def __init__(self):
        self.lock = threading.Lock()
        self.jobs = {}
        self.count = 0

    def start(self, kind, target, key, work):
        """Runs work(job) in a thread; the same work already running is reused."""
        with self.lock:
            for job in self.jobs.values():
                if job.key == key and job.status == "running":
                    return job
            self.count += 1
            job = Job("j%d" % self.count, kind, target, key)
            self.jobs[job.id] = job

        def body():
            try:
                job.result = work(job)
                job.status = "done"
                job.progress = 1.0
            except Cancelled:
                job.status = "cancelled"
            except ToolError as error:
                job.status = "failed"
                job.error = str(error)
            except Exception as error:  # A bug or an unexpected program failure.
                job.status = "failed"
                job.error = "%s: %s" % (type(error).__name__, error)
                log("job", job.id, "failed:", job.error)
            finally:
                job.finished = time.time()
                job.done.set()

        threading.Thread(target=body, name=job.id, daemon=True).start()
        return job

    def get(self, job_id):
        with self.lock:
            return self.jobs.get(job_id)

    def all(self):
        with self.lock:
            return list(self.jobs.values())


JOBS = Jobs()


def run_program(command, job=None, on_stdout=None, on_stderr=None, binary_stdout=False,
                timeout=None, cwd=None):
    """Runs a program. Returns (exit code, stdout, stderr); stdout is bytes when
    binary_stdout. on_stdout/on_stderr get text lines as they come. A cancelled job kills
    the program."""
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=cwd, creationflags=NO_WINDOW)
    except OSError as error:
        raise ToolError("Cannot run %s: %s" % (command[0], error))
    stdout_chunks, stderr_lines = [], []

    def read_stdout():
        if binary_stdout:
            while True:
                chunk = process.stdout.read(65536)
                if not chunk:
                    break
                stdout_chunks.append(chunk)
            return
        for raw in process.stdout:
            line = raw.decode("utf-8", "replace")
            stdout_chunks.append(line)
            if on_stdout:
                on_stdout(line.rstrip("\r\n"))

    def read_stderr():
        for raw in process.stderr:
            line = raw.decode("utf-8", "replace")
            stderr_lines.append(line)
            if on_stderr:
                on_stderr(line.rstrip("\r\n"))

    readers = [threading.Thread(target=read_stdout, daemon=True),
               threading.Thread(target=read_stderr, daemon=True)]
    for reader in readers:
        reader.start()
    started = time.time()
    while True:
        try:
            process.wait(timeout=0.2)
            break
        except subprocess.TimeoutExpired:
            if (job and job.cancelled.is_set()) or (timeout and time.time() - started > timeout):
                process.kill()
                process.wait()
                for reader in readers:
                    reader.join(timeout=2)
                if job and job.cancelled.is_set():
                    raise Cancelled()
                raise ToolError("%s took longer than %d s." % (Path(command[0]).name, timeout))
    for reader in readers:
        reader.join()
    stdout = b"".join(stdout_chunks) if binary_stdout else "".join(stdout_chunks)
    return process.returncode, stdout, "".join(stderr_lines)


def require(command, what):
    if not command:
        raise ToolError("%s was not found. It comes with Shotcut AI (bin folder); set %s to "
                        "its path if it is elsewhere." % (what[0], what[1]))
    return command


def media_path(value):
    if not isinstance(value, str) or not value.strip():
        raise ToolError("\"path\" must be the absolute path of a media file.")
    path = Path(os.path.expanduser(value.strip()))
    if not path.is_file():
        raise ToolError("File not found: %s" % value)
    return path.resolve()


# ---------------------------------------------------------------------------------------
# Cache: one JSON file per media file, keyed by its path, size and modification time.

CACHE_LOCK = threading.Lock()


def media_key(path):
    stat = path.stat()
    text = "%s|%d|%d" % (str(path).lower() if IS_WINDOWS else str(path), stat.st_size,
                         int(stat.st_mtime))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]


def cache_file(path):
    return cache_dir() / (media_key(path) + ".json")


def cache_load(path):
    try:
        with open(cache_file(path), encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("version") == CACHE_VERSION:
            return data
    except (OSError, ValueError):
        pass
    return {"version": CACHE_VERSION, "path": str(path)}


def cache_get(path, section, key=None):
    data = cache_load(path).get(section)
    if key is not None:
        data = (data or {}).get(key)
    return data


def cache_put(path, section, value, key=None):
    with CACHE_LOCK:
        data = cache_load(path)
        if key is None:
            data[section] = value
        else:
            data.setdefault(section, {})[key] = value
        folder = cache_dir()
        folder.mkdir(parents=True, exist_ok=True)
        target = cache_file(path)
        temporary = target.with_suffix(".tmp")
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary, target)


# ---------------------------------------------------------------------------------------
# Probe.

def fraction(text):
    try:
        numerator, _, denominator = str(text).partition("/")
        value = float(numerator) / float(denominator or 1)
        return value if math.isfinite(value) else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def aspect_text(width, height):
    if not width or not height:
        return None
    ratio = width / height
    for a, b in ((16, 9), (9, 16), (4, 3), (3, 4), (1, 1), (4, 5), (21, 9), (2, 1)):
        if abs(ratio - a / b) < 0.01:
            return "%d:%d" % (a, b)
    return "%.2f:1" % ratio


def parse_probe(data, path):
    """The compact description of ffprobe's JSON."""
    streams = data.get("streams", [])
    info = data.get("format", {})
    duration = float(info.get("duration") or 0)
    result = {"path": str(path), "container": info.get("format_name"),
              "size_mb": round(int(info.get("size") or 0) / 1048576, 2)}
    video = None
    for stream in streams:
        if stream.get("codec_type") == "video" and not stream.get("disposition", {}).get(
                "attached_pic"):
            video = stream
            break
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if video:
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        rotation = 0
        for side in video.get("side_data_list", []) or []:
            if "rotation" in side:
                rotation = int(round(float(side["rotation"])))
        if not rotation and video.get("tags", {}).get("rotate"):
            rotation = -int(float(video["tags"]["rotate"]))
        rotation %= 360
        if rotation in (90, 270):
            width, height = height, width
        fps = fraction(video.get("avg_frame_rate")) or fraction(video.get("r_frame_rate"))
        frames = int(video.get("nb_frames") or 0)
        still = (video.get("codec_name") in IMAGE_CODECS
                 and (frames <= 1 or info.get("format_name", "").startswith("image2")
                      or "_pipe" in info.get("format_name", "")))
        result["type"] = "image" if still else "video"
        result["video"] = {"codec": video.get("codec_name"), "width": width, "height": height,
                           "aspect": aspect_text(width, height)}
        if not still:
            result["video"]["fps"] = round(fps, 3)
        if rotation:
            result["video"]["rotation"] = rotation
        if video.get("pix_fmt"):
            result["video"]["pixel_format"] = video["pix_fmt"]
        if not duration and not still:
            duration = float(video.get("duration") or 0)
    elif audio:
        result["type"] = "audio"
    else:
        result["type"] = "other"
    if audio:
        result["audio"] = []
        for stream in audio:
            entry = {"codec": stream.get("codec_name"),
                     "sample_rate": int(stream.get("sample_rate") or 0),
                     "channels": int(stream.get("channels") or 0)}
            language = stream.get("tags", {}).get("language")
            if language and language != "und":
                entry["language"] = language
            result["audio"].append(entry)
        if not duration:
            duration = float(audio[0].get("duration") or 0)
    if result.get("type") != "image":
        result["duration"] = round(duration, 3)
    created = info.get("tags", {}).get("creation_time")
    if created:
        result["created"] = created
    return result


def probe(path):
    cached = cache_get(path, "probe")
    if cached:
        return cached
    command = require(ffprobe(), ("ffprobe", "SHOTCUT_FFPROBE"))
    code, out, err = run_program(command + ["-v", "error", "-print_format", "json",
                                            "-show_format", "-show_streams", str(path)],
                                 timeout=120)
    if code != 0:
        raise ToolError("ffprobe cannot read %s: %s" % (path.name, err.strip()[-300:]))
    try:
        data = json.loads(out)
    except ValueError:
        raise ToolError("ffprobe gave no information about %s." % path.name)
    result = parse_probe(data, path)
    cache_put(path, "probe", result)
    return result


# ---------------------------------------------------------------------------------------
# Scenes.

SCORE_PATTERN = re.compile(r"lavfi\.scene_score=([0-9.eE+-]+)")
TIME_PATTERN = re.compile(r"pts_time:([0-9.eE+-]+)")


def parse_scene_scores(lines):
    """[(time, score)] from the output of metadata=print."""
    scores, current = [], None
    for line in lines:
        match = TIME_PATTERN.search(line)
        if match:
            current = float(match.group(1))
            continue
        match = SCORE_PATTERN.search(line)
        if match and current is not None:
            scores.append((current, float(match.group(1))))
            current = None
    return scores


def pick_cuts(scores, threshold, min_length):
    """The cuts: scores over the threshold, keeping the strongest within min_length."""
    cuts = []
    for time_, score in scores:
        if score < threshold or time_ <= 0:
            continue
        if cuts and time_ - cuts[-1][0] < min_length:
            if score > cuts[-1][1]:
                cuts[-1] = (time_, score)
            continue
        cuts.append((time_, score))
    return cuts


def scene_scores(job, path, duration):
    cached = cache_get(path, "scene_scores")
    if cached is not None:
        return [tuple(pair) for pair in cached]
    command = require(ffmpeg(), ("ffmpeg", "SHOTCUT_FFMPEG"))
    lines = []

    def on_line(line):
        lines.append(line)
        match = TIME_PATTERN.search(line)
        if match and duration:
            job.update(float(match.group(1)) / duration)

    code, _, err = run_program(
        command + ["-hide_banner", "-nostdin", "-i", str(path), "-an", "-sn", "-dn", "-vf",
                   "scale=320:-2,select='gte(scene,0)',metadata=print:file=-", "-f", "null",
                   "-"], job=job, on_stdout=on_line)
    if code != 0:
        raise ToolError("ffmpeg cannot read the video of %s: %s" % (path.name,
                                                                    err.strip()[-300:]))
    scores = parse_scene_scores(lines)
    # Keep only the frames that could be cuts, so the cache stays small.
    kept = [(round(t, 3), round(s, 4)) for t, s in scores if s >= 0.05]
    cache_put(path, "scene_scores", kept)
    return kept


def scenes_result(path, info, scores, threshold, min_length):
    duration = info.get("duration") or 0.0
    cuts = pick_cuts(scores, threshold, min_length)
    bounds = [0.0] + [time_ for time_, _ in cuts] + [duration]
    scenes = []
    for index in range(len(bounds) - 1):
        start, end = bounds[index], bounds[index + 1]
        if end - start > 0.001:
            scenes.append({"index": len(scenes), "start": round(start, 3), "end": round(end, 3),
                           "duration": round(end - start, 3)})
    return {"path": str(path), "duration": duration, "threshold": threshold,
            "cuts": [{"time": round(t, 3), "score": round(s, 3)} for t, s in cuts],
            "scenes": scenes}


def detect_scenes(job, path, threshold, min_length):
    info = probe(path)
    if info["type"] != "video":
        raise ToolError("%s has no video (it is %s)." % (path.name, info["type"]))
    scores = scene_scores(job, path, info.get("duration"))
    return scenes_result(path, info, scores, threshold, min_length)


# ---------------------------------------------------------------------------------------
# Contact sheet.

DRAWTEXT = {"works": True}


def clock(seconds):
    minutes, seconds = divmod(max(0.0, seconds), 60)
    hours, minutes = divmod(int(minutes), 60)
    if hours:
        return "%d:%02d:%04.1f" % (hours, minutes, seconds)
    return "%d:%04.1f" % (minutes, seconds)


def sheet_times(info, count, start, end, scenes):
    duration = info.get("duration") or 0.0
    if info["type"] == "image":
        return [0.0]
    start = max(0.0, start or 0.0)
    end = min(duration, end) if end else duration
    if end - start <= 0:
        raise ToolError("The range %.3f-%.3f s is empty (the file lasts %.3f s)." % (
            start, end, duration))
    if scenes:
        middles = [(scene["start"] + scene["end"]) / 2 for scene in scenes
                   if scene["end"] > start and scene["start"] < end]
        if middles:
            if len(middles) <= count:
                return middles
            step = len(middles) / count
            return [middles[int(i * step)] for i in range(count)]
    step = (end - start) / count
    # The middle of each part, and never the very last frame, which may not decode.
    return [min(start + (i + 0.5) * step, max(0.0, duration - 0.05)) for i in range(count)]


def extract_frame(command, path, time_, width, target, label):
    filters = "scale=%d:-2" % width
    if label and DRAWTEXT["works"]:
        text = clock(time_).replace(":", "\\:")
        with_text = filters + (",drawtext=text='%s':x=6:y=6:fontsize=%d:fontcolor=white:"
                               "box=1:boxcolor=black@0.6:boxborderw=4" % (text,
                                                                         max(12, width // 16)))
        code, _, _ = run_program(command + ["-hide_banner", "-nostdin", "-loglevel", "error",
                                            "-ss", "%.3f" % time_, "-i", str(path),
                                            "-frames:v", "1", "-an", "-vf", with_text,
                                            "-q:v", "3", "-y", str(target)], timeout=60)
        if code == 0 and target.is_file():
            return
        # ffmpeg without fonts: frames without the time on them.
        DRAWTEXT["works"] = False
    code, _, err = run_program(command + ["-hide_banner", "-nostdin", "-loglevel", "error",
                                          "-ss", "%.3f" % time_, "-i", str(path),
                                          "-frames:v", "1", "-an", "-vf", filters, "-q:v", "3",
                                          "-y", str(target)], timeout=60)
    if code != 0 or not target.is_file():
        raise ToolError("ffmpeg cannot get the frame at %.3f s of %s: %s" % (
            time_, path.name, err.strip()[-200:]))


def contact_sheet(path, count, columns, width, start, end, times, use_scenes):
    info = probe(path)
    if info["type"] not in ("video", "image"):
        raise ToolError("%s has no picture (it is %s)." % (path.name, info["type"]))
    command = require(ffmpeg(), ("ffmpeg", "SHOTCUT_FFMPEG"))
    if times:
        duration = info.get("duration") or 0.0
        times = [max(0.0, min(float(t), max(0.0, duration - 0.05))) for t in times][:48]
    else:
        scenes = None
        if use_scenes and info["type"] == "video":
            cached = cache_get(path, "scene_scores")
            if cached is None:
                raise ToolError("Call detect_scenes first to use scenes, or leave scenes out.")
            scenes = scenes_result(path, info, [tuple(p) for p in cached], 0.3, 0.4)["scenes"]
        times = sheet_times(info, count, start, end, scenes)
    columns = max(1, min(columns, len(times)))
    rows = (len(times) + columns - 1) // columns
    with tempfile.TemporaryDirectory(prefix="shotcut-sheet-") as folder:
        folder = Path(folder)
        errors = []

        def work(indices):
            for index in indices:
                try:
                    extract_frame(command, path, times[index], width,
                                  folder / ("f%03d.jpg" % index), True)
                except ToolError as error:
                    errors.append(str(error))

        threads = [threading.Thread(target=work, args=(list(range(n, len(times), 4)),))
                   for n in range(min(4, len(times)))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if errors:
            raise ToolError(errors[0])
        sheet = folder / "sheet.jpg"
        code, _, err = run_program(command + [
            "-hide_banner", "-nostdin", "-loglevel", "error", "-framerate", "1",
            "-start_number", "0", "-i", str(folder / "f%03d.jpg"), "-vf",
            "tile=%dx%d:padding=4:margin=4:color=0x101114" % (columns, rows), "-frames:v", "1",
            "-q:v", "4", "-y", str(sheet)], timeout=120)
        if code != 0 or not sheet.is_file():
            raise ToolError("ffmpeg cannot build the contact sheet: %s" % err.strip()[-300:])
        image = sheet.read_bytes()
    frames = [{"index": i, "time": round(t, 3), "row": i // columns, "column": i % columns}
              for i, t in enumerate(times)]
    return {"path": str(path), "columns": columns, "rows": rows, "frames": frames,
            "labels": DRAWTEXT["works"]}, image


# ---------------------------------------------------------------------------------------
# Audio: loudness, silences, tempo and beats.

def parse_loudness(text):
    """Integrated loudness, range and true peak from the summary of ebur128."""
    summary = text[text.rfind("Summary:"):] if "Summary:" in text else ""
    result = {}
    for key, pattern in (("integrated_lufs", r"I:\s*(-?[0-9.]+|-inf)\s*LUFS"),
                         ("range_lu", r"LRA:\s*(-?[0-9.]+)\s*LU"),
                         ("true_peak_dbfs", r"Peak:\s*(-?[0-9.]+|-inf)\s*dBFS")):
        match = re.search(pattern, summary)
        if match:
            value = match.group(1)
            result[key] = None if value == "-inf" else round(float(value), 1)
    return result


def parse_silences(text, duration):
    silences, start = [], None
    for line in text.splitlines():
        match = re.search(r"silence_start:\s*(-?[0-9.]+)", line)
        if match:
            start = max(0.0, float(match.group(1)))
            continue
        match = re.search(r"silence_end:\s*([0-9.]+)", line)
        if match and start is not None:
            end = float(match.group(1))
            silences.append({"start": round(start, 3), "end": round(end, 3),
                             "duration": round(end - start, 3)})
            start = None
    if start is not None and duration and duration > start:
        silences.append({"start": round(start, 3), "end": round(duration, 3),
                         "duration": round(duration - start, 3)})
    return silences


def onset_envelope(samples, rate, hop):
    """Onset strength per hop: the rise of the log energy of the pre-emphasized signal."""
    window = hop * 2
    if len(samples) < window + 1:
        return []
    # Pre-emphasis boosts attacks (drums, plucks) over sustained sounds.
    emphasized = list(map(lambda value, last: value - 0.97 * last, samples[1:], samples[:-1]))
    squares = itertools.accumulate(map(operator.mul, emphasized, emphasized), initial=0.0)
    prefix = list(squares)
    count = (len(emphasized) - window) // hop
    energies = [math.log(prefix[frame * hop + window] - prefix[frame * hop] + 1e3)
                for frame in range(count)]
    onsets = [0.0] + [max(0.0, energies[i] - energies[i - 1]) for i in range(1, len(energies))]
    # Remove the local mean (half a second each way), so that only sudden rises count.
    frames_per_second = rate / hop
    radius = max(1, int(frames_per_second / 2))
    prefix = [0.0]
    for value in onsets:
        prefix.append(prefix[-1] + value)
    result = []
    for i, value in enumerate(onsets):
        lo, hi = max(0, i - radius), min(len(onsets), i + radius + 1)
        mean = (prefix[hi] - prefix[lo]) / (hi - lo)
        result.append(max(0.0, value - mean))
    return result


def estimate_tempo(envelope, frames_per_second, low_bpm=60.0, high_bpm=200.0):
    """(bpm, confidence 0-1) from the autocorrelation of the onset envelope, weighted
    towards common tempos (around 120 BPM)."""
    limit = min(len(envelope), int(frames_per_second * 90))
    values = envelope[:limit]
    min_lag = max(1, int(frames_per_second * 60 / high_bpm))
    max_lag = min(len(values) - 1, int(math.ceil(frames_per_second * 60 / low_bpm)))
    if max_lag <= min_lag + 2:
        return None, 0.0
    correlations = {}
    for lag in range(min_lag - 1, max_lag + 2):
        if lag <= 0 or lag >= len(values):
            continue
        correlations[lag] = sum(map(operator.mul, values, values[lag:])) / (len(values) - lag)
    weighted = {}
    for lag in range(min_lag, max_lag + 1):
        if lag not in correlations:
            continue
        bpm = 60.0 * frames_per_second / lag
        weight = math.exp(-0.5 * (math.log2(bpm / 120.0) / 1.0) ** 2)
        weighted[lag] = correlations[lag] * weight
    if not weighted:
        return None, 0.0
    best = max(weighted, key=weighted.get)
    # Refine the lag between frames with a parabola through its neighbours.
    lag = float(best)
    left, right = correlations.get(best - 1), correlations.get(best + 1)
    center = correlations[best]
    if left is not None and right is not None:
        denominator = left - 2 * center + right
        if denominator < 0:
            lag += 0.5 * (left - right) / denominator
    mean = sum(correlations.values()) / len(correlations)
    confidence = 0.0 if mean <= 0 else max(0.0, min(1.0, (center / mean - 1.0) / 3.0))
    return 60.0 * frames_per_second / lag, confidence


def track_beats(envelope, frames_per_second, bpm, tightness=100.0):
    """Beat times in seconds by dynamic programming (Ellis 2007)."""
    if not envelope or not bpm:
        return []
    period = 60.0 * frames_per_second / bpm
    scores = list(envelope)
    back = [-1] * len(envelope)
    low, high = max(1, int(round(period * 0.8))), int(round(period * 1.25))
    penalties = [(step, tightness * math.log(step / period) ** 2)
                 for step in range(low, high + 1)]
    for t in range(low, len(envelope)):
        best, best_from = 0.0, -1
        for step, penalty in penalties:
            source = t - step
            if source < 0:
                break
            value = scores[source] - penalty
            if value > best:
                best, best_from = value, source
        if best_from >= 0:
            scores[t] = envelope[t] + best
            back[t] = best_from
    # The last beat: the best score in the last period.
    tail = range(max(0, len(scores) - int(period) - 1), len(scores))
    t = max(tail, key=lambda i: scores[i])
    beats = []
    while t >= 0:
        beats.append(t)
        t = back[t]
    beats.reverse()
    return [round(frame / frames_per_second, 3) for frame in beats]


def read_pcm(data):
    samples = array.array("h")
    samples.frombytes(data[:len(data) - len(data) % 2])
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def rhythm(samples, rate):
    hop = rate // 100
    envelope = onset_envelope(samples, rate, hop)
    frames_per_second = rate / hop
    bpm, confidence = estimate_tempo(envelope, frames_per_second)
    if not bpm:
        return {"bpm": None, "confidence": 0.0, "beats": []}
    beats = track_beats(envelope, frames_per_second, bpm)
    # The energy of a frame covers two hops from its start, so a beat that starts at the
    # end of that window rises in the frame two hops earlier.
    beats = [round(t + 2.0 / frames_per_second, 3) for t in beats]
    return {"bpm": round(bpm, 1), "confidence": round(confidence, 2), "beats": beats}


BEAT_SECONDS = 600
BEAT_RATE = 8000


def analyze_audio(job, path, silence_db, min_silence, with_beats):
    info = probe(path)
    if not info.get("audio"):
        raise ToolError("%s has no audio." % path.name)
    duration = info.get("duration") or 0.0
    key = "%g|%g" % (silence_db, min_silence)
    result = cache_get(path, "audio", key)
    command = require(ffmpeg(), ("ffmpeg", "SHOTCUT_FFMPEG"))
    if not result:
        def on_progress(line):
            if line.startswith("out_time_us=") and duration:
                try:
                    job.update(0.7 * int(line.split("=")[1]) / 1e6 / duration)
                except ValueError:
                    pass

        code, _, err = run_program(command + [
            "-hide_banner", "-nostdin", "-nostats", "-progress", "pipe:1", "-i", str(path),
            "-vn", "-sn", "-dn", "-af",
            "silencedetect=noise=%gdB:d=%g,ebur128=peak=true:framelog=verbose" % (
                silence_db, min_silence), "-f", "null", "-"], job=job, on_stdout=on_progress)
        if code != 0:
            raise ToolError("ffmpeg cannot read the audio of %s: %s" % (path.name,
                                                                        err.strip()[-300:]))
        silences = parse_silences(err, duration)
        silent = sum(item["duration"] for item in silences)
        result = {"path": str(path), "duration": duration, "loudness": parse_loudness(err),
                  "silence_db": silence_db, "silences": silences,
                  "silence_ratio": round(silent / duration, 3) if duration else 0.0}
        cache_put(path, "audio", result, key)
    result = dict(result)
    if with_beats:
        beats = cache_get(path, "rhythm")
        if not beats:
            job.update(0.75, "tempo and beats")
            code, pcm, err = run_program(command + [
                "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(path), "-vn",
                "-t", str(BEAT_SECONDS), "-ac", "1", "-ar", str(BEAT_RATE), "-f", "s16le",
                "-acodec", "pcm_s16le", "-"], job=job, binary_stdout=True)
            if code != 0:
                raise ToolError("ffmpeg cannot decode the audio of %s: %s" % (
                    path.name, err.strip()[-300:]))
            job.update(0.85)
            beats = rhythm(read_pcm(pcm), BEAT_RATE)
            if duration > BEAT_SECONDS:
                beats["analyzed_seconds"] = BEAT_SECONDS
            cache_put(path, "rhythm", beats)
        result["tempo"] = beats
    return result


# ---------------------------------------------------------------------------------------
# Speech.

PROGRESS_PATTERN = re.compile(r"progress\s*=\s*(\d+)%")


def ascii_path(path):
    """A path whisper-cli can open on Windows even with accents in it (the short name)."""
    text = str(path)
    if not IS_WINDOWS or text.isascii():
        return text
    try:
        import ctypes
        buffer = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(text, buffer, 1024):
            return buffer.value
    except (AttributeError, OSError):
        pass
    return text


def words_from_tokens(segments):
    """Words with times from the tokens of whisper-cli's full JSON output."""
    words = []
    for segment in segments:
        current = None
        segment_offsets = segment.get("offsets", {})
        previous_end = segment_offsets.get("from", 0) / 1000.0
        for token in segment.get("tokens", []):
            text = token.get("text", "")
            if not text or (text.startswith("[_") and text.endswith("]")):
                continue
            # Tokens without their own times (older models) take the time before them.
            offsets = token.get("offsets") or {}
            begin = offsets.get("from", previous_end * 1000.0) / 1000.0
            finish = offsets.get("to", begin * 1000.0) / 1000.0
            previous_end = finish
            if current is None or text.startswith(" "):
                if current:
                    words.append(current)
                current = {"raw": text, "start": begin, "end": finish,
                           "p": token.get("p", 1.0)}
            else:
                current["raw"] += text
                current["end"] = finish
                current["p"] = min(current["p"], token.get("p", 1.0))
        if current:
            words.append(current)
    result = []
    for word in words:
        text = word["raw"].encode("utf-8", "surrogateescape").decode("utf-8", "replace").strip()
        if text:
            result.append([round(word["start"], 2), round(word["end"], 2), text,
                           round(word["p"], 2)])
    return result


def parse_whisper(data):
    """Segments, words and language from whisper-cli's --output-json-full file."""
    segments = []
    for segment in data.get("transcription", []):
        offsets = segment.get("offsets", {})
        text = segment.get("text", "")
        text = text.encode("utf-8", "surrogateescape").decode("utf-8", "replace").strip()
        if text:
            segments.append({"start": round(offsets.get("from", 0) / 1000.0, 2),
                             "end": round(offsets.get("to", 0) / 1000.0, 2), "text": text})
    return {"language": data.get("result", {}).get("language"), "segments": segments,
            "words": words_from_tokens(data.get("transcription", []))}


def srt_time(seconds):
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return "%02d:%02d:%02d,%03d" % (hours, minutes, seconds, milliseconds)


def write_srt(segments, target):
    lines = []
    for index, segment in enumerate(segments, 1):
        lines += [str(index), "%s --> %s" % (srt_time(segment["start"]), srt_time(segment["end"])),
                  segment["text"], ""]
    target.write_text("\n".join(lines), encoding="utf-8")


def transcribe(job, path, language, model):
    info = probe(path)
    if not info.get("audio"):
        raise ToolError("%s has no audio to transcribe." % path.name)
    model_path = resolve_model(model)
    key = "%s|%s" % (Path(model_path).name, language)
    cached = cache_get(path, "transcripts", key)
    if cached:
        return cached
    command = require(ffmpeg(), ("ffmpeg", "SHOTCUT_FFMPEG"))
    whisper_command = require(whisper(), ("whisper-cli", "SHOTCUT_WHISPER"))
    duration = info.get("duration") or 0.0
    with tempfile.TemporaryDirectory(prefix="shotcut-speech-") as folder:
        folder = Path(folder)
        wav = folder / "audio.wav"
        job.update(0.01, "extracting the audio")
        code, _, err = run_program(command + [
            "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1",
            "-ar", "16000", "-c:a", "pcm_s16le", "-y", str(wav)], job=job)
        if code != 0:
            raise ToolError("ffmpeg cannot extract the audio of %s: %s" % (
                path.name, err.strip()[-300:]))
        job.update(0.05, "transcribing")

        def on_line(line):
            match = PROGRESS_PATTERN.search(line)
            if match:
                job.update(0.05 + 0.93 * int(match.group(1)) / 100.0)

        output = folder / "speech"
        arguments = ["-m", ascii_path(model_path), "-f", ascii_path(wav), "-l",
                     language or "auto", "-ojf", "-of",
                     os.path.join(ascii_path(folder), "speech"), "-pp", "-t",
                     str(max(1, min(8, os.cpu_count() or 4)))]
        code, _, err = run_program(whisper_command + arguments, job=job, on_stderr=on_line)
        if code != 0 or not output.with_suffix(".json").is_file():
            # Like Shotcut's Speech to Text: try again without the GPU.
            job.update(0.05, "transcribing without the GPU")
            code, _, err = run_program(whisper_command + arguments + ["-ng"], job=job,
                                       on_stderr=on_line)
        if code != 0 or not output.with_suffix(".json").is_file():
            raise ToolError("whisper-cli failed: %s" % err.strip()[-400:])
        raw = output.with_suffix(".json").read_bytes()
    data = json.loads(raw.decode("utf-8", "surrogateescape"))
    result = parse_whisper(data)
    result.update({"path": str(path), "duration": duration, "model": Path(model_path).name})
    result["word_count"] = len(result["words"])
    srt = cache_dir() / ("%s.%s.%s.srt" % (media_key(path), Path(model_path).stem,
                                           language or "auto"))
    srt.parent.mkdir(parents=True, exist_ok=True)
    write_srt(result["segments"], srt)
    result["srt"] = str(srt)
    cache_put(path, "transcripts", result, key)
    return result


def transcript_view(result, start, end, with_words, max_words):
    """The part of a transcript to send: a time range, and words only when asked."""
    view = {key: result[key] for key in ("path", "language", "model", "duration", "srt",
                                         "word_count") if key in result}

    def inside(item_start, item_end):
        return (start is None or item_end > start) and (end is None or item_start < end)

    view["segments"] = [s for s in result["segments"] if inside(s["start"], s["end"])]
    if with_words:
        words = [w for w in result["words"] if inside(w[0], w[1])]
        view["words_format"] = "[start, end, text, probability]"
        view["words"] = words[:max_words]
        if len(words) > max_words:
            view["words_truncated"] = "%d more; ask for a later start" % (len(words) - max_words)
    return view


# ---------------------------------------------------------------------------------------
# Describe a clip and a folder.

def describe(job, path, with_speech):
    info = probe(path)
    summary = {"path": str(path), "type": info["type"]}
    if "duration" in info:
        summary["duration"] = info["duration"]
    video = info.get("video")
    if video:
        text = "%dx%d" % (video["width"], video["height"])
        if video.get("fps"):
            text += " %g fps" % video["fps"]
        summary["video"] = "%s %s%s" % (text, video.get("codec"),
                                        " rotated %d" % video["rotation"]
                                        if video.get("rotation") else "")
    if info.get("audio"):
        first = info["audio"][0]
        summary["audio"] = "%s %d Hz %d ch" % (first["codec"], first["sample_rate"],
                                               first["channels"])
    if info["type"] == "video":
        job.update(0.05, "scenes")
        scenes = scenes_result(path, info, scene_scores(job, path, info.get("duration")), 0.3,
                               0.4)["scenes"]
        summary["scenes"] = {"count": len(scenes),
                             "list": [[s["start"], s["end"]] for s in scenes[:60]]}
        if len(scenes) > 60:
            summary["scenes"]["more"] = len(scenes) - 60
    if info.get("audio"):
        job.update(0.5, "audio")
        audio = analyze_audio(job, path, -35.0, 0.5, info["type"] == "audio")
        details = {"loudness": audio["loudness"], "silence_ratio": audio["silence_ratio"],
                   "silences": len(audio["silences"])}
        tempo = audio.get("tempo")
        if tempo and tempo.get("bpm") and tempo.get("confidence", 0) >= 0.3:
            details["tempo_bpm"] = tempo["bpm"]
        summary["audio_analysis"] = details
        transcripts = cache_get(path, "transcripts") or {}
        transcript = next(iter(transcripts.values()), None)
        if not transcript and with_speech:
            job.update(0.6, "speech")
            transcript = transcribe(job, path, "auto", None)
        if transcript:
            text = " ".join(segment["text"] for segment in transcript["segments"])
            summary["speech"] = {"language": transcript.get("language"),
                                 "words": transcript.get("word_count"),
                                 "excerpt": text[:400] + ("..." if len(text) > 400 else "")}
    hints = []
    if info["type"] in ("video", "image"):
        hints.append("contact_sheet to see it")
    if info.get("audio") and "speech" not in summary:
        hints.append("transcribe for the speech")
    if hints:
        summary["next"] = hints
    return summary


def media_files(folder, recursive):
    pattern = "**/*" if recursive else "*"
    files = []
    for path in sorted(folder.glob(pattern)):
        suffix = path.suffix.lower()
        if path.is_file() and suffix in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | IMAGE_EXTENSIONS:
            files.append(path)
    return files


def analyze_folder(job, folder, recursive, deep, with_speech):
    files = media_files(folder, recursive)
    if not files:
        raise ToolError("No media files in %s." % folder)
    files = files[:500]
    index = []
    for number, path in enumerate(files):
        job.update(number / len(files), "%d/%d %s" % (number + 1, len(files), path.name))
        try:
            if deep:
                entry = describe(SubJob(job, number / len(files), 1.0 / len(files)), path,
                                 with_speech)
            else:
                info = probe(path)
                entry = {"path": str(path), "type": info["type"]}
                for key in ("duration", "video"):
                    if key in info:
                        entry[key] = info[key]
        except ToolError as error:
            entry = {"path": str(path), "error": str(error)}
        entry.pop("next", None)
        index.append(entry)
    counts = {}
    for entry in index:
        counts[entry.get("type", "error")] = counts.get(entry.get("type", "error"), 0) + 1
    total = sum(entry.get("duration") or 0 for entry in index)
    return {"folder": str(folder), "files": len(index), "types": counts,
            "total_duration": round(total, 1), "items": index}


# ---------------------------------------------------------------------------------------
# Models.

def download_model(job, name):
    model = next((m for m in known_models() if m["name"] == name), None)
    if not model:
        raise ToolError("Unknown model \"%s\". Models: %s." % (
            name, ", ".join(m["name"] for m in known_models())))
    target = models_dir() / model["file"]
    if target.is_file():
        return {"model": name, "path": str(target), "already_downloaded": True}
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    request = urllib.request.Request(model["url"], headers={"User-Agent": "Shotcut-AI"})
    with urllib.request.urlopen(request, timeout=60) as response, open(partial, "wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
            received += len(chunk)
            job.update(received / total if total else None,
                       "%.0f of %.0f MB" % (received / 1048576, total / 1048576))
    if total and received != total:
        partial.unlink(missing_ok=True)
        raise ToolError("The download of %s stopped at %d of %d bytes." % (name, received, total))
    os.replace(partial, target)
    return {"model": name, "path": str(target), "size_mb": round(received / 1048576, 1)}


def setup_json():
    def version(command, flag):
        if not command:
            return None
        try:
            code, out, err = run_program(command + [flag], timeout=20)
        except ToolError:
            return None
        text = (out or err).strip().splitlines()
        return text[0][:120] if text else "found"

    ff, fp, wh = ffmpeg(), ffprobe(), whisper()
    folder = models_dir()
    return {
        "ffmpeg": {"command": ff and ff[-1], "version": version(ff, "-version")},
        "ffprobe": {"command": fp and fp[-1], "version": version(fp, "-version")},
        "whisper": {"command": wh and wh[-1]},
        "models_folder": str(folder),
        "models_installed": [Path(path).name for path in installed_models()],
        "default_model": default_model(),
        "models_available": [{"name": m["name"], "size_mb": m["size_mb"]}
                             for m in known_models()],
        "cache_folder": str(cache_dir()),
        "python": sys.version.split()[0],
    }


# ---------------------------------------------------------------------------------------
# MCP tools.

READ_ONLY = {"readOnlyHint": True, "openWorldHint": False}
WAIT = {"type": "number", "minimum": 0, "maximum": 120,
        "description": "Seconds to wait for the result (default 20); after that the answer is a "
                       "job id and the work goes on."}
PATH = {"type": "string", "description": "Absolute path of the media file."}


def tool(name, title, description, properties, required=(), annotations=READ_ONLY):
    return {"name": name, "title": title, "description": description,
            "inputSchema": {"type": "object", "properties": properties,
                            "required": list(required), "additionalProperties": False},
            "annotations": dict(annotations, title=title)}


TOOLS = [
    tool("check_setup", "Check setup",
         "Where the programs (ffmpeg, ffprobe, whisper-cli), the Whisper models and the cache "
         "are, which models can be downloaded, and the running jobs. Call it when something "
         "does not work.", {}),
    tool("probe_media", "Probe media",
         "Technical facts of a media file: type (video, audio, image), duration, size, frame "
         "rate, codecs, rotation and audio streams.", {"path": PATH}, ["path"]),
    tool("describe_clip", "Describe clip",
         "A compact summary of a clip for choosing takes: probe facts, scenes (shots), "
         "loudness, silences, tempo of music and, when available or asked, the speech. It runs "
         "the analyses that are not cached yet.",
         {"path": PATH, "speech": {"type": "boolean",
                                   "description": "Also transcribe the speech (slower)."},
          "wait": WAIT}, ["path"]),
    tool("detect_scenes", "Detect scenes",
         "The shots of a video: the cuts (time and strength 0-1) and the scenes between them. "
         "A lower threshold finds softer cuts.",
         {"path": PATH,
          "threshold": {"type": "number", "minimum": 0.05, "maximum": 1,
                        "description": "Cut strength from 0 to 1 (default 0.3)."},
          "min_length": {"type": "number", "minimum": 0,
                         "description": "Shortest scene in seconds (default 0.4)."},
          "wait": WAIT}, ["path"]),
    tool("contact_sheet", "Contact sheet",
         "One image with several frames of a video, each labelled with its time: the cheap "
         "way to see a clip. Frames are spread evenly, taken from the middle of each scene "
         "(scenes, after detect_scenes) or at the given times.",
         {"path": PATH,
          "count": {"type": "integer", "minimum": 1, "maximum": 48,
                    "description": "Number of frames (default 12)."},
          "columns": {"type": "integer", "minimum": 1, "maximum": 8,
                      "description": "Frames per row (default 4)."},
          "width": {"type": "integer", "minimum": 96, "maximum": 640,
                    "description": "Width of each frame in pixels (default 320)."},
          "start": {"type": "number", "minimum": 0, "description": "From this time (seconds)."},
          "end": {"type": "number", "minimum": 0, "description": "Up to this time (seconds)."},
          "times": {"type": "array", "items": {"type": "number", "minimum": 0},
                    "maxItems": 48, "description": "Exact times in seconds instead."},
          "scenes": {"type": "boolean", "description": "One frame per scene."}},
         ["path"]),
    tool("analyze_audio", "Analyze audio",
         "Loudness (integrated LUFS, range, true peak), silences and, for music, the tempo "
         "and the beat times to cut to the rhythm (the first 10 minutes).",
         {"path": PATH,
          "silence_db": {"type": "number", "minimum": -90, "maximum": -10,
                         "description": "Level below which it is silence (default -35 dB)."},
          "min_silence": {"type": "number", "minimum": 0.05,
                          "description": "Shortest silence in seconds (default 0.5)."},
          "beats": {"type": "boolean", "description": "Tempo and beats (default true)."},
          "start": {"type": "number", "minimum": 0,
                    "description": "Only list silences and beats from this time."},
          "end": {"type": "number", "minimum": 0,
                  "description": "Only list silences and beats up to this time."},
          "wait": WAIT}, ["path"]),
    tool("transcribe", "Transcribe",
         "The speech of a file with times: phrases (segments) and, with words, every word "
         "with its start and end, to cut between words and to make subtitles. Runs "
         "whisper.cpp on this computer; an SRT file is also written. Long files take a while.",
         {"path": PATH,
          "language": {"type": "string",
                       "description": "Language code such as es or en (default auto)."},
          "model": {"type": "string",
                    "description": "Model name (base, small-q5_1...) or file; default: the one "
                                   "chosen in Shotcut or the best downloaded."},
          "words": {"type": "boolean", "description": "Include the words (default false)."},
          "start": {"type": "number", "minimum": 0, "description": "Only from this time."},
          "end": {"type": "number", "minimum": 0, "description": "Only up to this time."},
          "max_words": {"type": "integer", "minimum": 1, "maximum": 5000,
                        "description": "At most this many words (default 800)."},
          "wait": WAIT}, ["path"]),
    tool("analyze_folder", "Analyze folder",
         "An index of the media files in a folder: type, duration and, with deep (default), "
         "scenes, loudness and tempo, to find material. Cached per file.",
         {"path": {"type": "string", "description": "Absolute path of the folder."},
          "recursive": {"type": "boolean", "description": "Include subfolders."},
          "deep": {"type": "boolean",
                   "description": "Scenes and audio too (default true); false: only probe."},
          "speech": {"type": "boolean", "description": "Transcribe the speech too (slow)."},
          "wait": WAIT}, ["path"]),
    tool("download_model", "Download Whisper model",
         "Downloads a Whisper model for transcribe into the folder that Shotcut AI uses "
         "(Subtitles > Speech to Text). Only once; the transcription itself is local.",
         {"name": {"type": "string",
                   "description": "base (148 MB, a good start), small-q5_1 (190 MB, better "
                                  "for Spanish), tiny, small, medium-q5_0, large-v3-q5_0..."},
          "wait": WAIT}, ["name"], {"readOnlyHint": False, "openWorldHint": True}),
    tool("get_jobs", "Get jobs",
         "The analysis jobs: status, progress and, for one job, its result.",
         {"job": {"type": "string", "description": "A job id (j1...) to get its result."}}),
    tool("cancel_job", "Cancel job", "Stops a running job.",
         {"job": {"type": "string", "description": "A job id (j1...)."}}, ["job"],
         {"readOnlyHint": False, "openWorldHint": False}),
]
TOOLS_BY_NAME = {entry["name"]: entry for entry in TOOLS}


def validate(schema, arguments):
    """An error message for arguments that do not fit the schema, else None."""
    if not isinstance(arguments, dict):
        return "The arguments must be an object."
    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in arguments:
            return "Missing required argument \"%s\"." % name
    for name, value in arguments.items():
        if name not in properties:
            return "Unknown argument \"%s\". Arguments: %s." % (name, ", ".join(properties))
        rule = properties[name]
        kind = rule.get("type")
        checks = {"string": lambda v: isinstance(v, str),
                  "boolean": lambda v: isinstance(v, bool),
                  "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
                  "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
                  "array": lambda v: isinstance(v, list)}
        if kind in checks and not checks[kind](value):
            return "\"%s\" must be %s." % (name, kind)
        if kind in ("integer", "number"):
            if "minimum" in rule and value < rule["minimum"]:
                return "\"%s\" must be at least %s." % (name, rule["minimum"])
            if "maximum" in rule and value > rule["maximum"]:
                return "\"%s\" must be at most %s." % (name, rule["maximum"])
        if kind == "array":
            if "maxItems" in rule and len(value) > rule["maxItems"]:
                return "\"%s\" can have at most %d items." % (name, rule["maxItems"])
            items = rule.get("items", {})
            if items.get("type") == "number" and not all(
                    checks["number"](v) and v >= items.get("minimum", -math.inf) for v in value):
                return "\"%s\" must be a list of numbers of at least %s." % (
                    name, items.get("minimum", "any"))
    return None


def wait_for(job, arguments, report):
    """The result of a job if it ends within "wait" seconds, else its status."""
    limit = float(arguments.get("wait", 20))
    deadline = time.time() + limit
    last = None
    while not job.done.wait(timeout=min(1.0, max(0.0, deadline - time.time()))):
        if time.time() >= deadline:
            break
        if report and job.progress != last:
            last = job.progress
            report(job)
    if job.status == "done":
        return job.result
    if job.status == "failed":
        raise ToolError(job.error)
    if job.status == "cancelled":
        raise ToolError("The job %s was cancelled." % job.id)
    status = job.json()
    status["hint"] = ("Still working. Call this tool again later (the result will be ready "
                      "and cached) or get_jobs with job \"%s\"." % job.id)
    return status


def call_tool(name, arguments, report=None):
    """(content blocks, is error) for a tools/call."""
    entry = TOOLS_BY_NAME.get(name)
    if not entry:
        raise KeyError(name)
    error = validate(entry["inputSchema"], arguments)
    if error:
        return [{"type": "text", "text": error}], True
    try:
        data, image = run_tool(name, arguments, report)
    except ToolError as error:
        return [{"type": "text", "text": str(error)}], True
    content = [{"type": "text", "text": json.dumps(data, ensure_ascii=False,
                                                   separators=(",", ":"))}]
    if image:
        content.append({"type": "image", "data": base64.b64encode(image).decode("ascii"),
                        "mimeType": "image/jpeg"})
    return content, False


def run_tool(name, arguments, report):
    if name == "check_setup":
        data = setup_json()
        data["jobs"] = [job.json() for job in JOBS.all() if job.status == "running"]
        return data, None
    if name == "get_jobs":
        if arguments.get("job"):
            job = JOBS.get(arguments["job"])
            if not job:
                raise ToolError("Unknown job \"%s\"." % arguments["job"])
            return job.json(with_result=True), None
        return {"jobs": [job.json() for job in JOBS.all()]}, None
    if name == "cancel_job":
        job = JOBS.get(arguments["job"])
        if not job:
            raise ToolError("Unknown job \"%s\"." % arguments["job"])
        job.cancelled.set()
        return {"job": job.id, "status": "cancelling" if job.status == "running"
                else job.status}, None
    if name == "download_model":
        job = JOBS.start("download_model", arguments["name"], ("download", arguments["name"]),
                         lambda job: download_model(job, arguments["name"]))
        return wait_for(job, arguments, report), None
    if name == "analyze_folder":
        folder = Path(os.path.expanduser(arguments["path"].strip()))
        if not folder.is_dir():
            raise ToolError("Folder not found: %s" % arguments["path"])
        folder = folder.resolve()
        deep = arguments.get("deep", True)
        speech = arguments.get("speech", False)
        job = JOBS.start("analyze_folder", folder.name,
                         ("folder", str(folder), arguments.get("recursive", False), deep, speech),
                         lambda job: analyze_folder(job, folder, arguments.get("recursive", False),
                                                    deep, speech))
        return wait_for(job, arguments, report), None
    path = media_path(arguments.get("path"))
    if name == "probe_media":
        return probe(path), None
    if name == "contact_sheet":
        return contact_sheet(path, arguments.get("count", 12), arguments.get("columns", 4),
                             arguments.get("width", 320), arguments.get("start"),
                             arguments.get("end"), arguments.get("times"),
                             arguments.get("scenes", False))
    if name == "detect_scenes":
        threshold = arguments.get("threshold", 0.3)
        min_length = arguments.get("min_length", 0.4)
        job = JOBS.start("detect_scenes", path.name, ("scenes", str(path)),
                         lambda job: detect_scenes(job, path, threshold, min_length))
        return wait_for(job, arguments, report), None
    if name == "describe_clip":
        speech = arguments.get("speech", False)
        job = JOBS.start("describe_clip", path.name, ("describe", str(path), speech),
                         lambda job: describe(job, path, speech))
        return wait_for(job, arguments, report), None
    if name == "analyze_audio":
        silence_db = arguments.get("silence_db", -35.0)
        min_silence = arguments.get("min_silence", 0.5)
        beats = arguments.get("beats", True)
        job = JOBS.start("analyze_audio", path.name,
                         ("audio", str(path), silence_db, min_silence, beats),
                         lambda job: analyze_audio(job, path, silence_db, min_silence, beats))
        result = wait_for(job, arguments, report)
        if "job" in result:
            return result, None
        return audio_view(result, arguments.get("start"), arguments.get("end")), None
    if name == "transcribe":
        language = arguments.get("language") or "auto"
        model = arguments.get("model")
        job = JOBS.start("transcribe", path.name, ("speech", str(path), language, model),
                         lambda job: transcribe(job, path, language, model))
        result = wait_for(job, arguments, report)
        if "job" in result:
            return result, None
        return transcript_view(result, arguments.get("start"), arguments.get("end"),
                               arguments.get("words", False),
                               arguments.get("max_words", 800)), None
    raise ToolError("Unknown tool %s" % name)


def audio_view(result, start, end):
    view = dict(result)

    def inside(time_):
        return (start is None or time_ >= start) and (end is None or time_ <= end)

    view["silences"] = [s for s in result["silences"] if inside(s["start"]) or inside(s["end"])]
    tempo = result.get("tempo")
    if tempo:
        tempo = dict(tempo)
        beats = [t for t in tempo.get("beats", []) if inside(t)]
        tempo["beats"] = beats[:600]
        if len(beats) > 600:
            tempo["beats_truncated"] = "%d more; ask for a later start" % (len(beats) - 600)
        view["tempo"] = tempo
    return view


# ---------------------------------------------------------------------------------------
# The MCP server over standard input and output.

class Server:
    def __init__(self, output=None):
        self.output = output or sys.stdout
        self.lock = threading.Lock()

    def write(self, message):
        text = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        with self.lock:
            self.output.write(text + "\n")
            self.output.flush()

    def reply(self, request_id, result=None, error=None):
        message = {"jsonrpc": "2.0", "id": request_id}
        if error:
            message["error"] = error
        else:
            message["result"] = result
        self.write(message)

    def handle(self, message):
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            self.reply(message.get("id") if isinstance(message, dict) else None,
                       error={"code": -32600, "message": "Invalid request"})
            return
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}
        if method is None:
            return  # A response from the client.
        if request_id is None:
            return  # A notification (initialized, cancelled...).
        if method == "initialize":
            requested = params.get("protocolVersion")
            version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
            self.reply(request_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "title": SERVER_TITLE, "version": VERSION},
                "instructions": INSTRUCTIONS})
        elif method == "ping":
            self.reply(request_id, {})
        elif method == "tools/list":
            self.reply(request_id, {"tools": TOOLS})
        elif method in ("resources/list", "resources/templates/list", "prompts/list"):
            key = {"resources/list": "resources", "resources/templates/list":
                   "resourceTemplates", "prompts/list": "prompts"}[method]
            self.reply(request_id, {key: []})
        elif method == "logging/setLevel":
            self.reply(request_id, {})
        elif method == "tools/call":
            # In a thread: other requests are answered while a tool waits for a job.
            threading.Thread(target=self.tools_call, args=(request_id, params),
                             daemon=True).start()
        else:
            self.reply(request_id, error={"code": -32601, "message": "Method not found: %s"
                                          % method})

    def tools_call(self, request_id, params):
        name = params.get("name")
        arguments = params.get("arguments") or {}
        token = (params.get("_meta") or {}).get("progressToken")
        report = None
        if token is not None:
            def send_progress(job):
                self.write({"jsonrpc": "2.0", "method": "notifications/progress",
                            "params": {"progressToken": token,
                                       "progress": round(job.progress * 100),
                                       "total": 100, "message": job.message or job.kind}})
            report = send_progress
        try:
            content, is_error = call_tool(name, arguments, report)
        except KeyError:
            self.reply(request_id, error={"code": -32602, "message": "Unknown tool: %s" % name})
            return
        except Exception as error:  # Never leave a request without an answer.
            log("tool", name, "failed:", repr(error))
            content, is_error = [{"type": "text", "text": "Internal error: %s" % error}], True
        self.reply(request_id, {"content": content, "isError": is_error})

    def run(self, stream=None):
        for line in stream or sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                self.reply(None, error={"code": -32700, "message": "Parse error"})
                continue
            for item in message if isinstance(message, list) else [message]:
                self.handle(item)


def main():
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    Server().run()


if __name__ == "__main__":
    main()
