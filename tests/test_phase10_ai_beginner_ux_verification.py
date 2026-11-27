#!/usr/bin/env python3
"""
test_phase10_ai_beginner_ux_verification.py

Phase 10 Verification Suite: Shotcut AI for people who have never edited a video
- P1: Ready-made requests (MCP prompts): the protocol, the 7 recipes, the server and the
      stdio bridge offer them; the live smoke test and the docs list the same ones
- P2: Instructions that ask the AI for plain words, a plan before big changes and no
      deleting without asking
- C1: Connect to Claude in one click: Claude Desktop settings merged with a backup (unit
      tested in C++), Claude Code through its command line, the Python of the package
- U1: The AI Assistant panel: status, requests to copy, the steps of the AI with one-click
      undo; the AI chip of the top bar never pushes Export out; on and off without a
      restart; opens by itself the first time; Help > AI Assistant: First Steps
- W1: Windows: "Shotcut AI.exe" with the icon instead of a .bat, the embeddable Python, an
      installer that asks for a desktop shortcut, all checked by the build
- T1: Spanish translations of every new text
- D1: The beginner's guide, the MCP guide, the roadmap and the traceability files
"""

import importlib.util
import io
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
TOOLS_CPP = SRC / "ai" / "aitools.cpp"
TOOLS_H = SRC / "ai" / "aitools.h"
PROTOCOL_CPP = SRC / "ai" / "mcpprotocol.cpp"
PROTOCOL_H = SRC / "ai" / "mcpprotocol.h"
CLIENT_SETUP_CPP = SRC / "ai" / "clientsetup.cpp"
CLIENT_SETUP_H = SRC / "ai" / "clientsetup.h"
SERVER_CPP = SRC / "aiagentserver.cpp"
SERVER_H = SRC / "aiagentserver.h"
DOCK_CPP = SRC / "docks" / "aiassistantdock.cpp"
DOCK_H = SRC / "docks" / "aiassistantdock.h"
MAINWINDOW_CPP = SRC / "mainwindow.cpp"
MAINWINDOW_H = SRC / "mainwindow.h"
SETTINGS_CPP = SRC / "settings.cpp"
SRC_CMAKE = SRC / "CMakeLists.txt"
TESTS_CMAKE = PROJECT_ROOT / "tests" / "CMakeLists.txt"
PROTOCOL_TEST = PROJECT_ROOT / "tests" / "test_mcp_protocol.cpp"
LIVE_SMOKE = PROJECT_ROOT / "tests" / "live_mcp_smoke.py"
ANALYSIS_SMOKE = PROJECT_ROOT / "tests" / "live_analysis_smoke.py"
BRIDGE = PROJECT_ROOT / "scripts" / "shotcut_mcp_bridge.py"
ANALYSIS = PROJECT_ROOT / "scripts" / "shotcut_analysis.py"
BUNDLE = PROJECT_ROOT / "scripts" / "bundle-windows-msys2.sh"
WINDOWS_CI = PROJECT_ROOT / ".github" / "workflows" / "build-windows-shotcut-ai.yml"
PACKAGING = PROJECT_ROOT / "packaging" / "windows"
LAUNCHER_C = PACKAGING / "shotcut-ai-launcher.c"
LAUNCHER_RC = PACKAGING / "shotcut-ai-launcher.rc"
INSTALLER = PACKAGING / "shotcut-ai.iss"
UPSTREAM_INSTALLER = PACKAGING / "shotcut.iss"
ICON = PACKAGING / "shotcut-logo-64.ico"
SPANISH = PROJECT_ROOT / "translations" / "shotcut_es.ts"
GUIDE = PROJECT_ROOT / "docs" / "guia-principiante.md"
DOCS_MCP = PROJECT_ROOT / "docs" / "ai-mcp.md"
DOCS_BUILD = PROJECT_ROOT / "docs" / "build-windows.md"
ROADMAP = PROJECT_ROOT / "docs" / "ROADMAP_SHOTCUT_AI.md"
PLAN = PROJECT_ROOT / "plan.md"
AGENT = PROJECT_ROOT / "agent.md"

RECIPES = ["make_video", "remove_silences", "cut_to_music", "transcribe_speech",
           "explain_project", "review_video", "prepare_for_youtube"]


def read(path):
    return Path(path).read_text(encoding="utf-8")


def flat(text):
    return re.sub(r"\s+", " ", text)


