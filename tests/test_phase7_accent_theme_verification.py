#!/usr/bin/env python3
"""
test_phase7_accent_theme_verification.py

Phase 7 Verification Suite: accent colors and theme switch (Grafito)
- A1: Four accent presets (Grafito Orange #FF7A45 by default, Electric Blue #5B8CFF,
      Golden Amber #F5B83D, Neon Lavender #B08CFF) in Settings > Theme > Accent Color
- A2: Persistence: the accent is saved as #RRGGBB (registry or config file) and a broken
      value falls back to the default; setAccentColor() notifies accentColorChanged()
- A3: Every orange of the style sheets (main, hover and pressed shades, rgba) is replaced
      by the accent; no orange is left in any style sheet with another accent
- A4: The hover and pressed shades keep their offsets from the accent (same hue)
- A5: Rendered: the accent reaches the widgets of an application that re-applies the
      style sheet at run time, without creating the widgets again (no restart)
- A6: Live change: palette and style sheet re-applied on accentColorChanged(); widgets
      with their own style sheets, the QML views and the playhead follow the accent
- A7: One Grafito switch (Settings.isGrafito()) instead of checks of the palette lightness
- T1: Theme switch: "Grafito Modern" and "Classic Fusion Dark" (the dark theme of Shotcut
      before the redesign) next to the other themes, which all stay
- T2: The timeline keeps the selection and the timecode keeps its width when the style
      sheet is applied again
"""

import colorsys
import os
import re
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QtMsgType, Qt, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication, QFrame, QToolButton, QVBoxLayout, QWidget  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from tests.validate_qml import validate_qml_content  # noqa: E402

SRC = PROJECT_ROOT / "src"
SETTINGS_CPP = SRC / "settings.cpp"
SETTINGS_H = SRC / "settings.h"
UTIL_CPP = SRC / "util.cpp"
UTIL_H = SRC / "util.h"
MAINWINDOW_CPP = SRC / "mainwindow.cpp"
MAINWINDOW_H = SRC / "mainwindow.h"
MAINWINDOW_UI = SRC / "mainwindow.ui"
QMLAPPLICATION_CPP = SRC / "qmltypes" / "qmlapplication.cpp"
QMLAPPLICATION_H = SRC / "qmltypes" / "qmlapplication.h"
TIMELINEITEMS_CPP = SRC / "qmltypes" / "timelineitems.cpp"
DOCKTOOLBAR_CPP = SRC / "widgets" / "docktoolbar.cpp"
PLAYLISTDOCK_CPP = SRC / "docks" / "playlistdock.cpp"
PLAYLISTDOCK_UI = SRC / "docks" / "playlistdock.ui"
FILESDOCK_CPP = SRC / "docks" / "filesdock.cpp"
TIMELINEDOCK_CPP = SRC / "docks" / "timelinedock.cpp"
ICONVIEW_CPP = SRC / "widgets" / "playlisticonview.cpp"
INSPECTOR_CPP = SRC / "widgets" / "inspectorwidget.cpp"
TIMESPINBOX_CPP = SRC / "widgets" / "timespinbox.cpp"
PLAYER_CPP = SRC / "player.cpp"
TIMELINE_QML = SRC / "qml" / "views" / "timeline" / "timeline.qml"
TRACK_QML = SRC / "qml" / "views" / "timeline" / "Track.qml"
CAPCUT_THEME_QSS = PROJECT_ROOT / "capcut_theme.qss"

