#!/usr/bin/env python3
"""
test_phase9_ai_analysis_verification.py

Phase 9 Verification Suite: perception for the AI (roadmap phases 0 and 1)
- A1: The media analysis server (scripts/shotcut_analysis.py) reads ffprobe, scene scores,
      loudness, silences and whisper-cli output correctly
- A2: Tempo and beats from audio made in the test (pure Python, no ffmpeg)
- A3: The server end to end over stdio with stand-in ffmpeg, ffprobe and whisper-cli: every
      tool, jobs, cache, GPU fallback, SRT, clear errors; standard library only
- A4: Whisper models: Shotcut's model list, folder and choice
- A5: Installed next to the bridge on every platform; the Windows zip has whisper-cli and
      the ggml backends and the build checks the analysis with a real model
- F1: Compact answers of Shotcut AI: the data once, media ids and a media table
- F2: The video profile is built from its values (no stale "PAL 4:3" description)
- F3: Files that Microsoft Store apps save under AppData are found (unit tested in C++)
- F4: Copy MCP Configuration sets up shotcut-analysis too; the two Shotcut processes are
      the startup watchdog and the application
- D1: sc.py, the samples generator, the guides and the roadmap
"""

import array
import ast
import importlib.util
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
SCRIPTS = PROJECT_ROOT / "scripts"
MEDIA = PROJECT_ROOT / "tests" / "media"
ANALYSIS = SCRIPTS / "shotcut_analysis.py"
SC = SCRIPTS / "sc.py"
FAKE_FFMPEG = MEDIA / "fake_ffmpeg.py"
FAKE_WHISPER = MEDIA / "fake_whisper.py"
MAKE_SAMPLES = MEDIA / "make_samples.py"
LIVE_SMOKE = PROJECT_ROOT / "tests" / "live_analysis_smoke.py"
TOOLS_CPP = SRC / "ai" / "aitools.cpp"
PROTOCOL_CPP = SRC / "ai" / "mcpprotocol.cpp"
PROTOCOL_H = SRC / "ai" / "mcpprotocol.h"
SERVER_CPP = SRC / "aiagentserver.cpp"
PROTOCOL_TEST = PROJECT_ROOT / "tests" / "test_mcp_protocol.cpp"
SRC_CMAKE = SRC / "CMakeLists.txt"
WINDOWS_CI = PROJECT_ROOT / ".github" / "workflows" / "build-windows-shotcut-ai.yml"
BUNDLE = SCRIPTS / "bundle-windows-msys2.sh"
MODELS_QML = SRC / "qml" / "extensions" / "whispermodel.qml"
DOCS_MCP = PROJECT_ROOT / "docs" / "ai-mcp.md"
DOCS_ANALYSIS = PROJECT_ROOT / "docs" / "ai-analysis.md"
DOCS_BUILD = PROJECT_ROOT / "docs" / "build-windows.md"
ROADMAP = PROJECT_ROOT / "docs" / "ROADMAP_SHOTCUT_AI.md"