def block(source, start):
    """The brace block that follows the first occurrence of `start`."""
    begin = source.index("{", source.index(start))
    depth = 0
    for index in range(begin, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[begin:index + 1]
    raise ValueError("Unbalanced block after %s" % start)


def literals(source):
    """The text of the C++ string literals in `source`, joined."""
    return "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', source))


def load_bridge():
    spec = importlib.util.spec_from_file_location("shotcut_mcp_bridge_p10", BRIDGE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recipe_names():
    return re.findall(r'list\.append\(\s*\{QStringLiteral\("([a-z_]+)"\)', read(TOOLS_CPP))


def tr_texts(source):
    """The texts of the tr() calls in `source`, with their literals joined."""
    texts = set()
    for match in re.finditer(r'tr\(((?:\s*"(?:[^"\\]|\\.)*")+)', source):
        text = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1)))
        texts.add(text.replace('\\n', '\n').replace('\\"', '"'))
    return texts


# ---------------------------------------------------------------------------------------
class TestPhase10Prompts(unittest.TestCase):

    def test_p1_protocol_lists_and_gets_prompts(self):
        header = read(PROTOCOL_H)
        self.assertIn("struct Prompt", header)
        self.assertIn("struct PromptArgument", header)
        self.assertIn("void addPrompt(const Prompt &prompt);", header)
        source = flat(read(PROTOCOL_CPP))
        self.assertIn('capabilities["prompts"] = QJsonObject{{"listChanged", false}};', source)
        self.assertIn('method == QLatin1String("prompts/get")', source)
        self.assertIn("result = getPrompt(name.toString(), params.value(\"arguments\").toObject(), "
                      "&error);", source)
        get = flat(block(read(PROTOCOL_CPP), "QJsonObject Server::getPrompt("))
        # A required argument that is missing is an error; the text becomes a user message.
        self.assertIn("if (argument.required && text.isEmpty())", get)
        self.assertIn('{"role", "user"}', get)
        # The prompts are only announced when there are some.
        init = flat(block(read(PROTOCOL_CPP), "QJsonObject Server::initializeResult("))
        self.assertIn("if (!m_prompts.isEmpty())", init)

    def test_p1_seven_recipes_for_common_jobs(self):
        self.assertEqual(recipe_names(), RECIPES)
        recipes = block(read(TOOLS_CPP), "QList<AiTools::Recipe> AiTools::recipes()")
        # The recipes that act ask for a plan first; explain and review change nothing.
        self.assertEqual(recipes.count("beginnerWay()"), 5)
        for words in ("Do not change anything", "never in the middle of one",
                      "-14 LUFS", "SRT subtitle file"):
            self.assertIn(words, literals(recipes))
        way = literals(block(read(TOOLS_CPP), "QString beginnerWay()"))
        self.assertIn("tell me your plan in 3 to 5 short points and wait for my OK", way)
        register = block(read(TOOLS_CPP), "void AiTools::registerPrompts(")
        self.assertIn("server.addPrompt(", register)
        self.assertIn("m_tools->registerPrompts(m_mcp);", read(SERVER_CPP))

    def test_p1_smoke_test_and_docs_list_the_same_recipes(self):
        smoke = read(LIVE_SMOKE)
        listed = re.search(r"REQUIRED_PROMPTS = \{([^}]*)\}", smoke, re.S).group(1)
        self.assertEqual(sorted(re.findall(r'"([a-z_]+)"', listed)), sorted(RECIPES))
        self.assertIn('client.request("prompts/list")', smoke)
        self.assertIn('"prompts/get"', smoke)
        docs = read(DOCS_MCP)
        for name in RECIPES:
            self.assertIn("`%s`" % name, docs)

    def test_p1_bridge_offers_prompts_before_and_after_shotcut_opens(self):
        module = load_bridge()
        bridge = module.Bridge(url="http://127.0.0.1:9/mcp", output=io.StringIO(),
                               poll_interval=0.1)
        local = bridge.local_initialize_result()
        self.assertTrue(local["capabilities"]["prompts"]["listChanged"])
        self.assertIn("prompts", local["instructions"])
        forwarded = module.Bridge.with_list_changed(
            {"capabilities": {"tools": {"listChanged": False}, "prompts": {"listChanged": False}}})
        self.assertTrue(forwarded["capabilities"]["prompts"]["listChanged"])
        self.assertTrue(forwarded["capabilities"]["tools"]["listChanged"])
        # A server without prompts does not get them from the bridge.
        plain = module.Bridge.with_list_changed({"capabilities": {}})
        self.assertNotIn("prompts", plain["capabilities"])
        self.assertIn('"notifications/prompts/list_changed"', read(BRIDGE))

    def test_p2_instructions_for_beginners(self):
        text = literals(block(read(TOOLS_CPP), "QString AiTools::instructions()"))
        for words in ("The user may never have edited a video",
                      "in plain words", "explain any editing term",
                      "say your plan in 3 to 5 short points and wait for the user's OK",
                      "Never delete the user's files",
                      "never overwrite a project file without asking",
                      "AI Assistant panel", "suggest what the user could ask next"):
            self.assertIn(words, text)
        self.assertIn("AiTools::instructions())", flat(read(SERVER_CPP)))
        self.assertNotIn("kInstructions", read(SERVER_CPP))


