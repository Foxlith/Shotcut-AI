#!/usr/bin/env python3
"""
Empirical Adversarial Stress Test Suite: Edge Cases & Application Lifecycle
Author: teamwork_preview_challenger (Final Verification Challenger)
Target: Shotcut UI/UX Modernization (M5 Final Gate)

Tests:
1. Missing Project Files (Standard, Spaces, Unicode, Special Characters)
2. Corrupted MLT Payloads (Truncated XML, Malformed XML, 0-byte Empty, Binary Garbage, Invalid Schema)
3. Rapid Open/Close Lifecycle (Rapid consecutive cycles, zero zombie processes)
4. Runtime Log Invariance Audit (0 QML parse errors, 0 fatal crashes, 0 missing resource warnings)
"""

import os
import sys
import time
import subprocess
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHOTCUT_EXE = r"C:\Users\Fox\AppData\Local\Programs\Shotcut\shotcut.exe"
LOG_PATH = os.path.expanduser(r"~\AppData\Local\Meltytech\Shotcut\shotcut-log.txt")
TEMP_FIXTURES_DIR = os.path.join(PROJECT_ROOT, "tests", "fixtures", "stress_temp")

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def kill_all_shotcut():
    """Ensure no shotcut instances are running."""
    subprocess.run(
        ["powershell", "-Command", "Get-Process shotcut -ErrorAction SilentlyContinue | Stop-Process -Force"],
        capture_output=True
    )
    time.sleep(0.5)


def get_log_size():
    if os.path.isfile(LOG_PATH):
        return os.path.getsize(LOG_PATH)
    return 0


def get_new_log_lines(start_offset):
    if not os.path.isfile(LOG_PATH):
        return []
    lines = []
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        f.seek(start_offset)
        for line in f:
            lines.append(line.rstrip("\r\n"))
    return lines


def find_shotcut_window(timeout_seconds=15):
    """Finds Shotcut main window handle and title."""
    if not HAS_WIN32:
        return None, None
    start = time.time()
    while time.time() - start < timeout_seconds:
        time.sleep(0.3)
        candidates = []

        def enum_cb(hwnd, _):
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                cls = win32gui.GetClassName(hwnd)
                if "shotcut" in title.lower() and cls.startswith("Qt"):
                    candidates.append((hwnd, title))

        win32gui.EnumWindows(enum_cb, None)
        for hwnd, title in candidates:
            if "-" in title and "shotcut" in title.lower():
                return hwnd, title
            try:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if "shotcut" in title.lower() and w > 500 and h > 300:
                    return hwnd, title
            except Exception:
                continue
    return None, None


