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
"""

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS_CMAKE = PROJECT_ROOT / "translations" / "CMakeLists.txt"
MAIN_CPP = PROJECT_ROOT / "src" / "main.cpp"
QML_APPLICATION = PROJECT_ROOT / "src" / "qmltypes" / "qmlapplication.cpp"
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "build-windows-shotcut-ai.yml"


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