# ---------------------------------------------------------------------------------------
class TestPhase10Connect(unittest.TestCase):

    def test_c1_claude_desktop_settings_are_merged_safely(self):
        header = read(CLIENT_SETUP_H)
        for name in ("claudeDesktopConfigCandidates", "chooseConfigFile", "mergeMcpServers",
                     "writeMcpServers"):
            self.assertIn(name, header)
        source = read(CLIENT_SETUP_CPP)
        # Microsoft Store packages of Claude first, then the usual file.
        self.assertIn('QStringList{QStringLiteral("Claude*")}', source)
        self.assertIn('"/LocalCache/Roaming/"', source)
        write = flat(block(source, "bool writeMcpServers("))
        self.assertIn('const auto backup = path + QStringLiteral(".bak");', write)
        self.assertIn("QSaveFile file(path);", write)
        self.assertIn("if (result == MergeResult::Invalid)", write)
        # Only Qt Core: unit tested in tests/test_mcp_protocol.cpp.
        self.assertNotIn("QtWidgets", source)
        self.assertIn("${CMAKE_SOURCE_DIR}/src/ai/clientsetup.cpp", read(TESTS_CMAKE))
        self.assertIn("ai/clientsetup.cpp ai/clientsetup.h", read(SRC_CMAKE))
        tests = read(PROTOCOL_TEST)
        for name in ("void promptsAreReadyMadeRequests()", "void observerSeesClients()",
                     "void connectsClaudeDesktop()", "void quotesPythonWithSpaces()"):
            self.assertIn(name, tests)

    def test_c1_the_panel_connects_claude_desktop_and_claude_code(self):
        dock = read(DOCK_CPP)
        desktop = flat(block(dock, "void AiAssistantDock::connectClaudeDesktop()"))
        self.assertIn('qEnvironmentVariable("APPDATA")', desktop)
        self.assertIn('qEnvironmentVariable("LOCALAPPDATA")', desktop)
        self.assertIn("ClientSetup::writeMcpServers(path, AIAgentServer::claudeDesktopServers(port), "
                      "&error)", desktop)
        self.assertIn("claude.ai/download", desktop)
        code = flat(block(dock, "void AiAssistantDock::connectClaudeCode()"))
        self.assertIn('QStandardPaths::findExecutable(QStringLiteral("claude"))', code)
        self.assertIn('QProcess::execute(claude, {"mcp", "remove", "--scope", "user", server.first});',
                      code)
        self.assertIn('QStringList{"mcp", "add", "--scope", "user"} + server.second', code)
        # Without Claude Code the commands are copied, as before.
        self.assertIn("QGuiApplication::clipboard()->setText(commands);", code)

    def test_c1_the_python_of_the_package(self):
        source = flat(block(read(SERVER_CPP), "QString AIAgentServer::pythonPath()"))
        self.assertIn('QStringLiteral("../python/python.exe")', source)
        self.assertIn('return QStringLiteral("python3");', source)
        config = flat(block(read(SERVER_CPP), "QString AIAgentServer::clientConfiguration("))
        self.assertIn("pythonPath()", config)
        quoted = flat(block(read(PROTOCOL_CPP), "QString clientConfiguration("))
        self.assertIn("python.contains(QLatin1Char(' '))", quoted)

    def test_c1_server_reports_its_clients(self):
        self.assertIn("void clientActivity(const QString &clientName, const QString &method);",
                      read(SERVER_H))
        observer = flat(read(SERVER_CPP))
        self.assertIn("m_mcp.setObserver(", observer)
        self.assertIn('info.value("title").toString(info.value("name").toString())', observer)
        self.assertIn("emit clientActivity(m_clientName, method);", observer)


