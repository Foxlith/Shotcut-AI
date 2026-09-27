#!/usr/bin/env python3
"""
Grafito workspace layout generator (Phase 3).

Builds a PySide6 replica of the Shotcut MainWindow dock/toolbar structure
(same objectNames as the C++ code, see MainWindow::setupAndConnectDocks(),
MainWindow::setupSideBar() and MainWindow::setupTopBar() in src/mainwindow.cpp),
arranges it at the 1440x900 reference size and serializes it with
QMainWindow::saveState(). The results are the kLayout*Default states in
src/defaultlayouts.h used by the workspace switcher.

QMainWindow::restoreState() only matches docks and toolbars by objectName, so a
replica with identical names produces states the real application restores.

Every workspace shares the Grafito skeleton (plan.md, section 3):

    8px margin | sidebar 52 | 8 | Media 300 | 8 | viewer (flex) | 8 | Inspector 300 | 8px
    top bar 52 + 8 gap, top row 500, 8px separator, timeline 324, 8px margin

Usage:
    python scripts/generate_grafito_layout.py                # print the Editing state (base64)
    python scripts/generate_grafito_layout.py --write        # update src/defaultlayouts.h
    python scripts/generate_grafito_layout.py --screenshot out.png [--workspace Color]
"""

import argparse
import os
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QSize, Qt  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QSizePolicy,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_LAYOUTS_H = os.path.join(PROJECT_ROOT, "src", "defaultlayouts.h")
THEME_QSS = os.path.join(PROJECT_ROOT, "capcut_theme.qss")
ICONS_DIR = os.path.join(PROJECT_ROOT, "icons", "dark", "32x32")

# Reference metrics (must match the constants in src/mainwindow.cpp).
WINDOW_SIZE = QSize(1440, 900)
TOP_BAR_HEIGHT = 52
PANEL_GAP = 8
SIDEBAR_WIDTH = 52
SIDEBAR_BUTTON_SIZE = 40
MEDIA_WIDTH = 300
INSPECTOR_WIDTH = 300
METER_WIDTH = 72
TOP_ROW_HEIGHT = 500
TIMELINE_HEIGHT = WINDOW_SIZE.height() - TOP_BAR_HEIGHT - PANEL_GAP - TOP_ROW_HEIGHT - PANEL_GAP - PANEL_GAP

# objectNames used by the C++ docks.
SIDEBAR = "sideBarDock"
MEDIA_TABS = ["PlaylistDock", "FilesDock", "RecentDock", "NotesDock", "SubtitlesDock", "ElementsDock"]
INSPECTOR_TABS = ["propertiesDock", "FiltersDock", "JobsDock", "historyDock", "EncodeDock"]
BOTTOM_TABS = ["TimelineDock", "KeyframesDock", "MarkersDock"]
# ScopeController: ScopeWidget objectName + "Dock", all created in the right area.
SCOPES = [
    "AudioLoudnessMeterDock", "AudioPeakMeterDock", "AudioSpectrumDock", "AudioSurroundDock",
    "AudioVectorDock", "AudioWaveformDock", "VideoHistogramDock", "RgbParadeDock",
    "RgbWaveformDock", "VideoVectorDock", "VideoWaveformDock", "VideoZoomDock",
]
VIDEO_SCOPES = ["VideoWaveformDock", "RgbParadeDock", "RgbWaveformDock", "VideoHistogramDock",
                "VideoVectorDock", "VideoZoomDock"]
AUDIO_SCOPES = ["AudioWaveformDock", "AudioLoudnessMeterDock", "AudioSpectrumDock",
                "AudioSurroundDock", "AudioVectorDock"]
METER = "AudioPeakMeterDock"
MEDIA_VISIBLE = {"PlaylistDock", "FilesDock", "RecentDock"}
INSPECTOR_VISIBLE = {"propertiesDock", "FiltersDock", "JobsDock", "historyDock"}


def _order(first, names):
    """Tab order with `first` moved to the front (the first tab is the raised one)."""
    return [first] + [n for n in names if n != first]


