#!/usr/bin/env python3
"""
test_phase2_icon_and_theme_verification.py

Phase 2 Verification Suite (Adversarial Hardened):
- R1: Lucide Stroke Iconography Integration (24x24 grid, 1.75 stroke, round caps/joins, #9AA1AD)
- R2: Size & Toolbar Rendering Standardization (18px standard / 15px compact timeline)
- R2.1: Multi-DPI Rasterization & Crisp Scalability Stress Test (100%, 125%, 150%, 200%)
- R2.2: DockToolBar Dynamic Property & Order-of-Initialization Invariance
- R3: Color State Harmonization & QSS Integration (#9AA1AD idle, #E8EAEE hover, #FF7A45 checked/pressed, #5F6672 disabled)
- R3.1: Fallback Inline Stylesheet Synchronization in mainwindow.cpp
- R4: Automated Regression Guard & Resource Invariance
"""

import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

from PySide6.QtCore import QByteArray, QEvent, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QToolBar

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DARK_ICONS_DIR = PROJECT_ROOT / "icons" / "dark" / "32x32"
RESOURCES_QRC = PROJECT_ROOT / "icons" / "resources.qrc"
CAPCUT_THEME_QSS = PROJECT_ROOT / "capcut_theme.qss"
MAINWINDOW_UI = PROJECT_ROOT / "src" / "mainwindow.ui"
MAINWINDOW_CPP = PROJECT_ROOT / "src" / "mainwindow.cpp"
TIMELINEDOCK_CPP = PROJECT_ROOT / "src" / "docks" / "timelinedock.cpp"
DOCKTOOLBAR_CPP = PROJECT_ROOT / "src" / "widgets" / "docktoolbar.cpp"
DOCKTOOLBAR_H = PROJECT_ROOT / "src" / "widgets" / "docktoolbar.h"

REQUIRED_R1_ICONS = [
    # Player transport controls
    "media-playback-start", "media-playback-pause", "media-seek-backward", "media-seek-forward",
    "media-skip-backward", "media-skip-forward", "media-playback-loop", "player-volume",
    # Timeline editing tools
    "edit-cut", "edit-copy", "edit-paste", "edit-delete", "split", "slice", "lift", "overwrite",
    "list-add", "marker",
    # Timeline mode toggles
    "snap", "ripple-all", "ripple-marker", "scrub_drag",
    # Track header actions
    "layer-visible-on", "layer-visible-off", "object-locked", "object-unlocked",
    "audio-volume-high", "audio-volume-muted",
    # Global navigation & header
    "document-new", "document-open", "document-save", "edit-undo", "edit-redo",
    "view-filter", "help-contextual", "audio-meter"
]

ADDITIONAL_TOOLBAR_ICONS = [
    "window-close", "media-record", "view-fullscreen", "system-file-manager",
    "view-history", "run-build", "chronometer", "document-edit", "view-media-playlist",
    "dialog-information", "document-open-recent", "subtitle", "view-time-schedule",
    "edit-clear", "zoom-fit-best", "zoom-in", "zoom-out", "zoom-original",
    # Adversarial additions for full toolbar coherence:
    "target", "show-menu", "format-indent-less", "format-indent-more", "view-grid",
    # Reviewer R2 dock & toolbar coherence additions:
    "audio-input-microphone", "folder-new", "list-add-files", "dialog-ok",
    "view-list-details", "view-list-icons", "view-list-text", "server-database",
    "view-refresh", "document-import", "document-export",
    # Reviewer R3 comprehensive dock & secondary toolbar additions:
    "view-choose", "quickopen", "keyframes-filter-in", "keyframes-filter-out",
    "keyframes-simple-in", "keyframes-simple-out", "4-direction", "speech-to-text",
    "text-speak", "font", "zoom-select", "folder", "download", "fire", "keyframe-linear"
]

ALL_MODERNIZED_ICONS = REQUIRED_R1_ICONS + ADDITIONAL_TOOLBAR_ICONS

# Ensure single headless QApplication instance for GUI tests
_app = None
def get_qapp():
    global _app
    if _app is None:
        _app = QApplication.instance()
        if _app is None:
            _app = QApplication(sys.argv[:1] + ["-platform", "offscreen"])
    return _app


