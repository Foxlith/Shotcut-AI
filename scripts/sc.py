#!/usr/bin/env python3
"""
sc.py: call the MCP tools of Shotcut AI from a terminal.

    python sc.py tools                                  # the tools of Shotcut AI
    python sc.py call get_state
    python sc.py call get_timeline track=V1
    python sc.py call split_clip track=V1 clip=0 position=3
    python sc.py call add_filter track=V1 clip=0 filter_id=brightness 'parameters={"level": 1.2}'
    python sc.py --analysis tools                       # the media analysis server
    python sc.py --analysis call contact_sheet path=C:/Videos/a.mp4 --images out

Arguments are name=value; a value that is valid JSON (numbers, true, false, objects,
lists) is sent as JSON, anything else as text. Images (get_frame, contact_sheet) are
saved to the --images folder instead of being printed. Only the Python standard library
is needed. Shotcut AI must be open (Settings > AI Agent (MCP)).
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


class HttpClient:
    """MCP over HTTP, like Claude Code or OpenCode."""

    def __init__(self, url):
        self.url = url
        self.next_id = 0

    def request(self, method, params=None):
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            message["params"] = params
        request = urllib.request.Request(
            self.url, data=json.dumps(message).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"})
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                reply = json.loads(response.read())
        except urllib.error.URLError as error:
            raise SystemExit("Shotcut AI does not answer at %s (%s). Open it and check "
                             "Settings > AI Agent (MCP)." % (self.url, error))
        if "error" in reply:
            raise SystemExit("%s: %s" % (method, reply["error"].get("message")))
        return reply["result"]

    def close(self):
        pass


class StdioClient:
    """MCP over standard input and output, like Claude Desktop starts a server."""

    def __init__(self, command):
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        text=True, encoding="utf-8")
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
                raise SystemExit("The server stopped.")
            reply = json.loads(line)
            if reply.get("id") == self.next_id:
                break
        if "error" in reply:
            raise SystemExit("%s: %s" % (method, reply["error"].get("message")))
        return reply["result"]

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=10)


def parse_arguments(pairs):
    arguments = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit("Arguments are name=value, not %r" % pair)
        name, value = pair.split("=", 1)
        try:
            arguments[name] = json.loads(value)
        except ValueError:
            arguments[name] = value
    return arguments


def show(result, images, raw):
    if raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("isError") else 0
    for block in result.get("content", []):
        if block.get("type") == "text":
            try:
                print(json.dumps(json.loads(block["text"]), ensure_ascii=False, indent=2))
            except ValueError:
                print(block["text"])
        elif block.get("type") == "image":
            folder = images or "."
            os.makedirs(folder, exist_ok=True)
            extension = ".png" if block.get("mimeType") == "image/png" else ".jpg"
            path = os.path.join(folder, "image-%s%s" % (time.strftime("%Y%m%d-%H%M%S"), extension))
            with open(path, "wb") as handle:
                handle.write(base64.b64decode(block["data"]))
            print("(image saved to %s)" % path)
    if result.get("isError"):
        print("(the tool reported an error)", file=sys.stderr)
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("SHOTCUT_AI_URL",
                                                        "http://127.0.0.1:9999/mcp"),
                        help="MCP endpoint of Shotcut AI")
    parser.add_argument("--analysis", action="store_true",
                        help="Use the media analysis server (shotcut_analysis.py) instead")
    parser.add_argument("--images", help="Folder for the images of the answers (default .)")
    parser.add_argument("--raw", action="store_true", help="Print the whole MCP answer")
    parser.add_argument("action", choices=["tools", "call"])
    parser.add_argument("tool", nargs="?")
    parser.add_argument("arguments", nargs="*", help="name=value")
    options = parser.parse_args()

    if options.analysis:
        client = StdioClient([sys.executable, os.path.join(HERE, "shotcut_analysis.py")])
    else:
        client = HttpClient(options.url)
    try:
        client.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                      "clientInfo": {"name": "sc.py", "version": "1"}})
        if options.action == "tools":
            for entry in client.request("tools/list")["tools"]:
                print("%-20s %s" % (entry["name"], entry.get("description", "").split(". ")[0]))
            return 0
        if not options.tool:
            raise SystemExit("call needs a tool name, such as get_state")
        result = client.request("tools/call", {"name": options.tool,
                                               "arguments": parse_arguments(options.arguments)})
        return show(result, options.images, options.raw)
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
