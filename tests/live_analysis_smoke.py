#!/usr/bin/env python3
"""
live_analysis_smoke.py

Live check of the media analysis server (scripts/shotcut_analysis.py, installed as
share/shotcut/mcp/shotcut_analysis.py) with the real ffmpeg, ffprobe and whisper-cli. It
makes media with known contents (tests/media/make_samples.py), talks MCP to the server
over standard input and output like Claude Desktop, and checks the answers:

    python tests/live_analysis_smoke.py
    python tests/live_analysis_smoke.py --server dist/Shotcut-AI/share/shotcut/mcp/shotcut_analysis.py
    python tests/live_analysis_smoke.py --download-model tiny-q5_1 --speech jfk.wav \\
        --expect "ask not what your country can do for you"

Scenes must be found within 2 frames, silences within 0.1 s, the tempo within 2 BPM and
the loudness difference within 1 dB. Exit code 0 means every check passed. It is not
part of run_e2e_tests.py --fast because it needs ffmpeg (the Windows build runs it with
the programs of the zip).
"""

import argparse
import base64
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests", "media"))
import make_samples  # noqa: E402

TOOLS = {"check_setup", "probe_media", "describe_clip", "detect_scenes", "contact_sheet",
         "analyze_audio", "transcribe", "analyze_folder", "download_model", "get_jobs",
         "cancel_job"}


class Failure(Exception):
    pass


def check(condition, message):
    if not condition:
        raise Failure(message)
    print("  ok  " + message)


class Server:
    def __init__(self, script, environment):
        self.process = subprocess.Popen([sys.executable, script], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, env=environment, text=True,
                                        encoding="utf-8")
        self.next_id = 0

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
                raise Failure("The server stopped")
            reply = json.loads(line)
            if reply.get("id") == self.next_id:
                break
        if "error" in reply:
            raise Failure("%s: %s" % (method, reply["error"]))
        return reply["result"]

    def tool(self, name, arguments=None, expect_error=False):
        result = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        texts = [block["text"] for block in result["content"] if block["type"] == "text"]
        if result.get("isError") != expect_error:
            raise Failure("%s(%s): %s" % (name, json.dumps(arguments), texts[:1]))
        images = [block for block in result["content"] if block["type"] == "image"]
        data = json.loads(texts[-1]) if texts and not expect_error else texts
        return data, images

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=20)


def words_of(text):
    return re.sub(r"[^a-z0-9áéíóúñü ]+", " ", text.lower()).split()


