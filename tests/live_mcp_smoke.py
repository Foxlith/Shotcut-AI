#!/usr/bin/env python3
"""
live_mcp_smoke.py

Live check of the AI agent server of a running Shotcut AI (Phase 8). It talks MCP over
HTTP like Claude Code or OpenCode, optionally through the stdio bridge like Claude
Desktop, and edits the open project like an AI agent would:

    python tests/live_mcp_smoke.py                      # every check, needs --media
    python tests/live_mcp_smoke.py --read-only          # no change to the project
    python tests/live_mcp_smoke.py --media clip.mp4     # edit: add, split, filter, undo
    python tests/live_mcp_smoke.py --bridge share/shotcut/mcp/shotcut_mcp_bridge.py

Only the Python standard library is needed. Exit code 0 means every check passed.
It is not part of `run_e2e_tests.py --fast` because it needs the application open.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REQUIRED_TOOLS = {
    "get_state", "get_timeline", "get_playlist", "get_frame", "list_actions", "list_filters",
    "get_clip_filters", "play", "pause", "seek", "step", "undo", "redo", "run_action",
    "open_media", "add_to_playlist", "open_project", "save_project", "append_clip",
    "insert_clip", "overwrite_clip", "split_clip", "remove_clip", "move_clip", "trim_clip",
    "set_fade", "add_track", "set_track", "select_clips", "add_filter", "set_filter_param",
    "set_filter_enabled", "remove_filter",
}


class Failure(Exception):
    pass


class HttpClient:
    def __init__(self, url):
        self.url = url
        self.next_id = 0

    def post(self, message, headers=None):
        request = urllib.request.Request(
            self.url, data=json.dumps(message).encode("utf-8"), method="POST",
            headers=dict({"Content-Type": "application/json",
                          "Accept": "application/json, text/event-stream"}, **(headers or {})))
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            return error.code, None

    def request(self, method, params=None):
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            message["params"] = params
        status, response = self.post(message)
        if status != 200 or not response:
            raise Failure("%s: HTTP %s" % (method, status))
        if "error" in response:
            raise Failure("%s: %s" % (method, response["error"]))
        return response["result"]

    def notify(self, method):
        return self.post({"jsonrpc": "2.0", "method": method})[0]


class BridgeClient:
    """The same requests through the stdio bridge, as Claude Desktop sends them."""

    def __init__(self, bridge, url):
        environment = dict(os.environ, SHOTCUT_AI_URL=url)
        self.process = subprocess.Popen([sys.executable, bridge], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, env=environment,
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
                raise Failure("The bridge stopped")
            response = json.loads(line)
            if response.get("id") == self.next_id:
                break
        if "error" in response:
            raise Failure("%s: %s" % (method, response["error"]))
        return response["result"]

    def notify(self, method):
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.process.stdin.flush()

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=10)


def tool(client, name, arguments=None, expect_error=False):
    result = client.request("tools/call", {"name": name, "arguments": arguments or {}})
    texts = [block["text"] for block in result["content"] if block["type"] == "text"]
    if result.get("isError") != expect_error:
        raise Failure("%s(%s): %s" % (name, json.dumps(arguments), texts[:1]))
    data = result.get("structuredContent")
    if data is None and texts:
        try:
            data = json.loads(texts[0])
        except ValueError:
            data = texts[0]
    return data, result


def check(condition, message):
    if not condition:
        raise Failure(message)
    print("  ok  " + message)


def handshake(client, label):
    result = client.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                           "clientInfo": {"name": "live_mcp_smoke", "version": "1"}})
    check(result["protocolVersion"] == "2025-06-18", "%s: initialize negotiates 2025-06-18" % label)
    check(result["serverInfo"]["name"] == "shotcut-ai", "%s: server is shotcut-ai" % label)
    client.notify("notifications/initialized")
    tools = {entry["name"]: entry for entry in client.request("tools/list")["tools"]}
    missing = REQUIRED_TOOLS - set(tools)
    check(not missing, "%s: tools/list has the %d tools (missing: %s)"
          % (label, len(REQUIRED_TOOLS), sorted(missing) or "none"))
    return tools


def read_only_checks(client, url):
    state, _ = tool(client, "get_state")
    check("project" in state and "player" in state and "timeline" in state, "get_state")
    timeline, _ = tool(client, "get_timeline")
    check(isinstance(timeline.get("tracks"), list), "get_timeline lists %d track(s)"
          % len(timeline["tracks"]))
    tool(client, "get_playlist")
    actions, _ = tool(client, "list_actions")
    check(actions["count"] > 50, "list_actions: %d actions" % actions["count"])
    filters, _ = tool(client, "list_filters", {"type": "video"})
    check(filters["count"] > 10, "list_filters: %d video filters" % filters["count"])
    filters, _ = tool(client, "list_filters", {"type": "audio"})
    check(filters["count"] > 5, "list_filters: %d audio filters" % filters["count"])
    tool(client, "seek", {"position": -1}, expect_error=True)
    print("  ok  invalid arguments are tool errors")
    if state["player"]["duration"]["frames"] > 0:
        frame, result = tool(client, "get_frame", {"width": 320})
        images = [block for block in result["content"] if block["type"] == "image"]
        check(images and len(base64.b64decode(images[0]["data"])) > 500,
              "get_frame returns a %dx%d image" % (frame["width"], frame["height"]))
    # Security: a web page (foreign Origin) is refused.
    status = HttpClient(url).post({"jsonrpc": "2.0", "id": 1, "method": "ping"},
                                  {"Origin": "http://evil.example"})[0]
    check(status == 403, "a foreign Origin gets HTTP 403")
    return state


def editing_checks(client, media):
    before, _ = tool(client, "get_state")
    added, _ = tool(client, "add_to_playlist", {"paths": [os.path.abspath(media)]})
    index = added["added"][-1]["index"]
    check(added["added"], "add_to_playlist adds %s" % os.path.basename(media))
    appended, _ = tool(client, "append_clip", {"playlist_index": index})
    track, clip = appended["track"], appended["clip"]
    check(clip["duration"] > 0, "append_clip adds a %.2f s clip on track %d"
          % (clip["duration"], track))
    middle = round((clip["start"] + clip["end"]) / 2, 3)
    split, _ = tool(client, "split_clip", {"track": track, "clip": clip["index"],
                                           "position": middle})
    check(len(split["clips"]) == 2, "split_clip at %.3f s makes two clips" % middle)
    filters, _ = tool(client, "list_filters", {"query": "brightness", "type": "video"})
    if filters["filters"]:
        filter_id = filters["filters"][0]["id"]
        added_filter, _ = tool(client, "add_filter", {"track": track, "clip": clip["index"],
                                                      "filter_id": filter_id})
        check(added_filter["filter"]["id"] == filter_id, "add_filter adds %s" % filter_id)
        tool(client, "undo")
    tool(client, "seek", {"position": middle, "target": "project"})
    tool(client, "get_frame", {"width": 320})
    state, _ = tool(client, "get_state")
    check(state["undo"]["undo"].startswith("AI: "), "the last step is named %r"
          % state["undo"]["undo"])
    for _ in range(3):
        tool(client, "undo")
    after, _ = tool(client, "get_state")
    check(after["playlist"]["items"] == before["playlist"]["items"]
          and after["timeline"]["tracks"] == before["timeline"]["tracks"],
          "undo returns the playlist and the timeline to the start")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("SHOTCUT_AI_URL",
                                                        "http://127.0.0.1:9999/mcp"))
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--media", help="A media file for the editing checks.")
    parser.add_argument("--bridge", help="Also check the stdio bridge at this path.")
    options = parser.parse_args()
    try:
        print("MCP over HTTP at %s" % options.url)
        client = HttpClient(options.url)
        handshake(client, "HTTP")
        read_only_checks(client, options.url)
        if not options.read_only:
            if not options.media:
                raise Failure("--media is needed for the editing checks (or use --read-only)")
            editing_checks(client, options.media)
        if options.bridge:
            print("MCP through the stdio bridge %s" % options.bridge)
            bridge = BridgeClient(options.bridge, options.url)
            try:
                handshake(bridge, "bridge")
                state, _ = tool(bridge, "get_state")
                check("project" in state, "bridge: get_state")
            finally:
                bridge.close()
    except (Failure, urllib.error.URLError, OSError) as error:
        print("FAILED: %s" % error)
        return 1
    print("All live MCP checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
