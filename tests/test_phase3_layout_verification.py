#!/usr/bin/env python3
"""
test_phase3_layout_verification.py

Phase 3 Verification Suite: Dock Structure & Minimalist Top Bar (Grafito)
- L1: Top bar (52 px) contents in src/mainwindow.ui and MainWindow::setupTopBar()
- L2: Classic menu bar hidden behind the main menu button, shortcuts preserved, Alt access
- L3: Icon sidebar (52 px) entries in MainWindow::setupSideBar()
- L4: 4-column dock arrangement in MainWindow::setupAndConnectDocks()
- L5: Serialized workspace states (src/defaultlayouts.h) restored into a replica with the
      same objectNames: exact 1440x900 geometry, 8 px gaps, sidebar in every workspace
- L6: Invariance - every command of the former toolbar keeps an entry point
- L7: Grafito QSS rules (capcut_theme.qss + fallback in mainwindow.cpp) and rendered colors
"""

import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QtMsgType, qInstallMessageHandler  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QTabBar, QToolBar, QToolButton, QWidget  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import generate_grafito_layout as layout  # noqa: E402

MAINWINDOW_UI = PROJECT_ROOT / "src" / "mainwindow.ui"
MAINWINDOW_CPP = PROJECT_ROOT / "src" / "mainwindow.cpp"
MAINWINDOW_H = PROJECT_ROOT / "src" / "mainwindow.h"
SETTINGS_CPP = PROJECT_ROOT / "src" / "settings.cpp"
CAPCUT_THEME_QSS = PROJECT_ROOT / "capcut_theme.qss"

# Commands that lived in the main toolbar before Phase 3 (Phase 2 / M3 layout).
FORMER_TOOLBAR_ACTIONS = [
    "actionOpen", "actionOpenOther2", "actionSave",
    "actionTimeline", "actionPlaylist", "actionFilters", "actionKeyframes",
    "actionProperties", "actionFiles", "actionMarkers", "actionSubtitles", "actionNotes",
    "actionAudioMeter", "actionEncode", "actionJobs",
    "actionRecent", "actionHistory", "actionWhatsThis",
    "actionLayoutLogging", "actionLayoutEditing", "actionLayoutEffects",
    "actionLayoutColor", "actionLayoutAudio", "actionLayoutPlayer",
]
SIDEBAR_ACTIONS = ["actionPlaylist", "actionFilters", "actionKeyframes",
                   "actionSubtitles", "actionNotes", "actionRecent"]


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def function_body(source, signature):
    """Return the body of a C++ function definition starting with `signature`."""
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:index + 1]
    raise ValueError(f"Unbalanced body for {signature}")


_app = None


def get_qapp():
    global _app
    if _app is None:
        _app = QApplication.instance()
        if _app is None:
            _app = QApplication(sys.argv[:1] + ["-platform", "offscreen"])
    return _app


class _QtWarningCollector:
    def __init__(self):
        self.messages = []

    def __call__(self, msg_type, context, message):
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            self.messages.append(message)


