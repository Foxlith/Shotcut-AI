#!/usr/bin/env python3
"""
test_phase5_timeline_verification.py

Phase 5 Verification Suite: Multitrack Timeline (Grafito)
- T1: Canvas tokens in timeline.qml: #111317 canvas, #1D2027 current lane, #1B1E24 headers,
      4 px between tracks in the header, lane and track columns
- T2: Playhead: 2 px accent line with a pin head; accent from the palette (dark themes)
- T3: Ruler: 28 px, round label intervals and minor ticks; new timelines at 60 px per second
      (the interval logic runs in a JavaScript engine)
- T4: Track headers: 164 px, V2/V1/A1/A2 badges numbered from the video track count, track
      heights V2 44 / V1 58 / A1 52 / A2 40 scaled by the track height setting (Timeline.js
      runs in a JavaScript engine), every header control kept
- T5: Clips: 6 px radius, video/image/audio tokens, accent border and outer ring when selected,
      #3DD6B0 waveform at 85 %
- T6: 44 px toolbar in the specified groups with #1F2229 dividers (QSS + fallback)
- T7: Invariance: every toolbar action, track header command and track height command kept;
      empty tracks show a dashed drop hint
"""

import os
import re
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtQml import QJSEngine  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from tests.validate_qml import validate_qml_content  # noqa: E402

SRC = PROJECT_ROOT / "src"
TIMELINE_DIR = SRC / "qml" / "views" / "timeline"
TIMELINE_QML = TIMELINE_DIR / "timeline.qml"
TRACKHEAD_QML = TIMELINE_DIR / "TrackHead.qml"
TRACK_QML = TIMELINE_DIR / "Track.qml"
CLIP_QML = TIMELINE_DIR / "Clip.qml"
RULER_QML = TIMELINE_DIR / "Ruler.qml"
TIMELINE_JS = TIMELINE_DIR / "Timeline.js"
TIMELINEDOCK_CPP = SRC / "docks" / "timelinedock.cpp"
DOCKTOOLBAR_CPP = SRC / "widgets" / "docktoolbar.cpp"
MULTITRACK_CPP = SRC / "models" / "multitrackmodel.cpp"
MULTITRACK_H = SRC / "models" / "multitrackmodel.h"
QMLAPPLICATION_CPP = SRC / "qmltypes" / "qmlapplication.cpp"
TIMELINEITEMS_CPP = SRC / "qmltypes" / "timelineitems.cpp"
MAINWINDOW_CPP = SRC / "mainwindow.cpp"
CAPCUT_THEME_QSS = PROJECT_ROOT / "capcut_theme.qss"

# The timeline toolbar before Phase 5 (src/docks/timelinedock.cpp); all of it stays.
TOOLBAR_ACTIONS = [
    "timelineCutAction", "timelineCopyAction", "timelinePasteAction", "timelineAppendAction",
    "timelineDeleteAction", "timelineLiftAction", "timelineOverwriteAction", "timelineSplitAction",
    "timelineMarkerAction", "timelinePrevMarkerAction", "timelineNextMarkerAction",
    "timelineSnapAction", "timelineScrubDragAction", "timelineRippleAction",
    "timelineRippleAllTracksAction", "timelineRippleMarkersAction", "timelineZoomOutAction",
    "timelineZoomInAction", "timelineZoomFitAction", "timelineRecordAudioAction",
]
# Commands of the track headers (TrackHead.qml) before Phase 5.
TRACK_HEAD_CALLS = [
    "timeline.setTrackLock(index, !isLocked)", "timeline.toggleTrackMute(index)",
    "timeline.toggleOtherTracksMute(index)", "timeline.toggleTrackHidden(index)",
    "timeline.toggleOtherTracksHidden(index)", "timeline.setTrackName(index, text)",
    "timeline.filteredClicked()", "timeline.setTrackGain(index, gain)",
]
TRACK_HEAD_IDS = ["lockButton", "volumeButton", "volumePopup", "popupMuteButton", "volumeSlider",
                  "hideButton", "filterButton", "nameEdit", "inlineMeter", "inlineVolumeSlider"]


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


def enclosing(source, marker):
    """Return the brace block that contains the first occurrence of `marker`."""
    position = source.index(marker)
    depth = 0
    for index in range(position, -1, -1):
        if source[index] == "}":
            depth += 1
        elif source[index] == "{":
            if depth == 0:
                return block(source[index:], "{")
            depth -= 1
    raise ValueError(f"No block encloses {marker}")


def assert_in_order(test, text, needles):
    positions = []
    for needle in needles:
        test.assertIn(needle, text)
        positions.append(text.index(needle))
    test.assertEqual(positions, sorted(positions), f"Out of order: {needles}")


_app = None


def js_engine():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication(sys.argv[:1] + ["-platform", "offscreen"])
    return QJSEngine()


