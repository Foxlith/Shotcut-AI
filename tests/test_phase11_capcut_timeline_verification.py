#!/usr/bin/env python3
"""
test_phase11_capcut_timeline_verification.py

Phase 11 Verification Suite: a timeline that works like CapCut's
- K1: CapCut shortcuts as second shortcuts: Ctrl+B / Ctrl+Shift+B split, Q / W delete what is
      left / right of the playhead; the shortcuts of Shotcut stay, and nothing else uses them
- H1: Hover preview (the preview axis of CapCut): a setting and a toolbar action, a
      HoverHandler that follows the mouse, gives the playhead back on leaving, keeps it on a
      click or an edit, and waits while playing or dragging; no auto-scroll while previewing
- S1: Snap guide: every snap of a move or a trim shows a line where the edge snapped
- D1: The duration of each clip on the clip
- I1: The icon of the toolbar action, its translations, the study and the traceability
"""

import re
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
TIMELINE_DOCK = SRC / "docks" / "timelinedock.cpp"
TIMELINE_DOCK_H = SRC / "docks" / "timelinedock.h"
SETTINGS_CPP = SRC / "settings.cpp"
SETTINGS_H = SRC / "settings.h"
TIMELINE_QML = SRC / "qml" / "views" / "timeline" / "timeline.qml"
TRACK_JS = SRC / "qml" / "views" / "timeline" / "Track.js"
CLIP_QML = SRC / "qml" / "views" / "timeline" / "Clip.qml"
ICONS = PROJECT_ROOT / "icons"
QRC = ICONS / "resources.qrc"
SPANISH = PROJECT_ROOT / "translations" / "shotcut_es.ts"
STUDY = PROJECT_ROOT / "docs" / "estudio-capcut-linea-de-tiempo.md"
GUIDE = PROJECT_ROOT / "docs" / "guia-principiante.md"
PLAN = PROJECT_ROOT / "plan.md"
AGENT = PROJECT_ROOT / "agent.md"
ROADMAP = PROJECT_ROOT / "docs" / "ROADMAP_SHOTCUT_AI.md"


def read(path):
    return Path(path).read_text(encoding="utf-8")


def flat(text):
    """One space between words, and none after an opening parenthesis (clang-format wraps)."""
    return re.sub(r"\(\s+", "(", re.sub(r"\s+", " ", text))


