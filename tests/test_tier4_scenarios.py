#!/usr/bin/env python3
"""
Tier 4: Real-World Application Scenario Tests for Shotcut UI/UX Modernization
Uses pywin32 to launch Shotcut, load projects, verify Qt MainWindow rendering,
inspect shotcut-log.txt for 0 QML syntax errors or crashes, and assert clean WM_CLOSE exit (code 0).
(>= 7 realistic application-level scenarios).
"""

import os
import sys
import time
import subprocess
import unittest

import win32gui
import win32con

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHOTCUT_EXE = r"C:\Users\Fox\AppData\Local\Programs\Shotcut\shotcut.exe"
LOG_PATH = os.path.expanduser(r"~\AppData\Local\Meltytech\Shotcut\shotcut-log.txt")
SAMPLE_PROJECT = r"C:\Users\Fox\Desktop\ACAS\PROYECTO_ACA_POO1_SHOTCUT.mlt"
FIXTURE_PROJECT = os.path.join(PROJECT_ROOT, "tests", "fixtures", "minimal_project.mlt")


def find_shotcut_window(timeout_seconds=20):
    """
    Locates the Shotcut Qt MainWindow.
    Differentiates between the temporary splash screen (Title=='Shotcut')
    and the main window (contains '-' or window title with project info).
    """
    start = time.time()
    while time.time() - start < timeout_seconds:
        time.sleep(0.5)
        candidates = []

        def enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                cls = win32gui.GetClassName(hwnd)
                if "shotcut" in title.lower() and cls.startswith("Qt"):
                    candidates.append((hwnd, title, cls))

        win32gui.EnumWindows(enum_cb, None)
        for hwnd, title, cls in candidates:
            # Main window contains hyphens separating project, profile, and app name
            if "-" in title and "shotcut" in title.lower():
                return hwnd, title, cls
            # Or if title has Shotcut and dimensions > 400x300
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if "shotcut" in title.lower() and w > 500 and h > 300:
                return hwnd, title, cls

    return None, None, None


def check_log_errors(log_path, start_offset=0):
    """Scan log file from start_offset for critical QML errors or fatal exceptions."""
    if not os.path.isfile(log_path):
        return []
    critical_errors = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(start_offset)
        for line in f:
            lower = line.lower()
            if "syntaxerror" in lower or "component is not ready" in lower:
                critical_errors.append(line.strip())
            elif "[fatal  ]" in lower or "[panic  ]" in lower:
                critical_errors.append(line.strip())
    return critical_errors


def get_log_size(log_path):
    """Returns current size of log file to mark start offset."""
    if os.path.isfile(log_path):
        return os.path.getsize(log_path)
    return 0


