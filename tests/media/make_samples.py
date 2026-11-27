#!/usr/bin/env python3
"""
make_samples.py

Makes small media files with known contents for the media analysis tests
(tests/live_analysis_smoke.py) and writes what is in them to samples.json:

    python tests/media/make_samples.py OUTPUT_FOLDER [--ffmpeg PATH]

- scenes.mp4   8 s video (640x360, 25 fps) with cuts at 2.0, 4.4 and 6.0 s, and a tone
- silences.wav tone with silences from 2.0 to 3.0 s and from 5.0 to 6.5 s
- beat_120.wav 30 s of kick drum on every beat and hi-hat on every half beat, 120 BPM
- loud.wav     1 kHz tone; quiet.wav: the same 10 dB lower
- still.png    an image

Only ffmpeg is needed (the one in the bin folder of Shotcut AI works). Real material,
such as the samples/ folder of the roadmap, stays out of git.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

CUTS = [2.0, 4.4, 6.0]
SILENCES = [[2.0, 3.0], [5.0, 6.5]]
BPM = 120.0


def run(ffmpeg, *arguments):
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"] + list(arguments)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise SystemExit("ffmpeg failed: %s\n%s" % (" ".join(command),
                                                     result.stderr.decode("utf-8", "replace")))


def make(folder, ffmpeg):
    os.makedirs(folder, exist_ok=True)
    path = lambda name: os.path.join(folder, name)  # noqa: E731

    # Four shots that look nothing alike, cut at known frames (25 fps).
    shots = [("testsrc2=size=640x360:rate=25", 2.0), ("color=c=0xC03020:size=640x360:rate=25",
                                                      2.4),
             ("smptebars=size=640x360:rate=25", 1.6), ("mandelbrot=size=640x360:rate=25", 2.0)]
    arguments = []
    for source, seconds in shots:
        arguments += ["-f", "lavfi", "-t", str(seconds), "-i", source]
    arguments += ["-f", "lavfi", "-t", "8", "-i", "sine=frequency=440:sample_rate=48000"]
    arguments += ["-filter_complex",
                  "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0,format=yuv420p[v]",
                  "-map", "[v]", "-map", "4:a", "-c:v", "libx264", "-preset", "veryfast",
                  "-g", "25", "-c:a", "aac", "-shortest", path("scenes.mp4")]
    run(ffmpeg, *arguments)

    run(ffmpeg, "-f", "lavfi", "-i",
        "aevalsrc='0.3*sin(2*PI*440*t)*(lt(t,2)+gte(t,3)*lt(t,5)+gte(t,6.5))':"
        "s=48000:d=8", path("silences.wav"))

    # Kick on the beat (every 0.5 s) and hi-hat on every half beat.
    run(ffmpeg, "-f", "lavfi", "-i",
        "aevalsrc='0.8*sin(2*PI*55*t)*exp(-25*mod(t,0.5))"
        "+0.15*(random(0)*2-1)*exp(-120*mod(t,0.25))':s=44100:d=30", path("beat_120.wav"))

    run(ffmpeg, "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=5",
        "-af", "volume=-6dB", "-ac", "2", path("loud.wav"))
    run(ffmpeg, "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=5",
        "-af", "volume=-16dB", "-ac", "2", path("quiet.wav"))

    run(ffmpeg, "-f", "lavfi", "-i", "testsrc2=size=800x600", "-frames:v", "1",
        path("still.png"))

    manifest = {
        "scenes.mp4": {"type": "video", "duration": 8.0, "fps": 25, "cuts": CUTS,
                       "width": 640, "height": 360},
        "silences.wav": {"type": "audio", "duration": 8.0, "silences": SILENCES},
        "beat_120.wav": {"type": "audio", "duration": 30.0, "bpm": BPM},
        "loud.wav": {"type": "audio", "louder_than": "quiet.wav", "difference_db": 10.0},
        "quiet.wav": {"type": "audio"},
        "still.png": {"type": "image", "width": 800, "height": 600},
    }
    with open(path("samples.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder")
    parser.add_argument("--ffmpeg", default=os.environ.get("SHOTCUT_FFMPEG")
                        or shutil.which("ffmpeg"))
    options = parser.parse_args()
    if not options.ffmpeg:
        raise SystemExit("ffmpeg not found: pass --ffmpeg")
    manifest = make(options.folder, options.ffmpeg)
    print("Made %d samples in %s" % (len(manifest), options.folder))
    return 0


if __name__ == "__main__":
    sys.exit(main())