def block(source, start):
    begin = source.index("{", source.index(start))
    depth = 0
    for index in range(begin, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[begin:index + 1]
    raise ValueError("Unbalanced block after %s" % start)


def action_block(source, title):
    """The code from `new QAction(tr("title")` to its Actions.add()."""
    start = source.index('new QAction(tr("%s")' % title)
    return source[start:source.index("Actions.add(", start)]


class TestPhase11Shortcuts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dock = read(TIMELINE_DOCK)

    def test_k1_capcut_shortcuts_next_to_shotcut_ones(self):
        expected = {
            "Split At Playhead": "{QKeySequence(Qt::Key_S), QKeySequence(Qt::CTRL | Qt::Key_B)}",
            "Split All Tracks At Playhead": "{QKeySequence(Qt::SHIFT | Qt::Key_S), "
                                            "QKeySequence(Qt::CTRL | Qt::SHIFT | Qt::Key_B)}",
            "Ripple Trim Clip In": "{QKeySequence(Qt::SHIFT | Qt::Key_I), QKeySequence(Qt::Key_Q)}",
            "Ripple Trim Clip Out": "{QKeySequence(Qt::SHIFT | Qt::Key_O), QKeySequence(Qt::Key_W)}",
        }
        for title, shortcuts in expected.items():
            with self.subTest(action=title):
                self.assertIn("action->setShortcuts(" + shortcuts + ");", flat(action_block(self.dock, title)))
        # Q and W are the same edit as CapCut's: ripple trim at the playhead.
        self.assertIn("trimClipAtPlayhead(TimelineDock::TrimInPoint, true);",
                      action_block(self.dock, "Ripple Trim Clip In") + self.dock[self.dock.index(
                          'new QAction(tr("Ripple Trim Clip In")'):][:600])

    def test_k1_nothing_else_uses_the_new_shortcuts(self):
        sources = "\n".join(read(path) for path in SRC.rglob("*.cpp"))
        for pattern in (r"Qt::CTRL \| Qt::Key_B\)", r"Qt::CTRL \| Qt::SHIFT \| Qt::Key_B\)",
                        r"QKeySequence\(Qt::Key_Q\)", r"QKeySequence\(Qt::Key_W\)"):
            with self.subTest(shortcut=pattern):
                self.assertEqual(len(re.findall(pattern, sources)), 1)


class TestPhase11HoverPreview(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.qml = read(TIMELINE_QML)

    def test_h1_setting_and_toolbar_action(self):
        self.assertIn("Q_PROPERTY(bool timelineHoverPreview READ timelineHoverPreview WRITE "
                      "setTimelineHoverPreview NOTIFY timelineHoverPreviewChanged)",
                      flat(read(SETTINGS_H)))
        self.assertIn('settings.value("timeline/hoverPreview", true).toBool()', read(SETTINGS_CPP))
        action = flat(action_block(read(TIMELINE_DOCK), "Hover Preview"))
        self.assertIn("action->setCheckable(true);", action)
        self.assertIn("Settings.setTimelineHoverPreview(checked);", action)
        self.assertIn('QIcon::fromTheme("hover_preview", QIcon(":/icons/dark/32x32/hover_preview.png"))',
                      action)
        dock = read(TIMELINE_DOCK)
        toolbar = dock[dock.index('toolbar->addAction(Actions["timelineScrubDragAction"]);'):]
        self.assertTrue(toolbar.startswith('toolbar->addAction(Actions["timelineScrubDragAction"]);\n'
                                           '    toolbar->addAction(Actions["timelineHoverPreviewAction"]);\n'
                                           '    toolbar->addAction(Actions["timelineRippleAction"]);'))

    def test_h1_follows_the_mouse_and_gives_the_playhead_back(self):
        at = flat(block(self.qml, "function hoverPreviewAt(x)"))
        self.assertIn("if (!settings.timelineHoverPreview || trackHeaderRepeater.count === 0 || "
                      "timeline.isPlaying()) return;", at)
        self.assertIn("if (hoverSavedPosition < 0) hoverSavedPosition = timeline.position;", at)
        end = flat(block(self.qml, "function endHoverPreview()"))
        self.assertIn("hoverSavedPosition = -1;", end)
        self.assertIn("if (!timeline.isPlaying()) timeline.position = saved;", end)
        handler = flat(block(self.qml, "HoverHandler {"))
        self.assertIn("enabled: settings.timelineHoverPreview", handler)
        self.assertIn("if (!hovered) root.endHoverPreview();", handler)
        # Never while a button is down (drags and trims) or while selecting.
        self.assertIn("point.pressedButtons === Qt.NoButton && !scrubMouseArea.containsPress && "
                      "!selectionBox.visible", handler)
        self.assertIn("bool TimelineDock::isPlaying() const", read(TIMELINE_DOCK))
        self.assertIn("Q_INVOKABLE bool isPlaying() const;", read(TIMELINE_DOCK_H))

    def test_h1_a_click_or_an_edit_keeps_the_new_position(self):
        pressed = flat(block(self.qml, "onPressed: mouse => {"))
        self.assertIn("root.commitHoverPreview(); timeline.position =", pressed)
        modified = flat(block(self.qml, "function onModified()"))
        self.assertIn("root.commitHoverPreview();", modified)
        # The view does not scroll under the mouse while previewing.
        position = flat(block(self.qml, "function onPositionChanged()"))
        self.assertIn("root.hoverSavedPosition < 0", position)
        origin = flat(block(self.qml, "Rectangle {\n                id: hoverOrigin"))
        self.assertIn("visible: root.hoverSavedPosition >= 0 && root.hoverSavedPosition !== timeline.position",
                      origin)


class TestPhase11SnapGuideAndDuration(unittest.TestCase):

    def test_s1_every_snap_shows_the_guide(self):
        track = read(TRACK_JS)
        helper = flat(block(track, "function snapAt(x, value)"))
        self.assertIn("snapGuide.show(x)", helper)
        for name, count in (("snapClip", 11), ("snapTrimIn", 8), ("snapTrimOut", 7)):
            with self.subTest(function=name):
                body = block(track, "function %s(" % name)
                self.assertEqual(body.count("snapAt("), count)
        # No snap is left without the guide.
        trims = track[track.index("function snapTrimIn"):track.index("function snapDrop")]
        self.assertNotRegex(trims, r"return Math\.round")
        qml = read(TIMELINE_QML)
        guide = flat(block(qml, "Rectangle {\n                id: snapGuide"))
        self.assertIn("function show(x) { contentX = x; visible = true; snapGuideTimer.restart(); }",
                      guide)
        self.assertIn("onTriggered: snapGuide.visible = false", guide)

    def test_d1_duration_on_each_clip(self):
        label = flat(block(read(CLIP_QML), "Text {\n        id: durationLabel"))
        self.assertIn("readonly property real seconds: profile.fps > 0 ? clipDuration / profile.fps : 0",
                      label)
        self.assertIn("qsTr('%1 s').arg(seconds.toLocaleString(Qt.locale(), 'f', 1))", label)
        self.assertIn("visible: !elided && !isBlank && !isTransition && clipDuration > 0", label)
        self.assertIn("anchors { bottom: parent.bottom right: parent.right", label)


class TestPhase11IconTranslationsDocs(unittest.TestCase):

    def test_i1_icon(self):
        qrc = read(QRC)
        for path in ("dark/32x32/hover_preview.png", "light/32x32/hover_preview.png",
                     "dark/32x32/hover_preview.svg"):
            with self.subTest(icon=path):
                self.assertIn("<file>%s</file>" % path, qrc)
                self.assertTrue((ICONS / path).is_file())
        for path in ("dark/32x32/hover_preview.png", "light/32x32/hover_preview.png"):
            data = (ICONS / path).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), (32, 32))
        self.assertIn('stroke="#9AA1AD"', read(ICONS / "dark/32x32/hover_preview.svg"))

    def test_i1_spanish(self):
        root = ET.parse(SPANISH).getroot()
        found = {}
        for context in root.findall("context"):
            for message in context.findall("message"):
                found[(context.findtext("name"), message.findtext("source"))] = message.findtext(
                    "translation")
        self.assertEqual(found.get(("TimelineDock", "Hover Preview")), "Vista previa al pasar el ratón")
        self.assertTrue(found.get(("TimelineDock", "Show the frame under the mouse in the player. "
                                                   "A click moves the playhead there.")))
        self.assertEqual(found.get(("Clip", "%1 s")), "%1 s")

    def test_i1_study_and_traceability(self):
        study = read(STUDY)
        for heading in ("## 1. Cómo se mueve la persona por la línea de tiempo",
                        "## 2. Cómo interactúa con la persona", "## 3. Por qué es tan usado",
                        "## 4. Qué tiene Shotcut AI y qué se añadió", "## Fuentes"):
            self.assertIn(heading, study)
        for words in ("Ctrl+B", "**Q** y **W**", "eje de previsualización", "Guía del imán",
                      "Pista principal magnética"):
            self.assertIn(words, study)
        self.assertGreaterEqual(study.count("](https://"), 6)
        self.assertIn("estudio-capcut-linea-de-tiempo.md", read(GUIDE))
        self.assertIn("FASE 11", read(PLAN))
        self.assertIn("Fase 11", read(AGENT))
        self.assertIn("test_phase11_capcut_timeline_verification.py", read(AGENT))
        self.assertIn("Fase 11", read(ROADMAP))


if __name__ == "__main__":
    unittest.main(verbosity=2)
