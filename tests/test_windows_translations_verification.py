#!/usr/bin/env python3
"""
test_windows_translations_verification.py

Windows translations: choosing a language in the Windows build must change the interface.
The Windows build of Shotcut AI uses the MSYS2 layout (WINDOWS_DEPLOY=OFF, NODEPLOY):
bin/shotcut.exe and its data in share/shotcut. Until this fix the Shotcut .qm files were
not installed on Windows, and src/main.cpp looked for them in bin/share/translations, so
only the standard Qt buttons followed the language.

- T1: CMake installs the .qm files on Windows, where src/main.cpp looks for them
- T2: src/main.cpp looks in share/shotcut/translations with NODEPLOY, like dataDir()
- T3: The Windows workflow fails if shotcut_es.qm is missing from the bundle or the install
- R1: Choosing a language restarts at once, without a question, and comes back with the same
      project, its unsaved changes (recovered from the auto-save file without asking) and the
      playhead, and says "Language changed to ..."
"""

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS_CMAKE = PROJECT_ROOT / "translations" / "CMakeLists.txt"
MAIN_CPP = PROJECT_ROOT / "src" / "main.cpp"
QML_APPLICATION = PROJECT_ROOT / "src" / "qmltypes" / "qmlapplication.cpp"
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "build-windows-shotcut-ai.yml"
MAINWINDOW_CPP = PROJECT_ROOT / "src" / "mainwindow.cpp"
SETTINGS_CPP = PROJECT_ROOT / "src" / "settings.cpp"
SPANISH = PROJECT_ROOT / "translations" / "shotcut_es.ts"


def read(path):
    return Path(path).read_text(encoding="utf-8")


def translations_block(source):
    """The part of main.cpp that chooses the translations folder."""
    start = source.index("// Load translations")
    return source[start:source.index("qtTranslator.load", start)]


class TestT1InstallRule(unittest.TestCase):
    def setUp(self):
        self.cmake = read(TRANSLATIONS_CMAKE)

    def test_qm_files_are_installed_on_windows(self):
        windows = self.cmake[self.cmake.index("elseif(WIN32)"):]
        self.assertIn('PATTERN "*.qm"', windows)
        self.assertIn("share/shotcut/translations", windows,
                      "WINDOWS_DEPLOY=OFF must install to share/shotcut/translations")
        self.assertIn("share/translations", windows.replace("share/shotcut/translations", ""),
                      "WINDOWS_DEPLOY=ON must keep share/translations")
        deploy = re.search(r"if\(WINDOWS_DEPLOY\)\s*set\(\w+ ([^)]*)\)", windows)
        self.assertIsNotNone(deploy)
        self.assertTrue(deploy.group(1).endswith("/share/translations"), deploy.group(1))

    def test_linux_install_is_unchanged(self):
        linux = self.cmake[self.cmake.index("if(UNIX AND NOT APPLE)"):self.cmake.index("elseif(WIN32)")]
        self.assertIn("${CMAKE_INSTALL_DATADIR}/shotcut/translations", linux)


class TestT2LookupFolder(unittest.TestCase):
    def setUp(self):
        self.block = translations_block(read(MAIN_CPP))

    def test_official_layout_only_without_nodeploy(self):
        self.assertIn("#elif defined(Q_OS_WIN) && !defined(NODEPLOY)", self.block)

    def test_nodeploy_uses_the_linux_path(self):
        fallback = self.block[self.block.index("#else"):self.block.index("#endif")]
        for step in ('dir.cdUp();', 'dir.cd("share");', 'dir.cd("shotcut");',
                     'dir.cd("translations");'):
            self.assertIn(step, fallback)

    def test_matches_data_dir(self):
        self.assertIn("(defined(Q_OS_WIN) && defined(NODEPLOY))", read(QML_APPLICATION))


class TestT3WorkflowChecks(unittest.TestCase):
    def setUp(self):
        self.workflow = read(WORKFLOW)

    def test_bundle_is_checked(self):
        step = self.workflow[self.workflow.index("- name: Check the translations"):]
        step = step[:step.index("- name:", 10)]
        self.assertIn("share/shotcut/translations", step)
        self.assertIn("shotcut_es.qm", step)
        self.assertIn("exit 1", step)
        self.assertLess(self.workflow.index("- name: Bundle the runtime"),
                        self.workflow.index("- name: Check the translations"))

    def test_install_is_checked(self):
        step = self.workflow[self.workflow.index("- name: Check the installer"):]
        step = step[:step.index("- name:", 10)]
        self.assertIn(r"share\shotcut\translations\shotcut_es.qm", step)


def function(source, signature):
    """The body of a C++ function, from its signature to the matching brace."""
    begin = source.index("{", source.index(signature))
    depth = 0
    for index in range(begin, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[begin:index + 1]
    raise ValueError(signature)


class TestR1RestartWithoutFuss(unittest.TestCase):
    def setUp(self):
        self.main_window = read(MAINWINDOW_CPP)

    def test_language_menu_restarts_without_asking(self):
        body = function(self.main_window, "void MainWindow::onLanguageTriggered")
        self.assertIn("== Settings.language()", body, "the current language does nothing")
        restart = body.index("restartForLanguage();")
        self.assertLess(body.index("JOBS.hasIncomplete()"), restart)
        self.assertLess(restart, body.index("QMessageBox dialog"),
                        "the question is only for running jobs")

    def test_unsaved_changes_survive_the_restart(self):
        body = function(self.main_window, "void MainWindow::restartForLanguage")
        self.assertIn("doAutosave();", body)
        self.assertLess(body.index("doAutosave();"), body.index("setFileName(QString())"),
                        "the auto-save file is detached so that it is not removed")
        self.assertIn("continueModified()", body, "a failed auto-save asks as on closing")
        self.assertIn("Settings.setRestartSession(project, m_player->position(), modified)", body)
        self.assertIn("m_restartKeepsProject = true;", body)
        self.assertIn("m_exitCode = EXIT_RESTART;", body)
        self.assertIn("if (isVisible())", body, "an aborted restart goes back to normal")
        close = function(self.main_window, "void MainWindow::closeEvent")
        self.assertIn("(m_restartKeepsProject || continueModified())", close)

    def test_restore_reopens_recovers_and_seeks(self):
        body = function(self.main_window, "bool MainWindow::restoreAfterLanguageRestart")
        self.assertLess(body.index("Settings.clearRestartSession();"), body.index("open("),
                        "restored only once")
        self.assertIn("m_recoverWithoutAsking = project;", body)
        self.assertIn("m_player->seek(position)", body)
        self.assertIn('tr("Language changed to %1")', body)
        check = function(self.main_window, "bool MainWindow::checkAutoSave")
        self.assertIn("m_recoverWithoutAsking != url", check)
        self.assertLess(check.index("m_recoverWithoutAsking != url"), check.index("dialog.exec()"))
        main = read(MAIN_CPP)
        self.assertLess(main.index("restoreAfterLanguageRestart()"), main.index("a.resourceArg.isEmpty()"))

    def test_settings_and_spanish(self):
        settings = read(SETTINGS_CPP)
        for key in ("restart/project", "restart/position", "restart/modified"):
            self.assertIn('"%s"' % key, settings)
        self.assertIn('settings.remove("restart")', settings)
        self.assertIn("<translation>Idioma cambiado a %1</translation>", read(SPANISH))


if __name__ == "__main__":
    unittest.main(verbosity=2)
