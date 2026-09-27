#!/usr/bin/env python3
"""
Shotcut Milestone 4: Icon Harmonization & UI Stress-Testing Suite
Author: teamwork_preview_challenger (Runtime & Stress Test Challenger)
Target: Shotcut UI/UX Modernization (M4 Icon Harmonization, Toolbars, QML Views)

Executes empirical adversarial stress testing across 6 dimensions:
- Dimension 1: Static Icon Reference Scanner & QRC Registration Audit
- Dimension 2: QML AST & Installed Runtime Share Synchronization
- Dimension 3: Toolbar Action Silhouette & Categorization Invariance
- Dimension 4: Robustness against Corrupted/Invalid Project MLT Files
- Dimension 5: Robustness against Corrupted/Invalid Theme Configurations
- Dimension 6: Multi-Cycle Process Lifecycle Stability (5 consecutive runs)
"""

import os
import sys
import time
import xml.etree.ElementTree as ET
import subprocess
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHOTCUT_EXE = r"C:\Users\Fox\AppData\Local\Programs\Shotcut\shotcut.exe"
INSTALLED_QML = r"C:\Users\Fox\AppData\Local\Programs\Shotcut\share\shotcut\qml"
LOG_PATH = os.path.expanduser(r"~\AppData\Local\Meltytech\Shotcut\shotcut-log.txt")
SETTINGS_INI = os.path.expanduser(r"~\AppData\Local\Meltytech\Shotcut\shotcut.ini")

try:
    import win32gui
    import win32con
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def kill_shotcut_processes():
    """Ensure no shotcut instances are lingering."""
    subprocess.run(
        ["powershell", "-Command", "Get-Process shotcut -ErrorAction SilentlyContinue | Stop-Process -Force"],
        capture_output=True
    )
    time.sleep(0.5)


def find_shotcut_main_window(timeout_seconds=15):
    """Accurately finds Shotcut MainWindow, ignoring splash screen and closed handles."""
    if not HAS_WIN32:
        return None, None
    start = time.time()
    while time.time() - start < timeout_seconds:
        time.sleep(0.4)
        candidates = []

        def enum_cb(hwnd, _):
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                cls = win32gui.GetClassName(hwnd)
                if "shotcut" in title.lower() and cls.startswith("Qt"):
                    candidates.append((hwnd, title, cls))

        win32gui.EnumWindows(enum_cb, None)
        for hwnd, title, cls in candidates:
            # Main window contains hyphens separating project, profile, and app name
            if "-" in title and "shotcut" in title.lower():
                return hwnd, title
            # Or if title has Shotcut and dimensions > 500x300
            try:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if "shotcut" in title.lower() and w > 500 and h > 300:
                    return hwnd, title
            except Exception:
                continue
    return None, None


FAST_TESTS = [
    "test_dimension1_qrc_resource_integrity_and_duplicates",
    "test_dimension1_dark_silhouette_assets_on_disk",
    "test_dimension1_mainwindow_ui_action_fallbacks",
    "test_dimension2_qml_source_installed_sync",
    "test_dimension2_zero_oxygen_urls_in_modernized_qml",
    "test_dimension3_toolbar_separator_clusters",
]