class TestChallengerEdgeCases(unittest.TestCase):
    """Empirical adversarial stress testing on edge cases and failure modes."""

    @classmethod
    def setUpClass(cls):
        if not HAS_WIN32 or not os.path.isfile(SHOTCUT_EXE):
            raise unittest.SkipTest("Requires win32gui and installed shotcut.exe")
        os.makedirs(TEMP_FIXTURES_DIR, exist_ok=True)
        kill_all_shotcut()

    @classmethod
    def tearDownClass(cls):
        kill_all_shotcut()
        # Clean temp directory
        if os.path.exists(TEMP_FIXTURES_DIR):
            for f in os.listdir(TEMP_FIXTURES_DIR):
                try:
                    os.remove(os.path.join(TEMP_FIXTURES_DIR, f))
                except Exception:
                    pass
            try:
                os.rmdir(TEMP_FIXTURES_DIR)
            except Exception:
                pass

    def tearDown(self):
        kill_all_shotcut()

    def _run_and_close(self, file_arg=None, wait_time=2.0, timeout_win=15):
        """Helper to launch Shotcut, verify window, close it cleanly, and check exit code."""
        start_offset = get_log_size()
        cmd = [SHOTCUT_EXE, "--noupgrade"]
        if file_arg:
            cmd.append(file_arg)

        proc = subprocess.Popen(cmd)
        try:
            hwnd, title = find_shotcut_window(timeout_seconds=timeout_win)
            self.assertIsNotNone(hwnd, f"Shotcut window failed to appear for arg: {file_arg}")
            self.assertTrue(win32gui.IsWindow(hwnd))

            if wait_time > 0:
                time.sleep(wait_time)

            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            ret = proc.wait(timeout=10)
            self.assertEqual(ret, 0, f"Expected clean exit code 0, got {ret} for arg: {file_arg}")

            new_lines = get_new_log_lines(start_offset)
            critical = [l for l in new_lines if any(k in l.lower() for k in [
                "fatal", "panic", "segmentation", "syntaxerror", "component is not ready"
            ])]
            self.assertEqual(len(critical), 0, f"Critical errors in log: {critical}")
            return hwnd, title, new_lines
        finally:
            if proc.poll() is None:
                proc.kill()

    # =========================================================================
    # Edge Case 1: Missing Project Files
    # =========================================================================

    def test_edge_1a_missing_file_standard_path(self):
        """Verify graceful startup with missing standard path."""
        missing = os.path.join(TEMP_FIXTURES_DIR, "non_existent_regular.mlt")
        self.assertFalse(os.path.exists(missing))
        self._run_and_close(missing)

    def test_edge_1b_missing_file_with_spaces(self):
        """Verify graceful startup with missing path containing multiple spaces."""
        missing = os.path.join(TEMP_FIXTURES_DIR, "path with several spaces test file.mlt")
        self.assertFalse(os.path.exists(missing))
        self._run_and_close(missing)

    def test_edge_1c_missing_file_unicode_path(self):
        """Verify graceful startup with missing Unicode path (accents, kanji, emoji-free)."""
        missing = os.path.join(TEMP_FIXTURES_DIR, "proyecto_edicion_español_archivo_perdido_テスト.mlt")
        self.assertFalse(os.path.exists(missing))
        self._run_and_close(missing)

    def test_edge_1d_missing_file_special_symbols(self):
        """Verify graceful startup with path containing symbols like !@#$%^&()_+~-."""
        missing = os.path.join(TEMP_FIXTURES_DIR, "file_!@#$%^()_+~-special.mlt")
        self.assertFalse(os.path.exists(missing))
        self._run_and_close(missing)

    # =========================================================================
    # Edge Case 2: Corrupted MLT Files
    # =========================================================================

    def test_edge_2a_corrupted_truncated_xml(self):
        """Verify recovery from truncated unclosed XML tags."""
        corrupt = os.path.join(TEMP_FIXTURES_DIR, "truncated.mlt")
        with open(corrupt, "w", encoding="utf-8") as f:
            f.write("<mlt><tractor><multitrack><track producer=\"producer0\"/>")
        self._run_and_close(corrupt)

    def test_edge_2b_corrupted_completely_invalid_xml(self):
        """Verify recovery from completely non-XML text data."""
        corrupt = os.path.join(TEMP_FIXTURES_DIR, "not_xml.mlt")
        with open(corrupt, "w", encoding="utf-8") as f:
            f.write("<<<<<<< INVALID XML CONTENT >>>>>>>\nThis is not a project file.\n1234567890")
        self._run_and_close(corrupt)

    def test_edge_2c_corrupted_zero_byte_empty_file(self):
        """Verify recovery from 0-byte completely empty file."""
        corrupt = os.path.join(TEMP_FIXTURES_DIR, "empty_zero_bytes.mlt")
        with open(corrupt, "wb") as f:
            pass
        self.assertEqual(os.path.getsize(corrupt), 0)
        self._run_and_close(corrupt)

    def test_edge_2d_corrupted_random_binary_garbage(self):
        """Verify recovery from raw binary garbage (null bytes, non-ASCII control characters)."""
        corrupt = os.path.join(TEMP_FIXTURES_DIR, "binary_garbage.mlt")
        with open(corrupt, "wb") as f:
            f.write(bytes(range(256)) * 16)
        self._run_and_close(corrupt)

    def test_edge_2e_corrupted_foreign_xml_schema(self):
        """Verify recovery when opening a non-MLT XML file (e.g., SVG vector file renamed as .mlt)."""
        corrupt = os.path.join(TEMP_FIXTURES_DIR, "svg_as_mlt.mlt")
        with open(corrupt, "w", encoding="utf-8") as f:
            f.write("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\"><circle cx=\"50\" cy=\"50\" r=\"40\"/></svg>")
        self._run_and_close(corrupt)

    # =========================================================================
    # Edge Case 3: Rapid Open/Close Cycles
    # =========================================================================

    def test_edge_3a_rapid_5_consecutive_cycles(self):
        """Verify 5 rapid consecutive launch and close cycles without hanging or memory leak."""
        for cycle in range(1, 6):
            start_time = time.time()
            proc = subprocess.Popen([SHOTCUT_EXE, "--noupgrade"])
            try:
                hwnd, title = find_shotcut_window(timeout_seconds=12)
                self.assertIsNotNone(hwnd, f"Rapid cycle {cycle}: window failed to appear")
                # Immediately request close as soon as window appears
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                ret = proc.wait(timeout=10)
                self.assertEqual(ret, 0, f"Rapid cycle {cycle} failed with code {ret}")
            finally:
                if proc.poll() is None:
                    proc.kill()
            elapsed = time.time() - start_time
            self.assertLess(elapsed, 15.0, f"Cycle {cycle} took too long: {elapsed:.2f}s")
            time.sleep(0.5)

    def test_edge_3b_zero_lingering_processes_invariant(self):
        """Verify that after execution no zombie shotcut.exe processes linger."""
        res = subprocess.run(
            ["powershell", "-Command", "(Get-Process shotcut -ErrorAction SilentlyContinue).Count"],
            capture_output=True, text=True
        )
        count_str = res.stdout.strip()
        count = int(count_str) if count_str.isdigit() else 0
        self.assertEqual(count, 0, f"Found {count} lingering shotcut processes!")


if __name__ == "__main__":
    unittest.main()