# Workspace specifications. Each column is a vertical stack of tab groups; the first
# dock of every group is its raised tab. "meter" is an optional narrow column between
# the viewer and the Inspector.
WORKSPACE_SPECS = {
    # Registro: browse and log media; no timeline.
    "Logging": {
        "left": [MEDIA_TABS],
        "right": [INSPECTOR_TABS, SCOPES],
        "bottom": [BOTTOM_TABS],
        "visible": MEDIA_VISIBLE | {"propertiesDock", "historyDock"},
    },
    # Edicion: the reference layout (MainWindow::setupAndConnectDocks()).
    "Editing": {
        "left": [MEDIA_TABS],
        "right": [INSPECTOR_TABS, _order(METER, SCOPES)],
        "bottom": [BOTTOM_TABS],
        "visible": MEDIA_VISIBLE | INSPECTOR_VISIBLE | {"TimelineDock"},
    },
    # Efectos: Filters raised in the Inspector, Keyframes next to the Timeline, peak meter.
    "Effects": {
        "left": [MEDIA_TABS],
        "meter": METER,
        "right": [_order("FiltersDock", INSPECTOR_TABS), [n for n in SCOPES if n != METER]],
        "bottom": [BOTTOM_TABS],
        "visible": MEDIA_VISIBLE | INSPECTOR_VISIBLE | {METER, "TimelineDock", "KeyframesDock"},
    },
    # Color: video scopes below the Inspector.
    "Color": {
        "left": [MEDIA_TABS],
        "right": [_order("FiltersDock", INSPECTOR_TABS),
                  VIDEO_SCOPES + [n for n in SCOPES if n not in VIDEO_SCOPES]],
        "bottom": [BOTTOM_TABS],
        "visible": MEDIA_VISIBLE | {"FiltersDock", "propertiesDock", "EncodeDock",
                                    "TimelineDock", "KeyframesDock"} | set(VIDEO_SCOPES),
    },
    # Audio: audio scopes below the Inspector and the peak meter next to the viewer.
    "Audio": {
        "left": [MEDIA_TABS],
        "meter": METER,
        "right": [_order("FiltersDock", INSPECTOR_TABS),
                  AUDIO_SCOPES + [n for n in SCOPES if n not in AUDIO_SCOPES + [METER]]],
        "bottom": [BOTTOM_TABS],
        "visible": MEDIA_VISIBLE | {"FiltersDock", "propertiesDock", "EncodeDock", METER,
                                    "TimelineDock", "KeyframesDock",
                                    "AudioWaveformDock", "AudioLoudnessMeterDock", "AudioSpectrumDock"},
    },
    # Reproductor: player only, the sidebar brings panels back.
    "Player": {
        "left": [MEDIA_TABS],
        "right": [INSPECTOR_TABS, SCOPES],
        "bottom": [BOTTOM_TABS],
        "visible": set(),
    },
}
# src/defaultlayouts.h constant for each workspace.
WORKSPACE_CONSTANTS = {
    "Logging": "kLayoutLoggingDefault",
    "Editing": "kLayoutEditingDefault",
    "Effects": "kLayoutEffectsDefault",
    "Color": "kLayoutColorDefault",
    "Audio": "kLayoutAudioDefault",
    "Player": "kLayoutPlayerDefault",
}

# Sidebar entries and their icons (ui->actionPlaylist, ... in src/mainwindow.ui).
SIDEBAR_ENTRIES = [
    ("Playlist", "view-media-playlist"), ("Filters", "view-filter"), ("Keyframes", "chronometer"),
    ("Subtitles", "subtitle"), ("Notes", "document-edit"), ("Recent", "document-open-recent"),
]
HELP_ENTRY = ("What's This?", "help-contextual")
WORKSPACE_LABELS = ["Logging", "Editing", "FX", "Color", "Audio", "Player"]


def load_theme():
    with open(THEME_QSS, "r", encoding="utf-8") as f:
        return f.read()


def icon(name):
    return QIcon(os.path.join(ICONS_DIR, name + ".png"))