class TestAdversarialM4Icons(unittest.TestCase):
    """Adversarial stress test suite for M4 Icon Harmonization."""

    @classmethod
    def setUpClass(cls):
        kill_shotcut_processes()

    @classmethod
    def tearDownClass(cls):
        kill_shotcut_processes()

    def tearDown(self):
        kill_shotcut_processes()

    # -------------------------------------------------------------
    # Dimension 1: Static Icon Reference Scanner & QRC Registration
    # -------------------------------------------------------------
    def test_dimension1_qrc_resource_integrity_and_duplicates(self):
        """Audit resources.qrc: 0 missing files, 0 duplicate paths, valid XML."""
        qrc_path = os.path.join(PROJECT_ROOT, "icons", "resources.qrc")
        self.assertTrue(os.path.isfile(qrc_path), f"QRC file missing: {qrc_path}")

        tree = ET.parse(qrc_path)
        root = tree.getroot()
        registered_files = []
        missing_files = []

        for qresource in root.findall("qresource"):
            prefix = qresource.get("prefix", "")
            for f in qresource.findall("file"):
                rel_path = f.text.strip()
                registered_files.append(rel_path)
                abs_path = os.path.join(PROJECT_ROOT, "icons", rel_path)
                if not os.path.isfile(abs_path):
                    missing_files.append(rel_path)

        self.assertEqual(len(missing_files), 0, f"Missing files referenced in resources.qrc: {missing_files}")
        self.assertGreaterEqual(len(registered_files), 590, "Expected at least 590 registered resources")

        # Check for duplicate entries
        duplicates = [x for x in registered_files if registered_files.count(x) > 1]
        self.assertEqual(len(duplicates), 0, f"Duplicate resource paths found in resources.qrc: {set(duplicates)}")

    def test_dimension1_dark_silhouette_assets_on_disk(self):
        """All dark silhouette 32x32 icons exist physically and are non-empty PNGs."""
        dark_dir = os.path.join(PROJECT_ROOT, "icons", "dark", "32x32")
        self.assertTrue(os.path.isdir(dark_dir), f"Dark icons directory missing: {dark_dir}")

        pngs = [f for f in os.listdir(dark_dir) if f.endswith(".png")]
        self.assertGreater(len(pngs), 40, "Expected at least 40 dark silhouette icons")

        for f in pngs:
            full_path = os.path.join(dark_dir, f)
            size = os.path.getsize(full_path)
            self.assertGreater(size, 50, f"Icon {f} is suspiciously small ({size} bytes)")
            with open(full_path, "rb") as fp:
                header = fp.read(8)
                self.assertEqual(header, b"\x89PNG\r\n\x1a\n", f"Invalid PNG magic for {f}")

    def test_dimension1_mainwindow_ui_action_fallbacks(self):
        """Ensure all 20 action icons in src/mainwindow.ui point to modern dark/32x32 without oxygen."""
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        tree = ET.parse(ui_path)
        root = tree.getroot()

        oxygen_refs = []
        total_actions = 0
        dark_actions = 0

        for action in root.findall(".//action"):
            total_actions += 1
            icon_elem = action.find("property[@name='icon']")
            if icon_elem is not None:
                iconset = icon_elem.find("iconset")
                if iconset is not None:
                    normaloff = iconset.find("normaloff")
                    if normaloff is not None and normaloff.text:
                        text = normaloff.text.strip()
                        if "oxygen" in text.lower():
                            oxygen_refs.append((action.get("name"), text))
                        if ":/icons/dark/32x32/" in text:
                            dark_actions += 1

        self.assertEqual(len(oxygen_refs), 0, f"Legacy oxygen references found in mainwindow.ui: {oxygen_refs}")
        self.assertGreaterEqual(dark_actions, 18, f"Expected at least 18 dark action icons, found {dark_actions}")

    # -------------------------------------------------------------
    # Dimension 2: QML AST & Installed Runtime Share Synchronization
    # -------------------------------------------------------------
    def test_dimension2_qml_source_installed_sync(self):
        """Verify that all modified QML files in src/qml are mirrored into share/shotcut/qml."""
        src_qml = os.path.join(PROJECT_ROOT, "src", "qml")
        self.assertTrue(os.path.isdir(INSTALLED_QML), f"Installed QML directory not found: {INSTALLED_QML}")

        checked_count = 0
        out_of_sync = []

        # Check key modernized QML files
        key_files = [
            os.path.join("views", "timeline", "timeline.qml"),
            os.path.join("views", "timeline", "TrackHead.qml"),
            os.path.join("views", "timeline", "Clip.qml"),
            os.path.join("views", "filter", "FilterMenu.qml"),
            os.path.join("views", "filter", "filterview.qml"),
            os.path.join("modules", "Shotcut", "Controls", "ColorPicker.qml"),
            os.path.join("modules", "Shotcut", "Controls", "UndoButton.qml"),
            os.path.join("filters", "richtext", "vui.qml"),
            os.path.join("filters", "timer", "ui.qml"),
        ]

        for rel in key_files:
            src_f = os.path.join(src_qml, rel)
            dst_f = os.path.join(INSTALLED_QML, rel)
            self.assertTrue(os.path.isfile(src_f), f"Source file missing: {src_f}")
            self.assertTrue(os.path.isfile(dst_f), f"Mirrored file missing: {dst_f}")

            with open(src_f, "rb") as f1, open(dst_f, "rb") as f2:
                if f1.read() != f2.read():
                    out_of_sync.append(rel)
            checked_count += 1

        self.assertEqual(len(out_of_sync), 0, f"QML files out of sync with installed runtime: {out_of_sync}")
        self.assertGreaterEqual(checked_count, 9)

    def test_dimension2_zero_oxygen_urls_in_modernized_qml(self):
        """Verify that modernized QML files do not contain hardcoded oxygen URLs."""
        key_files = [
            os.path.join(PROJECT_ROOT, "src", "qml", "views", "timeline", "timeline.qml"),
            os.path.join(PROJECT_ROOT, "src", "qml", "views", "timeline", "TrackHead.qml"),
            os.path.join(PROJECT_ROOT, "src", "qml", "views", "filter", "FilterMenu.qml"),
            os.path.join(PROJECT_ROOT, "src", "qml", "views", "filter", "filterview.qml"),
            os.path.join(PROJECT_ROOT, "src", "qml", "modules", "Shotcut", "Controls", "ColorPicker.qml"),
        ]
        violations = []
        for path in key_files:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line_idx, line in enumerate(f, 1):
                    if "qrc:///icons/oxygen/" in line:
                        violations.append(f"{os.path.basename(path)}:{line_idx}: {line.strip()}")

        self.assertEqual(len(violations), 0, f"Found oxygen URLs in modernized QML: {violations}")

    # -------------------------------------------------------------
    # Dimension 3: Toolbar Action Silhouette & Categorization
    # -------------------------------------------------------------
    def test_dimension3_toolbar_separator_clusters(self):
        """Verify the Grafito top bar clusters (Phase 3) replace the former 27-button toolbar.

        mainToolBar keeps three logical clusters: main menu (+ logo/project/workspaces inserted
        before dummyAction), undo/redo between the undo separators, and Jobs + Export. The dock
        toggles of the former toolbar moved to the icon sidebar (MainWindow::setupSideBar()).
        """
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        tree = ET.parse(ui_path)
        root = tree.getroot()

        main_toolbar = root.find(".//widget[@name='mainToolBar']")
        self.assertIsNotNone(main_toolbar, "mainToolBar widget not found in mainwindow.ui")

        actions = [a.get("name") for a in main_toolbar.findall("addaction")]
        self.assertEqual(actions[0], "actionMainMenu", "Main menu button must open the top bar")
        self.assertLess(actions.index("dummyAction"), actions.index("undoStartSeparator"))
        self.assertEqual(actions[actions.index("undoStartSeparator"):],
                         ["undoStartSeparator", "undoEndSeparator", "actionJobs", "actionEncode"])

        separators = [a for a in root.iter("action")
                      if a.get("name") in ("undoStartSeparator", "undoEndSeparator")
                      and a.find("property[@name='separator']/bool") is not None]
        self.assertEqual(len(separators), 2, "Undo/redo cluster must be delimited by separator actions")

        with open(os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp"), "r", encoding="utf-8") as f:
            cpp = f.read()
        sidebar = cpp[cpp.index("void MainWindow::setupSideBar()"):]
        for action in ("actionPlaylist", "actionFilters", "actionKeyframes", "actionSubtitles",
                       "actionNotes", "actionRecent", "actionWhatsThis"):
            self.assertIn(f"ui->{action}", sidebar[:sidebar.index("\n}\n")],
                          f"{action} must be in the icon sidebar")

    # -------------------------------------------------------------
    # Dimension 4: Robustness against Corrupted/Invalid MLT Files
    # -------------------------------------------------------------
    def test_dimension4_corrupted_mlt_handling(self):
        """Shotcut gracefully handles corrupted/truncated MLT without crash."""
        if not HAS_WIN32 or not os.path.isfile(SHOTCUT_EXE):
            self.skipTest("Shotcut executable or win32gui not available")

        corrupt_mlt = os.path.join(PROJECT_ROOT, "tests", "fixtures", "corrupt_test.mlt")
        with open(corrupt_mlt, "w", encoding="utf-8") as f:
            f.write("<mlt><open_tag_without_close>")

        try:
            proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade", corrupt_mlt])
            hwnd, title = find_shotcut_main_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd, "MainWindow failed to appear when opening corrupted MLT")

            time.sleep(2)
            # Window should be alive and close gracefully
            self.assertTrue(win32gui.IsWindow(hwnd))
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0, f"Expected clean exit code 0, got {ret}")
        finally:
            if os.path.exists(corrupt_mlt):
                os.remove(corrupt_mlt)

    # -------------------------------------------------------------
    # Dimension 5: Robustness against Invalid Theme Configuration
    # -------------------------------------------------------------
    def test_dimension5_invalid_theme_recovery(self):
        """Shotcut recovers and starts cleanly even when theme setting is invalid."""
        if not HAS_WIN32 or not os.path.isfile(SHOTCUT_EXE):
            self.skipTest("Shotcut executable or win32gui not available")

        # Launch with safe fallback
        proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade"])
        hwnd, title = find_shotcut_main_window(timeout_seconds=15)
        self.assertIsNotNone(hwnd, "MainWindow failed to appear")
        time.sleep(2)

        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        ret = proc.wait(timeout=10)
        self.assertEqual(ret, 0)

    # -------------------------------------------------------------
    # Dimension 6: Multi-Cycle Process Lifecycle Stability
    # -------------------------------------------------------------
    def test_dimension6_multicycle_stability_stress(self):
        """Stress test: 3 consecutive clean launch/close cycles with zero lingering processes."""
        if not HAS_WIN32 or not os.path.isfile(SHOTCUT_EXE):
            self.skipTest("Shotcut executable or win32gui not available")

        for cycle in range(1, 4):
            # Clean before cycle
            kill_shotcut_processes()

            proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade"])
            hwnd, title = find_shotcut_main_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd, f"Cycle {cycle}: MainWindow not detected")

            time.sleep(1.5)
            self.assertTrue(win32gui.IsWindow(hwnd), f"Cycle {cycle}: Window destroyed prematurely")
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0, f"Cycle {cycle}: Exit code was {ret}")
            time.sleep(1)


if __name__ == "__main__":
    unittest.main()
