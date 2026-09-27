#!/usr/bin/env python3
"""
test_phase4_viewer_verification.py

Phase 4 Verification Suite: Video Viewer & Transport Controls (Grafito)
- V1: Viewer header (44 px): [ Source | Project ], video mode chip, zoom (Fit), grid, full screen
- V2: #08090B stage with the 6 px stereo peak meter at the right edge of the video
- V3: 4 px progress bar with in/out brackets and a 12 px circular handle (ScrubBar)
- V4: Transport row: 15 px timecode | Start, Previous Frame, 44 px Play, Next Frame, End |
      Loop, Volume; wraps the time above the controls on a narrow player
- V5: Style sheet (capcut_theme.qss and the fallback in mainwindow.cpp) applied to replicas
      of the C++ classes, built from their Q_PROPERTY declarations, and rendered colors
- V6: Invariance: every player action, shortcut, menu entry, zoom and grid option is kept
"""

import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Property, Qt, QtMsgType, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QTabBar, QToolButton, QWidget  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
PLAYER_CPP = SRC / "player.cpp"
PLAYER_H = SRC / "player.h"
MAINWINDOW_CPP = SRC / "mainwindow.cpp"
SCRUBBAR_CPP = SRC / "scrubbar.cpp"
SCRUBBAR_H = SRC / "scrubbar.h"
PLAY_BUTTON_H = SRC / "widgets" / "transportplaybutton.h"
PLAY_BUTTON_CPP = SRC / "widgets" / "transportplaybutton.cpp"
METER_H = SRC / "widgets" / "scopes" / "playerpeakmeterwidget.h"
METER_CPP = SRC / "widgets" / "scopes" / "playerpeakmeterwidget.cpp"
SCOPE_METER_H = SRC / "widgets" / "scopes" / "audiopeakmeterscopewidget.h"
SCOPE_METER_CPP = SRC / "widgets" / "scopes" / "audiopeakmeterscopewidget.cpp"
UTIL_H = SRC / "util.h"
UTIL_CPP = SRC / "util.cpp"
CMAKELISTS = SRC / "CMakeLists.txt"
CAPCUT_THEME_QSS = PROJECT_ROOT / "capcut_theme.qss"
RESOURCES_QRC = PROJECT_ROOT / "icons" / "resources.qrc"
DARK_ICONS = PROJECT_ROOT / "icons" / "dark" / "32x32"

# Every action the player registered before Phase 4 (src/player.cpp, Player::setupActions()).
PLAYER_ACTIONS = [
    "playerPlayPauseAction", "playerLoopAction", "playerLoopRangeAllAction",
    "playerLoopRangeMarkerAction", "playerLoopRangeSelectionAction", "playerLoopRangeAroundAction",
    "playerSkipNextAction", "playerSkipPreviousAction", "playerRewindAction",
    "playerFastForwardAction", "playerSeekStartAction", "playerSeekEndAction",
    "playerNextFrameAction", "playerPreviousFrameAction", "playerForwardOneSecondAction",
    "playerBackwardOneSecondAction", "playerForwardTwoSecondsAction", "playerBackwardTwoAction",
    "playerForwardFiveSecondsAction", "playerBackwardFiveSecondsAction",
    "playerForwardTenSecondsAction", "playerBackwardTenSecondsAction", "playerForwardJumpAction",
    "playerBackwardJumpAction", "playerSetJumpAction", "playerSetInAction", "playerSetOutAction",
    "playerSetPositionAction", "playerSwitchSourceProgramAction", "playerPauseAction",
    "playerFocus", "playerToggleVui",
]
# Transport commands of the Player menu (MainWindow::setupAndConnectPlayerWidget()).
PLAYER_MENU_ACTIONS = [
    "playerPlayPauseAction", "playerLoopAction", "playerFastForwardAction", "playerRewindAction",
    "playerSkipNextAction", "playerSkipPreviousAction", "playerSeekStartAction",
    "playerSeekEndAction", "playerNextFrameAction", "playerPreviousFrameAction",
]
LOOP_RANGE_ACTIONS = ["playerLoopRangeAllAction", "playerLoopRangeMarkerAction",
                      "playerLoopRangeSelectionAction", "playerLoopRangeAroundAction"]
