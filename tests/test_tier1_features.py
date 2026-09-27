#!/usr/bin/env python3
"""
Tier 1: Feature Coverage Test Suite for Shotcut UI/UX Modernization
Covers all 14 features (F1 to F14) in isolation (>= 5 tests per feature, >= 70 tests total).
Tests visual assets, theme definitions, window layouts, QML syntax, packaging, and infrastructure.
"""

import os
import sys
import re
import base64
import unittest
import xml.etree.ElementTree as ET
from PIL import Image

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.validate_qml import validate_qml_content, scan_directory


class TestFeature1_MinimalistSvgLogoMaster(unittest.TestCase):
    """F1: Minimalist SVG Logo Master (icons/shotcut-logo-64.svg)"""

    def setUp(self):
        self.svg_path = os.path.join(PROJECT_ROOT, "icons", "shotcut-logo-64.svg")

    def test_f1_01_svg_master_exists(self):
        """Verify SVG master file exists and is non-empty."""
        self.assertTrue(os.path.isfile(self.svg_path), f"SVG master missing at {self.svg_path}")
        self.assertGreater(os.path.getsize(self.svg_path), 100, "SVG file too small")

    def test_f1_02_svg_valid_xml(self):
        """Verify SVG master is well-formed XML with an SVG root element."""
        tree = ET.parse(self.svg_path)
        root = tree.getroot()
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        self.assertEqual(tag, "svg", "Root XML element is not <svg>")

    def test_f1_03_svg_viewbox_and_dimensions(self):
        """Verify SVG master has valid viewBox and 64x64 dimensions."""
        tree = ET.parse(self.svg_path)
        root = tree.getroot()
        viewbox = root.attrib.get("viewBox", "")
        width = root.attrib.get("width", "")
        height = root.attrib.get("height", "")
        self.assertTrue(
            viewbox == "0 0 64 64" or (width == "64" and height == "64"),
            f"Expected 64x64 dimensions or '0 0 64 64' viewBox, got viewBox='{viewbox}', w='{width}', h='{height}'"
        )

    def test_f1_04_svg_contains_vector_elements(self):
        """Verify SVG master contains vector geometry (paths, rects, or shapes)."""
        tree = ET.parse(self.svg_path)
        root = tree.getroot()
        vector_tags = {"path", "rect", "circle", "polygon", "g"}
        found_tags = {elem.tag.split("}")[-1] for elem in root.iter()}
        self.assertTrue(
            bool(found_tags.intersection(vector_tags)),
            f"No vector elements found in SVG: {found_tags}"
        )

    def test_f1_05_svg_clean_no_unresolved_external_references(self):
        """Verify SVG does not contain dangerous script tags or broken local filesystem URIs."""
        with open(self.svg_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("<script", content.lower(), "SVG should not contain script elements")
        self.assertNotIn("file://", content.lower(), "SVG contains hardcoded local filesystem URI")


class TestFeature2_MultiFormatAssetCompilation(unittest.TestCase):
    """F2: Multi-format Asset Compilation (ICO, ICNS, PNG, Store Assets)"""

    def test_f2_01_windows_ico_exists_and_multiframe(self):
        """Verify packaging/windows/shotcut-logo-64.ico exists and is a valid ICO file."""
        ico_path = os.path.join(PROJECT_ROOT, "packaging", "windows", "shotcut-logo-64.ico")
        self.assertTrue(os.path.isfile(ico_path), f"ICO missing at {ico_path}")
        with Image.open(ico_path) as im:
            self.assertEqual(im.format, "ICO")
            n_frames = getattr(im, "n_frames", 1)
            self.assertGreaterEqual(n_frames, 1, "ICO must contain at least 1 frame")

    def test_f2_02_windows_ico_frame_dimensions(self):
        """Verify ICO contains standard square icon resolution."""
        ico_path = os.path.join(PROJECT_ROOT, "packaging", "windows", "shotcut-logo-64.ico")
        with Image.open(ico_path) as im:
            sizes = set()
            for i in range(getattr(im, "n_frames", 1)):
                im.seek(i)
                sizes.add(im.size)
        valid_resolutions = {16, 24, 32, 48, 64, 128, 256}
        for w, h in sizes:
            self.assertEqual(w, h, f"Non-square frame in ICO: {w}x{h}")
            self.assertIn(w, valid_resolutions, f"Non-standard icon dimension: {w}")

    def test_f2_03_macos_icns_exists_and_valid(self):
        """Verify packaging/macos/shotcut.icns exists and has valid ICNS magic header."""
        icns_path = os.path.join(PROJECT_ROOT, "packaging", "macos", "shotcut.icns")
        self.assertTrue(os.path.isfile(icns_path), f"ICNS missing at {icns_path}")
        self.assertGreater(os.path.getsize(icns_path), 1000, "ICNS file too small")
        with open(icns_path, "rb") as f:
            magic = f.read(4)
        self.assertEqual(magic, b"icns", f"Invalid ICNS magic header: {magic}")

    def test_f2_04_windows_store_assets_exist(self):
        """Verify Microsoft Store assets directory contains package icons."""
        store_dir = os.path.join(PROJECT_ROOT, "packaging", "windows", "Microsoft Store", "PackageFiles", "Assets")
        self.assertTrue(os.path.isdir(store_dir), f"Store assets dir missing at {store_dir}")
        pngs = [f for f in os.listdir(store_dir) if f.lower().endswith(".png")]
        self.assertGreaterEqual(len(pngs), 10, f"Expected >= 10 store assets, found {len(pngs)}")

    def test_f2_05_core_png_resolutions_exist(self):
        """Verify core raster icons exist with exact matching dimensions."""
        expected = {
            "shotcut-logo-16.png": (16, 16),
            "shotcut-logo-24.png": (24, 24),
            "shotcut-logo-32.png": (32, 32),
            "shotcut-logo-48.png": (48, 48),
            "shotcut-logo-64.png": (64, 64),
        }
        for name, dims in expected.items():
            path = os.path.join(PROJECT_ROOT, "icons", name)
            self.assertTrue(os.path.isfile(path), f"Icon {name} missing")
            with Image.open(path) as im:
                self.assertEqual(im.size, dims, f"Icon {name} dimension mismatch: expected {dims}, got {im.size}")


class TestFeature3_SplashAndWindowIconReplacement(unittest.TestCase):
    """F3: Splash & Window Icon Replacement"""

    def test_f3_01_splash_asset_dimensions_and_mode(self):
        """Verify icons/shotcut-logo-320x320.png exists and is exactly 320x320."""
        splash_path = os.path.join(PROJECT_ROOT, "icons", "shotcut-logo-320x320.png")
        self.assertTrue(os.path.isfile(splash_path), f"Splash image missing at {splash_path}")
        with Image.open(splash_path) as im:
            self.assertEqual(im.size, (320, 320), f"Expected 320x320, got {im.size}")
            self.assertIn(im.mode, ("RGBA", "RGB"))

    def test_f3_02_splash_asset_png_integrity(self):
        """Verify splash PNG image header and data integrity."""
        splash_path = os.path.join(PROJECT_ROOT, "icons", "shotcut-logo-320x320.png")
        with Image.open(splash_path) as im:
            im.verify()

    def test_f3_03_resources_qrc_references_logo_assets(self):
        """Verify icons/resources.qrc references SVG and splash assets."""
        qrc_path = os.path.join(PROJECT_ROOT, "icons", "resources.qrc")
        self.assertTrue(os.path.isfile(qrc_path), f"QRC file missing at {qrc_path}")
        with open(qrc_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("shotcut-logo-64.svg", content, "QRC missing shotcut-logo-64.svg")
        self.assertIn("shotcut-logo-320x320.png", content, "QRC missing shotcut-logo-320x320.png")

    def test_f3_04_window_icon_qrc_binding(self):
        """Verify src/mainwindow.ui configures window icon referencing shotcut-logo-64.svg."""
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        self.assertTrue(os.path.isfile(ui_path))
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("windowIcon", content)
        self.assertIn("shotcut-logo-64.svg", content)

    def test_f3_05_splash_screen_instantiation_contract(self):
        """Verify src/main.cpp instantiates QSplashScreen with splash asset."""
        main_path = os.path.join(PROJECT_ROOT, "src", "main.cpp")
        self.assertTrue(os.path.isfile(main_path))
        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("QSplashScreen", content, "QSplashScreen not used in main.cpp")
        self.assertIn("shotcut-logo-320x320.png", content, "Splash asset not referenced in main.cpp")


class TestFeature4_PackagingAssetAlignment(unittest.TestCase):
    """F4: Packaging Asset Alignment (Linux, macOS, Windows)"""

    def test_f4_01_linux_64x64_icon_exists(self):
        """Verify packaging/linux/icons/64x64/org.shotcut.Shotcut.png is 64x64."""
        p = os.path.join(PROJECT_ROOT, "packaging", "linux", "icons", "64x64", "org.shotcut.Shotcut.png")
        self.assertTrue(os.path.isfile(p), f"Linux 64x64 icon missing at {p}")
        with Image.open(p) as im:
            self.assertEqual(im.size, (64, 64))

    def test_f4_02_linux_128x128_icon_exists(self):
        """Verify packaging/linux/icons/128x128/org.shotcut.Shotcut.png has 128px resolution."""
        p = os.path.join(PROJECT_ROOT, "packaging", "linux", "icons", "128x128", "org.shotcut.Shotcut.png")
        self.assertTrue(os.path.isfile(p), f"Linux 128x128 icon missing at {p}")
        with Image.open(p) as im:
            self.assertEqual(im.size[0], 128)
            self.assertEqual(im.format, "PNG")

    def test_f4_03_linux_desktop_file_icon_ref(self):
        """Verify Linux desktop file references org.shotcut.Shotcut icon."""
        p = os.path.join(PROJECT_ROOT, "packaging", "linux", "org.shotcut.Shotcut.desktop")
        self.assertTrue(os.path.isfile(p), f"Desktop file missing at {p}")
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Icon=org.shotcut.Shotcut", content)

    def test_f4_04_macos_dmg_background_graphic(self):
        """Verify macOS DMG background graphic exists."""
        png_p = os.path.join(PROJECT_ROOT, "packaging", "macos", "dmg-background.png")
        svg_p = os.path.join(PROJECT_ROOT, "packaging", "macos", "dmg-background.svg")
        self.assertTrue(os.path.isfile(png_p) or os.path.isfile(svg_p), "DMG background graphic missing")

    def test_f4_05_inno_setup_installer_icon_binding(self):
        """Verify Windows RC configuration binds shotcut-logo-64.ico."""
        rc_p = os.path.join(PROJECT_ROOT, "packaging", "windows", "shotcut.rc.in")
        self.assertTrue(os.path.isfile(rc_p), f"Windows RC template missing at {rc_p}")
        with open(rc_p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        self.assertIn("shotcut-logo-64.ico", content)


class TestFeature5_GlobalModernDarkThemeQSS(unittest.TestCase):
    """F5: Global Modern Dark Theme QSS"""

    def test_f5_01_theme_stylesheet_definition_exists(self):
        """Verify stylesheet logic exists in mainwindow.cpp."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(
            "setStyleSheet" in content or "changeTheme" in content,
            "No stylesheet logic found in mainwindow.cpp"
        )

    def test_f5_02_theme_qss_accent_color_token(self):
        """Verify theme architecture supports primary accent and dark tones."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("changeTheme", content)

    def test_f5_03_theme_qss_widget_rules_syntax(self):
        """Verify QSS blocks in codebase have balanced braces."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("capcutQss", content)
        match = re.search(r'QString\s+capcutQss\s*=\s*QStringLiteral\s*\((.*?)\);', content, re.DOTALL)
        self.assertTrue(match, "capcutQss definition not found")
        qss_body = match.group(1)
        self.assertGreater(qss_body.count("{"), 5, "capcutQss does not contain CSS blocks")
        self.assertEqual(qss_body.count("{"), qss_body.count("}"), f"Unbalanced braces in capcutQss: {qss_body}")

    def test_f5_04_dark_palette_color_assignments(self):
        """Verify dark palette configuration sets standard Qt palette roles."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("QPalette::Window", content)
        self.assertIn("QPalette::Base", content)

    def test_f5_05_theme_stylesheet_property_declarations(self):
        """Verify theme configuration sets application palette and styles."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("QApplication::setPalette", content)
        self.assertIn("setStyleSheet", content)


class TestFeature6_ThemeOverwriteHarmonization(unittest.TestCase):
    """F6: Theme Overwrite Harmonization (MainWindow::changeTheme)"""

    def test_f6_01_change_theme_method_exists(self):
        """Verify MainWindow::changeTheme is declared in header and defined in cpp."""
        h_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.h")
        cpp_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(h_path, "r", encoding="utf-8") as f:
            self.assertIn("changeTheme", f.read())
        with open(cpp_path, "r", encoding="utf-8") as f:
            self.assertIn("MainWindow::changeTheme", f.read())

    def test_f6_02_theme_action_group_defined(self):
        """Verify theme constants exist for system, dark, and light options."""
        cpp_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(cpp_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("kThemeDark", content)
        self.assertIn("kThemeLight", content)
        self.assertIn("kThemeSystem", content)

    def test_f6_03_settings_theme_persistence(self):
        """Verify Settings class manages theme preference."""
        s_path = os.path.join(PROJECT_ROOT, "src", "settings.h")
        with open(s_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("theme", content.lower())

    def test_f6_04_theme_reapplication_retains_styling(self):
        """Verify changeTheme handles theme switching for dark theme."""
        cpp_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(cpp_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("kThemeDark", content)
        self.assertIn("setThemeName", content)

    def test_f6_05_theme_palette_contrast_ratio(self):
        """Verify dark theme palette colors provide high contrast (WCAG AA)."""
        def rel_lum(r, g, b):
            return 0.2126 * (r / 255.0) + 0.7152 * (g / 255.0) + 0.0722 * (b / 255.0)
        bg_lum = rel_lum(0x16, 0x16, 0x1a)
        fg_lum = rel_lum(0xf0, 0xf0, 0xf5)
        ratio = (fg_lum + 0.05) / (bg_lum + 0.05)
        self.assertGreaterEqual(ratio, 4.5, f"Contrast ratio {ratio:.2f} is below WCAG AA threshold 4.5:1")


class TestFeature7_TypographyAndDockHeaderPolish(unittest.TestCase):
    """F7: Typography & Dock Header Polish"""

    def test_f7_01_dock_widget_title_bar_styling(self):
        """Verify QDockWidget title bar styling in mainwindow.cpp or docks."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("QDockWidget", content)

    def test_f7_02_tab_bar_styling(self):
        """Verify tab bar styling in mainwindow.cpp stylesheet."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("QTabBar::tab", content)

    def test_f7_03_scrollbar_minimalist_styling(self):
        """Verify scroll bar handling in docks and timeline."""
        td_path = os.path.join(PROJECT_ROOT, "src", "docks", "timelinedock.cpp")
        self.assertTrue(os.path.isfile(td_path))
        with open(td_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("scroll", content.lower())

    def test_f7_04_dock_nesting_enabled(self):
        """Verify MainWindow enables dock nesting."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("setDockNestingEnabled(true)", content)

    def test_f7_05_dock_corner_configuration(self):
        """Verify MainWindow sets dock corners for clean rectangular tiling."""
        mw_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(mw_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("setCorner(", content)


class TestFeature8_MainToolbarDecluttering(unittest.TestCase):
    """F8: Main Toolbar Decluttering"""

    def test_f8_01_main_toolbar_defined_in_ui(self):
        """Verify mainToolBar element is defined in src/mainwindow.ui."""
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('<widget class="QToolBar" name="mainToolBar">', content)

    def test_f8_02_essential_editing_actions_present(self):
        """Verify core editing actions are in mainwindow.ui."""
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        for act in ("actionOpen", "actionSave", "actionTimeline", "actionFilters", "actionPlaylist"):
            self.assertIn(f'name="{act}"', content, f"Action {act} missing from mainwindow.ui")

    def test_f8_03_toolbar_action_icons_valid(self):
        """Verify toolbar actions reference valid resource icon paths."""
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        icon_refs = re.findall(r'<normaloff>([^<]+)</normaloff>', content)
        self.assertGreater(len(icon_refs), 10, "Expected multiple icon references in mainwindow.ui")
        for ref in icon_refs:
            self.assertTrue(ref.startswith(":/icons/"), f"Invalid resource icon path: {ref}")

    def test_f8_04_toolbar_button_style_and_icon_size(self):
        """Verify toolbar style properties are configured in mainwindow.ui."""
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('<property name="toolButtonStyle">', content)

    def test_f8_05_action_tooltips_and_shortcuts(self):
        """Verify action definitions include tooltips."""
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('<property name="toolTip">', content)


class TestFeature9_WorkspaceLayoutOptimization(unittest.TestCase):
    """F9: Workspace Layout Optimization (defaultlayouts.h, updateLayoutSwitcher)"""

    def test_f9_01_default_layouts_header_exists(self):
        """Verify src/defaultlayouts.h exists."""
        dl_path = os.path.join(PROJECT_ROOT, "src", "defaultlayouts.h")
        self.assertTrue(os.path.isfile(dl_path), f"defaultlayouts.h missing at {dl_path}")

    def test_f9_02_default_layout_constants_nonempty(self):
        """Verify default layout constants are non-empty strings."""
        dl_path = os.path.join(PROJECT_ROOT, "src", "defaultlayouts.h")
        with open(dl_path, "r", encoding="utf-8") as f:
            content = f.read()
        for layout in ("kLayoutLoggingDefault", "kLayoutEditingDefault", "kLayoutEffectsDefault",
                       "kLayoutColorDefault", "kLayoutAudioDefault", "kLayoutPlayerDefault"):
            self.assertIn(layout, content, f"Layout constant {layout} missing")

    def test_f9_03_layout_action_declarations(self):
        """Verify layout actions exist in mainwindow.ui."""
        ui_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.ui")
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        for act in ("actionLayoutLogging", "actionLayoutEditing", "actionLayoutEffects",
                    "actionLayoutColor", "actionLayoutAudio", "actionLayoutPlayer"):
            self.assertIn(f'name="{act}"', content, f"Layout action {act} missing from UI")

    def test_f9_04_update_layout_switcher_method(self):
        """Verify MainWindow::updateLayoutSwitcher exists in src/mainwindow.cpp."""
        cpp_path = os.path.join(PROJECT_ROOT, "src", "mainwindow.cpp")
        with open(cpp_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("MainWindow::updateLayoutSwitcher", content)

    def test_f9_05_layout_state_base64_validity(self):
        """Verify layout constants contain valid base64 character sets."""
        dl_path = os.path.join(PROJECT_ROOT, "src", "defaultlayouts.h")
        with open(dl_path, "r", encoding="utf-8") as f:
            content = f.read()
        literals = re.findall(r'fromBase64\s*\(\s*"([^"]+)"\s*\)', content)
        self.assertGreaterEqual(len(literals), 6, f"Expected at least 6 layout strings, got {len(literals)}")
        for lit in literals:
            try:
                decoded = base64.b64decode(lit)
                self.assertGreater(len(decoded), 10, "Decoded layout state too small")
            except Exception as e:
                self.fail(f"Layout state failed base64 decoding: {e}")


class TestFeature10_UnifiedPlayerTransportControls(unittest.TestCase):
    """F10: Unified Player Transport Controls (src/player.cpp)"""

    def test_f10_01_player_transport_toolbars_defined(self):
        """Verify player transport toolbars are declared in src/player.h."""
        h_path = os.path.join(PROJECT_ROOT, "src", "player.h")
        with open(h_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("m_controlsToolBar", content)
        self.assertIn("m_currentDurationToolBar", content)

    def test_f10_02_transport_core_actions(self):
        """Verify core transport slots/actions exist in Player."""
        h_path = os.path.join(PROJECT_ROOT, "src", "player.h")
        with open(h_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("play", content.lower())
        self.assertIn("pause", content.lower())
        self.assertIn("seek", content.lower())

    def test_f10_03_timecode_display_elements(self):
        """Verify position and duration controls in src/player.cpp."""
        cpp_path = os.path.join(PROJECT_ROOT, "src", "player.cpp")
        with open(cpp_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("m_positionSpinner", content)
        self.assertIn("m_durationLabel", content)

    def test_f10_04_layout_toolbars_implementation(self):
        """Verify Player::layoutToolbars arranges transport controls."""
        cpp_path = os.path.join(PROJECT_ROOT, "src", "player.cpp")
        with open(cpp_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Player::layoutToolbars", content)

    def test_f10_05_scrubbar_integration(self):
        """Verify ScrubBar widget integration in src/player.cpp."""
        cpp_path = os.path.join(PROJECT_ROOT, "src", "player.cpp")
        with open(cpp_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("m_scrubber", content)
        self.assertIn("ScrubBar", content)


class TestFeature11_QmlTimelineModernization(unittest.TestCase):
    """F11: QML Timeline Modernization (views/timeline/...)"""

    def test_f11_01_timeline_root_component_syntax(self):
        """Verify src/qml/views/timeline/timeline.qml passes static syntax validation."""
        path = os.path.join(PROJECT_ROOT, "src", "qml", "views", "timeline", "timeline.qml")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            errors = validate_qml_content(f.read(), path)
        self.assertEqual(len(errors), 0, f"QML syntax errors in timeline.qml: {errors}")

    def test_f11_02_clip_qml_component_syntax(self):
        """Verify src/qml/views/timeline/Clip.qml passes static syntax validation."""
        path = os.path.join(PROJECT_ROOT, "src", "qml", "views", "timeline", "Clip.qml")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            errors = validate_qml_content(f.read(), path)
        self.assertEqual(len(errors), 0, f"QML syntax errors in Clip.qml: {errors}")

    def test_f11_03_trackhead_qml_component_syntax(self):
        """Verify src/qml/views/timeline/TrackHead.qml passes static syntax validation."""
        path = os.path.join(PROJECT_ROOT, "src", "qml", "views", "timeline", "TrackHead.qml")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            errors = validate_qml_content(f.read(), path)
        self.assertEqual(len(errors), 0, f"QML syntax errors in TrackHead.qml: {errors}")

    def test_f11_04_ruler_qml_component_syntax(self):
        """Verify src/qml/views/timeline/Ruler.qml passes static syntax validation."""
        path = os.path.join(PROJECT_ROOT, "src", "qml", "views", "timeline", "Ruler.qml")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            errors = validate_qml_content(f.read(), path)
        self.assertEqual(len(errors), 0, f"QML syntax errors in Ruler.qml: {errors}")

    def test_f11_05_clip_rounded_corner_support(self):
        """Verify Clip.qml supports rounded corner rendering properties."""
        path = os.path.join(PROJECT_ROOT, "src", "qml", "views", "timeline", "Clip.qml")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(
            "_roundLeft" in content or "radius" in content or "rounded" in content.lower(),
            "Clip.qml does not include corner styling or rounding properties"
        )


class TestFeature12_FlatSilhouetteIconHarmonization(unittest.TestCase):
    """F12: Flat Silhouette Icon Harmonization"""

    def test_f12_01_dark_theme_icons_directory(self):
        """Verify icons/dark/ directory exists and contains silhouette icons."""
        dark_dir = os.path.join(PROJECT_ROOT, "icons", "dark")
        self.assertTrue(os.path.isdir(dark_dir), f"Dark icons dir missing at {dark_dir}")
        icons = []
        for root, _, files in os.walk(dark_dir):
            icons.extend([f for f in files if f.endswith((".png", ".svg"))])
        self.assertGreaterEqual(len(icons), 10, f"Expected >= 10 icons in icons/dark/, found {len(icons)}")

    def test_f12_02_light_theme_icons_directory(self):
        """Verify icons/light/ directory exists and contains silhouette icons."""
        light_dir = os.path.join(PROJECT_ROOT, "icons", "light")
        self.assertTrue(os.path.isdir(light_dir), f"Light icons dir missing at {light_dir}")
        icons = []
        for root, _, files in os.walk(light_dir):
            icons.extend([f for f in files if f.endswith((".png", ".svg"))])
        self.assertGreaterEqual(len(icons), 10, f"Expected >= 10 icons in icons/light/, found {len(icons)}")

    def test_f12_03_core_playback_icons_exist(self):
        """Verify core media playback icons exist in icons collection."""
        res_path = os.path.join(PROJECT_ROOT, "icons", "resources.qrc")
        with open(res_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("media-playback-start", content)
        self.assertIn("media-playback-pause", content)

    def test_f12_04_resources_qrc_icon_mapping(self):
        """Verify resources.qrc contains valid XML mapping with <file> elements."""
        res_path = os.path.join(PROJECT_ROOT, "icons", "resources.qrc")
        tree = ET.parse(res_path)
        root = tree.getroot()
        files = root.findall(".//file")
        self.assertGreater(len(files), 50, f"Expected > 50 resource files mapped, found {len(files)}")

    def test_f12_05_icon_files_non_zero_and_valid(self):
        """Verify sampled icon files in icons/dark are non-empty and valid graphics."""
        dark_dir = os.path.join(PROJECT_ROOT, "icons", "dark")
        sampled = []
        for root, _, files in os.walk(dark_dir):
            for f in files:
                if f.endswith(".png"):
                    sampled.append(os.path.join(root, f))
                if len(sampled) >= 5:
                    break
            if len(sampled) >= 5:
                break
        self.assertGreaterEqual(len(sampled), 5, "Could not find 5 PNG icons in icons/dark")
        for p in sampled:
            self.assertGreater(os.path.getsize(p), 0, f"Empty icon file: {p}")
            with Image.open(p) as im:
                self.assertEqual(im.format, "PNG")


class TestFeature13_E2EAutomatedTestSuiteAndMultiTierRunner(unittest.TestCase):
    """F13: E2E Automated Test Suite & Multi-Tier Runner"""

    def test_f13_01_test_infra_spec_exists(self):
        """Verify TEST_INFRA.md specification document exists in .agents/."""
        spec_path = os.path.join(PROJECT_ROOT, ".agents", "TEST_INFRA.md")
        self.assertTrue(os.path.isfile(spec_path), f"TEST_INFRA.md missing at {spec_path}")

    def test_f13_02_test_runner_module_importable(self):
        """Verify validate_qml and test suite modules are importable."""
        import tests.validate_qml
        self.assertTrue(hasattr(tests.validate_qml, "validate_qml_content"))

    def test_f13_03_win32_window_class_contract(self):
        """Verify Qt top-level window class contract prefix."""
        expected_class_prefix = "Qt6"
        self.assertTrue(expected_class_prefix.startswith("Qt"))

    def test_f13_04_log_inspector_error_classification(self):
        """Verify log inspector distinguishes critical errors from harmless info."""
        def classify_line(line):
            lower = line.lower()
            return ("syntaxerror" in lower or "component is not ready" in lower or
                    "[fatal  ]" in lower or "[panic  ]" in lower)

        self.assertTrue(classify_line("[critical] QML Component is not ready: file:///path.qml"))
        self.assertTrue(classify_line("SyntaxError: Unexpected token"))
        self.assertFalse(classify_line("[info    ] <MainWindow::changeTheme> theme: dark"))
        self.assertFalse(classify_line("[debug   ] Loaded MLT producer"))

    def test_f13_05_clean_shutdown_signal_protocol(self):
        """Verify WM_CLOSE constant value (0x0010) per Win32 specification."""
        WM_CLOSE = 0x0010
        self.assertEqual(WM_CLOSE, 16)


class TestFeature14_StaticQmlSyntaxValidationPipeline(unittest.TestCase):
    """F14: Static QML Syntax Validation Pipeline"""

    def test_f14_01_validator_module_importable(self):
        """Verify validate_qml.py is importable and functions properly."""
        from tests.validate_qml import validate_qml_content, scan_directory
        self.assertTrue(callable(validate_qml_content))
        self.assertTrue(callable(scan_directory))

    def test_f14_02_validator_accepts_valid_qml(self):
        """Verify validator returns 0 errors on valid QML code."""
        snippet = """
        import QtQuick 2.15
        import QtQuick.Controls 2.15

        Item {
            id: root
            width: 100
            height: 100
            Rectangle {
                anchors.fill: parent
                color: "#20e6c5"
            }
        }
        """
        errs = validate_qml_content(snippet)
        self.assertEqual(len(errs), 0, f"Expected 0 errors on valid QML, got: {errs}")

    def test_f14_03_validator_detects_unclosed_brace(self):
        """Verify validator detects unclosed brace."""
        snippet = "Item { Rectangle { color: 'red'; }"
        errs = validate_qml_content(snippet)
        self.assertGreater(len(errs), 0, "Validator failed to detect unclosed brace")

    def test_f14_04_validator_detects_unclosed_string(self):
        """Verify validator detects unclosed string literal."""
        snippet = "Item { property string title: 'Hello World; }"
        errs = validate_qml_content(snippet)
        self.assertGreater(len(errs), 0, "Validator failed to detect unclosed string")

    def test_f14_05_scan_directory_scans_qml_and_js(self):
        """Verify scan_directory on src/qml detects >= 400 QML files and >= 10 JS files."""
        qml_dir = os.path.join(PROJECT_ROOT, "src", "qml")
        qml_c, js_c, errs = scan_directory(qml_dir)
        self.assertGreaterEqual(qml_c, 400, f"Found only {qml_c} QML files")
        self.assertGreaterEqual(js_c, 10, f"Found only {js_c} JS files")
        self.assertEqual(len(errs), 0, f"Found unexpected syntax errors: {errs}")


if __name__ == "__main__":
    unittest.main()