class TestPhase5Timeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.timeline = read(TIMELINE_QML)
        cls.head = read(TRACKHEAD_QML)
        cls.track = read(TRACK_QML)
        cls.clip = read(CLIP_QML)
        cls.ruler = read(RULER_QML)
        cls.dock = read(TIMELINEDOCK_CPP)

    # T1 -----------------------------------------------------------------
    def test_t1_canvas_tokens(self):
        for token in ("property color trackBgDark: grafito ? '#111317'",
                      "property color selectedTrackColor: grafito ? '#1D2027'",
                      "property color trackHeadColor: grafito ? '#1B1E24'",
                      "property color trackHeadHoverColor: grafito ? '#262A33'",
                      "property color trackHeadActiveColor: grafito ? '#22252D'",
                      "property color dividerColor: grafito ? '#1F2229'",
                      "property int trackSpacing: 4",
                      "readonly property bool grafito: activePalette.window.hsvValue < 0.5",
                      "color: trackBgDark"):
            self.assertIn(token, self.timeline)
        # Headers, lanes and tracks keep the same 4 px spacing so they stay aligned.
        self.assertEqual(self.timeline.count("spacing: root.trackSpacing"), 3)
        self.assertIn("color: (index === timeline.currentTrack) ? selectedTrackColor", self.timeline)

    def test_t1_qml_syntax(self):
        for path in (TIMELINE_QML, TRACKHEAD_QML, TRACK_QML, CLIP_QML, RULER_QML):
            self.assertEqual(validate_qml_content(read(path)), [], path.name)

    # T2 -----------------------------------------------------------------
    def test_t2_playhead(self):
        cursor = enclosing(self.timeline, "id: cursor\n")
        self.assertIn("color: accentColor", cursor)
        self.assertIn("width: root.snapToDevicePixel(2)", cursor)
        self.assertIn("property color accentColor: application.playheadColor", self.timeline)
        head = block(self.timeline, "Shotcut.TimelinePlayhead {")
        self.assertIn("width: 12", head)
        self.assertIn("height: 16", head)
        color = block(read(QMLAPPLICATION_CPP), "QColor QmlApplication::playheadColor()")
        self.assertIn("lightnessF() < 0.5", color)
        self.assertIn("palette.color(QPalette::Highlight)", color)
        self.assertIn("QColor(0xe0, 0x46, 0x4e)", color)
        paint = block(read(TIMELINEITEMS_CPP), "class TimelinePlayhead : public QQuickPaintedItem")
        self.assertIn("path.quadTo(0, 0, radius, 0);", paint)
        self.assertIn("QmlApplication::playheadColor()", paint)

    # T3 -----------------------------------------------------------------
    def test_t3_ruler(self):
        self.assertIn("height: 28", self.ruler)
        self.assertIn("readonly property int minorTicks:", self.ruler)
        self.assertIn("font.family: 'Geist Mono'", self.ruler)
        body = block(self.ruler, "readonly property real intervalFrames:")
        labels = re.search(r"labelSeconds: (\[[^\]]*\])", self.ruler).group(1)
        engine = js_engine()
        interval = engine.evaluate(
            f"(function(labelSeconds, profile, timeScale) {body})")
        self.assertFalse(interval.isError(), interval.toString())

        def seconds(fps, scale):
            result = interval.call([engine.evaluate(labels), engine.evaluate(f"({{fps: {fps}}})"), scale])
            return result.toNumber() / fps

        # 60 px per second (the default zoom) labels every 2 seconds, 120 px apart.
        self.assertEqual(seconds(30, 2.0), 2)
        self.assertEqual(seconds(25, 60 / 25), 2)
        self.assertEqual(seconds(30, 10.0), 1)       # zoomed in
        self.assertEqual(seconds(30, 0.05), 60)      # zoomed out
        self.assertEqual(seconds(30, 0.0001), 7200)  # the longest interval

    def test_t3_default_zoom_60_px_per_second(self):
        scale = block(read(MULTITRACK_CPP), "double MultitrackModel::scaleFactor() const")
        self.assertIn("60.0 / fps", scale)
        self.assertIn("return qBound(0.0, result, 27.01);", scale)  # saved zoom unchanged

    # T4 -----------------------------------------------------------------
    def test_t4_track_heights(self):
        engine = js_engine()
        engine.evaluate("var multitrack = {trackHeight: 50};")
        result = engine.evaluate(read(TIMELINE_JS))
        self.assertFalse(result.isError(), result.toString())
        height = engine.globalObject().property("trackHeight")

        def heights():
            return [height.call([audio, main]).toInt()
                    for audio, main in ((False, False), (False, True), (True, True), (True, False))]

        self.assertEqual(heights(), [44, 58, 52, 40])  # V2, V1, A1, A2
        engine.evaluate("multitrack.trackHeight = 100;")  # Make Tracks Taller
        self.assertEqual(heights(), [88, 116, 104, 80])
        engine.evaluate("multitrack.trackHeight = 10;")
        self.assertEqual(heights(), [10, 12, 10, 10])
        # Headers, lanes and tracks use the same height per track.
        expression = "Logic.trackHeight(model.audio, model.audio ? model.isTopAudio : model.isBottomVideo)"
        self.assertEqual(self.timeline.count(expression), 2)
        self.assertIn("height: Logic.trackHeight(audio, audio ? isTopAudio : isBottomVideo)", self.timeline)
        self.assertNotIn("Logic.trackHeight()", self.timeline)

    def test_t4_track_badges(self):
        code = re.search(r"trackCode: (.+)", self.timeline).group(1)
        engine = js_engine()
        rows = [(False, 0), (False, 1), (True, 2), (True, 3)]
        codes = [engine.evaluate(f"(function(model, index, multitrack) {{ return {code}; }})")
                 .call([engine.evaluate(f"({{audio: {str(audio).lower()}}})"), index,
                        engine.evaluate("({videoTrackCount: 2})")]).toString()
                 for audio, index in rows]
        self.assertEqual(codes, ["V2", "V1", "A1", "A2"])
        header = read(MULTITRACK_H)
        self.assertIn("Q_PROPERTY(int videoTrackCount READ videoTrackCount NOTIFY videoTrackCountChanged)", header)
        model = read(MULTITRACK_CPP)
        for signal in ("rowsInserted", "rowsRemoved", "modelReset"):
            self.assertIn(f"connect(this, &QAbstractItemModel::{signal}", model)
        self.assertIn(": 164; // Grafito track headers", model)
        badge = enclosing(self.head, "id: trackBadge")
        self.assertIn("color: isVideo ? '#24346B' : '#0F3B35'", badge)
        self.assertIn("root.accentColor", badge)
        self.assertIn("text: trackHeadRoot.trackCode", badge)
        self.assertIn("text: isDefaultName ? (isVideo ? qsTr('Video') : qsTr('Audio')) : trackName", self.head)

    def test_t4_track_header_layout(self):
        self.assertIn("inlineAudioControlsEnabled: height >= root.inlineAudioControlsThreshold", self.timeline)
        self.assertIn("stackedHeaderLayout: height >= root.separateTrackHeaderRowsThreshold", self.timeline)
        self.assertIn("property int separateTrackHeaderRowsThreshold: 44", self.timeline)
        self.assertIn("property int inlineAudioControlsThreshold: 80", self.timeline)
        self.assertIn("columns: trackHeadRoot.stackedHeaderLayout ? 1 : 2", self.head)
        self.assertIn("color: root.trackHeadColor", self.head)
        self.assertIn("color: root.trackHeadHoverColor", self.head)
        self.assertIn("color: root.trackHeadActiveColor", self.head)
        # Lock and volume line up on every track: shown last, buttons aligned right.
        buttons = self.head[self.head.index("id: trackHeadButtons"):]
        assert_in_order(self, buttons, ["id: filterButton", "id: hideButton",
                                        "id: audioLevelIndicatorMouseArea", "id: lockButton",
                                        "id: volumeButton"])

    # T5 -----------------------------------------------------------------
    def test_t5_clip_tokens(self):
        for kind, colors in (("video", "['#24346B', '#4D6BE0', '#EEF1FF', '#B7C2F0']"),
                             ("image", "['#34275A', '#8E6FE0', '#EEE8FF', '#C9B8FF']"),
                             ("audio", "['#0F3B35', '#2BB596', '#E6FFF8', '#A8E6D6']")):
            self.assertIn(f'"{kind}": {colors}', self.clip)
        self.assertIn("readonly property real _cornerRadius: 6", self.clip)
        self.assertIn("readonly property color waveformColor: isAudio ? '#3DD6B0' : clipBorderColor", self.clip)
        self.assertIn("opacity: isTrackMute ? 0.2 : 0.85", self.clip)
        self.assertIn("fillColor: clipRoot.waveformColor", self.clip)
        self.assertIn("(group < 0 ? root.accentColor : root.groupSelectionColor)", self.clip)
        self.assertIn("Qt.lighter(clipBorderColor, 1.15)", self.clip)  # hover
        self.assertEqual(self.clip.count("border.color: clipRoot.frameColor") + self.clip.count("border.color: frameColor"), 2)
        for old in ("#20e6c5", "#ff3b7c", "'lightgray'"):
            self.assertNotIn(old, self.clip)

    def test_t5_selection_ring(self):
        ring = enclosing(self.timeline, "// Accent ring 1 px outside each selected clip")
        self.assertIn("model: timeline.selection", ring)
        self.assertIn("border.width: 1", ring)
        self.assertIn("accentColor", ring)
        self.assertIn("x: clipN ? clipN.x - 2 : 0", ring)
        self.assertIn("width: clipN ? clipN.width + 4 : 0", ring)

    # T6 -----------------------------------------------------------------
    def test_t6_toolbar_groups(self):
        start = self.dock.index('toolbar->setObjectName("timelineToolbar");')
        toolbar = self.dock[start:self.dock.index("vboxLayout->setMenuBar(toolbar);", start)]
        assert_in_order(self, toolbar, [
            "menuButton->setMenu(m_mainMenu);", "toolbar->addSeparator();",
            'Actions["timelineCutAction"]', 'Actions["timelineCopyAction"]', 'Actions["timelinePasteAction"]',
            'Actions["timelineNewGenerator"]', 'Actions["timelineAppendAction"]', 'Actions["timelineDeleteAction"]',
            'Actions["timelineLiftAction"]', 'Actions["timelineOverwriteAction"]', 'Actions["timelineSplitAction"]',
            'Actions["timelineMarkerAction"]', 'Actions["timelinePrevMarkerAction"]',
            'Actions["timelineNextMarkerAction"]', 'Actions["timelineSnapAction"]',
            'Actions["timelineScrubDragAction"]', 'Actions["timelineRippleAction"]',
            'Actions["timelineRippleAllTracksAction"]', 'Actions["timelineRippleMarkersAction"]',
            "spacer->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);",
            'Actions["timelineRecordAudioAction"]', 'Actions["timelineZoomOutAction"]',
            "toolbar->addWidget(zoomSlider);", 'Actions["timelineZoomInAction"]',
            'Actions["timelineZoomFitAction"]',
        ])
        self.assertEqual(toolbar.count("toolbar->addSeparator();"), 5)
        style = read(DOCKTOOLBAR_CPP)
        self.assertIn("barHeight = 44;", style)
        self.assertIn('objectName() == "timelineToolbar"', block(style, "bool DockToolBar::isGrafitoTimeline() const"))

    def test_t6_toolbar_style_sheet(self):
        qss = read(CAPCUT_THEME_QSS)
        bar = re.search(r"(?m)^DockToolBar#timelineToolbar \{([^}]*)\}", qss).group(1)
        self.assertIn("background-color: #15171C;", bar)
        self.assertIn("border-bottom: 1px solid #1F2229;", bar)
        separator = re.search(r"(?m)^DockToolBar#timelineToolbar::separator \{([^}]*)\}", qss).group(1)
        self.assertIn("background-color: #1F2229;", separator)
        fallback = read(MAINWINDOW_CPP)
        self.assertIn('"DockToolBar#timelineToolbar { background-color: #15171C;', fallback)
        self.assertIn('"DockToolBar#timelineToolbar::separator { width: 1px; background-color: #1F2229;', fallback)

    # T7 -----------------------------------------------------------------
    def test_t7_toolbar_actions_kept(self):
        start = self.dock.index('toolbar->setObjectName("timelineToolbar");')
        toolbar = self.dock[start:self.dock.index("vboxLayout->setMenuBar(toolbar);", start)]
        for action in TOOLBAR_ACTIONS:
            self.assertIn(f'toolbar->addAction(Actions["{action}"]);', toolbar)

    def test_t7_track_header_commands_kept(self):
        for call in TRACK_HEAD_CALLS:
            self.assertIn(call, self.head)
        for identifier in TRACK_HEAD_IDS:
            self.assertIn(f"id: {identifier}", self.head)
        # Dragging a header moves the track; dragging the divider resizes the headers.
        self.assertIn("id: dragMouseArea", self.timeline)
        self.assertIn("timeline.moveTrack(drop.source.trackHead.trackIndex, trackHead.trackIndex)", self.timeline)
        self.assertIn("drag.minimumX: 150", self.timeline)
        self.assertIn("onPositionChanged: multitrack.trackHeaderWidth =", self.timeline)
        for action in ("timelineTracksShorterAction", "timelineTracksTallerAction",
                       "timelineResetTrackHeightAction"):
            self.assertIn(f'trackHeightMenu->addAction(Actions["{action}"]);', self.dock)

    def test_t7_empty_track_hint(self):
        self.assertIn("readonly property bool isEmpty:", self.track)
        hint = enclosing(self.timeline, "// Empty track: a dashed drop area with a hint")
        self.assertIn("visible: root.grafito && parent.isEmpty", self.timeline)
        self.assertIn("ctx.setLineDash([4, 3]);", hint)
        self.assertIn("qsTr('Drag audio here')", hint)
        self.assertIn("qsTr('Drag video here')", hint)


if __name__ == "__main__":
    unittest.main()
