#!/usr/bin/env python3
"""A stand-in for whisper-cli in the tests: it answers like whisper-cli -ojf with a
fixed transcript (the JFK sample of whisper.cpp) without a model.

FAKE_WHISPER_NEEDS_NO_GPU=1 makes it fail unless -ng is passed, like a broken GPU.
"""

import json
import os
import sys


def main(arguments):
    values = {}
    flags = set()
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in ("-m", "-f", "-l", "-of", "-t"):
            values[argument] = arguments[index + 1]
            index += 2
            continue
        flags.add(argument)
        index += 1
    if os.environ.get("FAKE_WHISPER_NEEDS_NO_GPU") and "-ng" not in flags:
        print("ggml_vulkan: no device found", file=sys.stderr)
        return 1
    for name in ("-m", "-f", "-of"):
        if name not in values:
            print("missing %s" % name, file=sys.stderr)
            return 2
    if not os.path.isfile(values["-m"]) or not os.path.isfile(values["-f"]):
        print("cannot open the model or the audio", file=sys.stderr)
        return 3
    for progress in (0, 50, 100):
        print("whisper_print_progress_callback: progress = %3d%%" % progress, file=sys.stderr)

    def token(text, start, end, p=0.9):
        return {"text": text, "timestamps": {}, "offsets": {"from": start, "to": end},
                "id": 1, "p": p, "t_dtw": -1}

    segments = [
        {"offsets": {"from": 0, "to": 3900},
         "text": " And so my fellow Americans, ask not what your country can do for you,",
         "tokens": [token("[_BEG_]", 0, 0), token(" And", 320, 550), token(" so", 550, 800),
                    token(" my", 800, 1100), token(" fellow", 1100, 1500),
                    token(" Americ", 1500, 1900), token("ans", 1900, 2150, 0.8),
                    token(",", 2150, 2200), token(" ask", 2600, 2900), token(" not", 2900, 3100),
                    token(" what", 3100, 3300), token(" your", 3300, 3500),
                    token(" country", 3500, 3700), token(" can", 3700, 3750),
                    token(" do", 3750, 3800), token(" for", 3800, 3850),
                    token(" you", 3850, 3900), token(",", 3900, 3900),
                    {"text": "[_TT_195]", "id": 2, "p": 0.5, "t_dtw": -1}]},
        {"offsets": {"from": 3900, "to": 11000},
         "text": " ask what you can do for your country.",
         "tokens": [token(" ask", 7900, 8300), token(" what", 8300, 8600),
                    token(" you", 8600, 8800), token(" can", 8800, 9100),
                    token(" do", 9100, 9400), token(" for", 9400, 9700),
                    token(" your", 9700, 10000), token(" country", 10000, 10800),
                    token(".", 10800, 11000)]},
    ]
    output = {"systeminfo": "fake", "model": {"type": "tiny"},
              "params": {"model": values["-m"], "language": values.get("-l", "auto"),
                         "translate": False},
              "result": {"language": "en" if values.get("-l", "auto") == "auto"
                         else values["-l"]},
              "transcription": segments}
    with open(values["-of"] + ".json", "w", encoding="utf-8") as handle:
        json.dump(output, handle)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