# ---------------------------------------------------------------------------------------
class TestPhase10Assistant(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dock = read(DOCK_CPP)
        cls.main = read(MAINWINDOW_CPP)

    def test_u1_panel_shows_status_requests_and_steps(self):
        self.assertIn("docks/aiassistantdock.cpp docks/aiassistantdock.h", read(SRC_CMAKE))
        constructor = flat(block(self.dock, "AiAssistantDock::AiAssistantDock("))
        self.assertIn('setObjectName("AiAssistantDock");', constructor)
        self.assertIn("for (const auto &recipe : AiTools::recipes())", constructor)
        self.assertIn("connect(m_undoStack, &QUndoStack::indexChanged, this, "
                      "&AiAssistantDock::updateSteps);", constructor)
        self.assertIn("scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);", constructor)
        # The three states that a beginner needs to tell apart, with a color each.
        status = flat(block(self.dock, "void AiAssistantDock::updateStatus()"))
        for color in ("#7A808C", "#E5484D", "#F5B83D", "#3DD68C"):
            self.assertIn(color, status)
        # Cards wrap to the panel and work with the keyboard too.
        card = flat(block(self.dock, "bool AiAssistantDock::eventFilter("))
        self.assertIn("key == Qt::Key_Return || key == Qt::Key_Enter || key == Qt::Key_Space", card)
        self.assertIn("QGuiApplication::clipboard()->setText(", card)

    def test_u1_steps_of_the_ai_undo_with_one_click(self):
        steps = flat(block(self.dock, "void AiAssistantDock::updateSteps()"))
        self.assertIn("command->text().startsWith(prefix)", steps)
        self.assertIn('tr("(undone)")', steps)
        undo = flat(block(self.dock, "void AiAssistantDock::onUndoClicked()"))
        self.assertIn("m_undoStack->setIndex(done ? index : index + 1);", undo)
        edit = flat(block(read(TOOLS_CPP), "Mcp::ToolResult AiTools::edit("))
        self.assertIn("emit stepDone(step);", edit)
        self.assertIn('tr("%1 (Ctrl+Z to undo)").arg(text), 6);', edit)
        self.assertIn('return tr("AI: %1").arg(QString());',
                      flat(block(read(TOOLS_CPP), "QString AiTools::stepPrefix()")))

    def test_u1_the_ai_server_turns_on_and_off_without_a_restart(self):
        running = flat(block(self.main, "void MainWindow::setAiServerRunning(bool running)"))
        self.assertIn("m_aiAgentServer = new AIAgentServer(Settings.aiServerPort(), this);", running)
        self.assertIn("delete m_aiAgentServer;", running)
        self.assertIn("m_aiAssistantDock->setServer(m_aiAgentServer);", running)
        menu = flat(block(self.main, "void MainWindow::setupSettingsMenu()"))
        self.assertIn("setAiServerRunning(checked);", menu)
        self.assertNotIn("to turn the AI agent server %2", menu)
        self.assertNotIn("Starts after a restart", menu)
        for name in ("actionShowAiAssistant", "actionConnectClaudeDesktop",
                     "actionConnectClaudeCode"):
            self.assertIn('"%s"' % name, menu)

    def test_u1_chip_first_run_and_help(self):
        setup = flat(block(self.main, "void MainWindow::setupAiAssistant()"))
        self.assertIn("m_aiStatusAction = ui->mainToolBar->insertWidget(ui->actionJobs, "
                      "m_aiStatusButton);", setup)
        self.assertIn("ui->menuHelp->insertAction(ui->actionForum, guide);", setup)
        self.assertIn("if (m_aiAgentServer && !Settings.aiAssistantShown())", setup)
        self.assertIn('settings.value("aiServer/assistantShown", false).toBool()',
                      read(SETTINGS_CPP))
        show = flat(block(self.main, "void MainWindow::showAiAssistant()"))
        self.assertIn("tabifyDockWidget(m_propertiesDock, m_aiAssistantDock);", show)
        # The chip steps aside before Export would be pushed out of the bar.
        adjust = flat(block(self.main, "void MainWindow::adjustMainToolbar()"))
        self.assertIn("if (action == m_aiStatusAction || !action->isVisible())", adjust)
        self.assertIn("m_aiStatusAction->setVisible(this->width() >= needed);", adjust)
        self.assertIn("adjustMainToolbar();",
                      flat(block(self.main, "void MainWindow::updateProjectInfo()")))
        # The dock is created with the others, before the saved layout is restored.
        docks = flat(block(self.main, "void MainWindow::setupAndConnectDocks()"))
        self.assertIn("m_aiAssistantDock = new AiAssistantDock(m_undoStack, this);", docks)
        self.assertIn("ui->menuView->addAction(m_aiAssistantDock->toggleViewAction());", docks)

    def test_u1_existing_functions_stay(self):
        # Invariance: the Phase 8 menu keeps every entry, including Copy MCP Configuration.
        menu = flat(block(self.main, "void MainWindow::setupSettingsMenu()"))
        for text in ('tr("Enable AI Agent Server")', 'tr("Copy MCP Configuration")'):
            self.assertIn(text, menu)
        for client in ("ClaudeCode", "ClaudeDesktop", "OpenCode", "Antigravity"):
            self.assertIn("Mcp::Client::%s" % client, menu)
        self.assertIn("if (Settings.aiServerEnabled()) m_aiAgentServer = new AIAgentServer("
                      "Settings.aiServerPort(), this);", flat(self.main))


# ---------------------------------------------------------------------------------------
class TestPhase10Windows(unittest.TestCase):

    def test_w1_launcher_has_the_icon_and_starts_shotcut(self):
        launcher = read(LAUNCHER_C)
        self.assertIn('L"%ls\\\\bin\\\\shotcut.exe"', launcher)
        self.assertIn('L"\\"%ls\\" %ls", program, arguments', launcher)
        self.assertIn("CreateProcessW(program, commandLine", launcher)
        self.assertIn("MessageBoxW(", launcher)
        rc = read(LAUNCHER_RC)
        self.assertIn('IDI_ICON1 ICON "shotcut-logo-64.ico"', rc)
        # The icon is the multi-size icon of the new logo, up to 256 px.
        data = ICON.read_bytes()
        reserved, kind, count = struct.unpack("<HHH", data[:6])
        self.assertEqual((reserved, kind), (0, 1))
        sizes = {struct.unpack("<B", data[6 + 16 * i:7 + 16 * i])[0] or 256 for i in range(count)}
        self.assertTrue({16, 32, 48, 256} <= sizes, sizes)

    def test_w1_launcher_compiles_for_windows(self):
        gcc = shutil.which("x86_64-w64-mingw32-gcc")
        windres = shutil.which("x86_64-w64-mingw32-windres")
        if not gcc or not windres:
            self.skipTest("No MinGW cross compiler here (the Windows build compiles it)")
        with tempfile.TemporaryDirectory() as folder:
            res = Path(folder) / "launcher.res"
            exe = Path(folder) / "Shotcut AI.exe"
            subprocess.run([windres, "-I", str(PACKAGING), str(LAUNCHER_RC), "-O", "coff",
                            "-o", str(res)], check=True, capture_output=True)
            result = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-municode", "-mwindows",
                                     "-O2", str(LAUNCHER_C), str(res), "-o", str(exe)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b"MZ", exe.read_bytes()[:2])

    def test_w1_bundle_builds_the_launcher_instead_of_a_bat(self):
        bundle = read(BUNDLE)
        self.assertIn('rm -f "$DIST/Shotcut AI.bat"', bundle)
        self.assertIn("packaging/windows/shotcut-ai-launcher.rc", bundle)
        self.assertIn('gcc -municode -mwindows -O2 -s', bundle)
        self.assertIn('-o "$DIST/Shotcut AI.exe"', bundle)
        self.assertNotIn("@echo off", bundle)

    def test_w1_installer_asks_for_a_desktop_shortcut(self):
        iss = read(INSTALLER)
        tasks = re.search(r"\[Tasks\](.*?)\n\[", iss, re.S).group(1)
        desktop = [line for line in tasks.splitlines() if line.startswith("Name: \"desktopicon\"")]
        self.assertEqual(len(desktop), 1)
        self.assertIn("{cm:CreateDesktopIcon}", desktop[0])
        # Checked by default: the user only has to click Next.
        self.assertNotIn("unchecked", desktop[0])
        icons = re.search(r"\[Icons\](.*?)\n\[", iss, re.S).group(1)
        self.assertIn('Name: "{autodesktop}\\Shotcut AI"; Filename: "{app}\\bin\\shotcut.exe"', icons)
        self.assertIn("Tasks: desktopicon", icons)
        self.assertIn('Name: "{autoprograms}\\Shotcut AI"', icons)
        for setting in ("PrivilegesRequired=lowest", "SetupIconFile=shotcut-logo-64.ico",
                        "OutputBaseFilename=Shotcut-AI-Setup", 'AppMutex="Meltytech Shotcut Running Mutex"',
                        'MessagesFile: "compiler:Languages\\Spanish.isl"', "LicenseFile=..\\..\\COPYING"):
            self.assertIn(setting, iss)
        self.assertTrue((PROJECT_ROOT / "COPYING").is_file())
        # Its own id, and the upstream installer of Shotcut stays.
        app_id = re.search(r"^AppId=(.*)$", iss, re.M).group(1)
        self.assertNotIn(app_id, read(UPSTREAM_INSTALLER))
        self.assertIn("Name: desktopIcon;", read(UPSTREAM_INSTALLER))

    def test_w1_build_adds_python_and_checks_launcher_and_installer(self):
        ci = read(WINDOWS_CI)
        self.assertIn("python-$version-embed-amd64.zip", ci)
        self.assertIn("Expand-Archive python-embed.zip -DestinationPath dist\\Shotcut-AI\\python", ci)
        self.assertEqual(ci.count("--python dist\\Shotcut-AI\\python\\python.exe"), 2)
        self.assertIn('Get-Item "dist\\Shotcut-AI\\Shotcut AI.exe"', ci)
        self.assertIn('& $iscc /Qp "/DAppVersion=$env:VERSION" packaging\\windows\\shotcut-ai.iss', ci)
        self.assertIn('"/TASKS=desktopicon"', ci)
        self.assertIn('Join-Path $desktop "Shotcut AI.lnk"', ci)
        self.assertIn("if (Test-Path $shortcut) { throw \"The uninstaller left the desktop shortcut\" }",
                      ci)
        self.assertIn("name: Shotcut-AI-Setup", ci)
        self.assertIn("path: dist/Shotcut-AI-Setup.exe", ci)
        for smoke in (LIVE_SMOKE, ANALYSIS_SMOKE):
            self.assertIn('parser.add_argument("--python"', read(smoke))