class TestPhase3StaticContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = ET.parse(MAINWINDOW_UI).getroot()
        cls.cpp = read(MAINWINDOW_CPP)
        cls.header = read(MAINWINDOW_H)

    # L1 -----------------------------------------------------------------
    def test_l1_top_bar_contains_only_grafito_actions(self):
        """mainToolBar holds only: menu | (logo, project, workspaces) | undo/redo | Jobs | Export."""
        toolbar = self.ui.find(".//widget[@name='mainToolBar']")
        self.assertIsNotNone(toolbar)
        actions = [a.get("name") for a in toolbar.findall("addaction")]
        self.assertEqual(actions, ["actionMainMenu", "dummyAction", "undoStartSeparator",
                                   "undoEndSeparator", "actionJobs", "actionEncode"])

    def test_l1_top_bar_metrics(self):
        """52 px bar + 8 px gap, 28 px logo, 52 px sidebar and 40 px sidebar buttons."""
        for constant, value in (("kTopBarHeight", 52), ("kPanelGap", 8), ("kTopBarLogoSize", 28),
                                ("kSideBarWidth", 52), ("kSideBarButtonSize", 40)):
            self.assertRegex(self.cpp, rf"static constexpr int {constant} = {value};")
        body = function_body(self.cpp, "void MainWindow::setupTopBar()")
        # Repolished (not only polished) so that QToolBar#mainToolBar sets its margins, and
        # before sizing it: the style sheet engine resets the minimum size when it polishes.
        self.assertIn("Util::repolish(ui->mainToolBar);", body)
        self.assertIn("ui->mainToolBar->setFixedHeight(kTopBarHeight + kPanelGap);", body)
        self.assertLess(body.index("Util::repolish(ui->mainToolBar);"),
                        body.index("ui->mainToolBar->setFixedHeight("))
        self.assertIn("ui->mainToolBar->setContentsMargins(0, 0, 0, kPanelGap);", body)
        self.assertIn('logo->setObjectName("topBarLogo");', body)
        self.assertIn("logo->setFixedSize(kTopBarLogoSize, kTopBarLogoSize);", body)
        self.assertIn('m_projectButton->setObjectName("projectButton");', body)
        self.assertIn('m_projectMetaLabel->setObjectName("projectMeta");', body)
        self.assertIn("Settings.recent()", body, "Project selector must list recent projects")

    def test_l1_project_metadata_line(self):
        """Metadata line: resolution, fps, audio channels and saved/modified state."""
        body = function_body(self.cpp, "void MainWindow::updateProjectInfo()")
        for token in ("MLT.profile().width()", "MLT.profile().height()", "MLT.profile().fps()",
                      'tr("Stereo")', 'tr("Mono")', 'tr("Saved")', 'tr("Modified")', "isWindowModified()",
                      "QChar(0x00B7)"):
            self.assertIn(token, body)
        self.assertIn("updateProjectInfo();", function_body(self.cpp, "void MainWindow::updateWindowTitle()"))
        self.assertIn("QEvent::ModifiedChange", function_body(self.cpp, "void MainWindow::changeEvent("))

    def test_l1_workspace_switcher_is_segmented(self):
        """updateLayoutSwitcher() builds one segmented control with the 6 workspaces in order."""
        body = function_body(self.cpp, "void MainWindow::updateLayoutSwitcher()")
        order = [m for m in re.findall(r"ui->(actionLayout\w+)", body)]
        self.assertEqual(order, ["actionLayoutLogging", "actionLayoutEditing", "actionLayoutEffects",
                                 "actionLayoutColor", "actionLayoutAudio", "actionLayoutPlayer"])
        self.assertIn("Qt::ToolButtonTextOnly", body)
        self.assertIn("ui->mainToolBar->insertWidget(ui->dummyAction, layoutSwitcher);", body)
        self.assertIn('kLayoutSwitcherName[] = "workspaceSwitcher"', self.cpp)

    def test_l1_jobs_and_export_buttons(self):
        """Jobs shows the pending job count; Export is the primary button bound to the Export panel."""
        body = function_body(self.cpp, "void MainWindow::applyTopBarButtonStyles()")
        self.assertIn('button->setObjectName("jobsButton");', body)
        self.assertIn('button->setObjectName("exportButton");', body)
        self.assertIn("widgetForAction(ui->actionEncode)", body)
        jobs = function_body(self.cpp, "void MainWindow::updateJobsButton()")
        self.assertIn('tr("Jobs (%1)")', jobs)
        self.assertIn("connect(&JOBS, &JobQueue::jobAdded, this, &MainWindow::updateJobsButton);", self.cpp)
        self.assertIn("connect(ui->actionEncode, SIGNAL(triggered()), this, SLOT(onEncodeTriggered()));", self.cpp)

    # L2 -----------------------------------------------------------------
    def test_l2_menu_bar_hidden_behind_main_menu(self):
        """Menu bar hidden (except native macOS bar) and its menus reused by the main menu button."""
        visibility = function_body(self.cpp, "void MainWindow::updateMenuBarVisibility()")
        self.assertIn("menuBar()->isNativeMenuBar()", visibility)
        self.assertIn("menuBar()->setVisible(Settings.showMenuBar() || !Settings.showToolBar());", visibility)
        menu = function_body(self.cpp, "void MainWindow::setupMainMenu()")
        self.assertIn("m_mainMenu->addActions(menuBar()->actions());", menu)
        self.assertIn("ui->actionMainMenu->setMenu(m_mainMenu);", menu)
        self.assertIn('settings.value("menuBar", false)', read(SETTINGS_CPP))

    def test_l2_menu_shortcuts_survive_hidden_menu_bar(self):
        """All menu actions are registered on the window so Ctrl+S, Alt+1..6, etc. keep working."""
        body = function_body(self.cpp, "void MainWindow::registerMenuShortcuts(QMenu *menu)")
        self.assertIn("registerMenuShortcuts(action->menu());", body)
        self.assertIn("addAction(action);", body)
        self.assertIn("registerMenuShortcuts(action->menu());", function_body(self.cpp, "MainWindow::MainWindow()"))

    def test_l2_alt_key_opens_main_menu(self):
        body = function_body(self.cpp, "bool MainWindow::eventFilter(QObject *target, QEvent *event)")
        self.assertIn("Qt::Key_Alt", body)
        self.assertIn("&MainWindow::showMainMenu", body)

    def test_l2_show_menu_bar_option(self):
        view_menu = self.ui.find(".//widget[@name='menuView']")
        entries = [a.get("name") for a in view_menu.findall("addaction")]
        self.assertIn("actionShowMenuBar", entries)
        self.assertIn("void on_actionShowMenuBar_triggered(bool checked);", self.header)

    # L3 -----------------------------------------------------------------
    def test_l3_sidebar_entries(self):
        """Sidebar: Media, Filters, Keyframes, Subtitles, Notes, Recent and Help pinned at the bottom."""
        body = function_body(self.cpp, "void MainWindow::setupSideBar()")
        order = re.findall(r"\{ui->(action\w+), m_(\w+)\}", body)
        self.assertEqual([a for a, _ in order], SIDEBAR_ACTIONS)
        self.assertEqual([d for _, d in order], ["playlistDock", "filtersDock", "keyframesDock",
                                                 "subtitlesDock", "notesDock", "recentDock"])
        self.assertLess(body.index("QSizePolicy::Expanding"), body.index("toolbar->addAction(ui->actionWhatsThis);"))
        self.assertIn('m_sideBarDock->setObjectName("sideBarDock");', body)
        self.assertIn('toolbar->setObjectName("sidebarToolBar");', body)
        self.assertIn("m_sideBarDock->setFixedWidth(kSideBarWidth);", body)
        self.assertIn('button->setProperty("active", visible);', body)
        # The sidebar never gets a title bar, whatever "Show Title Bars" says.
        self.assertIn("if (dock == m_sideBarDock)",
                      function_body(self.cpp, "void MainWindow::on_actionShowTitleBars_triggered(bool checked)"))

    # L4 -----------------------------------------------------------------
    def test_l4_dock_arrangement(self):
        body = function_body(self.cpp, "void MainWindow::setupAndConnectDocks()")
        for pair in (("m_playlistDock", "m_filesDock"), ("m_filesDock", "m_recentDock"),
                     ("m_propertiesDock", "m_jobsDock"), ("m_jobsDock", "m_historyDock"),
                     ("m_historyDock", "m_filtersDock"), ("m_timelineDock", "m_keyframesDock")):
            self.assertIn(f"tabifyDockWidget({pair[0]}, {pair[1]});", body)
        self.assertIn("splitDockWidget(m_sideBarDock, m_playlistDock, Qt::Horizontal);", body)
        self.assertIn("addDockWidget(Qt::RightDockWidgetArea, m_propertiesDock);", body)
        self.assertIn("addDockWidget(Qt::BottomDockWidgetArea, m_timelineDock);", body)
        self.assertIn("dock->setAttribute(Qt::WA_StyledBackground);", body)
        corners = function_body(self.cpp, "void MainWindow::resetDockCorners()")
        self.assertIn("setCorner(Qt::BottomLeftCorner, Qt::BottomDockWidgetArea);", corners)
        self.assertIn("setCorner(Qt::BottomRightCorner, Qt::BottomDockWidgetArea);", corners)
        self.assertIn("setContentsMargins(kPanelGap, 0, kPanelGap, kPanelGap);", self.cpp)
        self.assertIn("m_filtersDock->setMinimumSize(300, 300);", body)

    def test_l4_saved_layout_migration(self):
        """Saved layouts older than the Grafito layout are replaced once by the new default."""
        match = re.search(r"static constexpr int kDockLayoutVersion = (\d+);", self.cpp)
        self.assertGreaterEqual(int(match.group(1)), 2)
        body = function_body(self.cpp, "void MainWindow::readWindowSettings()")
        self.assertIn("restoreState(kLayoutEditingDefault);", body)
        self.assertIn("Settings.setLayoutMode(LayoutMode::Editing);", body)

    # L6 -----------------------------------------------------------------
    def test_l6_former_toolbar_commands_keep_an_entry_point(self):
        """Invariance: every command removed from the toolbar is still reachable."""
        menu_actions = set()
        for menu in self.ui.iter("widget"):
            if menu.get("class") == "QMenu":
                menu_actions.update(a.get("name") for a in menu.findall("addaction"))
        toolbar = {a.get("name") for a in self.ui.find(".//widget[@name='mainToolBar']").findall("addaction")}
        new_homes = "".join(function_body(self.cpp, sig) for sig in (
            "void MainWindow::setupSideBar()", "void MainWindow::setupMainMenu()",
            "void MainWindow::updateLayoutSwitcher()", "void MainWindow::setupTopBar()"))
        mirrored = function_body(self.cpp, "void MainWindow::mirrorViewActionShortcuts()")
        missing = []
        for action in FORMER_TOOLBAR_ACTIONS:
            if action in toolbar or action in menu_actions or f"ui->{action}" in new_homes:
                continue
            # Panel toggles: the action mirrors a dock whose toggle lives in the View menu.
            match = re.search(r"mirroredActions\.insert\((m_\w+)->toggleViewAction\(\), ui->" + action + r"\)",
                              mirrored)
            if match and f"ui->menuView->addAction({match.group(1)}->toggleViewAction());" in self.cpp:
                continue
            if action == "actionAudioMeter" and "audioMeterDock->toggleViewAction()" in mirrored \
                    and "menu->addAction(scopeDock->toggleViewAction());" in \
                    read(PROJECT_ROOT / "src" / "controllers" / "scopecontroller.cpp"):
                continue
            missing.append(action)
        self.assertEqual(missing, [], f"Commands without an entry point: {missing}")

    def test_l6_open_other_menu_safe_without_toolbar_button(self):
        body = function_body(self.cpp, "void MainWindow::on_actionOpenOther2_triggered()")
        self.assertIn("if (widget && widget->isVisible())", body)
        self.assertIn("QCursor::pos()", body)