ANALYSIS_TOOLS = ["check_setup", "probe_media", "describe_clip", "detect_scenes",
                  "contact_sheet", "analyze_audio", "transcribe", "analyze_folder",
                  "download_model", "get_jobs", "cancel_job"]


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def block(source, start):
    """Return the brace block that follows the first occurrence of `start`."""
    begin = source.index("{", source.index(start))
    depth = 0
    for index in range(begin, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[begin:index + 1]
    raise ValueError(f"Unbalanced block after {start}")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = load(ANALYSIS, "shotcut_analysis_under_test")


def click_track(bpm, seconds=30, rate=8000, hats=True, seed=7):
    """Kick drum on every beat and noise hi-hat on every half beat, as 16-bit samples."""
    generator = random.Random(seed)
    samples = [0.0] * (seconds * rate)
    beat = 60.0 / bpm
    t = 0.0
    while t < seconds:
        start = int(t * rate)
        for i in range(min(1600, len(samples) - start)):
            samples[start + i] += 0.8 * math.sin(2 * math.pi * 55 * i / rate) * math.exp(-i / 400.0)
        t += beat
    if hats:
        t = 0.0
        while t < seconds:
            start = int(t * rate)
            for i in range(min(400, len(samples) - start)):
                samples[start + i] += 0.15 * (generator.random() * 2 - 1) * math.exp(-i / 60.0)
            t += beat / 2
    return array.array("h", (int(max(-1.0, min(1.0, v)) * 32000) for v in samples))


class StdioServer:
    """The analysis server as a subprocess, like an MCP client starts it."""

    def __init__(self, environment):
        self.process = subprocess.Popen([sys.executable, str(ANALYSIS)], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        env=environment, text=True, encoding="utf-8")
        self.next_id = 0
        self.notifications = []

    def request(self, method, params=None):
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            message["params"] = params
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise AssertionError("the server stopped: " + self.process.stderr.read())
            reply = json.loads(line)
            if reply.get("id") == self.next_id:
                return reply
            self.notifications.append(reply)

    def tool(self, name, arguments=None, meta=None):
        params = {"name": name, "arguments": arguments or {}}
        if meta:
            params["_meta"] = meta
        result = self.request("tools/call", params)["result"]
        texts = [block["text"] for block in result["content"] if block["type"] == "text"]
        images = [block for block in result["content"] if block["type"] == "image"]
        return result["isError"], texts, images

    def data(self, name, arguments=None):
        is_error, texts, _ = self.tool(name, arguments)
        if is_error:
            raise AssertionError("%s failed: %s" % (name, texts))
        return json.loads(texts[-1])

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=20)
        self.process.stdout.close()
        self.process.stderr.close()