def build_top_bar(workspace="Editing"):
    """Replica of MainWindow::setupTopBar() / updateLayoutSwitcher()."""
    toolbar = QToolBar("Toolbar")
    toolbar.setObjectName("mainToolBar")
    toolbar.setMovable(False)
    toolbar.setFloatable(False)
    toolbar.setIconSize(QSize(18, 18))
    toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
    toolbar.ensurePolished()  # as MainWindow::setupTopBar() does
    toolbar.setFixedHeight(TOP_BAR_HEIGHT + PANEL_GAP)
    toolbar.setContentsMargins(0, 0, 0, PANEL_GAP)

    menu_action = toolbar.addAction(icon("show-menu"), "Menu")
    menu_action.setMenu(QMenu(toolbar))
    menu_button = toolbar.widgetForAction(menu_action)
    menu_button.setObjectName("mainMenuButton")
    menu_button.setPopupMode(QToolButton.InstantPopup)

    logo = QLabel()
    logo.setObjectName("topBarLogo")
    logo.setFixedSize(28, 28)
    logo.setAlignment(Qt.AlignCenter)
    logo.setPixmap(QIcon(os.path.join(PROJECT_ROOT, "icons", "shotcut-logo-64.svg")).pixmap(QSize(20, 20)))
    toolbar.addWidget(logo)

    project = QWidget()
    project.setObjectName("projectInfo")
    layout = QVBoxLayout(project)
    layout.setContentsMargins(4, 0, 4, 0)
    layout.setSpacing(0)
    project_button = QToolButton()
    project_button.setObjectName("projectButton")
    project_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
    project_button.setPopupMode(QToolButton.InstantPopup)
    project_button.setAutoRaise(True)
    project_button.setMenu(QMenu(project_button))
    project_button.setText("Proyecto_Prueba_Shotcut_AI")
    meta = QLabel("1920×1080 · 30 fps · Stereo · Saved")
    meta.setObjectName("projectMeta")
    layout.addWidget(project_button, 0, Qt.AlignLeft | Qt.AlignVCenter)
    layout.addWidget(meta, 0, Qt.AlignLeft | Qt.AlignVCenter)
    toolbar.addWidget(project)

    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    toolbar.addWidget(spacer)

    switcher = QWidget()
    switcher.setObjectName("workspaceSwitcher")
    switcher.setAttribute(Qt.WA_StyledBackground)
    switcher.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    row = QHBoxLayout(switcher)
    row.setContentsMargins(3, 3, 3, 3)
    row.setSpacing(2)
    checked = list(WORKSPACE_SPECS).index(workspace)
    for index, text in enumerate(WORKSPACE_LABELS):
        button = QToolButton()
        button.setText(text)
        button.setCheckable(True)
        button.setChecked(index == checked)
        button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        button.setAutoRaise(True)
        row.addWidget(button)
    toolbar.addWidget(switcher)

    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    toolbar.addWidget(spacer)

    toolbar.addAction(icon("edit-undo"), "Undo")
    toolbar.addAction(icon("edit-redo"), "Redo")
    toolbar.addSeparator()
    jobs = toolbar.addAction(icon("run-build"), "Jobs")
    jobs_button = toolbar.widgetForAction(jobs)
    jobs_button.setObjectName("jobsButton")
    jobs_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    export = toolbar.addAction(icon("media-record"), "Export")
    export_button = toolbar.widgetForAction(export)
    export_button.setObjectName("exportButton")
    export_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
    return toolbar


def build_sidebar(window):
    """Replica of MainWindow::setupSideBar()."""
    sidebar = QDockWidget("Sidebar", window)
    sidebar.setObjectName(SIDEBAR)
    sidebar.setFeatures(QDockWidget.DockWidgetClosable)
    sidebar.setTitleBarWidget(QWidget())
    sidebar.setFixedWidth(SIDEBAR_WIDTH)
    bar = QToolBar("Sidebar", sidebar)
    bar.setObjectName("sidebarToolBar")
    bar.setOrientation(Qt.Vertical)
    bar.setMovable(False)
    bar.setFloatable(False)
    bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
    bar.setIconSize(QSize(18, 18))

    def add_entry(text, icon_name):
        action = bar.addAction(icon(icon_name), text)
        bar.widgetForAction(action).setFixedSize(SIDEBAR_BUTTON_SIZE, SIDEBAR_BUTTON_SIZE)

    for text, icon_name in SIDEBAR_ENTRIES:
        add_entry(text, icon_name)
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    bar.addWidget(spacer)
    add_entry(*HELP_ENTRY)
    sidebar.setWidget(bar)
    return sidebar


