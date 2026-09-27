#!/usr/bin/env python3
"""Shotcut AI MCP bridge: standard input/output <-> HTTP.

Some MCP clients, such as Claude Desktop, only start local servers that talk over
standard input and output. This bridge forwards every JSON-RPC message to the MCP
endpoint of the running Shotcut AI (http://127.0.0.1:9999/mcp, or the SHOTCUT_AI_URL
environment variable) and prints the answers, one JSON message per line.

It only needs the Python standard library (Python 3.8 or later) and it may start
before Shotcut AI: while the application is closed it answers initialize and ping
itself, lists no tools and tells the client (notifications/tools/list_changed) as
soon as the application opens.

Client configuration (Claude Desktop, Antigravity and other stdio clients):

    {"mcpServers": {"shotcut-ai": {"command": "python",
                                   "args": ["<path>/shotcut_mcp_bridge.py"]}}}
"""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

URL = os.environ.get("SHOTCUT_AI_URL", "http://127.0.0.1:9999/mcp")
# Some tools wait for the user (a dialog in Shotcut AI), so calls may take a while.
TIMEOUT = float(os.environ.get("SHOTCUT_AI_TIMEOUT", "300"))
PROTOCOL_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
NOT_RUNNING = ("Shotcut AI is not open, or its AI agent server is off "
               "(Settings > AI Agent (MCP) in Shotcut AI). Open Shotcut AI and try again.")


class Bridge:
    def __init__(self, url=URL, output=None, poll_interval=2.0):
        self.url = url
        self.output = output or sys.stdout
        self.poll_interval = poll_interval
        self.write_lock = threading.Lock()
        self.app_lock = threading.RLock()
        self.session = None
        self.protocol_version = None
        self.client_initialize = None
        self.app_initialized = False
        self.watching = False

    # -- Output -----------------------------------------------------------------------

    def write(self, message):
        with self.write_lock:
            self.output.write(json.dumps(message, separators=(",", ":"), ensure_ascii=False) + "\n")
            self.output.flush()

    # -- HTTP -------------------------------------------------------------------------

    @staticmethod
    def parse_body(body, content_type):
        if not body:
            return None
        if "text/event-stream" in content_type:
            # Server-sent events: the last data line holds the response.
            result = None
            for line in body.decode("utf-8").splitlines():
                if line.startswith("data:") and line[5:].strip():
                    result = json.loads(line[5:].strip())
            return result
        return json.loads(body)

    def post(self, message, timeout=None):
        """Sends one message; returns (HTTP status, parsed body or None).

        Raises OSError (URLError, timeout) when Shotcut AI cannot be reached.
        """
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        request = urllib.request.Request(self.url, data=json.dumps(message).encode("utf-8"),
                                         headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout or TIMEOUT) as response:
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    self.session = session
                return response.status, self.parse_body(response.read(),
                                                        response.headers.get("Content-Type", ""))
        except urllib.error.HTTPError as error:
            body = error.read()
            try:
                parsed = json.loads(body) if body else None
            except ValueError:
                parsed = None
            return error.code, parsed

    def initialize_app(self):
        """Opens a session with Shotcut AI using the initialize request of the client."""
        with self.app_lock:
            params = dict(self.client_initialize or {
                "protocolVersion": PROTOCOL_VERSIONS[0], "capabilities": {},
                "clientInfo": {"name": "shotcut-mcp-bridge", "version": "1"}})
            self.session = None
            self.protocol_version = None
            status, response = self.post({"jsonrpc": "2.0", "id": "bridge-initialize",
                                          "method": "initialize", "params": params}, timeout=5)
            if status != 200 or not isinstance(response, dict) or "result" not in response:
                raise OSError("Shotcut AI did not accept initialize (HTTP %s)" % status)
            self.protocol_version = response["result"].get("protocolVersion")
            self.post({"jsonrpc": "2.0", "method": "notifications/initialized"}, timeout=5)
            self.app_initialized = True
            return response["result"]

    # -- Messages ---------------------------------------------------------------------

    @staticmethod
    def with_list_changed(result):
        """The bridge may announce new tools later (when Shotcut AI opens)."""
        result = dict(result)
        capabilities = dict(result.get("capabilities") or {})
        tools = dict(capabilities.get("tools") or {})
        tools["listChanged"] = True
        capabilities["tools"] = tools
        result["capabilities"] = capabilities
        return result

    def local_initialize_result(self):
        requested = (self.client_initialize or {}).get("protocolVersion")
        version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return {"protocolVersion": version,
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "shotcut-ai", "title": "Shotcut AI (bridge)", "version": "1"},
                "instructions": NOT_RUNNING + " Its tools appear when it opens."}

    def unreachable_response(self, message):
        method = message.get("method")
        if "id" not in message:
            return None
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": message["id"], "result": {"tools": []}}
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": message["id"],
                    "result": {"content": [{"type": "text", "text": NOT_RUNNING}], "isError": True}}
        if method in ("resources/list", "prompts/list", "resources/templates/list"):
            key = {"resources/list": "resources", "prompts/list": "prompts",
                   "resources/templates/list": "resourceTemplates"}[method]
            return {"jsonrpc": "2.0", "id": message["id"], "result": {key: []}}
        return {"jsonrpc": "2.0", "id": message["id"],
                "error": {"code": -32000, "message": NOT_RUNNING}}

    def handle(self, message):
        """Handles one message from the client; returns the response or None."""
        method = message.get("method")
        has_id = "id" in message
        if method == "initialize" and has_id:
            self.client_initialize = message.get("params") or {}
            try:
                result = self.with_list_changed(self.initialize_app())
            except (OSError, ValueError):
                result = self.local_initialize_result()
                self.start_watching()
            return {"jsonrpc": "2.0", "id": message["id"], "result": result}
        if method == "ping" and has_id:
            return {"jsonrpc": "2.0", "id": message["id"], "result": {}}
        if method == "notifications/initialized":
            return None
        if method is None and not has_id:
            return None

        try:
            with self.app_lock:
                if not self.app_initialized:
                    self.initialize_app()
                status, response = self.post(message)
                if status == 404 and self.session:
                    # The session ended (for example Shotcut AI restarted): open a new one.
                    self.initialize_app()
                    status, response = self.post(message)
        except (OSError, ValueError):
            self.app_initialized = False
            self.start_watching()
            return self.unreachable_response(message)
        if not has_id:
            return None
        if response is None:
            return {"jsonrpc": "2.0", "id": message["id"],
                    "error": {"code": -32603,
                              "message": "Shotcut AI answered HTTP %s without a body" % status}}
        return response

    def start_watching(self):
        """Waits in the background for Shotcut AI, then asks the client to list the tools."""
        if self.watching:
            return
        self.watching = True

        def watch():
            while True:
                time.sleep(self.poll_interval)
                try:
                    self.initialize_app()
                except (OSError, ValueError):
                    continue
                self.watching = False
                self.write({"jsonrpc": "2.0", "method": "notifications/tools/list_changed"})
                return

        threading.Thread(target=watch, daemon=True).start()

    def run(self, stream=None):
        for line in stream or sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                self.write({"jsonrpc": "2.0", "id": None,
                            "error": {"code": -32700, "message": "Parse error"}})
                continue
            if isinstance(message, list):
                responses = [response for response in
                             (self.handle(item) for item in message if isinstance(item, dict))
                             if response is not None]
                if responses:
                    self.write(responses)
            elif isinstance(message, dict):
                response = self.handle(message)
                if response is not None:
                    self.write(response)


def main():
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    try:
        Bridge().run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