class TestPhase9AnalysisServer(unittest.TestCase):
    """A1-A5: the media analysis server."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="phase9-")
        root = Path(cls.temporary.name)
        cls.media = root / "media"
        cls.media.mkdir()
        for name in ("clip.mp4", "voice.wav", "photo.png"):
            (cls.media / name).write_bytes(b"not really media")
        cls.models = root / "models"
        cls.models.mkdir()
        (cls.models / "ggml-base.bin").write_bytes(b"model")
        cls.environment = dict(os.environ, SHOTCUT_FFMPEG=str(FAKE_FFMPEG),
                               SHOTCUT_FFPROBE=str(FAKE_FFMPEG), SHOTCUT_WHISPER=str(FAKE_WHISPER),
                               SHOTCUT_WHISPER_MODELS=str(cls.models),
                               SHOTCUT_ANALYSIS_CACHE=str(root / "cache"))
        cls.environment.pop("SHOTCUT_WHISPER_MODEL", None)
        cls.server = StdioServer(cls.environment)
        cls.server.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                          "clientInfo": {"name": "phase9", "version": "1"}})

    @classmethod
    def tearDownClass(cls):
        cls.server.close()
        cls.temporary.cleanup()

    # A1 -----------------------------------------------------------------
    def test_a1_probe_is_compact_and_right(self):
        rotated = {"streams": [{"codec_type": "video", "codec_name": "hevc", "width": 3840,
                                "height": 2160, "avg_frame_rate": "30000/1001",
                                "side_data_list": [{"rotation": -90}],
                                "disposition": {"attached_pic": 0}},
                               {"codec_type": "video", "codec_name": "mjpeg",
                                "disposition": {"attached_pic": 1}},
                               {"codec_type": "audio", "codec_name": "aac",
                                "sample_rate": "48000", "channels": 2,
                                "tags": {"language": "und"}}],
                   "format": {"format_name": "mov,mp4", "duration": "12.5", "size": "1048576"}}
        info = analysis.parse_probe(rotated, Path("phone.mp4"))
        self.assertEqual(info["type"], "video")
        # A phone video recorded upright: rotated 270, shown 2160x3840 (9:16).
        self.assertEqual((info["video"]["width"], info["video"]["height"]), (2160, 3840))
        self.assertEqual(info["video"]["aspect"], "9:16")
        self.assertEqual(info["video"]["rotation"], 270)
        self.assertEqual(info["video"]["fps"], 29.97)
        self.assertEqual(info["duration"], 12.5)
        self.assertNotIn("language", info["audio"][0])
        image = analysis.parse_probe({"streams": [{"codec_type": "video", "codec_name": "png",
                                                   "width": 800, "height": 600}],
                                      "format": {"format_name": "png_pipe"}}, Path("a.png"))
        self.assertEqual(image["type"], "image")
        self.assertNotIn("duration", image)
        sound = analysis.parse_probe({"streams": [{"codec_type": "audio", "codec_name": "mp3",
                                                   "sample_rate": "44100", "channels": 2}],
                                      "format": {"duration": "180.2"}}, Path("a.mp3"))
        self.assertEqual((sound["type"], sound["duration"]), ("audio", 180.2))

    def test_a1_scene_cuts(self):
        lines = []
        for frame in range(100):
            lines += ["frame:%d pts:%d pts_time:%g" % (frame, frame, frame / 25.0),
                      "lavfi.scene_score=%f" % (0.9 if frame in (25, 27, 60) else 0.02)]
        scores = analysis.parse_scene_scores(lines)
        self.assertEqual(len(scores), 100)
        # 1.0 and 1.08 s are closer than min_length: the stronger one stays.
        cuts = analysis.pick_cuts(scores, 0.3, 0.4)
        self.assertEqual([round(t, 2) for t, _ in cuts], [1.0, 2.4])
        result = analysis.scenes_result(Path("v.mp4"), {"duration": 4.0}, scores, 0.3, 0.4)
        self.assertEqual([(s["start"], s["end"]) for s in result["scenes"]],
                         [(0.0, 1.0), (1.0, 2.4), (2.4, 4.0)])
        self.assertEqual(analysis.pick_cuts(scores, 0.95, 0.4), [])

    def test_a1_loudness_and_silences(self):
        summary = ("[Parsed_ebur128_1 @ 0x1] Summary:\n\n  Integrated loudness:\n"
                   "    I:         -23.4 LUFS\n    Threshold: -33.6 LUFS\n\n  Loudness range:\n"
                   "    LRA:         6.1 LU\n\n  True peak:\n    Peak:       -0.4 dBFS\n")
        self.assertEqual(analysis.parse_loudness(summary),
                         {"integrated_lufs": -23.4, "range_lu": 6.1, "true_peak_dbfs": -0.4})
        self.assertEqual(analysis.parse_loudness("Summary:\n I: -inf LUFS\n Peak: -inf dBFS"),
                         {"integrated_lufs": None, "true_peak_dbfs": None})
        text = ("silence_start: 0\nsilence_end: 1.5 | silence_duration: 1.5\n"
                "silence_start: 9.25\n")
        self.assertEqual(analysis.parse_silences(text, 10.0),
                         [{"start": 0.0, "end": 1.5, "duration": 1.5},
                          {"start": 9.25, "end": 10.0, "duration": 0.75}])

    def test_a1_whisper_words_and_phrases(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "m.bin"
            audio = Path(folder) / "a.wav"
            model.write_bytes(b"m")
            audio.write_bytes(b"a")
            prefix = str(Path(folder) / "out")
            subprocess.run([sys.executable, str(FAKE_WHISPER), "-m", str(model), "-f",
                            str(audio), "-ojf", "-of", prefix], check=True, capture_output=True)
            data = json.loads(Path(prefix + ".json").read_text(encoding="utf-8"))
        result = analysis.parse_whisper(data)
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["segments"][0]["text"][:21], "And so my fellow Amer")
        words = result["words"]
        self.assertEqual([w[2] for w in words[:6]],
                         ["And", "so", "my", "fellow", "Americans,", "ask"])
        # "Americ" + "ans" + "," make one word from the first to the last token.
        self.assertEqual(words[4][:2], [1.5, 2.2])
        self.assertTrue(all(w[1] >= w[0] for w in words))
        # Special tokens ([_BEG_], [_TT_...]) are not words.
        self.assertFalse(any(w[2].startswith("[_") for w in words))
        # A token without times takes the time before it.
        loose = analysis.words_from_tokens([{"offsets": {"from": 1000, "to": 2000},
                                             "tokens": [{"text": " hola", "offsets":
                                                         {"from": 1000, "to": 1400}},
                                                        {"text": " mundo", "p": 0.5}]}])
        self.assertEqual(loose[1][:3], [1.4, 1.4, "mundo"])
        view = analysis.transcript_view(dict(result, path="x"), 3.0, None, True, 3)
        self.assertEqual([s["start"] for s in view["segments"]], [0.0, 3.9])
        self.assertEqual(len(view["words"]), 3)
        self.assertIn("words_truncated", view)
        self.assertNotIn("words", analysis.transcript_view(result, None, None, False, 10))

    # A2 -----------------------------------------------------------------
    def test_a2_tempo_and_beats(self):
        # 70 BPM with hi-hats on every half beat is easily taken for 140 BPM.
        for bpm in (120.0, 96.0, 70.0):
            samples = click_track(bpm)
            started = time.time()
            rhythm = analysis.rhythm(samples, 8000)
            elapsed = time.time() - started
            self.assertAlmostEqual(rhythm["bpm"], bpm, delta=2.0)
            period = 60.0 / bpm
            offsets = [abs(t - round(t / period) * period) for t in rhythm["beats"]]
            self.assertLess(statistics.median(offsets), 0.04)
            self.assertGreater(len(rhythm["beats"]), 30 / period - 3)
            self.assertLess(elapsed, 20)
        # Silence has no tempo.
        quiet = analysis.rhythm(array.array("h", [0] * 8000 * 5), 8000)
        self.assertTrue(quiet["bpm"] is None or quiet["confidence"] < 0.3)

    # A3 -----------------------------------------------------------------
    def test_a3_protocol_and_tools(self):
        reply = self.server.request("initialize", {"protocolVersion": "1999-01-01"})
        self.assertEqual(reply["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(reply["result"]["serverInfo"]["name"], "shotcut-analysis")
        self.assertIn("contact_sheet", reply["result"]["instructions"])
        tools = self.server.request("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ANALYSIS_TOOLS)
        for tool in tools:
            self.assertFalse(tool["inputSchema"]["additionalProperties"], tool["name"])
            self.assertTrue(tool["title"] and tool["description"], tool["name"])
            writes = tool["name"] in ("download_model", "cancel_job")
            self.assertEqual(tool["annotations"]["readOnlyHint"], not writes, tool["name"])
        self.assertEqual(self.server.request("ping")["result"], {})
        self.assertEqual(self.server.request("prompts/list")["result"], {"prompts": []})
        self.assertEqual(self.server.request("nope")["error"]["code"], -32601)
        self.assertEqual(self.server.request("tools/call", {"name": "nope"})["error"]["code"],
                         -32602)

    def test_a3_clear_errors(self):
        is_error, texts, _ = self.server.tool("probe_media",
                                              {"path": str(self.media / "missing.mp4")})
        self.assertTrue(is_error)
        self.assertIn("File not found", texts[0])
        is_error, texts, _ = self.server.tool("detect_scenes", {"path": "x", "treshold": 1})
        self.assertIn('Unknown argument "treshold"', texts[0])
        is_error, texts, _ = self.server.tool("contact_sheet", {"path": "x", "count": 100})
        self.assertIn('"count" must be at most 48', texts[0])
        is_error, texts, _ = self.server.tool("contact_sheet", {"path": "x", "count": "a"})
        self.assertIn('"count" must be integer', texts[0])
        is_error, texts, _ = self.server.tool("download_model", {"name": "gigantic"})
        self.assertTrue(is_error)
        self.assertIn("small-q5_1", texts[0])
        is_error, texts, _ = self.server.tool("contact_sheet",
                                              {"path": str(self.media / "voice.wav")})
        self.assertIn("has no picture", texts[0])

    def test_a3_media_tools_end_to_end(self):
        clip, voice = str(self.media / "clip.mp4"), str(self.media / "voice.wav")
        info = self.server.data("probe_media", {"path": clip})
        self.assertEqual((info["type"], info["video"]["width"], info["duration"]),
                         ("video", 1920, 10.0))
        scenes = self.server.data("detect_scenes", {"path": clip})
        self.assertEqual([cut["time"] for cut in scenes["cuts"]], [2.0, 4.4])
        audio = self.server.data("analyze_audio", {"path": voice, "end": 4})
        self.assertEqual(audio["loudness"]["integrated_lufs"], -16.2)
        self.assertEqual([s["start"] for s in audio["silences"]], [2.0])
        self.assertAlmostEqual(audio["tempo"]["bpm"], 120.0, delta=2.0)
        self.assertTrue(all(t <= 4 for t in audio["tempo"]["beats"]))
        is_error, texts, images = self.server.tool("contact_sheet", {"path": clip, "count": 5})
        self.assertFalse(is_error, texts)
        self.assertEqual(images[0]["mimeType"], "image/jpeg")
        sheet = json.loads(texts[0])
        self.assertEqual([f["time"] for f in sheet["frames"]], [1.0, 3.0, 5.0, 7.0, 9.0])
        self.assertEqual(sheet["columns"] * sheet["rows"] >= 5, True)
        summary = self.server.data("describe_clip", {"path": clip})
        self.assertEqual(summary["scenes"]["count"], 3)
        self.assertEqual(summary["audio_analysis"]["silences"], 2)
        index = self.server.data("analyze_folder", {"path": str(self.media)})
        self.assertEqual(index["types"], {"video": 1, "audio": 1, "image": 1})

    def test_a3_transcribe_with_gpu_fallback_and_srt(self):
        environment = dict(self.environment, FAKE_WHISPER_NEEDS_NO_GPU="1")
        with tempfile.TemporaryDirectory() as cache:
            environment["SHOTCUT_ANALYSIS_CACHE"] = cache
            runs = Path(cache) / "whisper-runs.txt"
            environment["FAKE_WHISPER_LOG"] = str(runs)
            server = StdioServer(environment)
            try:
                server.request("initialize", {"protocolVersion": "2025-06-18"})
                result = server.data("transcribe", {"path": str(self.media / "voice.wav"),
                                                    "words": True})
                self.assertEqual(result["model"], "ggml-base.bin")
                self.assertEqual(result["word_count"], 22)
                self.assertEqual(result["words"][4][2], "Americans,")
                srt = Path(result["srt"]).read_text(encoding="utf-8")
                self.assertIn("00:00:03,900 --> 00:00:11,000", srt)
                self.assertIn("ask what you can do for your country.", srt)
                # The GPU failed, so it ran again without it (-ng).
                self.assertEqual(runs.read_text(encoding="utf-8").split(), ["gpu", "no-gpu"])
                # Cached: the second call does not run whisper-cli again.
                again = server.data("transcribe", {"path": str(self.media / "voice.wav"),
                                                   "start": 5})
                self.assertEqual(len(again["segments"]), 1)
                self.assertNotIn("words", again)
                self.assertEqual(len(runs.read_text(encoding="utf-8").split()), 2)
            finally:
                server.close()

    def test_a3_jobs_and_waiting(self):
        job = analysis.JOBS.start("test", "t", ("test-wait",),
                                  lambda job: time.sleep(0.6) or {"done": True})
        # The same work while it runs is the same job.
        self.assertIs(analysis.JOBS.start("test", "t", ("test-wait",), lambda job: {}), job)
        status = analysis.wait_for(job, {"wait": 0}, None)
        self.assertEqual(status["job"], job.id)
        self.assertIn("get_jobs", status["hint"])
        self.assertEqual(analysis.wait_for(job, {"wait": 5}, None), {"done": True})

        def slow(job):
            for _ in range(100):
                job.update(0.1)
                time.sleep(0.05)
            return {}

        cancelled = analysis.JOBS.start("test", "t", ("test-cancel",), slow)
        cancelled.cancelled.set()
        cancelled.done.wait(5)
        self.assertEqual(cancelled.status, "cancelled")
        reports = []
        progressing = analysis.JOBS.start("test", "t", ("test-progress",), slow)
        analysis.wait_for(progressing, {"wait": 1.5}, reports.append)
        self.assertTrue(reports)
        progressing.cancelled.set()

    def test_a3_cache_follows_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            os.environ["SHOTCUT_ANALYSIS_CACHE"] = folder
            try:
                media = Path(folder) / "a.wav"
                media.write_bytes(b"one")
                analysis.cache_put(media, "probe", {"type": "audio"})
                analysis.cache_put(media, "transcripts", {"text": "hola"}, "base|es")
                self.assertEqual(analysis.cache_get(media, "probe"), {"type": "audio"})
                self.assertEqual(analysis.cache_get(media, "transcripts", "base|es"),
                                 {"text": "hola"})
                media.write_bytes(b"changed content")
                self.assertIsNone(analysis.cache_get(media, "probe"))
            finally:
                os.environ.pop("SHOTCUT_ANALYSIS_CACHE", None)

    def test_a3_standard_library_only(self):
        allowed = set(getattr(sys, "stdlib_module_names", ())) or {
            "array", "argparse", "ast", "base64", "hashlib", "itertools", "json", "math",
            "operator", "os", "re", "shutil", "subprocess", "sys", "tempfile", "threading",
            "time", "urllib", "pathlib", "winreg", "ctypes", "statistics", "random"}
        for script in (ANALYSIS, SC, MAKE_SAMPLES, LIVE_SMOKE):
            tree = ast.parse(read(script))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module.split(".")[0]]
                for name in names:
                    self.assertTrue(name in allowed or name == "make_samples",
                                    "%s imports %s" % (script.name, name))
        # Programs run without console windows on Windows and are killed when cancelled.
        source = read(ANALYSIS)
        self.assertIn("creationflags=NO_WINDOW", source)
        self.assertIn("process.kill()", source)

    # A4 -----------------------------------------------------------------
    def test_a4_whisper_models(self):
        models = analysis.known_models()
        names = [model["name"] for model in models]
        self.assertGreaterEqual(len(models), 18)
        for name in ("tiny-q5_1", "base", "small-q5_1", "large-v3"):
            self.assertIn(name, names)
        # The same files and URLs as Shotcut's Speech to Text.
        qml = read(MODELS_QML)
        for model in models:
            self.assertIn('file: "%s"' % model["file"], qml)
            self.assertIn(model["url"], qml)
        self.assertTrue(str(analysis.app_data_dir()).endswith(os.path.join("Meltytech",
                                                                           "Shotcut")))
        self.assertEqual(analysis.models_dir().name, "whispermodel")
        with tempfile.TemporaryDirectory() as folder:
            saved = {key: os.environ.get(key) for key in ("SHOTCUT_WHISPER_MODELS",
                                                          "SHOTCUT_WHISPER_MODEL")}
            os.environ["SHOTCUT_WHISPER_MODELS"] = folder
            os.environ.pop("SHOTCUT_WHISPER_MODEL", None)
            original = analysis.shotcut_setting
            analysis.shotcut_setting = lambda group, key: None
            try:
                with self.assertRaises(analysis.ToolError) as context:
                    analysis.resolve_model(None)
                self.assertIn("download_model", str(context.exception))
                for name in ("ggml-tiny.bin", "ggml-small.en.bin", "ggml-small-q5_1.bin"):
                    (Path(folder) / name).write_bytes(b"m")
                # The best multilingual model up to small, not the English-only one.
                self.assertEqual(Path(analysis.default_model()).name, "ggml-small-q5_1.bin")
                self.assertEqual(Path(analysis.resolve_model("tiny")).name, "ggml-tiny.bin")
                with self.assertRaises(analysis.ToolError) as context:
                    analysis.resolve_model("medium")
                self.assertIn("download_model", str(context.exception))
            finally:
                analysis.shotcut_setting = original
                for key, value in saved.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    # A5 -----------------------------------------------------------------
    def test_a5_installed_and_bundled(self):
        cmake = read(SRC_CMAKE)
        self.assertEqual(cmake.count("${CMAKE_SOURCE_DIR}/scripts/shotcut_analysis.py"), 3)
        # Installed next to the bridge, so it finds bin/ffmpeg the same way.
        self.assertIn('HERE.parent.parent.parent / "bin"', read(ANALYSIS))
        bundle = read(BUNDLE)
        self.assertIn('cp -v "$PREFIX/bin/whisper-cli.exe" "$DIST/bin/"', bundle)
        self.assertIn("*ggml-cpu*.dll", bundle)
        self.assertIn("*ggml-vulkan*.dll", bundle)
        self.assertLess(bundle.index("whisper-cli.exe"), bundle.index('echo "== DLLs"'))
        ci = read(WINDOWS_CI)
        self.assertIn("mingw-w64-ucrt-x86_64-whisper.cpp", ci)
        self.assertIn("./whisper-cli.exe --help", ci)
        self.assertIn("tests\\live_analysis_smoke.py --server "
                      "dist\\Shotcut-AI\\share\\shotcut\\mcp\\shotcut_analysis.py "
                      "--download-model tiny-q5_1 --speech jfk.wav", ci)
        self.assertIn("taskkill /PID $env:SHOTCUT_PID /T /F", ci)


class TestPhase9ApplicationFixes(unittest.TestCase):
    """F1-F4: the problems found in Fox's first tests."""

    @classmethod
    def setUpClass(cls):
        cls.tools = read(TOOLS_CPP)
        cls.protocol = read(PROTOCOL_CPP)

    # F1 -----------------------------------------------------------------
    def test_f1_data_is_sent_once(self):
        to_json = block(self.protocol, "QJsonObject ToolResult::toJson() const")
        self.assertNotIn('["structuredContent"]', to_json)
        self.assertIn("QJsonDocument::Compact", to_json)
        self.assertIn('QVERIFY(!result.contains("structuredContent"));', read(PROTOCOL_TEST))

    def test_f1_media_ids_and_table(self):
        clip = block(self.tools, "QJsonObject clipJson(")
        self.assertIn('clip["media"] = mediaRef(resource);', clip)
        self.assertNotIn('"resource"', clip)
        self.assertIn('if (full)', clip)
        for name in ("QJsonObject playlistItemJson(", "QJsonObject producerJson("):
            self.assertNotIn('"resource"', block(self.tools, name))
            self.assertIn("mediaRef(resource)", block(self.tools, name))
        run = block(self.tools, "Mcp::ToolResult AiTools::run(")
        self.assertIn('result.data.insert("media", media);', run)
        ref = block(self.tools, "QString mediaRef(")
        self.assertIn('QStringLiteral("m%1").arg(ids.size() + 1)', ref)
        # The same file keeps its id; tools that add clips take it back.
        self.assertIn('arguments.value("media").toString()', block(self.tools, "bool sourceXml("))
        self.assertEqual(self.tools.count('"media": {"type": "string",'), 2)
        timeline = self.tools[self.tools.index('add("get_timeline"'):
                              self.tools.index('add("get_playlist"')]
        self.assertIn('"detail": {"type": "string", "enum": ["compact", "full"]', timeline)
        self.assertIn('"track": {"type": ["integer", "string"]', timeline)

    # F2 -----------------------------------------------------------------
    def test_f2_profile_from_its_values(self):
        profile = block(self.tools, "QJsonObject profileJson()")
        for key in ('"aspect"', '"video_mode"', '"adapts_to_first_clip"', '"progressive"'):
            self.assertIn(key, profile)
        self.assertIn('QStringLiteral("%1x%2, %3 fps, %4")', profile)
        self.assertIn("Settings.playerProfile().isEmpty()", profile)
        self.assertIn("!profile.is_explicit()", profile)
        state = block(self.tools, "QJsonObject stateJson()")
        self.assertIn('{"profile", profileJson()}', state)
        self.assertNotIn("description()", state)

    # F3 -----------------------------------------------------------------
    def test_f3_store_app_files(self):
        self.assertIn("QString unvirtualizedPath(const QString &path,", read(PROTOCOL_H))
        unvirtualized = block(self.protocol, "QString unvirtualizedPath(")
        self.assertIn('"/LocalCache/"', unvirtualized)
        self.assertIn('QLatin1String("Claude")', unvirtualized)
        self.assertIn("void findsFilesOfStoreApps()", read(PROTOCOL_TEST))
        local = block(self.tools, "QString localPath(")
        self.assertIn("#ifdef Q_OS_WIN", local)
        self.assertIn('qEnvironmentVariable("LOCALAPPDATA")', local)
        # Every tool that opens a file looks for the private copy.
        self.assertEqual(self.tools.count("localPath("), 5)
        self.assertIn("Microsoft Store", block(self.tools, "QString fileNotFound("))
        self.assertEqual(self.tools.count('QStringLiteral("File not found: %1")'), 1)

    # F4 -----------------------------------------------------------------
    def test_f4_client_configuration_and_watchdog(self):
        configuration = block(self.protocol, "QString clientConfiguration(")
        self.assertIn("--scope user", configuration)
        self.assertIn('servers["shotcut-analysis"]', configuration)
        self.assertIn('"local"', configuration)
        server = read(SERVER_CPP)
        self.assertIn("shotcut/mcp/shotcut_analysis.py", server)
        self.assertIn("analysisPath(), python", server)
        # The second shotcut.exe: the startup watchdog of Shotcut.
        main = read(SRC / "main.cpp")
        self.assertIn("Run as a parent process to check if the child crashes on startup", main)
        self.assertIn("watchdog", read(DOCS_MCP))