class TestPhase3LayoutStates(unittest.TestCase):
    """L5: restore the serialized workspaces into the replica and measure them."""

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()
        cls.previous_qss = cls.app.styleSheet()
        cls.states = layout.read_states()

    @classmethod
    def tearDownClass(cls):
        cls.app.setStyleSheet(cls.previous_qss)

    def restore(self, workspace):
        state = self.states[layout.WORKSPACE_CONSTANTS[workspace]]
        ok, window, docks = layout.restore(self.app, state, workspace)
        self.addCleanup(window.close)
        self.assertTrue(ok, f"restoreState() rejected {workspace}")
        return window, docks

    @staticmethod
    def rect(widget):
        g = widget.geometry()
        return g.x(), g.y(), g.width(), g.height()

    def test_l5_six_workspace_states_present(self):
        self.assertEqual(set(layout.WORKSPACE_CONSTANTS.values()), set(self.states))

    def test_l5_editing_reference_geometry(self):
        """1440x900: 8 | 52 | 8 | 300 | 8 | 748 | 8 | 300 | 8, bar 52 + 8, row 500, timeline 324."""
        window, docks = self.restore("Editing")
        toolbar = window.findChild(QToolBar, "mainToolBar")
        self.assertEqual(self.rect(toolbar), (8, 0, 1424, 60))
        self.assertEqual(toolbar.contentsRect().height(), 52)
        self.assertEqual(self.rect(docks["sideBarDock"]), (8, 60, 52, 500))
        self.assertEqual(self.rect(window.centralWidget()), (376, 60, 748, 500))
        playlist, properties = docks["PlaylistDock"], docks["propertiesDock"]
        self.assertEqual((playlist.x(), playlist.width()), (68, 300))
        self.assertEqual((properties.x(), properties.width()), (1132, 300))
        self.assertEqual(playlist.geometry().bottom() + 1, 560)
        self.assertEqual(self.rect(docks["TimelineDock"]), (8, 568, 1424, 324))

    def test_l5_editing_tab_groups_and_visibility(self):
        window, docks = self.restore("Editing")
        media = {d.objectName() for d in window.tabifiedDockWidgets(docks["PlaylistDock"])}
        self.assertTrue({"FilesDock", "RecentDock"} <= media)
        inspector = {d.objectName() for d in window.tabifiedDockWidgets(docks["propertiesDock"])}
        self.assertTrue({"FiltersDock", "JobsDock", "historyDock"} <= inspector)
        visible = {name for name, dock in docks.items() if dock.isVisible()}
        self.assertEqual(visible, layout.WORKSPACE_SPECS["Editing"]["visible"] | {"sideBarDock"})
        bars = {tuple(bar.tabText(i) for i in range(bar.count())): bar
                for bar in window.findChildren(QTabBar) if bar.isVisible() and bar.count() > 1}
        self.assertIn(("Playlist", "Files", "Recent"), bars)
        # Phase 6: [ Inspector | Jobs | History ] first; Filters is still a tab.
        self.assertIn(("Inspector", "Jobs", "History", "Filters"), bars)
        # Tabs sit on top of the panels, right below the top bar.
        for bar in bars.values():
            self.assertEqual(bar.y(), 60)

    def test_l5_sidebar_first_column_in_every_workspace(self):
        for workspace in layout.WORKSPACE_SPECS:
            with self.subTest(workspace=workspace):
                window, docks = self.restore(workspace)
                sidebar = docks["sideBarDock"]
                self.assertTrue(sidebar.isVisible())
                self.assertEqual((sidebar.x(), sidebar.y(), sidebar.width()), (8, 60, 52))
                central = window.centralWidget()
                expected_x = 68 if workspace == "Player" else 376
                self.assertEqual(central.x(), expected_x)
                timeline = docks["TimelineDock"]
                if timeline.isVisible():
                    self.assertEqual((timeline.x(), timeline.width()), (8, 1424))
                    self.assertGreaterEqual(timeline.y(), 568)

    def test_l5_generator_is_deterministic(self):
        first, window, _ = layout.generate(self.app, "Editing")
        window.close()
        second, window, _ = layout.generate(self.app, "Editing")
        window.close()
        self.assertEqual(first, second)