# ---------------------------------------------------------------------------------------
class TestPhase10TranslationsAndDocs(unittest.TestCase):

    def test_t1_spanish_for_every_new_text(self):
        root = ET.parse(SPANISH).getroot()
        contexts = {c.findtext("name"): c for c in root.findall("context")}
        for name in ("AiAssistantDock", "AiTools"):
            self.assertIn(name, contexts)
            for message in contexts[name].findall("message"):
                source = message.findtext("source")
                translation = message.find("translation")
                with self.subTest(context=name, source=source[:40]):
                    self.assertTrue(translation.text)
                    self.assertNotEqual(translation.get("type"), "unfinished")
                    self.assertEqual(sorted(re.findall(r"%\d", source)),
                                     sorted(re.findall(r"%\d", translation.text)))
        for name, source in (("AiAssistantDock", DOCK_CPP), ("AiTools", TOOLS_CPP)):
            translated = {m.findtext("source") for m in contexts[name].findall("message")}
            missing = tr_texts(read(source)) - translated
            self.assertFalse(missing, "%s texts without Spanish: %s" % (name, missing))
        main = {m.findtext("source"): m.findtext("translation")
                for m in contexts["MainWindow"].findall("message")}
        self.assertEqual(main.get("AI Assistant: First Steps"), "Asistente IA: primeros pasos")
        self.assertEqual(main.get("AI"), "IA")

    def test_d1_beginner_guide(self):
        guide = read(GUIDE)
        for heading in ("## 1. Instalar", "## 2. Conectar con Claude", "## 3. Tu primer vídeo",
                        "## 4. Si algo no te gusta", "## 5. Exportar",
                        "## Prueba con alguien que no edita"):
            self.assertIn(heading, guide)
        self.assertIn("Shotcut-AI-Setup.exe", guide)
        self.assertIn("acceso directo en el escritorio", guide)
        self.assertIn("Deshacer este paso", guide)
        self.assertIn('return QStringLiteral(\n        "https://github.com/Foxlith/Shotcut-AI/blob/master/'
                      'docs/guia-principiante.md");', read(DOCK_CPP))

    def test_d1_guides_roadmap_and_traceability(self):
        mcp = read(DOCS_MCP)
        self.assertIn("## Recetas (prompts)", mcp)
        self.assertIn("Conectar con Claude", mcp)
        build = read(DOCS_BUILD)
        self.assertIn("Shotcut-AI-Setup", build)
        self.assertNotIn("Shotcut AI.bat", build)
        self.assertIn("Entrega UX", read(ROADMAP))
        self.assertIn("FASE 10", read(PLAN))
        agent = read(AGENT)
        self.assertIn("Fase 10", agent)
        self.assertIn("test_phase10_ai_beginner_ux_verification.py", agent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