class TestPhase9ToolsAndDocs(unittest.TestCase):
    """D1: sc.py, samples, guides and roadmap."""

    def test_d1_sc_command_line(self):
        sc = load(SC, "sc_under_test")
        self.assertEqual(sc.parse_arguments(["track=V1", "clip=0", "position=3.5",
                                             'parameters={"level": 1.2}', "ripple=false"]),
                         {"track": "V1", "clip": 0, "position": 3.5,
                          "parameters": {"level": 1.2}, "ripple": False})
        with self.assertRaises(SystemExit):
            sc.parse_arguments(["position"])
        with tempfile.TemporaryDirectory() as folder:
            result = {"content": [{"type": "text", "text": '{"ok": true}'},
                                  {"type": "image", "data": "aGVsbG8=", "mimeType": "image/jpeg"}],
                      "isError": False}
            self.assertEqual(sc.show(result, folder, False), 0)
            saved = list(Path(folder).glob("image-*.jpg"))
            self.assertEqual(saved[0].read_bytes(), b"hello")
        # The analysis server through sc.py, with no Shotcut AI running.
        output = subprocess.run([sys.executable, str(SC), "--analysis", "tools"],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(output.returncode, 0, output.stderr)
        for name in ANALYSIS_TOOLS:
            self.assertIn(name, output.stdout)

    def test_d1_samples_have_known_contents(self):
        samples = load(MAKE_SAMPLES, "make_samples_under_test")
        # Cuts on whole frames at 25 fps, so a match within 2 frames is meaningful.
        for cut in samples.CUTS:
            self.assertAlmostEqual(cut * 25, round(cut * 25))
        self.assertEqual(samples.BPM, 120.0)
        source = read(MAKE_SAMPLES)
        self.assertIn("lt(t,2)+gte(t,3)*lt(t,5)+gte(t,6.5)", source)
        self.assertIn("samples.json", source)
        smoke = read(LIVE_SMOKE)
        for check in ("2 * frame", "<= 0.1", "<= 2", "abs(difference - 10.0) <= 1.0"):
            self.assertIn(check, smoke)

    def test_d1_guides(self):
        docs = read(DOCS_ANALYSIS)
        documented = set(re.findall(r"^\| `([a-z_]+)` \|", docs, re.M))
        self.assertEqual(documented, set(ANALYSIS_TOOLS))
        for client in ("Claude Code", "Claude Desktop", "OpenCode", "Antigravity"):
            self.assertIn(client, docs)
        self.assertIn("shotcut_analysis.py", docs)
        mcp = read(DOCS_MCP)
        self.assertIn('"media": "m1"', mcp)
        self.assertIn("claude mcp add --scope user --transport http shotcut-ai", mcp)
        self.assertIn("ai-analysis.md", mcp)
        build = read(DOCS_BUILD)
        for package in ("mingw-w64-ucrt-x86_64-mlt", "mingw-w64-ucrt-x86_64-whisper.cpp",
                        "bundle-windows-msys2.sh", "-DWINDOWS_DEPLOY=OFF"):
            self.assertIn(package, build)
            if package.startswith("mingw"):
                self.assertIn(package, read(WINDOWS_CI))

    def test_d1_roadmap(self):
        roadmap = read(ROADMAP)
        self.assertIn("github.com/Foxlith/Shotcut-AI", roadmap)
        for task in ("0.1", "0.2", "0.4", "0.5", "1.1", "1.2", "1.3", "1.4", "1.6", "1.7",
                     "1.8"):
            self.assertRegex(roadmap, r"- \[x\] \*\*%s\*\*" % re.escape(task))
        # Real material and the timing on Fox's PC stay open until Fox checks them.
        for task in ("0.3", "1.5"):
            self.assertRegex(roadmap, r"- \[ \] \*\*%s\*\*" % re.escape(task))
        self.assertIn("Entrega 1", roadmap)
        self.assertIn("muestras/", read(PROJECT_ROOT / ".gitignore"))


if __name__ == "__main__":
    unittest.main()