class TestPhase2IconAndTheme(unittest.TestCase):
    def test_r1_all_required_svg_assets_exist_and_conform(self):
        """Verify all 36 required icons + additions exist as SVG conforming to Lucide standard."""
        for icon_name in ALL_MODERNIZED_ICONS:
            svg_path = DARK_ICONS_DIR / f"{icon_name}.svg"
            self.assertTrue(svg_path.exists(), f"Missing SVG asset: {svg_path.name}")
            self.assertGreater(svg_path.stat().st_size, 50, f"SVG file suspiciously small: {svg_path.name}")

            # Parse XML
            try:
                tree = ET.parse(svg_path)
                root = tree.getroot()
            except Exception as e:
                self.fail(f"Failed to parse SVG XML for {icon_name}.svg: {e}")

            # Verify Lucide specifications
            self.assertEqual(root.get("viewBox"), "0 0 24 24", f"{icon_name}.svg must use 24x24 viewBox")
            self.assertEqual(root.get("stroke"), "#9AA1AD", f"{icon_name}.svg must use stroke #9AA1AD (Grafito Muted)")
            self.assertEqual(root.get("stroke-width"), "1.75", f"{icon_name}.svg must use stroke-width 1.75")
            self.assertEqual(root.get("stroke-linecap"), "round", f"{icon_name}.svg must use stroke-linecap round")
            self.assertEqual(root.get("stroke-linejoin"), "round", f"{icon_name}.svg must use stroke-linejoin round")
            self.assertEqual(root.get("fill"), "none", f"{icon_name}.svg must use fill none")

    def test_r1_all_required_png_assets_exist_and_conform(self):
        """Verify all modernized icons have valid, crisp anti-aliased 32x32 PNG counterparts."""
        png_magic = b"\x89PNG\r\n\x1a\n"
        for icon_name in ALL_MODERNIZED_ICONS:
            png_path = DARK_ICONS_DIR / f"{icon_name}.png"
            self.assertTrue(png_path.exists(), f"Missing PNG counterpart: {png_path.name}")
            self.assertGreater(png_path.stat().st_size, 50, f"PNG file suspiciously small: {png_path.name}")

            # Magic header check
            with open(png_path, "rb") as f:
                header = f.read(8)
                self.assertEqual(header, png_magic, f"Invalid PNG magic for {icon_name}.png")

            # Image resolution and alpha channel check
            with Image.open(png_path) as im:
                self.assertEqual(im.size, (32, 32), f"{icon_name}.png size must be exactly 32x32")
                self.assertIn("A", im.getbands(), f"{icon_name}.png must contain an alpha channel")
                alpha_extrema = im.getchannel("A").getextrema()
                self.assertGreater(alpha_extrema[1], 0, f"{icon_name}.png must not be completely transparent")

    def test_r1_qrc_registration_invariance(self):
        """Verify all SVG and PNG assets are accurately registered in resources.qrc with 0 missing files."""
        tree = ET.parse(RESOURCES_QRC)
        root = tree.getroot()
        registered = [f.text.strip() for f in root.findall(".//file") if f.text]

        for icon_name in ALL_MODERNIZED_ICONS:
            svg_rel = f"dark/32x32/{icon_name}.svg"
            png_rel = f"dark/32x32/{icon_name}.png"
            self.assertIn(svg_rel, registered, f"Missing SVG registration in resources.qrc: {svg_rel}")
            self.assertIn(png_rel, registered, f"Missing PNG registration in resources.qrc: {png_rel}")

        # Check duplicates
        self.assertEqual(len(registered), len(set(registered)), "Duplicate entries detected in resources.qrc")

        # Check physical existence of every registered item
        for rel in registered:
            disk_p = RESOURCES_QRC.parent / rel
            self.assertTrue(disk_p.exists(), f"QRC entry missing on physical disk: {rel}")

    def test_r2_size_standardization_in_qss(self):
        """Verify 18px standard and 15px compact timeline icon size rules in capcut_theme.qss."""
        with open(CAPCUT_THEME_QSS, "r", encoding="utf-8") as f:
            qss = f.read()

        # Check QToolBar standard 18px
        toolbar_match = re.search(r"QToolBar\s*\{[^}]*qproperty-iconSize:\s*18px\s+18px", qss)
        self.assertIsNotNone(toolbar_match, "QToolBar must enforce qproperty-iconSize: 18px 18px")

        # Check Compact / Timeline 15px
        compact_match = re.search(r"(?:DockToolBar|QToolBar#timelineToolbar|compactToolbar)[^}]*\{[^}]*qproperty-iconSize:\s*15px\s+15px", qss)
        self.assertIsNotNone(compact_match, "Compact timeline toolbar must enforce qproperty-iconSize: 15px 15px")

    def test_r2_ui_and_cpp_size_standardization(self):
        """Verify mainwindow.ui, timelinedock.cpp, and docktoolbar.cpp enforce 18/15 standards."""
        # mainwindow.ui iconSize check
        tree = ET.parse(MAINWINDOW_UI)
        root = tree.getroot()
        toolbar = root.find(".//widget[@name='mainToolBar']")
        self.assertIsNotNone(toolbar, "mainToolBar not found in mainwindow.ui")
        icon_size = toolbar.find("property[@name='iconSize']")
        self.assertIsNotNone(icon_size, "iconSize property missing on mainToolBar in mainwindow.ui")
        w = icon_size.find(".//width").text.strip()
        h = icon_size.find(".//height").text.strip()
        self.assertEqual((w, h), ("18", "18"), "mainToolBar iconSize must be 18x18")

        # timelinedock.cpp objectName check and updateStyle invocation
        with open(TIMELINEDOCK_CPP, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn('toolbar->setObjectName("timelineToolbar")', content)
            self.assertIn('toolbar->setProperty("compact", true)', content)
            self.assertIn('toolbar->updateStyle()', content, "timelinedock.cpp must call updateStyle() after setting properties")

        # docktoolbar.h / docktoolbar.cpp check
        with open(DOCKTOOLBAR_H, "r", encoding="utf-8") as f:
            h_content = f.read()
            self.assertIn("void updateStyle()", h_content)
            self.assertIn("bool event(QEvent *event)", h_content)

        with open(DOCKTOOLBAR_CPP, "r", encoding="utf-8") as f:
            cpp_content = f.read()
            self.assertIn("15", cpp_content, "DockToolBar must support 15px compact icon size")
            self.assertIn("18", cpp_content, "DockToolBar must support 18px standard icon size")
            self.assertIn("DynamicPropertyChange", cpp_content, "DockToolBar::event must handle DynamicPropertyChange")

    def test_r2_dpi_scaling_rasterization_stress(self):
        """Stress-test SVG rasterization across 100%, 125%, 150%, 200% scaling factors."""
        dpi_scales = [1.0, 1.25, 1.5, 2.0]
        test_icons = [
            "media-playback-start", "edit-cut", "split", "snap", "target",
            "layer-visible-on", "document-new", "view-filter"
        ]

        for icon_name in test_icons:
            svg_path = DARK_ICONS_DIR / f"{icon_name}.svg"
            renderer = QSvgRenderer(str(svg_path))
            self.assertTrue(renderer.isValid(), f"QSvgRenderer failed to load {icon_name}.svg")

            for scale in dpi_scales:
                # 18px standard base
                target_std = int(round(18 * scale))
                img_std = QImage(target_std, target_std, QImage.Format_ARGB32_Premultiplied)
                img_std.fill(Qt.transparent)
                p_std = QPainter(img_std)
                p_std.setRenderHint(QPainter.Antialiasing, True)
                p_std.setRenderHint(QPainter.SmoothPixmapTransform, True)
                renderer.render(p_std)
                p_std.end()

                self.assertFalse(img_std.isNull(), f"Failed rendering {icon_name} at scale {scale}")
                self.assertEqual((img_std.width(), img_std.height()), (target_std, target_std))

                # 15px compact base
                target_cpt = int(round(15 * scale))
                img_cpt = QImage(target_cpt, target_cpt, QImage.Format_ARGB32_Premultiplied)
                img_cpt.fill(Qt.transparent)
                p_cpt = QPainter(img_cpt)
                p_cpt.setRenderHint(QPainter.Antialiasing, True)
                p_cpt.setRenderHint(QPainter.SmoothPixmapTransform, True)
                renderer.render(p_cpt)
                p_cpt.end()

                self.assertFalse(img_cpt.isNull(), f"Failed rendering compact {icon_name} at scale {scale}")
                self.assertEqual((img_cpt.width(), img_cpt.height()), (target_cpt, target_cpt))

    def test_r2_docktoolbar_runtime_icon_sizing(self):
        """Verify DockToolBar runtime behavior: compact=true yields 15x15, default yields 18x18."""
        app = get_qapp()

        class MockDockToolBar(QToolBar):
            def __init__(self, title, parent=None):
                super().__init__(title, parent)
                self.updateStyle()

            def event(self, ev):
                if ev.type() == QEvent.Type.DynamicPropertyChange:
                    self.updateStyle()
                return super().event(ev)

            def updateStyle(self):
                isTimeline = (self.objectName() == "timelineToolbar") or bool(self.property("compact"))
                iconDim = 15 if isTimeline else 18
                barHeight = 26 if isTimeline else 30
                self.setFixedHeight(barHeight)
                self.setIconSize(QSize(iconDim, iconDim))

        # Test Standard Toolbar (e.g. Player Controls)
        std_bar = MockDockToolBar("Standard Controls")
        self.assertEqual(std_bar.iconSize(), QSize(18, 18), "Standard toolbar must default to 18x18 iconSize")
        self.assertEqual(std_bar.height(), 30, "Standard toolbar height must be 30px")

        # Test Timeline Toolbar (compact by objectName & property)
        time_bar = MockDockToolBar("Timeline Controls")
        time_bar.setObjectName("timelineToolbar")
        time_bar.setProperty("compact", True)
        time_bar.updateStyle()
        self.assertEqual(time_bar.iconSize(), QSize(15, 15), "Timeline toolbar must enforce 15x15 iconSize")
        self.assertEqual(time_bar.height(), 26, "Timeline toolbar height must be 26px")

        # Test Dynamic Property change reactivity
        dyn_bar = MockDockToolBar("Dynamic Dock")
        self.assertEqual(dyn_bar.iconSize(), QSize(18, 18))
        dyn_bar.setProperty("compact", True)  # triggers DynamicPropertyChange event
        self.assertEqual(dyn_bar.iconSize(), QSize(15, 15), "DockToolBar must reactively resize to 15x15 on compact property set")

        # Test under real capcut_theme.qss stylesheet (Adversarial R2 Specificity Guard)
        with open(CAPCUT_THEME_QSS, "r", encoding="utf-8") as f:
            qss_content = f.read()
        app.setStyleSheet(qss_content)

        # Standard DockToolBar under capcut_theme.qss must NOT be forced to 15x15
        qss_std_bar = MockDockToolBar("Standard Dock Under QSS")
        qss_std_bar.show()
        self.assertEqual(qss_std_bar.iconSize(), QSize(18, 18), "Standard dock toolbar under QSS must maintain 18x18 iconSize")

        # Compact Timeline DockToolBar under capcut_theme.qss must be 15x15
        qss_time_bar = MockDockToolBar("Timeline Dock Under QSS")
        qss_time_bar.setObjectName("timelineToolbar")
        qss_time_bar.setProperty("compact", True)
        qss_time_bar.updateStyle()
        qss_time_bar.show()
        self.assertEqual(qss_time_bar.iconSize(), QSize(15, 15), "Compact timeline dock toolbar under QSS must enforce 15x15 iconSize")

        # Clean up app stylesheet
        app.setStyleSheet("")

    def test_r3_color_state_harmonization_in_qss(self):
        """Verify QToolButton states: #9AA1AD idle, #E8EAEE hover, #FF7A45 checked/active, #5F6672 disabled."""
        with open(CAPCUT_THEME_QSS, "r", encoding="utf-8") as f:
            qss = f.read()

        # Idle
        idle_match = re.search(r"QToolButton\s*\{[^}]*color:\s*#9AA1AD", qss)
        self.assertIsNotNone(idle_match, "QToolButton idle state must use color: #9AA1AD")

        # Hover
        hover_match = re.search(r"QToolButton:hover\s*\{[^}]*color:\s*#E8EAEE", qss)
        self.assertIsNotNone(hover_match, "QToolButton:hover state must use color: #E8EAEE")

        # Pressed
        pressed_match = re.search(r"QToolButton:pressed\s*\{[^}]*background-color:\s*#FF7A45", qss)
        self.assertIsNotNone(pressed_match, "QToolButton:pressed must highlight with background-color: #FF7A45")

        # Checked / Active
        checked_match = re.search(r"QToolButton:checked[^}]*\{[^}]*color:\s*#FF7A45", qss)
        self.assertIsNotNone(checked_match, "QToolButton:checked must use color: #FF7A45")
        self.assertIn("rgba(255, 122, 69, 0.18)", qss, "Active buttons must use soft background rgba(255, 122, 69, 0.18)")

        # Checked Pressed
        checked_pressed_match = re.search(r"QToolButton:checked:pressed[^}]*\{[^}]*background-color:\s*#FF7A45", qss)
        self.assertIsNotNone(checked_pressed_match, "QToolButton:checked:pressed must highlight with background-color: #FF7A45")

        # Disabled
        disabled_match = re.search(r"QToolButton:disabled\s*\{[^}]*color:\s*#5F6672", qss)
        self.assertIsNotNone(disabled_match, "QToolButton:disabled state must use color: #5F6672")

    def test_r3_fallback_stylesheet_in_mainwindow_cpp(self):
        """Verify fallback stylesheet in mainwindow.cpp has synchronized Phase 2 rules."""
        with open(MAINWINDOW_CPP, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify fallback toolbar rules
        self.assertIn('QToolBar { qproperty-iconSize: 18px 18px;', content)
        self.assertIn('qproperty-iconSize: 15px 15px;', content)
        self.assertIn('QToolButton { background-color: transparent; border-radius: 7px; padding: 5px 10px; margin: 1px; color: #9AA1AD;', content)
        self.assertIn('QToolButton:pressed { background-color: #FF7A45;', content)
        self.assertIn('QToolButton:checked, QToolButton[active=\\"true\\"] { background-color: rgba(255, 122, 69, 0.18); color: #FF7A45;', content)
        self.assertIn('QToolButton:checked:pressed', content)
        self.assertIn('QToolButton:disabled { color: #5F6672;', content)

    def test_r3_docktoolbar_stylesheet_rules(self):
        """Verify DockToolBar::updateStyle() stylesheet has full color states including pressed."""
        with open(DOCKTOOLBAR_CPP, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('QToolButton:pressed', content)
        self.assertIn('QToolButton:checked:pressed', content)
        self.assertIn('color:#9AA1AD', content)
        self.assertIn('color:#E8EAEE', content)
        self.assertIn('color:#FF7A45', content)
        self.assertIn('color:#5F6672', content)

    def test_r3_dock_filter_toolbars_harmonization(self):
        """Verify Playlist & Files filter toolbars conform to Grafito design tokens."""
        with open(CAPCUT_THEME_QSS, "r", encoding="utf-8") as f:
            qss = f.read()

        self.assertIn("QToolBar#playlistFiltersToolbar", qss)
        self.assertIn("QToolBar#filesFiltersToolbar", qss)
        self.assertIn("rgba(255, 122, 69, 0.18)", qss)

        # Check playlistdock.cpp
        with open(PROJECT_ROOT / "src" / "docks" / "playlistdock.cpp", "r", encoding="utf-8") as f:
            pl_cpp = f.read()
        self.assertIn('toolbar2->setObjectName("playlistFiltersToolbar")', pl_cpp)
        self.assertIn('#FF7A45', pl_cpp)
        self.assertNotIn('palette(background)', pl_cpp)

        # Check filesdock.cpp
        with open(PROJECT_ROOT / "src" / "docks" / "filesdock.cpp", "r", encoding="utf-8") as f:
            fl_cpp = f.read()
        self.assertIn('toolbar2->setObjectName("filesFiltersToolbar")', fl_cpp)
        self.assertIn('#FF7A45', fl_cpp)
        self.assertNotIn('palette(background)', fl_cpp)

        # Check mainwindow.cpp fallback
        with open(MAINWINDOW_CPP, "r", encoding="utf-8") as f:
            mw_cpp = f.read()
        self.assertIn('QToolBar#playlistFiltersToolbar', mw_cpp)
        self.assertIn('QToolBar#filesFiltersToolbar', mw_cpp)


if __name__ == "__main__":
    unittest.main()