ORANGE = "#FF7A45"
PRESETS = {
    "Grafito Orange": "#FF7A45",
    "Electric Blue": "#5B8CFF",
    "Golden Amber": "#F5B83D",
    "Neon Lavender": "#B08CFF",
}
# The files whose style sheets use the orange of Grafito.
STYLE_SHEET_SOURCES = [CAPCUT_THEME_QSS, MAINWINDOW_CPP, DOCKTOOLBAR_CPP, PLAYLISTDOCK_CPP,
                       FILESDOCK_CPP, PLAYLISTDOCK_UI]


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def block(source, start):
    """Return the brace block that follows the first occurrence of `start`."""
    begin = source.index("{", source.index(start))
    depth = 0
    for index in range(begin, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[begin:index + 1]
    raise ValueError(f"Unbalanced block after {start}")


def flat(text):
    """Collapse whitespace so that code checks survive clang-format line wrapping."""
    return re.sub(r"\s+", " ", text)


def render_1x(widget):
    """Render `widget` into an image with a device pixel ratio of 1 (see Phase 3)."""
    image = QImage(widget.size(), QImage.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(1.0)
    image.fill(Qt.transparent)
    widget.render(image)
    return image


def cpp_string(source, start):
    """The concatenated C++ string literals that follow `start`, unescaped."""
    literal = re.compile(r'\s*"((?:[^"\\]|\\.)*)"')
    position = source.index(start) + len(start)
    parts = []
    while True:
        match = literal.match(source, position)
        if not match:
            break
        parts.append(match.group(1))
        position = match.end()
    return "".join(parts).replace("\\\\", "\\")


def accent_regex():
    """The pattern of Util::accentStyleSheet() (Qt and Python share this syntax)."""
    pattern = cpp_string(read(UTIL_CPP), "static const QRegularExpression re(QStringLiteral(")
    return re.compile(pattern, re.IGNORECASE)


def accent_style_sheet(style_sheet, accent):
    """Python port of Util::accentStyleSheet() with the pattern of the C++ code."""
    orange = QColor(ORANGE)
    color = QColor(accent)
    if color == orange or not style_sheet:
        return style_sheet

    def shade(orange_shade):
        if orange_shade == orange:
            return color.name().upper()
        saturation = color.hslSaturationF() * orange_shade.hslSaturationF() / orange.hslSaturationF()
        lightness = color.lightnessF() + orange_shade.lightnessF() - orange.lightnessF()
        return QColor.fromHslF(color.hslHueF(), min(max(saturation, 0.0), 1.0),
                               min(max(lightness, 0.0), 1.0)).name().upper()

    def replace(match):
        if match.group(1):
            return shade(QColor("#" + match.group(1)))
        return f"{color.red()}, {color.green()}, {color.blue()}"

    return accent_regex().sub(replace, style_sheet)


def fallback_stylesheet():
    """The built-in Grafito style sheet of grafitoStyleSheet() in mainwindow.cpp."""
    cpp = read(MAINWINDOW_CPP)
    body = block(cpp, "static QString grafitoStyleSheet()")
    start = body.index("qss = QStringLiteral(")
    code = body[start:body.index("// clang-format on", start)]
    lines = [line for line in code.splitlines() if not line.strip().startswith("//")]
    literals = re.findall(r'"((?:[^"\\]|\\.)*)"', "\n".join(lines))
    return "".join(literal.replace('\\"', '"').replace("\\\\", "\\") for literal in literals)


def is_orange(hex_color):
    """Whether #RRGGBB looks like a shade of the Grafito orange."""
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    return 0.02 < hue < 0.09 and saturation > 0.5 and 0.3 < lightness < 0.85


def orange_tokens(text):
    """The orange colors (#RRGGBB and rgba(255, 122, 69, a)) left in `text`."""
    found = {m.upper() for m in re.findall(r"#[0-9A-Fa-f]{6}\b", text) if is_orange(m)}
    found.update(re.findall(r"255,\s*122,\s*69\b", text))
    return found


class CodeTestCase(unittest.TestCase):
    """assertIn/assertNotIn on source text ignore how the code is wrapped."""

    def assertIn(self, member, container, msg=None):
        if isinstance(member, str) and isinstance(container, str):
            member, container = flat(member), flat(container)
        super().assertIn(member, container, msg)

    def assertNotIn(self, member, container, msg=None):
        if isinstance(member, str) and isinstance(container, str):
            member, container = flat(member), flat(container)
        super().assertNotIn(member, container, msg)


class TestPhase7Accent(CodeTestCase):

    @classmethod
    def setUpClass(cls):
        cls.mainwindow = read(MAINWINDOW_CPP)
        cls.settings = read(SETTINGS_CPP)
        cls.util = read(UTIL_CPP)
        cls.qss = read(CAPCUT_THEME_QSS)
        cls.fallback = fallback_stylesheet()

    # A1 -----------------------------------------------------------------
    def test_a1_four_presets_in_the_accent_menu(self):
        menu = block(self.mainwindow, "void MainWindow::setupSettingsMenu()")
        self.assertIn('auto accentMenu = ui->menuTheme->addMenu(tr("Accent Color"));', menu)
        self.assertIn('accentMenu->setObjectName("menuAccentColor");', menu)
        for name, color in PRESETS.items():
            self.assertIn(f'{{tr("{name}"), QStringLiteral("{color}")}}', menu)
        self.assertIn("action->setCheckable(true);", menu)
        self.assertIn("action->setChecked(Settings.accentColor() == accent.second);", menu)
        # The checked preset shows a ring around its swatch.
        self.assertIn("swatch.addPixmap(pixmap, QIcon::Normal, state);", menu)
        # Only Grafito uses the accent color.
        self.assertIn("accentMenu->setEnabled(Settings.isGrafito());", menu)

    def test_a1_orange_is_the_default(self):
        self.assertIn('static const QString kDefaultAccentColor = QStringLiteral("#FF7A45");',
                      self.settings)
        getter = block(self.settings, "QString ShotcutSettings::accentColor() const")
        self.assertIn('settings.value("accentColor", kDefaultAccentColor)', getter)

    # A2 -----------------------------------------------------------------
    def test_a2_broken_values_fall_back_to_the_default(self):
        pattern = cpp_string(self.settings, "static const QRegularExpression re(QStringLiteral(")
        valid = re.compile(pattern)
        for value in ("#FF7A45", "#5b8cff", "#000000"):
            self.assertTrue(valid.match(value), value)
        for value in ("", "banana", "FF7A45", "#FF7A4", "#FF7A45FF", "#GG7A45", " #FF7A45",
                      "rgb(1,2,3)"):
            self.assertIsNone(valid.match(value), value)
        getter = block(self.settings, "QString ShotcutSettings::accentColor() const")
        self.assertIn("return isValidAccentColor(color) ? color.toUpper() : kDefaultAccentColor;",
                      getter)

    def test_a2_set_accent_color_validates_saves_and_notifies(self):
        setter = block(self.settings, "void ShotcutSettings::setAccentColor(const QString &s)")
        self.assertIn("if (!isValidAccentColor(s)) return;", setter)
        self.assertIn("if (color == accentColor()) return;", setter)
        self.assertIn('settings.setValue("accentColor", color);', setter)
        self.assertIn("emit accentColorChanged();", setter)
        header = read(SETTINGS_H)
        self.assertIn("void accentColorChanged();", header)
        self.assertIn("QString accentColor() const;", header)
        self.assertIn("void setAccentColor(const QString &);", header)

    # A3 -----------------------------------------------------------------
    def test_a3_the_substitution_covers_every_orange_of_the_style_sheets(self):
        regex = accent_regex()
        for path in STYLE_SHEET_SOURCES:
            for token in orange_tokens(read(path)):
                with self.subTest(file=path.name, token=token):
                    self.assertTrue(regex.search(token) or regex.search(token.lower()),
                                    f"{token} of {path.name} does not follow the accent")

    def test_a3_no_orange_is_left_with_another_accent(self):
        sheets = {"capcut_theme.qss": self.qss, "fallback": self.fallback,
                  "playlistdock.ui": read(PLAYLISTDOCK_UI)}
        for name, sheet in sheets.items():
            self.assertTrue(orange_tokens(sheet), name)
            for accent in list(PRESETS.values())[1:]:
                with self.subTest(sheet=name, accent=accent):
                    self.assertEqual(orange_tokens(accent_style_sheet(sheet, accent)), set())

    def test_a3_orange_leaves_the_style_sheet_unchanged(self):
        self.assertEqual(accent_style_sheet(self.qss, ORANGE), self.qss)
        body = block(self.util, "QString Util::accentStyleSheet(const QString &styleSheet)")
        self.assertIn("if (accent == kOrange || styleSheet.isEmpty()) return styleSheet;", body)

    def test_a3_rgba_keeps_its_alpha(self):
        sheet = "a { background: rgba(255, 122, 69, 0.18); } b { color: rgba(255,122,69,0.3); }"
        self.assertEqual(accent_style_sheet(sheet, "#5B8CFF"),
                         "a { background: rgba(91, 140, 255, 0.18); } "
                         "b { color: rgba(91, 140, 255,0.3); }")

    # A4 -----------------------------------------------------------------
    def test_a4_shades_keep_the_hue_of_the_accent(self):
        for accent in PRESETS.values():
            base = QColor(accent)
            hover = QColor(accent_style_sheet("#FF8F61", accent) if accent != ORANGE else "#FF8F61")
            pressed = QColor(accent_style_sheet("#E66835", accent) if accent != ORANGE else "#E66835")
            with self.subTest(accent=accent):
                self.assertEqual(accent_style_sheet("#FF7A45", accent), accent)
                self.assertAlmostEqual(hover.hslHueF(), base.hslHueF(), delta=0.02)
                self.assertAlmostEqual(pressed.hslHueF(), base.hslHueF(), delta=0.02)
                self.assertGreater(hover.lightnessF(), base.lightnessF())
                self.assertLess(pressed.lightnessF(), base.lightnessF())

    def test_a4_visited_links_follow_the_accent(self):
        palette = block(self.mainwindow, "static void setGrafitoPalette()")
        self.assertIn("const QColor accentColor(Settings.accentColor());", palette)
        self.assertIn("palette.setColor(QPalette::Highlight, accentColor);", palette)
        self.assertIn("palette.setColor(QPalette::Link, accentColor);", palette)
        self.assertIn('QColor(Util::accentStyleSheet("#D96232"))', palette)

    # A5 -----------------------------------------------------------------
    def test_a5_rendered_accent_changes_without_new_widgets(self):
        app = QApplication.instance() or QApplication(sys.argv)
        warnings = []

        def handler(mode, context, message):
            if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
                warnings.append(message)

        previous = qInstallMessageHandler(handler)
        window = QWidget()
        window.setObjectName("phase7Window")
        layout = QVBoxLayout(window)
        export = QToolButton()
        export.setObjectName("exportButton")
        export.setText("Export")
        layout.addWidget(export)
        # A widget with its own style sheet, like the Media dropzone (Util::followAccentColor()).
        card = QFrame()
        card.setObjectName("dropZoneCard")
        own_sheet = "QFrame#dropZoneCard { background-color: #FF7A45; }"
        card.setFixedSize(40, 20)
        layout.addWidget(card)
        window.resize(200, 120)
        try:
            app.setStyleSheet(self.qss)
            card.setStyleSheet(own_sheet)
            window.show()
            app.processEvents()
            # Left of the label, inside the rounded background.
            center = export.geometry().center()
            center.setX(export.geometry().left() + 8)
            image = render_1x(window)
            self.assertEqual(image.pixelColor(center).name().upper(), ORANGE)
            self.assertEqual(render_1x(card).pixelColor(20, 10).name().upper(), ORANGE)
            for accent in list(PRESETS.values())[1:] + [ORANGE]:
                # What MainWindow::onAccentColorChanged() and followAccentColor() do.
                app.setStyleSheet(accent_style_sheet(self.qss, accent))
                card.setStyleSheet(accent_style_sheet(own_sheet, accent))
                app.processEvents()
                with self.subTest(accent=accent):
                    image = render_1x(window)
                    self.assertEqual(image.pixelColor(center).name().upper(), accent)
                    self.assertEqual(render_1x(card).pixelColor(20, 10).name().upper(), accent)
            self.assertEqual([w for w in warnings if "parse" in w.lower()], [])
        finally:
            window.close()
            app.setStyleSheet("")
            qInstallMessageHandler(previous)

    # A6 -----------------------------------------------------------------
    def test_a6_live_change_without_restart(self):
        menu = block(self.mainwindow, "void MainWindow::setupSettingsMenu()")
        accents = menu[menu.index('addMenu(tr("Accent Color"))'):]
        self.assertIn("Settings.setAccentColor(action->data().toString());", accents)
        self.assertIn("connect(&Settings, &ShotcutSettings::accentColorChanged, this", accents)
        self.assertIn("onAccentColorChanged();", accents)
        self.assertNotIn("restartAfterChangeTheme", accents)
        slot = block(self.mainwindow, "void MainWindow::onAccentColorChanged()")
        self.assertIn("if (!Settings.isGrafito()) return;", slot)
        self.assertIn("setGrafitoPalette();", slot)
        self.assertIn("qApp->setStyleSheet(grafitoStyleSheet());", slot)
        self.assertIn("void onAccentColorChanged();", read(MAINWINDOW_H))
        sheet = block(self.mainwindow, "static QString grafitoStyleSheet()")
        self.assertIn("return Util::accentStyleSheet(qss);", sheet)

    def test_a6_widgets_with_their_own_style_sheets_follow_the_accent(self):
        toolbar = read(DOCKTOOLBAR_CPP)
        self.assertIn("connect(&Settings, SIGNAL(accentColorChanged()), SLOT(updateStyle()));", toolbar)
        self.assertIn("setStyleSheet(Util::accentStyleSheet(styleSheet));",
                      block(toolbar, "void DockToolBar::updateStyle()"))
        playlist = read(PLAYLISTDOCK_CPP)
        self.assertIn("Util::followAccentColor(ui->dropZoneCard);", playlist)
        self.assertIn("toolbar2->setStyleSheet(styleSheet); Util::followAccentColor(toolbar2);", playlist)
        self.assertIn("toolbar2->setStyleSheet(styleSheet); Util::followAccentColor(toolbar2);",
                      read(FILESDOCK_CPP))
        follow = block(self.util, "void Util::followAccentColor(QWidget *widget)")
        self.assertIn('widget->setProperty(kProperty, widget->styleSheet());', follow)
        self.assertIn("QObject::connect(&Settings, &ShotcutSettings::accentColorChanged, widget, apply);",
                      follow)
        # The dynamic property must not reach DockToolBar::event(), which restyles itself.
        self.assertNotIn("followAccentColor(toolbar)", playlist)

    def test_a6_qml_and_playhead_follow_the_accent(self):
        header = read(QMLAPPLICATION_H)
        self.assertIn("Q_PROPERTY(QColor playheadColor READ playheadColor NOTIFY accentColorChanged)",
                      header)
        self.assertIn("Q_PROPERTY(bool grafito READ grafito CONSTANT)", header)
        self.assertIn("void accentColorChanged();", header)
        cpp = read(QMLAPPLICATION_CPP)
        ctor = block(cpp, "QmlApplication::QmlApplication()")
        self.assertIn("connect(&Settings, &ShotcutSettings::accentColorChanged, this, "
                      "&QmlApplication::accentColorChanged);", ctor)
        self.assertIn("property color accentColor: application.playheadColor", read(TIMELINE_QML))
        playhead = block(read(TIMELINEITEMS_CPP), "class TimelinePlayhead : public QQuickPaintedItem")
        self.assertIn("connect(&Settings, &ShotcutSettings::accentColorChanged, this, [this]() "
                      "{ update(); });", playhead)

    # A7 -----------------------------------------------------------------
    def test_a7_one_grafito_switch(self):
        theme = block(self.mainwindow, "void MainWindow::changeTheme(const QString &theme)")
        self.assertIn("Settings.setGrafito(mytheme == kThemeDark);", theme)
        self.assertIn("bool isGrafito() const { return m_isGrafito; }", read(SETTINGS_H))
        self.assertIn("return Settings.isGrafito();", block(read(QMLAPPLICATION_CPP),
                                                              "bool QmlApplication::grafito()"))
        checks = {
            DOCKTOOLBAR_CPP: 'return objectName() == "timelineToolbar" && Settings.isGrafito();',
            ICONVIEW_CPP: "return m_cardMode && Settings.isGrafito();",
            INSPECTOR_CPP: "const bool dark = Settings.isGrafito();",
            PLAYER_CPP: "if (Settings.isGrafito()) {",
        }
        for path, check in checks.items():
            with self.subTest(file=path.name):
                source = read(path)
                self.assertIn(check, source)
                self.assertNotIn("lightnessF() < 0.5", source)
        self.assertIn("readonly property bool grafito: application.grafito", read(TIMELINE_QML))

    # T1 -----------------------------------------------------------------
    def test_t1_theme_actions(self):
        ui = read(MAINWINDOW_UI)
        menu = ui[ui.index('<widget class="QMenu" name="menuTheme">'):]
        menu = menu[:menu.index("</widget>")]
        self.assertEqual(re.findall(r'<addaction name="(\w+)"/>', menu),
                         ["actionSystemTheme", "actionSystemFusion", "actionFusionDark",
                          "actionClassicFusionDark", "actionFusionLight"])
        self.assertIn("<string>Grafito Modern</string>", ui)
        self.assertIn("<string>Classic Fusion Dark</string>", ui)
        settings_menu = block(self.mainwindow, "void MainWindow::setupSettingsMenu()")
        self.assertIn("group->addAction(ui->actionClassicFusionDark);", settings_menu)
        self.assertIn('else if (Settings.theme() == "classic-dark") '
                      "ui->actionClassicFusionDark->setChecked(true);", settings_menu)
        # The theme changes after a restart, as before.
        for action, theme in (("actionFusionDark", "dark"), ("actionClassicFusionDark", "classic-dark"),
                              ("actionFusionLight", "light")):
            slot = block(self.mainwindow, f"void MainWindow::on_{action}_triggered()")
            with self.subTest(action=action):
                self.assertIn(f'Settings.setTheme("{theme}");', slot)
                self.assertIn("restartAfterChangeTheme();", slot)
        self.assertIn("void on_actionClassicFusionDark_triggered();", read(MAINWINDOW_H))

    def test_t1_classic_fusion_dark_is_the_theme_before_the_redesign(self):
        theme = block(self.mainwindow, "void MainWindow::changeTheme(const QString &theme)")
        self.assertIn('static const auto kThemeClassicDark = QStringLiteral("classic-dark");',
                      self.mainwindow)
        classic = theme[theme.index("} else if (mytheme == kThemeClassicDark) {"):]
        classic = classic[:classic.index("} else if (mytheme == \"light\")")]
        for line in ("palette.setColor(QPalette::Window, QColor(50, 50, 50));",
                     "palette.setColor(QPalette::WindowText, QColor(220, 220, 220));",
                     "palette.setColor(QPalette::Base, QColor(30, 30, 30));",
                     "palette.setColor(QPalette::AlternateBase, QColor(40, 40, 40));",
                     "palette.setColor(QPalette::Highlight, QColor(23, 92, 118));",
                     "QTabBar::tab:top:selected { background: #404040; border-top: 2px solid #175c76; }",
                     "QIcon::setThemeName(kThemeDark);"):
            self.assertIn(line, classic)
        # No Grafito style sheet and no accent in the classic theme.
        self.assertNotIn("grafitoStyleSheet", classic)
        self.assertNotIn("accentColor", classic)

    def test_t1_grafito_branch_uses_the_helpers(self):
        theme = block(self.mainwindow, "void MainWindow::changeTheme(const QString &theme)")
        grafito = theme[theme.index("if (mytheme == kThemeDark) {"):]
        grafito = grafito[:grafito.index("} else if (mytheme == kThemeClassicDark)")]
        self.assertIn("setGrafitoPalette();", grafito)
        self.assertIn("qApp->setStyleSheet(grafitoStyleSheet());", grafito)
        # The built-in copy is still complete (checked by the Phase 3-6 suites too).
        self.assertGreater(len(self.fallback), 15000)
        self.assertIn("QToolButton#exportButton", self.fallback)

    # T2 -----------------------------------------------------------------
    def test_t2_timeline_shows_the_selection_after_a_reload(self):
        load = block(read(TIMELINEDOCK_CPP), "void TimelineDock::load(bool force)")
        self.assertIn("if (force) emit selectionChanged();", load)
        timeline = read(TIMELINE_QML)
        self.assertIn("onItemAdded: root.tracksEpoch++", timeline)
        self.assertIn("property var track: (tracksRepeater.count > modelData.y && root.tracksEpoch >= 0) "
                      "? trackAt(modelData.y) : null", timeline)
        self.assertIn("track.clipsEpoch >= 0", timeline)
        track = read(TRACK_QML)
        self.assertIn("property int clipsEpoch: 0", track)
        self.assertIn("onItemAdded: trackRoot.clipsEpoch++", track)
        for path in (TIMELINE_QML, TRACK_QML):
            self.assertEqual(validate_qml_content(read(path)), [], path.name)

    def test_t2_timecode_width_follows_its_font(self):
        spin = read(TIMESPINBOX_CPP)
        change = block(spin, "void TimeSpinBox::changeEvent(QEvent *event)")
        self.assertIn("if (event->type() == QEvent::FontChange) updateWidth();", change)
        self.assertIn('setFixedWidth(fontMetrics().boundingRect("_HHH:MM:SS;FFF_").width());',
                      block(spin, "void TimeSpinBox::updateWidth()"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
