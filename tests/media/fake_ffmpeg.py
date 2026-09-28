#!/usr/bin/env python3
"""A stand-in for ffmpeg and ffprobe in the tests of the media analysis server: it answers
like the real programs for the commands that shotcut_analysis.py runs, with fixed
results, so the tests need no ffmpeg:

- ffprobe (FAKE_FFMPEG_ROLE=ffprobe or the -print_format option): a 10 s 1920x1080 25 fps
  video with stereo audio for .mp4/.mov, an 8 s mono audio file for .wav/.mp3, an
  800x600 image for .png/.jpg
- scene scores (metadata=print): cuts at 2.0 and 4.4 s
- silencedetect + ebur128: silences 2.0-3.0 s and 5.0-6.5 s, -16.2 LUFS, -1.5 dBFS
- raw audio (-f s16le): 30 s at 8 kHz with a kick every 0.5 s (120 BPM)
- a WAV file, a frame or a contact sheet: small valid files
"""

import array
import base64
import json
import math
import os
import sys

TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAgAAAQABAAD//gAQTGF2YzYwLjMxLjEwMgD/2wBDAAgKCgsKCw0NDQ0NDRAPEBAQEBAQEB"
    "AQEBASEhIVFRUSEhIQEBISFBQVFRcXFxUVFRUXFxkZGR4eHBwjIyQrKzP/xABLAAEBAAAAAAAAAAAAAAAAAAAA"
    "BgEBAAAAAAAAAAAAAAAAAAAABhABAAAAAAAAAAAAAAAAAAAAABEBAAAAAAAAAAAAAAAAAAAAAP/AABEIAAgACA"
    "MBIgACEQADEQD/2gAMAwEAAhEDEQA/AJwA4H3/2Q==")


def probe(path):
    extension = os.path.splitext(path)[1].lower()
    if extension in (".png", ".jpg", ".jpeg"):
        streams = [{"codec_type": "video", "codec_name": "png", "width": 800, "height": 600,
                    "pix_fmt": "rgb24", "disposition": {"attached_pic": 0}}]
        return {"streams": streams, "format": {"format_name": "png_pipe", "size": "61530"}}
    audio = {"codec_type": "audio", "codec_name": "pcm_s16le", "sample_rate": "48000",
             "channels": 1, "duration": "8.000000", "tags": {"language": "spa"}}
    if extension in (".wav", ".mp3", ".m4a"):
        return {"streams": [audio], "format": {"format_name": "wav", "duration": "8.000000",
                                               "size": "768078"}}
    video = {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080,
             "avg_frame_rate": "25/1", "r_frame_rate": "25/1", "nb_frames": "250",
             "pix_fmt": "yuv420p", "disposition": {"attached_pic": 0}}
    return {"streams": [video, dict(audio, codec_name="aac", channels=2, duration="10.0")],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "10.000000",
                       "size": "5242880", "tags": {"creation_time": "2026-09-27T10:00:00Z"}}}


def pcm_clicks(seconds=30, rate=8000, bpm=120.0):
    samples = array.array("h", [0]) * (seconds * rate)
    period = int(rate * 60 / bpm)
    for start in range(0, len(samples), period):
        for i in range(min(800, len(samples) - start)):
            samples[start + i] = int(20000 * math.exp(-i / 150.0) * math.sin(i * 0.2))
    if sys.byteorder == "big":
        samples.byteswap()
    return samples.tobytes()


def main(arguments):
    if os.environ.get("FAKE_FFMPEG_ROLE") == "ffprobe" or "-print_format" in arguments:
        path = arguments[-1]
        if not os.path.isfile(path):
            print("%s: No such file or directory" % path, file=sys.stderr)
            return 1
        print(json.dumps(probe(path)))
        return 0
    if "-version" in arguments:
        print("ffmpeg version 0.0-fake")
        return 0
    joined = " ".join(arguments)
    if "metadata=print" in joined:
        frame = 0
        for step in range(250):
            time_ = step / 25.0
            score = 0.8 if step in (50, 110) else 0.01
            print("frame:%d    pts:%d     pts_time:%g" % (frame, step, time_))
            print("lavfi.scene_score=%f" % score)
            frame += 1
        return 0
    if "silencedetect" in joined:
        print("out_time_us=4000000\nprogress=continue\nout_time_us=8000000\nprogress=end")
        sys.stdout.flush()
        print("[silencedetect @ 0x1] silence_start: 2\n"
              "[silencedetect @ 0x1] silence_end: 3 | silence_duration: 1\n"
              "[silencedetect @ 0x1] silence_start: 5\n"
              "[silencedetect @ 0x1] silence_end: 6.5 | silence_duration: 1.5\n"
              "[Parsed_ebur128_1 @ 0x2] Summary:\n\n  Integrated loudness:\n"
              "    I:         -16.2 LUFS\n    Threshold: -26.3 LUFS\n\n  Loudness range:\n"
              "    LRA:         3.4 LU\n    Threshold:  -36.4 LUFS\n\n  True peak:\n"
              "    Peak:       -1.5 dBFS", file=sys.stderr)
        return 0
    if "s16le" in arguments:
        sys.stdout.buffer.write(pcm_clicks())
        return 0
    output = arguments[-1]
    if output.endswith(".wav"):
        with open(output, "wb") as handle:
            handle.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                         b"\x80\x3e\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        return 0
    if output.endswith(".jpg"):
        with open(output, "wb") as handle:
            handle.write(TINY_JPEG)
        return 0
    print("fake ffmpeg: unexpected command %s" % joined, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