class TestPhase3Theme(unittest.TestCase):
    """L7: Grafito rules for the top bar and sidebar, parsed and rendered by Qt."""

    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()
        cls.previous_qss = cls.app.styleSheet()
        cls.qss = read(CAPCUT_THEME_QSS)
        cls.cpp = read(MAINWINDOW_CPP)

    @classmethod
    def tearDownClass(cls):
        cls.app.setStyleSheet(cls.previous_qss)

    def rule(self, selector):
        match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", self.qss)
        self.assertIsNotNone(match, f"Missing QSS rule {selector}")
        return match.group(1)

    def test_l7_qss_rules(self):
        self.assertIn("margin: 0px 0px 8px 0px;", self.rule("QToolBar#mainToolBar"))
        self.assertIn("border-bottom: 1px solid #1F2229;", self.rule("QToolBar#mainToolBar"))
        logo = self.rule("QLabel#topBarLogo")
        self.assertIn("background-color: #FF7A45;", logo)
        self.assertIn("min-width: 28px;", logo)
        switcher = self.rule("QWidget#workspaceSwitcher")
        self.assertIn("background-color: #0F1115;", switcher)
        self.assertIn("border-radius: 10px;", switcher)
        pill = self.rule("QWidget#workspaceSwitcher QToolButton:checked")
        self.assertIn("background-color: #262A33;", pill)
        self.assertIn("color: #E8EAEE;", pill)
        self.assertIn("border-radius: 7px;", self.rule("QWidget#workspaceSwitcher QToolButton"))
        export = self.rule("QToolButton#exportButton")
        self.assertIn("background-color: #FF7A45;", export)
        self.assertIn("color: #140A05;", export)
        self.assertIn("background-color: #FF8F61;", self.rule("QToolButton#exportButton:hover"))
        self.assertIn("background-color: #E66835;", self.rule("QToolButton#exportButton:pressed"))
        self.assertIn("border: 1px solid #2A2E37;", self.rule("QToolButton#jobsButton"))
        self.assertIn("color: #858C98;", self.rule("QLabel#projectMeta"))
        self.assertIn("border-radius: 12px;", self.rule("QToolBar#sidebarToolBar"))
        self.assertIn("border-radius: 9px;", self.rule("QToolButton.sidebar-btn"))

    def test_l7_fallback_stylesheet_in_sync(self):
        for selector in ("QToolBar#mainToolBar {", "QLabel#topBarLogo {", "QWidget#workspaceSwitcher {",
                         "QWidget#workspaceSwitcher QToolButton:checked {", "QToolButton#exportButton {",
                         "QToolButton#jobsButton {", "QToolBar#sidebarToolBar {", "QLabel#projectMeta {"):
            self.assertIn(selector, self.cpp, f"Fallback stylesheet lacks {selector}")
        self.assertIn("QToolButton#exportButton { background-color: #FF7A45; color: #140A05;", self.cpp)

    def test_l7_qss_parses_without_warnings(self):
        collector = _QtWarningCollector()
        previous = qInstallMessageHandler(collector)
        try:
            self.app.setStyleSheet(self.qss)
            widget = QWidget()
            widget.setObjectName("workspaceSwitcher")
            widget.ensurePolished()
            self.app.processEvents()
        finally:
            qInstallMessageHandler(previous)
        parse_errors = [m for m in collector.messages if "style" in m.lower() and "parse" in m.lower()]
        self.assertEqual(parse_errors, [])

    def test_l7_rendered_top_bar_and_sidebar_colors(self):
        state = layout.read_states()[layout.WORKSPACE_CONSTANTS["Editing"]]
        ok, window, docks = layout.restore(self.app, state, "Editing")
        self.addCleanup(window.close)
        self.assertTrue(ok)
        image = window.grab().toImage()

        def color_at(widget, x, y):
            point = widget.mapTo(window, widget.rect().topLeft())
            return image.pixelColor(point.x() + x, point.y() + y).name().upper()

        export = window.findChild(QToolButton, "exportButton")
        self.assertEqual(color_at(export, 6, export.height() // 2), "#FF7A45")
        logo = window.findChild(QLabel, "topBarLogo")
        self.assertEqual((logo.width(), logo.height()), (28, 28))
        self.assertEqual(color_at(logo, 2, 14), "#FF7A45")
        self.assertEqual(logo.mapTo(window, logo.rect().center()).y(), 26 - 1)  # centered in the 52 px bar
        self.assertEqual(image.pixelColor(700, 51).name().upper(), "#1F2229")  # bar divider
        self.assertEqual(image.pixelColor(700, 56).name().upper(), "#0B0C0F")  # 8 px gap
        sidebar_bar = docks["sideBarDock"].widget()
        self.assertEqual(color_at(sidebar_bar, 26, 250), "#15171C")
        self.assertEqual(image.pixelColor(4, 300).name().upper(), "#0B0C0F")  # 8 px outer margin
        switcher = window.findChild(QWidget, "workspaceSwitcher")
        self.assertEqual(color_at(switcher, 2, switcher.height() // 2), "#0F1115")


if __name__ == "__main__":
    unittest.main()