def build_window(workspace="Editing"):
    """Create the replica with every dock in its creation-time area (before arranging)."""
    window = QMainWindow()
    window.setObjectName("MainWindow")
    window.setDockNestingEnabled(True)
    window.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
    window.setContentsMargins(PANEL_GAP, 0, PANEL_GAP, PANEL_GAP)
    window.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
    window.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
    window.setCorner(Qt.BottomLeftCorner, Qt.BottomDockWidgetArea)
    window.setCorner(Qt.BottomRightCorner, Qt.BottomDockWidgetArea)

    central = QWidget()
    central.setObjectName("centralWidget")
    window.setCentralWidget(central)
    window.addToolBar(Qt.TopToolBarArea, build_top_bar(workspace))

    docks = {}

    def make_dock(name, area):
        dock = QDockWidget(name.replace("Dock", "").replace("history", "History")
                           .replace("properties", "Properties"), window)
        dock.setObjectName(name)
        dock.setWidget(QWidget())
        dock.hide()
        window.addDockWidget(area, dock)
        docks[name] = dock
        return dock

    for name in SCOPES:
        make_dock(name, Qt.RightDockWidgetArea)
    docks[SIDEBAR] = build_sidebar(window)
    window.addDockWidget(Qt.LeftDockWidgetArea, docks[SIDEBAR])
    for name in MEDIA_TABS + INSPECTOR_TABS + BOTTOM_TABS:
        make_dock(name, Qt.LeftDockWidgetArea)
    docks["propertiesDock"].setMinimumWidth(300)
    docks["FiltersDock"].setMinimumSize(300, 300)
    docks["historyDock"].setMinimumWidth(150)
    # As MainWindow::setupAndConnectDocks(): the theme paints docks as floating panels.
    for dock in docks.values():
        dock.setAttribute(Qt.WA_StyledBackground)
    return window, docks


def arrange(window, docks, workspace="Editing"):
    """Place every dock according to WORKSPACE_SPECS[workspace].

    Splits are made before tabifying so each split moves a single dock.
    """
    spec = WORKSPACE_SPECS[workspace]
    d = docks
    placed = {SIDEBAR}

    def column(groups, area, anchor, first_orientation):
        heads = []
        for index, group in enumerate(groups):
            head = d[group[0]]
            window.addDockWidget(area, head)
            if index == 0 and anchor is not None:
                window.splitDockWidget(anchor, head, first_orientation)
            elif index > 0:
                window.splitDockWidget(heads[0], head, Qt.Vertical)
            heads.append(head)
            placed.add(group[0])
        return heads

    # Column 1 (sidebar) and column 2 (Media).
    window.addDockWidget(Qt.LeftDockWidgetArea, d[SIDEBAR])
    left_heads = column(spec["left"], Qt.LeftDockWidgetArea, d[SIDEBAR], Qt.Horizontal)
    # Optional narrow meter column, then column 4 (Inspector).
    meter = spec.get("meter")
    if meter:
        window.addDockWidget(Qt.RightDockWidgetArea, d[meter])
        placed.add(meter)
    right_heads = column(spec["right"], Qt.RightDockWidgetArea, d[meter] if meter else None, Qt.Horizontal)
    # Bottom (full width).
    column(spec["bottom"], Qt.BottomDockWidgetArea, None, Qt.Horizontal)

    for group in spec["left"] + spec["right"] + spec["bottom"]:
        members = [n for n in group if n not in placed or n == group[0]]
        for first, second in zip(members, members[1:]):
            window.tabifyDockWidget(d[first], d[second])
            placed.add(second)

    visible = spec["visible"] | {SIDEBAR}
    for name, dock in d.items():
        dock.setVisible(name in visible)
    for group in spec["left"] + spec["right"] + spec["bottom"]:
        shown = [n for n in group if n in visible]
        if shown:
            d[shown[0]].raise_()
    return left_heads, right_heads


