#!/usr/bin/env python3
"""
test_phase8_ai_mcp_verification.py

Phase 8 Verification Suite: live AI system (MCP)
- S1: The server listens only on this computer (127.0.0.1 and ::1) and refuses web pages
      (Origin and Host headers, 403) for MCP and for the WebSocket
- S2: One port: MCP at POST /mcp and the WebSocket through QWebSocketServer::handleConnection
- P1: The protocol layer (src/ai/mcpprotocol.*) is Qt Core only and unit tested with QtTest,
      which the Linux CI runs
- T1: The 33 tools: names, valid JSON schemas that refuse unknown arguments, read-only tools
      annotated, every edit one undo step "AI: ..." and the docs list the same tools
- T2: The tools reuse the user interface code (TimelineDock, PlaylistDock, FilterController)
      and the small new APIs (flushSelection, appendXml, appendFiles)
- W1: The legacy WebSocket commands run the tools and report real errors
- U1: Settings > AI Agent (MCP): enable, status and Copy MCP Configuration for the 4 clients
- B1: The stdio bridge (scripts/shotcut_mcp_bridge.py) end to end against a fake Shotcut AI:
      forwarding, local initialize and ping, Shotcut AI closed, list_changed when it opens,
      new session after 404, server-sent events
- I1: The bridge is installed to share/shotcut/mcp on every platform
"""

import http.server
import importlib.util
import io
import json
import re
import socket
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
SERVER_CPP = SRC / "aiagentserver.cpp"
SERVER_H = SRC / "aiagentserver.h"
PROTOCOL_CPP = SRC / "ai" / "mcpprotocol.cpp"
PROTOCOL_H = SRC / "ai" / "mcpprotocol.h"
TOOLS_CPP = SRC / "ai" / "aitools.cpp"
MAINWINDOW_CPP = SRC / "mainwindow.cpp"
SETTINGS_CPP = SRC / "settings.cpp"
TIMELINEDOCK_CPP = SRC / "docks" / "timelinedock.cpp"
TIMELINEDOCK_H = SRC / "docks" / "timelinedock.h"
PLAYLISTDOCK_H = SRC / "docks" / "playlistdock.h"
SRC_CMAKE = SRC / "CMakeLists.txt"
TESTS_CMAKE = PROJECT_ROOT / "tests" / "CMakeLists.txt"
PROTOCOL_TEST = PROJECT_ROOT / "tests" / "test_mcp_protocol.cpp"
LINUX_CI = PROJECT_ROOT / ".github" / "workflows" / "check-linux-build.yml"
WINDOWS_CI = PROJECT_ROOT / ".github" / "workflows" / "build-windows-shotcut-ai.yml"
BRIDGE = PROJECT_ROOT / "scripts" / "shotcut_mcp_bridge.py"
DOCS = PROJECT_ROOT / "docs" / "ai-mcp.md"

TOOLS = [
    "get_state", "get_timeline", "get_playlist", "get_frame", "list_actions", "list_filters",
    "get_clip_filters", "play", "pause", "seek", "step", "undo", "redo", "run_action",
    "open_media", "add_to_playlist", "open_project", "save_project", "append_clip",
    "insert_clip", "overwrite_clip", "split_clip", "remove_clip", "move_clip", "trim_clip",
    "set_fade", "add_track", "set_track", "select_clips", "add_filter", "set_filter_param",
    "set_filter_enabled", "remove_filter",
]
READ_ONLY_TOOLS = {"get_state", "get_timeline", "get_playlist", "get_frame", "list_actions",
                   "list_filters", "get_clip_filters"}
# Tools that change the project: one undo step each.
UNDOABLE_TOOLS = {"run_action", "add_to_playlist", "append_clip", "insert_clip",
                  "overwrite_clip", "split_clip", "remove_clip", "move_clip", "trim_clip",
                  "set_fade", "add_track", "set_track", "add_filter", "set_filter_param",
                  "set_filter_enabled", "remove_filter"}


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


def flat(text):
    return re.sub(r"\s+", " ", text)