class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: End-to-End Real-World Application Workloads & GUI Lifecycle"""

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(SHOTCUT_EXE):
            raise unittest.SkipTest(f"Shotcut executable not found at {SHOTCUT_EXE}")

    def tearDown(self):
        # Ensure no dangling shotcut processes remain after test
        subprocess.run(["powershell", "-Command", "Get-Process shotcut -ErrorAction SilentlyContinue | Stop-Process -Force"],
                       capture_output=True)
        time.sleep(0.5)

    def test_scenario_1_fresh_session_startup_and_shutdown(self):
        """Scenario 1: Empty fresh session startup, window detection, and clean WM_CLOSE exit."""
        start_offset = get_log_size(LOG_PATH)
        proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade"])
        try:
            hwnd, title, cls = find_shotcut_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd, "Shotcut MainWindow not detected within timeout")
            self.assertIn("shotcut", title.lower())

            # Allow UI components to settle
            time.sleep(3)

            # Check runtime log for QML parse errors
            errors = check_log_errors(LOG_PATH, start_offset)
            self.assertEqual(len(errors), 0, f"Critical log errors detected: {errors}")

            # Send graceful close
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0, f"Expected clean exit code 0, got {ret}")
        finally:
            if proc.poll() is None:
                proc.terminate()

    def test_scenario_2_default_project_load_with_tracks(self):
        """Scenario 2: Minimal project load with color producer and tractor tracks."""
        self.assertTrue(os.path.isfile(FIXTURE_PROJECT), f"Fixture project missing at {FIXTURE_PROJECT}")
        start_offset = get_log_size(LOG_PATH)
        proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade", FIXTURE_PROJECT])
        try:
            hwnd, title, cls = find_shotcut_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd, "MainWindow not detected when opening fixture project")

            time.sleep(3)

            errors = check_log_errors(LOG_PATH, start_offset)
            self.assertEqual(len(errors), 0, f"Critical log errors: {errors}")

            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0)
        finally:
            if proc.poll() is None:
                proc.terminate()

    def test_scenario_3_real_multitrack_aca_project_load(self):
        """Scenario 3: Real multi-track audio/video project load."""
        if not os.path.isfile(SAMPLE_PROJECT):
            self.skipTest(f"Sample project not found at {SAMPLE_PROJECT}")

        start_offset = get_log_size(LOG_PATH)
        proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade", SAMPLE_PROJECT])
        try:
            hwnd, title, cls = find_shotcut_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd, "MainWindow not detected for sample project")

            time.sleep(3)

            errors = check_log_errors(LOG_PATH, start_offset)
            self.assertEqual(len(errors), 0, f"Critical log errors: {errors}")

            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0)
        finally:
            if proc.poll() is None:
                proc.terminate()

    def test_scenario_4_missing_project_file_graceful_recovery(self):
        """Scenario 4: Non-existent project path launches Shotcut without crash."""
        start_offset = get_log_size(LOG_PATH)
        missing_proj = os.path.join(PROJECT_ROOT, "tests", "fixtures", "non_existent_404.mlt")
        proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade", missing_proj])
        try:
            hwnd, title, cls = find_shotcut_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd, "MainWindow should appear even if file does not exist")

            time.sleep(2)

            errors = check_log_errors(LOG_PATH, start_offset)
            self.assertEqual(len(errors), 0)

            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0)
        finally:
            if proc.poll() is None:
                proc.terminate()

    def test_scenario_5_headless_offscreen_platform_execution(self):
        """Scenario 5: Headless execution with Qt offscreen platform plugin."""
        proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade", "-platform", "offscreen"])
        try:
            # Let offscreen initialize QML engine and event loop
            time.sleep(3)
            self.assertIsNone(proc.poll(), "Process should remain running in offscreen mode")
            proc.terminate()
            ret = proc.wait(timeout=5)
            self.assertIsNotNone(ret)
        finally:
            if proc.poll() is None:
                proc.kill()

    def test_scenario_6_quick_startup_and_immediate_close(self):
        """Scenario 6: Immediate close upon window detection tests race condition resilience."""
        proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade"])
        try:
            hwnd, title, cls = find_shotcut_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd)

            # Immediately post close without settling
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0, f"Expected 0 on quick close, got {ret}")
        finally:
            if proc.poll() is None:
                proc.terminate()

    def test_scenario_7_consecutive_launch_lifecycle_stability(self):
        """Scenario 7: Consecutive launch-close-relaunch cycle confirms clean teardown."""
        # Cycle 1
        proc1 = subprocess.Popen([SHOTCUT_EXE, "--noupgrade"])
        try:
            hwnd1, _, _ = find_shotcut_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd1)
            time.sleep(1)
            win32gui.PostMessage(hwnd1, win32con.WM_CLOSE, 0, 0)
            ret1 = proc1.wait(timeout=10)
            self.assertEqual(ret1, 0)
        finally:
            if proc1.poll() is None:
                proc1.terminate()

        time.sleep(1)

        # Cycle 2
        proc2 = subprocess.Popen([SHOTCUT_EXE, "--noupgrade"])
        try:
            hwnd2, _, _ = find_shotcut_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd2)
            time.sleep(1)
            win32gui.PostMessage(hwnd2, win32con.WM_CLOSE, 0, 0)
            ret2 = proc2.wait(timeout=10)
            self.assertEqual(ret2, 0)
        finally:
            if proc2.poll() is None:
                proc2.terminate()

    def test_scenario_8_window_geometry_and_visibility_verification(self):
        """Scenario 8: Window geometry dimensions and visibility validation."""
        start_offset = get_log_size(LOG_PATH)
        proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade"])
        try:
            hwnd, title, cls = find_shotcut_window(timeout_seconds=15)
            self.assertIsNotNone(hwnd)

            # Assert visibility and minimum desktop dimensions
            self.assertTrue(win32gui.IsWindowVisible(hwnd), "Main window is not visible")
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            self.assertGreaterEqual(w, 600, f"Window width too small: {w}")
            self.assertGreaterEqual(h, 400, f"Window height too small: {h}")

            errors = check_log_errors(LOG_PATH, start_offset)
            self.assertEqual(len(errors), 0)

            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0)
        finally:
            if proc.poll() is None:
                proc.terminate()


if __name__ == "__main__":
    unittest.main()