def media_checks(server, folder, manifest):
    for name, facts in manifest.items():
        info, _ = server.tool("probe_media", {"path": os.path.join(folder, name)})
        check(info["type"] == facts["type"], "probe_media: %s is %s" % (name, facts["type"]))
        if "duration" in facts:
            check(abs(info["duration"] - facts["duration"]) < 0.1,
                  "probe_media: %s lasts %.2f s" % (name, info["duration"]))
        if "width" in facts:
            check((info["video"]["width"], info["video"]["height"]) ==
                  (facts["width"], facts["height"]),
                  "probe_media: %s is %dx%d" % (name, facts["width"], facts["height"]))

    video = manifest["scenes.mp4"]
    scenes, _ = server.tool("detect_scenes", {"path": os.path.join(folder, "scenes.mp4"),
                                              "wait": 120})
    found = [cut["time"] for cut in scenes["cuts"]]
    frame = 1.0 / video["fps"]
    matched = [t for t in video["cuts"] if any(abs(t - f) <= 2 * frame + 1e-6 for f in found)]
    check(len(matched) >= 0.9 * len(video["cuts"]) and len(found) <= len(video["cuts"]) + 1,
          "detect_scenes: cuts %s for %s (within 2 frames)" % (found, video["cuts"]))

    sheet, images = server.tool("contact_sheet", {"path": os.path.join(folder, "scenes.mp4"),
                                                  "count": 8, "width": 240})
    image = base64.b64decode(images[0]["data"]) if images else b""
    check(image[:3] == b"\xff\xd8\xff" and len(sheet["frames"]) == 8,
          "contact_sheet: %d frames in a %d KB JPEG (time labels: %s)"
          % (len(sheet["frames"]), len(image) // 1024, sheet["labels"]))
    sheet, images = server.tool("contact_sheet", {"path": os.path.join(folder, "scenes.mp4"),
                                                  "scenes": True})
    check(len(sheet["frames"]) == len(video["cuts"]) + 1,
          "contact_sheet: one frame per scene (%d)" % len(sheet["frames"]))

    audio, _ = server.tool("analyze_audio", {"path": os.path.join(folder, "silences.wav"),
                                             "beats": False, "wait": 120})
    got = [[s["start"], s["end"]] for s in audio["silences"]]
    expected = manifest["silences.wav"]["silences"]
    check(len(got) == len(expected) and all(abs(a - b) <= 0.1 for pair in zip(got, expected)
                                            for a, b in zip(*pair)),
          "analyze_audio: silences %s" % got)

    levels = {}
    for name in ("loud.wav", "quiet.wav"):
        result, _ = server.tool("analyze_audio", {"path": os.path.join(folder, name),
                                                  "beats": False, "wait": 120})
        levels[name] = result["loudness"]["integrated_lufs"]
    difference = levels["loud.wav"] - levels["quiet.wav"]
    check(abs(difference - 10.0) <= 1.0,
          "analyze_audio: %.1f and %.1f LUFS, %.1f dB apart" % (levels["loud.wav"],
                                                                 levels["quiet.wav"], difference))

    started = time.time()
    rhythm, _ = server.tool("analyze_audio", {"path": os.path.join(folder, "beat_120.wav"),
                                              "wait": 120})
    tempo = rhythm["tempo"]
    bpm = manifest["beat_120.wav"]["bpm"]
    period = 60.0 / bpm
    offsets = [abs(t - round(t / period) * period) for t in tempo["beats"]]
    check(abs(tempo["bpm"] - bpm) <= 2 and statistics.median(offsets) < 0.04,
          "analyze_audio: %.1f BPM, %d beats, median offset %.0f ms (%.1f s)"
          % (tempo["bpm"], len(tempo["beats"]), statistics.median(offsets) * 1000,
             time.time() - started))

    summary, _ = server.tool("describe_clip", {"path": os.path.join(folder, "scenes.mp4"),
                                               "wait": 120})
    check(summary["scenes"]["count"] == len(video["cuts"]) + 1,
          "describe_clip: %d scenes, %s" % (summary["scenes"]["count"], summary["video"]))
    index, _ = server.tool("analyze_folder", {"path": folder, "wait": 120})
    check(index.get("files") == len(manifest), "analyze_folder: %s files, %s"
          % (index.get("files"), index.get("types")))
    server.tool("probe_media", {"path": os.path.join(folder, "missing.mp4")}, expect_error=True)
    print("  ok  a missing file is a tool error")


def speech_checks(server, speech, expected, model):
    arguments = {"path": os.path.abspath(speech), "words": True, "wait": 120}
    if model:
        arguments["model"] = model
    started = time.time()
    result, _ = server.tool("transcribe", arguments)
    if "job" in result:
        raise Failure("transcribe did not finish in 120 s: %s" % result)
    elapsed = time.time() - started
    text = " ".join(segment["text"] for segment in result["segments"])
    check(" ".join(words_of(expected)) in " ".join(words_of(text)),
          "transcribe: \"%s\" (%s, %s, %.1f s for %.1f s of audio)"
          % (text.strip()[:120], result.get("language"), result.get("model"), elapsed,
             result.get("duration") or 0))
    words = result.get("words", [])
    starts = [word[0] for word in words]
    check(words and starts == sorted(starts) and all(w[1] >= w[0] for w in words),
          "transcribe: %d words with increasing times" % len(words))
    check(os.path.isfile(result["srt"]), "transcribe: SRT written")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", default=os.path.join(ROOT, "scripts", "shotcut_analysis.py"))
    parser.add_argument("--samples", help="Folder for the samples (default: a temporary one).")
    parser.add_argument("--download-model", help="Download this Whisper model first.")
    parser.add_argument("--model", help="Model for transcribe (default: the server's choice).")
    parser.add_argument("--speech", help="A speech recording for transcribe.")
    parser.add_argument("--expect", default="", help="Words that the speech contains.")
    options = parser.parse_args()
    environment = dict(os.environ)
    temporary = tempfile.mkdtemp(prefix="shotcut-analysis-smoke-")
    # A fresh cache, so that the programs really run.
    environment["SHOTCUT_ANALYSIS_CACHE"] = os.path.join(temporary, "cache")
    folder = options.samples or os.path.join(temporary, "samples")
    try:
        print("Media analysis server %s" % options.server)
        server = Server(options.server, environment)
        try:
            init = server.request("initialize", {"protocolVersion": "2025-06-18",
                                                 "capabilities": {},
                                                 "clientInfo": {"name": "smoke", "version": "1"}})
            check(init["serverInfo"]["name"] == "shotcut-analysis",
                  "initialize: %s %s" % (init["serverInfo"]["name"], init["protocolVersion"]))
            names = {tool["name"] for tool in server.request("tools/list")["tools"]}
            check(TOOLS <= names, "tools/list has the %d tools" % len(TOOLS))
            setup, _ = server.tool("check_setup")
            check(setup["ffmpeg"]["command"] and setup["ffprobe"]["command"],
                  "check_setup: ffmpeg %s" % setup["ffmpeg"]["command"])
            print("      whisper: %s" % setup["whisper"]["command"])
            manifest = make_samples.make(folder, setup["ffmpeg"]["command"])
            media_checks(server, folder, manifest)
            if options.download_model:
                started = time.time()
                result, _ = server.tool("download_model", {"name": options.download_model,
                                                           "wait": 120})
                if "job" in result:
                    raise Failure("download_model did not finish in 120 s: %s" % result)
                check(os.path.isfile(result["path"]), "download_model: %s (%.1f s)"
                      % (result["path"], time.time() - started))
            if options.speech:
                if not setup["whisper"]["command"]:
                    raise Failure("whisper-cli was not found")
                speech_checks(server, options.speech, options.expect, options.model)
            else:
                print("  --  transcription not checked (use --speech)")
        finally:
            server.close()
    except (Failure, OSError, ValueError, KeyError) as error:
        print("FAILED: %s" % error)
        return 1
    print("All media analysis checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