def tool_sources(cpp):
    """The registration of each tool: from add("name" to the next add(."""
    body = block(cpp, "void AiTools::registerTools(Mcp::Server &server)")
    starts = [(m.group(1), m.start()) for m in re.finditer(r'\badd\("([a-z_]+)"', body)]
    # insert_clip and overwrite_clip come from placeClip("name", ...).
    starts += [(m.group(1), m.start()) for m in re.finditer(r'placeClip\("([a-z_]+)"', body)]
    starts.sort(key=lambda item: item[1])
    result = {}
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(body)
        result[name] = body[start:end]
    # placeClip() registers through the shared lambda: give both the lambda body too.
    lambda_body = body[body.index("auto placeClip = "):body.index('placeClip("insert_clip"')]
    for name in ("insert_clip", "overwrite_clip"):
        result[name] = lambda_body + result.get(name, "")
    return result


def load_bridge_module():
    spec = importlib.util.spec_from_file_location("shotcut_mcp_bridge", BRIDGE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeShotcut:
    """A tiny MCP endpoint that answers like Shotcut AI and records the requests."""

    def __init__(self, port, session="abc", sse=False):
        self.port = port
        self.session = session
        self.sse = sse
        self.requests = []
        self.expire_session_once = False
        fake = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                message = json.loads(self.rfile.read(length))
                fake.requests.append((message, dict(self.headers)))
                if (fake.expire_session_once and message.get("method") == "tools/call"
                        and self.headers.get("Mcp-Session-Id")):
                    fake.expire_session_once = False
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if "id" not in message:
                    self.send_response(202)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                method = message.get("method")
                if method == "initialize":
                    result = {"protocolVersion": message["params"]["protocolVersion"],
                              "capabilities": {"tools": {"listChanged": False}},
                              "serverInfo": {"name": "shotcut-ai", "version": "test"}}
                elif method == "tools/list":
                    result = {"tools": [{"name": "get_state", "inputSchema": {"type": "object"}}]}
                elif method == "tools/call":
                    result = {"content": [{"type": "text", "text": "{\"ok\":true}"}],
                              "structuredContent": {"ok": True}, "isError": False}
                else:
                    result = {}
                body = json.dumps({"jsonrpc": "2.0", "id": message["id"],
                                   "result": result}).encode()
                self.send_response(200)
                if method == "initialize" and fake.session:
                    self.send_header("Mcp-Session-Id", fake.session)
                if fake.sse:
                    body = b"event: message\ndata: " + body + b"\n\n"
                    self.send_header("Content-Type", "text/event-stream")
                else:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def methods(self):
        return [message.get("method") for message, _ in self.requests]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class CodeTestCase(unittest.TestCase):
    def assertIn(self, member, container, msg=None):
        if isinstance(member, str) and isinstance(container, str):
            member, container = flat(member), flat(container)
        super().assertIn(member, container, msg)

    def assertNotIn(self, member, container, msg=None):
        if isinstance(member, str) and isinstance(container, str):
            member, container = flat(member), flat(container)
        super().assertNotIn(member, container, msg)


class TestPhase8Server(CodeTestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = read(SERVER_CPP)
        cls.protocol = read(PROTOCOL_CPP)
        cls.tools = read(TOOLS_CPP)

    # S1 -----------------------------------------------------------------
    def test_s1_listens_only_on_this_computer(self):
        self.assertNotIn("QHostAddress::Any", self.server)
        self.assertIn("{QHostAddress(QHostAddress::LocalHost), QHostAddress(QHostAddress::LocalHostIPv6)}",
                      self.server)
        accept = block(self.server, "void AIAgentServer::onNewTcpConnection()")
        self.assertIn("if (!socket->peerAddress().isLoopback()) { socket->abort();", accept)

    def test_s1_refuses_web_pages(self):
        http_block = block(self.server, "void AIAgentServer::respondHttp(")
        self.assertIn('if (!Mcp::isLocalHost(request.header("host")) || '
                      '!Mcp::isLocalOrigin(request.header("origin"))) {', http_block)
        self.assertIn("Mcp::httpResponse(403,", http_block)
        self.assertIn("Mcp::httpResponse(415,", http_block)
        upgrade = block(self.server, "void AIAgentServer::onTcpReadyRead(QTcpSocket *socket)")
        self.assertIn('if (!Mcp::isLocalHost(request.header("host")) || '
                      '!Mcp::isLocalOrigin(request.header("origin"))) {', upgrade)
        cors = block(self.server, "void AIAgentServer::onOriginAuthenticationRequired(")
        self.assertIn("authenticator->setAllowed(Mcp::isLocalOrigin(authenticator->origin().toLatin1()));",
                      cors)
        origin = block(self.protocol, "bool isLocalOrigin(const QByteArray &origin)")
        self.assertIn('url.scheme() != QLatin1String("http") && url.scheme() != QLatin1String("https")',
                      origin)

    # S2 -----------------------------------------------------------------
    def test_s2_one_port_for_mcp_and_the_websocket(self):
        upgrade = block(self.server, "void AIAgentServer::onTcpReadyRead(QTcpSocket *socket)")
        # Peek, so that the WebSocket handshake stays unread for QWebSocketServer.
        self.assertIn("socket->peek(", upgrade)
        self.assertIn("m_webSocketServer->handleConnection(socket);", upgrade)
        http_block = block(self.server, "void AIAgentServer::respondHttp(")
        self.assertIn('if (request.path() != "/mcp") {', http_block)
        self.assertIn('if (request.method != "POST") {', http_block)
        self.assertIn("const auto reply = m_mcp.handlePost(request.body);", http_block)
        # A tool may run a nested event loop (a dialog) while the client goes away.
        self.assertIn("QPointer<QTcpSocket> guard(socket);", http_block)

    # P1 -----------------------------------------------------------------
    def test_p1_protocol_layer_is_unit_tested(self):
        header = read(PROTOCOL_H)
        includes = re.findall(r"#include <(\w+)>", header + read(PROTOCOL_CPP))
        self.assertFalse([name for name in includes if name.startswith("QWidget")
                          or name.startswith("QTcp") or name.startswith("QWebSocket")])
        self.assertIn("add_executable(test_mcp_protocol", read(TESTS_CMAKE))
        self.assertIn("${CMAKE_SOURCE_DIR}/src/ai/mcpprotocol.cpp", read(TESTS_CMAKE))
        test = read(PROTOCOL_TEST)
        for case in ("initializeNegotiatesTheVersion", "invalidArgumentsAreToolErrors",
                     "protocolErrors", "parsesHttpRequests", "onlyLocalOriginsAndHosts",
                     "clientConfigurations"):
            self.assertIn(f"void {case}()", test)
        ci = read(LINUX_CI)
        self.assertIn("-DSHOTCUT_BUILD_TESTS=ON", ci)
        self.assertIn("ctest --test-dir build --output-on-failure", ci)
        versions = block(self.protocol, "QStringList Server::protocolVersions()")
        for version in ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"):
            self.assertIn(version, versions)

    # T1 -----------------------------------------------------------------
    def test_t1_tools_are_registered(self):
        sources = tool_sources(self.tools)
        self.assertEqual(sorted(sources), sorted(TOOLS))
        self.assertEqual(len(TOOLS), 33)

    def test_t1_schemas_are_valid_json_that_refuse_unknown_arguments(self):
        body = block(self.tools, "void AiTools::registerTools(Mcp::Server &server)")
        clip_properties = re.search(r'const char \*clipProperties = R"json\((.*?)\)json";', body,
                                    re.S).group(1)
        schemas = 0
        for name, source in tool_sources(self.tools).items():
            for literal in re.findall(r'R"json\((.*?)\)json"', source, re.S):
                text = literal.strip()
                if not text.startswith("{"):
                    # A piece added to the clip properties by clipSchema().
                    text = "{" + clip_properties + "," + text + "}"
                    schema = {"type": "object", "properties": json.loads(text),
                              "additionalProperties": False}
                else:
                    schema = json.loads(text)
                with self.subTest(tool=name):
                    self.assertEqual(schema["type"], "object")
                    self.assertIs(schema.get("additionalProperties"), False)
                schemas += 1
        self.assertGreaterEqual(schemas, 25)
        clip_schema = block(body, "auto clipSchema = [clipProperties]")
        self.assertIn('json += "}, \\"additionalProperties\\": false";', clip_schema)

    def test_t1_annotations_and_undo_steps(self):
        for name, source in tool_sources(self.tools).items():
            with self.subTest(tool=name):
                if name in READ_ONLY_TOOLS:
                    self.assertIn("readOnly(),", source)
                    self.assertNotIn("edit(", source)
                else:
                    self.assertIn("editing(", source)
                if name in UNDOABLE_TOOLS:
                    self.assertIn("return edit(", source)
        edit = block(self.tools, "Mcp::ToolResult AiTools::edit(")
        self.assertIn('const auto text = tr("AI: %1").arg(title);', edit)
        self.assertIn("stack->beginMacro(text);", edit)
        self.assertIn("stack->endMacro();", edit)
        # A step that changed nothing is dropped instead of cluttering History.
        self.assertIn("command->setObsolete(true); stack->undo();", edit)
        self.assertIn("MAIN.showStatusMessage(text, 3);", edit)
        run = block(self.tools, "Mcp::ToolResult AiTools::run(")
        self.assertIn("if (m_busy)", run)
        self.assertIn("QScopedValueRollback<bool> busy(m_busy, true);", run)

    def test_t1_docs_list_the_same_tools(self):
        docs = read(DOCS)
        documented = set(re.findall(r"^\| `([a-z_]+)` \|", docs, re.M))
        self.assertEqual(documented, set(TOOLS))
        for client in ("Claude Code", "Claude Desktop", "OpenCode", "Antigravity"):
            self.assertIn(client, docs)
        self.assertIn("http://127.0.0.1:9999/mcp", docs)

    # T2 -----------------------------------------------------------------
    def test_t2_tools_reuse_the_application(self):
        sources = tool_sources(self.tools)
        uses = {
            "split_clip": "timeline()->split(track, clip, position)",
            "remove_clip": "timeline()->lift(track, clip);",
            "move_clip": "QCoreApplication::sendPostedEvents(timeline(), QEvent::MetaCall);",
            "trim_clip": "timeline()->commitTrimCommand();",
            "set_fade": "timeline()->fadeIn(track, clip, fadeIn);",
            "append_clip": "timeline()->appendXml(track, xml);",
            "insert_clip": "timeline()->insert(track, position, xml, false);",
            "add_to_playlist": "MAIN.playlistDock()->appendFiles(paths);",
            "add_filter": "const int row = model->add(meta);",
            "set_filter_param": "filter->startUndoParameterCommand(",
            "set_filter_enabled": "Qt::CheckStateRole);",
            "run_action": "action->trigger();",
            "save_project": "MAIN.newProject(file.absoluteFilePath());",
        }
        for name, code in uses.items():
            with self.subTest(tool=name):
                self.assertIn(code, sources[name])
        self.assertIn("void flushSelection();", read(TIMELINEDOCK_H))
        self.assertIn("void appendXml(int trackIndex, const QString &xml);", read(TIMELINEDOCK_H))
        self.assertIn("void appendFiles(const QStringList &paths);", read(PLAYLISTDOCK_H))
        flush = block(read(TIMELINEDOCK_CPP), "void TimelineDock::flushSelection()")
        self.assertIn("m_selectionSignalTimer.stop(); emit selectionChanged(); "
                      "emitSelectedFromSelection();", flush)
        frame = sources["get_frame"]
        # The frame shown now, or a copy rendered at another time: the playhead stays.
        self.assertIn("image = videoWidget->image();", frame)
        self.assertIn('Mlt::Producer copy(MLT.profile(), "xml-string",', frame)

    def test_t2_actions_that_close_shotcut_are_blocked(self):
        blocked = block(self.tools, "bool isBlockedAction(const QString &name, QAction *action)")
        for name in ("actionExit", "actionReset", "actionAppDataSet", "actionFusionDark",
                     "actionClassicFusionDark"):
            self.assertIn(f'"{name}"', blocked)

    # W1 -----------------------------------------------------------------
    def test_w1_websocket_commands_run_tools(self):
        mapping = block(self.server, "QString AIAgentServer::toolForCommand(")
        self.assertIn('if (command == QLatin1String("open")) return QStringLiteral("open_media");',
                      mapping)
        handler = block(self.server, "QString AIAgentServer::handleWebSocketMessage(")
        self.assertIn("const auto result = m_mcp.callTool(toolName, arguments);", handler)
        self.assertIn('{"error", QStringLiteral("Unknown command: %1").arg(command)}', handler)
        self.assertIn('{"available_commands", commands}', handler)
        self.assertNotIn("// MAIN.player()->play();", self.server)

    # U1 -----------------------------------------------------------------
    def test_u1_settings_menu_and_switch(self):
        main = read(MAINWINDOW_CPP)
        self.assertIn('if (Settings.aiServerEnabled()) m_aiAgentServer = new AIAgentServer('
                      'Settings.aiServerPort(), this);', main)
        menu = block(main, "void MainWindow::setupSettingsMenu()")
        self.assertIn('auto aiMenu = new QMenu(tr("AI Agent (MCP)"), this);', menu)
        self.assertIn('tr("Enable AI Agent Server")', menu)
        self.assertIn('tr("Copy MCP Configuration")', menu)
        for client in ("ClaudeCode", "ClaudeDesktop", "OpenCode", "Antigravity"):
            self.assertIn(f"Mcp::Client::{client}", menu)
        settings = read(SETTINGS_CPP)
        self.assertIn('settings.value("aiServer/enabled", true).toBool()', settings)
        self.assertIn('settings.value("aiServer/port", 9999).toInt()', settings)


class TestPhase8Bridge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.module = load_bridge_module()

    def make_bridge(self, port, **kwargs):
        output = io.StringIO()
        bridge = self.module.Bridge(url=f"http://127.0.0.1:{port}/mcp", output=output,
                                    poll_interval=0.1, **kwargs)
        return bridge, output

    @staticmethod
    def initialize(bridge, version="2025-06-18"):
        return bridge.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                              "params": {"protocolVersion": version, "capabilities": {},
                                         "clientInfo": {"name": "test", "version": "1"}}})

    # B1 -----------------------------------------------------------------
    def test_b1_standard_library_only(self):
        imports = set(re.findall(r"^import (\w+)", read(BRIDGE), re.M))
        imports |= set(re.findall(r"^from (\w+)", read(BRIDGE), re.M))
        self.assertLessEqual(imports, {"json", "os", "sys", "threading", "time", "urllib"})

    def test_b1_forwards_to_shotcut(self):
        port = free_port()
        fake = FakeShotcut(port)
        try:
            bridge, _ = self.make_bridge(port)
            response = self.initialize(bridge)
            self.assertEqual(response["result"]["serverInfo"]["name"], "shotcut-ai")
            # The bridge may announce tools later, so it always offers listChanged.
            self.assertTrue(response["result"]["capabilities"]["tools"]["listChanged"])
            self.assertEqual(fake.methods()[:2], ["initialize", "notifications/initialized"])
            tools = bridge.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertEqual(tools["result"]["tools"][0]["name"], "get_state")
            call = bridge.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                  "params": {"name": "get_state", "arguments": {}}})
            self.assertEqual(call["id"], 2)
            self.assertTrue(call["result"]["structuredContent"]["ok"])
            # The session and the negotiated version travel in the headers (whose names
            # HTTP compares without case).
            headers = {name.lower(): value for name, value in fake.requests[-1][1].items()}
            self.assertEqual(headers.get("mcp-session-id"), "abc")
            self.assertEqual(headers.get("mcp-protocol-version"), "2025-06-18")
            # ping and notifications/initialized are answered by the bridge.
            count = len(fake.requests)
            self.assertEqual(bridge.handle({"jsonrpc": "2.0", "id": 3, "method": "ping"})["result"], {})
            self.assertIsNone(bridge.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
            self.assertEqual(len(fake.requests), count)
        finally:
            fake.close()

    def test_b1_shotcut_closed_then_opened(self):
        port = free_port()
        bridge, output = self.make_bridge(port)
        response = self.initialize(bridge, version="2025-11-25")
        self.assertEqual(response["result"]["protocolVersion"], "2025-11-25")
        self.assertIn("not open", response["result"]["instructions"])
        self.assertEqual(bridge.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
                         ["result"]["tools"], [])
        call = bridge.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                              "params": {"name": "get_state", "arguments": {}}})
        self.assertTrue(call["result"]["isError"])
        self.assertIn("Shotcut AI is not open", call["result"]["content"][0]["text"])
        # When Shotcut AI opens, the client is told to list the tools again.
        fake = FakeShotcut(port)
        try:
            deadline = time.time() + 5
            while "list_changed" not in output.getvalue() and time.time() < deadline:
                time.sleep(0.05)
            self.assertIn('"method":"notifications/tools/list_changed"', output.getvalue())
            tools = bridge.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
            self.assertEqual(len(tools["result"]["tools"]), 1)
        finally:
            fake.close()

    def test_b1_new_session_after_404(self):
        port = free_port()
        fake = FakeShotcut(port)
        try:
            bridge, _ = self.make_bridge(port)
            self.initialize(bridge)
            fake.expire_session_once = True
            call = bridge.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                                  "params": {"name": "get_state", "arguments": {}}})
            self.assertFalse(call["result"]["isError"])
            self.assertEqual(fake.methods().count("initialize"), 2)
        finally:
            fake.close()

    def test_b1_server_sent_events(self):
        port = free_port()
        fake = FakeShotcut(port, session=None, sse=True)
        try:
            bridge, _ = self.make_bridge(port)
            self.initialize(bridge)
            call = bridge.handle({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                                  "params": {"name": "get_state", "arguments": {}}})
            self.assertTrue(call["result"]["structuredContent"]["ok"])
        finally:
            fake.close()

    def test_b1_stdio_process(self):
        """The bridge as a client starts it: one JSON message per line on stdin/stdout."""
        port = free_port()
        fake = FakeShotcut(port)
        try:
            lines = [
                {"jsonrpc": "2.0", "id": 0, "method": "initialize",
                 "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                            "clientInfo": {"name": "test", "version": "1"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            ]
            process = subprocess.run(
                [sys.executable, str(BRIDGE)],
                input="\n".join(json.dumps(line) for line in lines) + "\nnot json\n",
                capture_output=True, text=True, timeout=30,
                env={"SHOTCUT_AI_URL": f"http://127.0.0.1:{port}/mcp", "PATH": ""})
            responses = [json.loads(line) for line in process.stdout.splitlines()]
            self.assertEqual([response.get("id") for response in responses], [0, 1, None])
            self.assertEqual(responses[2]["error"]["code"], -32700)
            self.assertEqual(process.returncode, 0)
        finally:
            fake.close()

    # I1 -----------------------------------------------------------------
    def test_i1_bridge_is_installed(self):
        cmake = read(SRC_CMAKE)
        self.assertEqual(cmake.count("scripts/shotcut_mcp_bridge.py"), 3)
        self.assertIn("DESTINATION ${CMAKE_INSTALL_PREFIX}/share/shotcut/mcp)", cmake)
        self.assertIn("DESTINATION ${CMAKE_INSTALL_DATADIR}/shotcut/mcp)", cmake)
        self.assertIn("Resources/shotcut/mcp)", cmake)
        server = read(SERVER_CPP)
        self.assertIn('QmlApplication::dataDir().absoluteFilePath("shotcut/mcp/shotcut_mcp_bridge.py")',
                      server)
        # The Windows build checks MCP and the bundled bridge with the new application.
        windows = read(WINDOWS_CI)
        self.assertIn("live_mcp_smoke.py --read-only --bridge "
                      "dist\\Shotcut-AI\\share\\shotcut\\mcp\\shotcut_mcp_bridge.py", windows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