def apply_sizes(window, docks, workspace="Editing"):
    spec = WORKSPACE_SPECS[workspace]
    d = docks
    visible = spec["visible"]

    def first_visible(group):
        return next((d[n] for n in group if n in visible), None)

    widths = [(d[SIDEBAR], SIDEBAR_WIDTH)]
    media = first_visible(spec["left"][0])
    if media:
        widths.append((media, MEDIA_WIDTH))
    window.resizeDocks([w for w, _ in widths], [s for _, s in widths], Qt.Horizontal)
    meter = spec.get("meter")
    inspector = next(filter(None, (first_visible(g) for g in spec["right"])), None)
    right = []
    if meter and meter in visible:
        right.append((d[meter], METER_WIDTH))
    if inspector:
        right.append((inspector, INSPECTOR_WIDTH))
    if right:
        window.resizeDocks([w for w, _ in right], [s for _, s in right], Qt.Horizontal)
    stacked = [w for w in (first_visible(g) for g in spec["right"]) if w]
    if len(stacked) > 1:
        share = TOP_ROW_HEIGHT // len(stacked)
        window.resizeDocks(stacked, [share] * len(stacked), Qt.Vertical)
    timeline = first_visible(spec["bottom"][0])
    if timeline:
        window.resizeDocks([timeline], [TIMELINE_HEIGHT], Qt.Vertical)


def settle(app, rounds=5):
    for _ in range(rounds):
        app.processEvents()


def generate(app, workspace="Editing", with_theme=True):
    """Return (state bytes, window, docks) for the arranged reference layout."""
    if with_theme:
        app.setStyleSheet(load_theme())
    window, docks = build_window(workspace)
    arrange(window, docks, workspace)
    window.resize(WINDOW_SIZE)
    window.show()
    settle(app)
    apply_sizes(window, docks, workspace)
    settle(app)
    state = window.saveState()
    return bytes(state.data()), window, docks


def restore(app, state, workspace="Editing", with_theme=True):
    """Restore a serialized state into a fresh, unarranged replica (as the app does)."""
    if with_theme:
        app.setStyleSheet(load_theme())
    window, docks = build_window(workspace)
    window.resize(WINDOW_SIZE)
    ok = window.restoreState(QByteArray(state))
    window.show()
    settle(app)
    return ok, window, docks


def read_states():
    """Return {constant name: state bytes} from src/defaultlayouts.h."""
    with open(DEFAULT_LAYOUTS_H, "r", encoding="utf-8") as f:
        content = f.read()
    found = re.findall(r'(kLayout\w+Default)\s*=\s*QByteArray::fromBase64\(\s*"([^"]+)"\s*\)', content)
    return {name: QByteArray.fromBase64(value.encode("ascii")).data() for name, value in found}


def write_states(states):
    """Replace the base64 literal of each {constant name: state bytes} in src/defaultlayouts.h."""
    with open(DEFAULT_LAYOUTS_H, "r", encoding="utf-8") as f:
        content = f.read()
    for name, state in states.items():
        encoded = QByteArray(state).toBase64().data().decode("ascii")
        pattern = r'(' + name + r'\s*=\s*QByteArray::fromBase64\(\s*")[^"]+("\s*\))'
        content, count = re.subn(pattern, lambda m: m.group(1) + encoded + m.group(2), content)
        if count != 1:
            raise RuntimeError(f"{name} not found in src/defaultlayouts.h")
    with open(DEFAULT_LAYOUTS_H, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="update the kLayout*Default states in src/defaultlayouts.h")
    parser.add_argument("--workspace", default="Editing", choices=list(WORKSPACE_SPECS))
    parser.add_argument("--screenshot", help="save a PNG of the replica restored from the generated state")
    args = parser.parse_args()

    app = QApplication.instance() or QApplication(sys.argv)
    states = {}
    for workspace in WORKSPACE_SPECS:
        state, window, _ = generate(app, workspace)
        window.close()
        states[WORKSPACE_CONSTANTS[workspace]] = state
    if args.write:
        write_states(states)
        print(f"Updated {len(states)} workspace states in {DEFAULT_LAYOUTS_H}")
    else:
        print(QByteArray(states[WORKSPACE_CONSTANTS[args.workspace]]).toBase64().data().decode("ascii"))
    if args.screenshot:
        ok, restored, _ = restore(app, states[WORKSPACE_CONSTANTS[args.workspace]], args.workspace)
        if not ok:
            raise RuntimeError("restoreState() rejected the generated state")
        restored.grab().save(args.screenshot)
        print(f"Saved {args.screenshot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