TRANSPORT_ICONS = ["go-first", "go-previous", "go-next", "go-last", "go-down"]


def render_1x(widget):
    """Render `widget` into an image with a device pixel ratio of 1.

    QWidget.grab() follows the screen scaling (for example 125 % on Windows): the image
    is then larger than the widget and every sampled pixel misses its target.
    """
    image = QImage(widget.size(), QImage.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(1.0)
    image.fill(Qt.transparent)
    widget.render(image)
    return image


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


def between(source, start, end):
    """Return the text from the first `start` to the next `end`."""
    first = source.index(start)
    return source[first:source.index(end, first)]


def assert_in_order(test, text, needles):
    positions = []
    for needle in needles:
        test.assertIn(needle, text)
        positions.append(text.index(needle))
    test.assertEqual(positions, sorted(positions), f"Out of order: {needles}")


def action_blocks(source):
    """Map each action registered in Player::setupActions() to the code that creates it."""
    body = function_body(source, "void Player::setupActions()")
    blocks = {}
    for chunk in re.split(r"\n(?=\s*action = new QAction)", body):
        for name in re.findall(r'Actions\.add\("(\w+)"', chunk):
            blocks[name] = chunk
    return blocks


def qproperties(header):
    """Q_PROPERTY declarations of a C++ header as [(type, name)]."""
    return re.findall(r"Q_PROPERTY\((\w+) (\w+) READ \w+ WRITE \w+\)", read(header))


def fallback_stylesheet():
    """The Grafito fallback style sheet of MainWindow::changeTheme() as plain QSS."""
    cpp = read(MAINWINDOW_CPP)
    marker = cpp.index("// Phase 4: Grafito viewer")
    start = cpp.rindex("qss = QStringLiteral(", 0, marker)
    block = cpp[start:cpp.index("// clang-format on", marker)]
    lines = [line for line in block.splitlines() if not line.strip().startswith("//")]
    literals = re.findall(r'"((?:[^"\\]|\\.)*)"', "\n".join(lines))
    return "".join(literal.replace('\\"', '"').replace("\\\\", "\\") for literal in literals)


def make_replica(class_name, base, header):
    """A Python class named like the C++ class, with the same Q_PROPERTYs, for style sheets."""
    attributes = {}
    for type_name, name in qproperties(header):
        python_type = QColor if type_name == "QColor" else int

        def getter(self, _name=name, _type=python_type):
            return self._values.get(_name, _type())

        def setter(self, value, _name=name, _type=python_type):
            self._values[_name] = QColor(value) if _type is QColor else int(value)

        attributes[name] = Property(python_type, getter, setter)

    def __init__(self, parent=None):
        base.__init__(self, parent)
        self._values = {}

    attributes["__init__"] = __init__
    return type(class_name, (base,), attributes)


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


class TestPhase4StaticContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cpp = read(PLAYER_CPP)
        cls.header = read(PLAYER_H)
        cls.main = read(MAINWINDOW_CPP)
        cls.ctor = function_body(cls.cpp, "Player::Player(QWidget *parent)")

    # V1 -----------------------------------------------------------------
    def test_v1_header_contents_and_order(self):
        """44 px header: [ Source | Project ], status, video mode chip, zoom, grid, full screen."""
        self.assertRegex(self.cpp, r"static constexpr int kHeaderHeight = 44;")
        self.assertIn('m_header->setObjectName("playerHeader");', self.ctor)
        self.assertIn("m_header->setFixedHeight(kHeaderHeight);", self.ctor)
        assert_in_order(self, self.ctor, [
            "headerLayout->addWidget(m_tabs, 0, Qt::AlignVCenter);",
            "headerLayout->addWidget(m_statusLabel, 1, Qt::AlignVCenter);",
            "headerLayout->addWidget(m_profileChip, 0, Qt::AlignVCenter);",
            "headerLayout->addWidget(m_zoomButton, 0, Qt::AlignVCenter);",
            "headerLayout->addWidget(m_gridButton, 0, Qt::AlignVCenter);",
            "headerLayout->addWidget(m_fullScreenButton, 0, Qt::AlignVCenter);",
        ])
        assert_in_order(self, self.ctor, ['m_tabs->addTab(tr("Source"));',
                                          'm_tabs->addTab(tr("Project"));'])
        self.assertIn('m_tabs->setObjectName("playerTabs");', self.ctor)
        self.assertIn("connect(m_tabs, &QTabBar::tabBarClicked, this, &Player::onTabBarClicked);",
                      self.ctor)
        self.assertIn("m_tabs->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);", self.ctor)

    def test_v1_video_mode_chip_zoom_and_full_screen(self):
        chip = function_body(self.cpp, "void Player::onProfileChanged()")
        for needle in ("MLT.profile().width()", "MLT.profile().height()", 'tr("%1 fps")',
                       "m_profileChip->setToolTip("):
            self.assertIn(needle, chip)
        self.assertIn("connect(this, &MainWindow::profileChanged, m_player, &Player::onProfileChanged);",
                      self.main)
        self.assertIn('tr("Fit")', function_body(self.cpp, "void Player::setZoom("))
        self.assertIn("m_zoomButton->setPopupMode(QToolButton::MenuButtonPopup);", self.ctor)
        self.assertIn("m_gridButton->setPopupMode(QToolButton::MenuButtonPopup);", self.ctor)
        full_screen = function_body(self.cpp, "void Player::setFullScreenAction(QAction *action)")
        self.assertIn("m_fullScreenButton->setDefaultAction(action);", full_screen)
        self.assertIn("m_player->setFullScreenAction(ui->actionEnterFullScreen);", self.main)

    def test_v1_compact_player(self):
        """A narrow player drops the in/selected line and the chip, never a command."""
        self.assertRegex(self.cpp, r"static constexpr int kCompactWidth = 560;")
        body = function_body(self.cpp, "void Player::layoutToolbars()")
        self.assertIn("const bool compact = width() < kCompactWidth;", body)
        self.assertIn("m_inSelectedToolBar->setVisible(!compact);", body)
        self.assertIn("m_profileChip->setVisible(!compact);", body)
        self.assertNotIn("m_controlsToolBar", body)
        self.assertNotIn("m_optionsToolBar", body)
        self.assertIn("layoutToolbars();", function_body(self.cpp, "void Player::resizeEvent("))

    # V2 -----------------------------------------------------------------
    def test_v2_stage_color(self):
        """The video sits on a #08090B stage; the video widget clears to the same color."""
        self.assertRegex(self.cpp, r"static constexpr QRgb kStageColor = 0xFF08090B;")
        self.assertIn('m_stage->setObjectName("playerStage");', self.ctor)
        self.assertIn("vlayout->addWidget(m_stage, 1);", self.ctor)
        self.assertIn("stagePalette.setColor(QPalette::Window, QColor(kStageColor));", self.ctor)
        self.assertIn("videoPalette.setColor(QPalette::Window, QColor(kStageColor));", self.ctor)
        self.assertIn("m_videoWidget->setPalette(videoPalette);", self.ctor)
        # The video widget turns its window color into the clear (letterbox) color.
        video = read(SRC / "videowidget.cpp")
        self.assertIn("setClearColor(palette().window().color());", video)

    def test_v2_peak_meter_embedded_right_of_video(self):
        assert_in_order(self, self.ctor, [
            "m_videoLayout->addWidget(m_videoScrollWidget, 10);",
            "m_peakMeter = new PlayerPeakMeterWidget;",
            "m_videoLayout->addWidget(m_peakMeter);",
        ])
        self.assertIn("m_peakMeter->onNewFrame(frame);",
                      function_body(self.cpp, "void Player::onFrameDisplayed("))
        self.assertIn("m_peakMeter->clear();", function_body(self.cpp, "void Player::reset()"))
        self.assertIn("m_peakMeter->clear();", function_body(self.cpp, "void Player::showPaused()"))

    def test_v2_peak_meter_widget(self):
        """6 px bars, #2BB596 to #F5C542, levels computed in the scope thread."""
        header = read(METER_H)
        source = read(METER_CPP)
        self.assertIn("class PlayerPeakMeterWidget Q_DECL_FINAL : public ScopeWidget", header)
        self.assertEqual({name for _, name in qproperties(METER_H)},
                         {"trackColor", "lowColor", "highColor", "peakColor", "barWidth"})
        self.assertIn("m_barWidth(6)", source)
        self.assertIn("QColor(0x2B, 0xB5, 0x96)", source)
        self.assertIn("QColor(0xF5, 0xC5, 0x42)", source)
        refresh = function_body(source, "void PlayerPeakMeterWidget::refreshScope(")
        self.assertIn("AudioPeakMeterScopeWidget::peakLevels(frame)", refresh)
        self.assertIn('"showLevels"', refresh)
        self.assertIn("Qt::QueuedConnection", refresh)
        # The Audio Peak Meter scope shares the same level computation.
        self.assertIn("static QVector<double> peakLevels(const SharedFrame &frame);",
                      read(SCOPE_METER_H))
        self.assertIn("peakLevels(",
                      function_body(read(SCOPE_METER_CPP), "void AudioPeakMeterScopeWidget::refreshScope("))
        cmake = read(CMAKELISTS)
        for path in ("widgets/scopes/playerpeakmeterwidget.cpp", "widgets/scopes/playerpeakmeterwidget.h",
                     "widgets/transportplaybutton.cpp", "widgets/transportplaybutton.h"):
            self.assertIn(path, cmake)

    # V3 -----------------------------------------------------------------
    def test_v3_progress_bar_metrics(self):
        """4 px track and 12 px circular handle, colors from the theme."""
        source = read(SCRUBBAR_CPP)
        self.assertRegex(source, r"static constexpr int kTrackHeight = 4;")
        self.assertRegex(source, r"static constexpr int kHandleSize = 12;")
        self.assertEqual({name for _, name in qproperties(SCRUBBAR_H)},
                         {"trackColor", "progressColor", "handleColor", "selectionColor",
                          "markerColor", "loopColor"})
        self.assertIn("drawEllipse", source)

    def test_v3_progress_bar_api_preserved(self):
        """Same ScrubBar interface as before: seeking, in/out, markers and loop range."""
        header = read(SCRUBBAR_H)
        for member in ("void setScale(int maximum);", "void setFramerate(double fps);",
                       "int position() const;", "void setInPoint(int in);", "void setOutPoint(int out);",
                       "void setMarkers(const QList<int> &);", "QList<int> markers() const",
                       "void setMargin(int margin)", "void setLoopRange(int start, int end);",
                       "void seeked(int);", "void inChanged(int);", "void outChanged(int);",
                       "void paused(int);", "bool onSeek(int value);"):
            self.assertIn(member, header)

    def test_v3_progress_bar_aligned_with_video(self):
        self.assertIn("const int rightInset = kStagePadding + m_peakMeter->sizeHint().width() + kStagePadding;",
                      self.ctor)
        self.assertIn("scrubLayout->setContentsMargins(0, 6, rightInset, 0);", self.ctor)
        assert_in_order(self, self.ctor, ["vlayout->addWidget(m_stage, 1);",
                                          "vlayout->addLayout(scrubLayout);",
                                          "vlayout->addWidget(m_transportBar);"])

    # V4 -----------------------------------------------------------------
    def test_v4_transport_controls_order(self):
        """Start, Previous Frame, 44 px Play, Next Frame, End."""
        controls = between(self.ctor, "m_controlsToolBar = new QToolBar", "m_optionsToolBar = new QToolBar")
        assert_in_order(self, controls, [
            'm_controlsToolBar->addAction(Actions["playerSeekStartAction"]);',
            'm_controlsToolBar->addAction(Actions["playerPreviousFrameAction"]);',
            "m_controlsToolBar->addWidget(m_playButton);",
            'm_controlsToolBar->addAction(Actions["playerNextFrameAction"]);',
            'm_controlsToolBar->addAction(Actions["playerSeekEndAction"]);',
        ])
        self.assertIn('m_playButton->setDefaultAction(Actions["playerPlayPauseAction"]);', controls)
        self.assertIn("m_playButton->setIconSize(QSize(kPlayIconSize, kPlayIconSize));", controls)

    def test_v4_play_button(self):
        header = read(PLAY_BUTTON_H)
        source = read(PLAY_BUTTON_CPP)
        self.assertIn("class TransportPlayButton : public QToolButton", header)
        self.assertEqual({name for _, name in qproperties(PLAY_BUTTON_H)},
                         {"fillColor", "hoverColor", "pressedColor", "glyphColor",
                          "disabledFillColor", "disabledGlyphColor", "diameter"})
        self.assertIn("m_diameter(44)", source)
        paint = function_body(source, "void TransportPlayButton::paintEvent(")
        for needle in ("drawEllipse(circle)", "disabledFillColor()", "pressedColor()", "hoverColor()",
                       "QPainter::CompositionMode_SourceIn"):
            self.assertIn(needle, paint)

    def test_v4_timecode_and_options(self):
        self.assertIn('m_positionSpinner->setObjectName("playerPositionSpinner");', self.ctor)
        self.assertIn('m_durationLabel->setObjectName("playerDurationLabel");', self.ctor)
        widths = function_body(self.cpp, "void Player::updateTimeWidths()")
        self.assertIn("findChild<QLineEdit *>()", widths)
        self.assertIn("updateTimeWidths();", function_body(self.cpp, "void Player::onDurationChanged()"))
        options = between(self.ctor, "m_optionsToolBar = new QToolBar", "for (QToolBar *toolbar")
        for action in LOOP_RANGE_ACTIONS:
            self.assertIn(f'loopMenu->addAction(Actions["{action}"]);', options)
        self.assertIn('loopButton->setDefaultAction(Actions["playerLoopAction"]);', options)
        assert_in_order(self, options, ["m_optionsToolBar->addWidget(loopButton);",
                                        "m_optionsToolBar->addWidget(m_volumeButton);"])
        self.assertIn("connect(m_volumeButton, SIGNAL(clicked()), this, SLOT(onVolumeTriggered()));", options)

    def test_v4_transport_row_layout(self):
        """time | centered controls | loop and volume; the time wraps above when narrow."""
        assert_in_order(self, self.ctor, [
            "CenteredRowLayout *transportLayout = new CenteredRowLayout(m_transportBar);",
            "transportLayout->addWidget(m_timeBlock);",
            "transportLayout->addWidget(m_controlsToolBar);",
            "transportLayout->addWidget(m_optionsToolBar);",
        ])
        layout = between(self.cpp, "class CenteredRowLayout : public QLayout", "QString blankTime()")
        self.assertIn("bool hasHeightForWidth() const override { return true; }", layout)
        self.assertIn("fitsOneLine(rect.width())", layout)
        self.assertIn("place(right, qMax(rightStart, leftEnd + gap));", layout)

    def test_v4_toolbars_take_their_named_rules(self):
        """QToolBar sets its margins before it is named: Util::repolish() applies the named rule."""
        loop = between(self.ctor, "for (QToolBar *toolbar :", "m_transportBar = new QWidget;")
        for toolbar in ("m_currentDurationToolBar", "m_inSelectedToolBar", "m_controlsToolBar",
                        "m_optionsToolBar"):
            self.assertIn(toolbar, loop)
        self.assertIn("Util::repolish(toolbar);", loop)
        self.assertIn("static void repolish(QWidget *widget);", read(UTIL_H))
        body = function_body(read(UTIL_CPP), "void Util::repolish(QWidget *widget)")
        assert_in_order(self, body, ["widget->style()->unpolish(widget);",
                                     "widget->style()->polish(widget);",
                                     "QEvent event(QEvent::StyleChange);",
                                     "QCoreApplication::sendEvent(widget, &event);"])
        # The Phase 3 top bar and sidebar toolbars and named buttons are repolished as well.
        self.assertIn("Util::repolish(ui->mainToolBar);", self.main)
        self.assertIn("Util::repolish(toolbar);", function_body(self.main, "void MainWindow::setupSideBar()"))
        self.assertEqual(function_body(self.main, "void MainWindow::applyTopBarButtonStyles()")
                         .count("Util::repolish(button);"), 3)

    def test_v4_transport_icons(self):
        qrc = {f.text for f in ET.parse(RESOURCES_QRC).getroot().iter("file")}
        for name in TRANSPORT_ICONS:
            for ext in ("png", "svg"):
                self.assertTrue((DARK_ICONS / f"{name}.{ext}").is_file(), f"{name}.{ext}")
                self.assertIn(f"dark/32x32/{name}.{ext}", qrc)
            image = QImage(str(DARK_ICONS / f"{name}.png"))
            self.assertEqual((image.width(), image.height()), (32, 32))
        for name in TRANSPORT_ICONS[:4]:
            self.assertIn(f'QIcon::fromTheme("{name}", QIcon(":/icons/dark/32x32/{name}.png"))', self.cpp)

    # V6 -----------------------------------------------------------------
    def test_v6_every_player_action_is_registered(self):
        registered = re.findall(r'Actions\.add\("(\w+)"', self.cpp)
        self.assertEqual(sorted(registered), sorted(PLAYER_ACTIONS))

    def test_v6_player_menu_keeps_every_transport_command(self):
        """Skip, Rewind and Fast Forward left the transport row but stay in the Player menu."""
        for action in PLAYER_MENU_ACTIONS:
            self.assertIn(f'ui->menuPlayer->addAction(Actions["{action}"]);', self.main)
        for action in LOOP_RANGE_ACTIONS:
            self.assertIn(f'loopRangeMenu->addAction(Actions["{action}"]);', self.main)

    def test_v6_shortcuts_unchanged(self):
        blocks = action_blocks(self.cpp)
        expected = {
            "playerPlayPauseAction": "QKeySequence(Qt::Key_Space)",
            "playerLoopAction": "QKeySequence(Qt::Key_Backslash)",
            "playerSkipNextAction": "QKeySequence(Qt::ALT | Qt::Key_Right)",
            "playerSkipPreviousAction": "QKeySequence(Qt::ALT | Qt::Key_Left)",
            "playerSeekStartAction": "QKeySequence(Qt::Key_Home)",
            "playerSeekEndAction": "QKeySequence(Qt::Key_End)",
            "playerNextFrameAction": "QKeySequence(Qt::Key_Right)",
            "playerPreviousFrameAction": "QKeySequence(Qt::Key_Left)",
        }
        for action, shortcut in expected.items():
            self.assertIn(f"action->setShortcut({shortcut});", blocks[action], action)
        self.assertIn('action->setProperty(Actions.hardKeyProperty, "J");', blocks["playerRewindAction"])
        self.assertIn('action->setProperty(Actions.hardKeyProperty, "L");', blocks["playerFastForwardAction"])

    def test_v6_zoom_grid_volume_and_mute_kept(self):
        for zoom in ("0.0f", "0.1f", "0.25f", "0.5f", "1.0f", "2.0f", "3.0f", "4.0f", "5.0f", "7.5f", "10.0f"):
            self.assertIn(f"->setData({zoom});", self.ctor)
        for grid in (2, 3, 4, 16, 10020, 10010, 8090, 95, 20001, 20169, 20043, 20916):
            self.assertIn(f"action->setData({grid});", self.ctor)
        self.assertIn('gridMenu->addAction(tr("Snapping"));', self.ctor)
        self.assertIn("m_volumeSlider->setRange(0, 99);", self.ctor)
        self.assertIn('m_muteButton->setObjectName(QString::fromUtf8("muteButton"));', self.ctor)
        self.assertIn("connect(m_muteButton, SIGNAL(clicked(bool)), this, SLOT(onMuteButtonToggled(bool)));",
                      self.ctor)


class TestPhase4StyleSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()
        cls.qss = read(CAPCUT_THEME_QSS)
        cls.fallback = fallback_stylesheet()
        cls.replicas = {
            "TransportPlayButton": make_replica("TransportPlayButton", QToolButton, PLAY_BUTTON_H),
            "PlayerPeakMeterWidget": make_replica("PlayerPeakMeterWidget", QWidget, METER_H),
            "ScrubBar": make_replica("ScrubBar", QWidget, SCRUBBAR_H),
        }

    def tearDown(self):
        self.app.setStyleSheet("")

    def rule(self, selector):
        match = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", self.qss)
        self.assertIsNotNone(match, f"Missing QSS rule {selector}")
        return match.group(1)

    def polished_replicas(self, stylesheet):
        """Apply `stylesheet` and return the polished replicas and the Qt warnings."""
        collector = _QtWarningCollector()
        previous = qInstallMessageHandler(collector)
        try:
            self.app.setStyleSheet(stylesheet)
            button = self.replicas["TransportPlayButton"]()
            button.setObjectName("playerPlayButton")
            meter = self.replicas["PlayerPeakMeterWidget"]()
            scrubber = self.replicas["ScrubBar"]()
            for widget in (button, meter, scrubber):
                widget.ensurePolished()
            self.app.processEvents()
        finally:
            qInstallMessageHandler(previous)
        return button, meter, scrubber, collector.messages

    # V5 -----------------------------------------------------------------
    def test_v5_qss_rules(self):
        self.assertIn("background-color: #08090B;", self.rule("QWidget#playerStage"))
        self.assertIn("border-radius: 12px;", self.rule("QWidget#Player"))
        self.assertIn("background-color: #0F1115;", self.rule("QTabBar#playerTabs"))
        self.assertIn("background-color: #262A33;", self.rule("QTabBar#playerTabs::tab:selected"))
        self.assertIn("background-color: #1D2027;", self.rule("QLabel#playerProfileChip"))
        timecode = self.rule("TimeSpinBox#playerPositionSpinner")
        self.assertIn("font-size: 15px;", timecode)
        self.assertIn('font-family: "Geist Mono", monospace;', timecode)
        self.assertIn("font-size: 15px;", self.rule("QLabel#playerTimeSeparator,\nQLabel#playerDurationLabel"))
        self.assertIn("image: url(:/icons/dark/32x32/go-down.png);",
                      self.rule("QWidget#playerHeader QToolButton::menu-arrow,\n"
                                "QToolBar#playerOptionsToolBar QToolButton::menu-arrow"))
        self.assertIn("padding: 0px;", self.rule("QToolBar#playerTimeToolBar,\nQToolBar#playerSelectionToolBar,\n"
                                                "QToolBar#playerControlsToolBar,\nQToolBar#playerOptionsToolBar"))

    def test_v5_fallback_stylesheet_in_sync(self):
        """Every Phase 4 selector of capcut_theme.qss is in the fallback of MainWindow::changeTheme()."""
        section = between(self.qss, "3c. GRAFITO VIEWER & TRANSPORT", "4. DOCKS & FLOATING PANELS")
        # Drop the rest of the section title comment and the comments inside the section.
        section = re.sub(r"/\*.*?\*/", "", section[section.index("*/") + 2:], flags=re.S)
        selectors = re.findall(r"(?m)^([^\s{}][^{}]*?)\s*\{", section)
        self.assertGreater(len(selectors), 20)
        flat = " ".join(self.fallback.split())
        for selector in selectors:
            for part in selector.split(","):
                self.assertIn(" ".join(part.split()), flat, f"Fallback lacks {part.strip()}")

    def test_v5_replicas_take_theme_values(self):
        """Qt applies every qproperty of the theme to the C++ property set, without warnings."""
        for name, stylesheet in (("capcut_theme.qss", self.qss), ("fallback", self.fallback)):
            with self.subTest(stylesheet=name):
                button, meter, scrubber, warnings = self.polished_replicas(stylesheet)
                problems = [m for m in warnings if "property" in m.lower() or "parse" in m.lower()]
                self.assertEqual(problems, [])
                colors = {key: value.name().upper() for key, value in button._values.items()
                          if isinstance(value, QColor)}
                self.assertEqual(colors, {"fillColor": "#FF7A45", "hoverColor": "#FF8F61",
                                          "pressedColor": "#E66835", "glyphColor": "#140A05",
                                          "disabledFillColor": "#262A33", "disabledGlyphColor": "#5F6672"})
                self.assertEqual(meter._values["trackColor"].name().upper(), "#1D2027")
                self.assertEqual(meter._values["lowColor"].name().upper(), "#2BB596")
                self.assertEqual(meter._values["highColor"].name().upper(), "#F5C542")
                self.assertEqual(meter._values["barWidth"], 6)
                self.assertEqual(scrubber._values["trackColor"].name().upper(), "#2A2E37")
                self.assertEqual(scrubber._values["progressColor"].name().upper(), "#FF7A45")
                self.assertEqual(scrubber._values["handleColor"].name().upper(), "#FFFFFF")
                loop = scrubber._values["loopColor"]
                self.assertEqual(loop.name().upper(), "#FF7A45")
                self.assertAlmostEqual(loop.alphaF(), 0.6, places=2)

    def test_v5_rendered_stage_header_and_chip(self):
        self.app.setStyleSheet(self.qss)
        player = QWidget()
        player.setObjectName("Player")
        player.resize(400, 160)
        stage = QWidget(player)
        stage.setObjectName("playerStage")
        stage.setGeometry(1, 45, 398, 100)
        tabs = QTabBar(player)
        tabs.setObjectName("playerTabs")
        tabs.setDrawBase(False)
        tabs.addTab("Source")
        tabs.addTab("Project")
        tabs.setCurrentIndex(1)
        tabs.move(12, 6)
        tabs.resize(tabs.sizeHint())
        chip = QLabel("1920x1080 30 fps", player)
        chip.setObjectName("playerProfileChip")
        chip.move(250, 10)
        chip.resize(chip.sizeHint())
        # Like Player::Player(): plain QWidgets paint their style sheet background.
        player.setAttribute(Qt.WA_StyledBackground)
        stage.setAttribute(Qt.WA_StyledBackground)
        player.show()
        self.app.processEvents()
        image = render_1x(player)
        self.addCleanup(player.close)
        self.assertEqual(image.pixelColor(200, 100).name().upper(), "#08090B")  # stage
        self.assertEqual(image.pixelColor(200, 152).name().upper(), "#15171C")  # panel
        selected = tabs.tabRect(1)
        point = tabs.mapTo(player, selected.topLeft())
        self.assertEqual(image.pixelColor(point.x() + 4, point.y() + selected.height() // 2).name().upper(),
                         "#262A33")
        self.assertEqual(image.pixelColor(chip.x() + 3, chip.y() + chip.height() // 2).name().upper(),
                         "#1D2027")


if __name__ == "__main__":
    unittest.main()
