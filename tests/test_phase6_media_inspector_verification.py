#!/usr/bin/env python3
"""
test_phase6_media_inspector_verification.py

Phase 6 Verification Suite: Media panel and Inspector (Grafito)
- M1: Media header: search field (#0F1115) and secondary "+ Import" button above the views;
      the search still filters the playlist proxy model
- M2: Two-column grid of 16:9 cards with a duration chip, the name and the type
      (PlaylistIconView card mode; the layout math runs here with the C++ constants)
- M3: Dashed #343944 dropzone below the grid ("Drag files here"), clickable and droppable
- M4: Flat Media bars and the invariance of every playlist control
- T1: Dock tab bars tagged by column: Media = segmented control, Inspector = 2 px accent
      underline (rendered in a replica of the Editing layout)
- T2: [ Inspector | Jobs | History ] tabs first; Filters stays a tab
- I1: The Properties dock hosts the InspectorWidget (header, TRANSFORM, FILTERS, properties)
- I2: TRANSFORM: position X/Y fields and scale/rotation/opacity sliders with numeric fields,
      undoable edits through the current filter, no drift of the position when scaling
- I3: FILTERS: #1D2027 rows with switches, "+ Add filter", reactivity to the selection
- Q1: Style sheet rules, fallback style sheet in sync, parsing without warnings
"""

import math
import os
import re
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shiboken6  # noqa: E402
from PySide6.QtCore import QEvent, Qt, QtMsgType, qInstallMessageHandler  # noqa: E402
from PySide6.QtQml import QJSEngine  # noqa: E402
from PySide6.QtWidgets import QApplication, QDockWidget, QTabBar, QWidget  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import generate_grafito_layout as layout  # noqa: E402
from tests.validate_qml import validate_qml_content  # noqa: E402

SRC = PROJECT_ROOT / "src"
PLAYLISTDOCK_CPP = SRC / "docks" / "playlistdock.cpp"
PLAYLISTDOCK_H = SRC / "docks" / "playlistdock.h"
ICONVIEW_CPP = SRC / "widgets" / "playlisticonview.cpp"
ICONVIEW_H = SRC / "widgets" / "playlisticonview.h"
PLAYLISTMODEL_CPP = SRC / "models" / "playlistmodel.cpp"
PLAYLISTMODEL_H = SRC / "models" / "playlistmodel.h"
DOCKTOOLBAR_CPP = SRC / "widgets" / "docktoolbar.cpp"
INSPECTOR_CPP = SRC / "widgets" / "inspectorwidget.cpp"
INSPECTOR_H = SRC / "widgets" / "inspectorwidget.h"
TOGGLE_CPP = SRC / "widgets" / "toggleswitch.cpp"
TOGGLE_H = SRC / "widgets" / "toggleswitch.h"
MAINWINDOW_CPP = SRC / "mainwindow.cpp"
MAINWINDOW_H = SRC / "mainwindow.h"
PLAYER_CPP = SRC / "player.cpp"
CMAKELISTS = SRC / "CMakeLists.txt"
ATTACHED_FILTERS_QML = SRC / "qml" / "views" / "filter" / "AttachedFilters.qml"
CAPCUT_THEME_QSS = PROJECT_ROOT / "capcut_theme.qss"
RESOURCES_QRC = PROJECT_ROOT / "icons" / "resources.qrc"

# Every control of the Media panel before Phase 6 (src/docks/playlistdock.cpp).
PLAYLIST_TOOLBAR_ACTIONS = [
    "playlistNewBin", "playlistAppendCutAction", "playlistRemoveCutAction",
    "playlistAddFilesAction", "playlistUpdateAction", "playlistViewDetailsAction",
    "playlistViewTilesAction", "playlistViewIconsAction", "playlistBinView",
    "playlistFiltersVideo", "playlistFiltersAudio", "playlistFiltersImage", "playlistFiltersOther",
]
# The properties widgets that the Properties panel showed; the Inspector keeps all of them.
PRODUCER_WIDGETS = [
    "Video4LinuxWidget", "PulseAudioWidget", "AlsaWidget", "DirectShowVideoWidget",
    "AvfoundationProducerWidget", "HtmlGeneratorWidget", "AvformatProducerWidget",
    "ImageProducerWidget", "DecklinkProducerWidget", "ColorProducerWidget",
    "GlaxnimateProducerWidget", "NoiseWidget", "IsingWidget", "LissajousWidget", "PlasmaWidget",
    "ColorBarsWidget", "ToneProducerWidget", "CountProducerWidget", "BlipProducerWidget",
    "MltClipProducerWidget", "LumaMixTransition", "TrackPropertiesWidget",
    "TimelinePropertiesWidget",
]


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


def cpp_constant(source, name):
    match = re.search(r"static const (?:auto|int|qreal) " + name + r" = ([0-9.]+);", source)
    if not match:
        raise AssertionError(f"Missing constant {name}")
    return float(match.group(1))


def q_round(value):
    """qRound(): halves away from zero."""
    return int(value + 0.5) if value >= 0 else int(value - 0.5)


def phase6_qss_rules(qss):
    """The rules of section 3e, each compressed to one line as in the fallback style sheet."""
    start = qss.index("3e. GRAFITO MEDIA & INSPECTOR")
    start = qss.index("*/", start) + 2
    end = qss.index("/* ----", start)
    text = re.sub(r"/\*.*?\*/", "", qss[start:end], flags=re.S)
    rules = []
    for match in re.finditer(r"([^{}]+)\{([^}]*)\}", text):
        selector = re.sub(r"\s*,\s*", ", ", " ".join(match.group(1).split()))
        properties = [p.strip() for p in match.group(2).split(";") if p.strip()]
        rules.append(f"{selector} {{ {'; '.join(properties)}; }}")
    return rules


_app = None


def get_qapp():
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication(sys.argv[:1] + ["-platform", "offscreen"])
    return _app


class _QtWarningCollector:
    def __init__(self):
        self.messages = []

    def __call__(self, msg_type, context, message):
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            self.messages.append(message)


def tag_tab_bars(window):
    """Port of MainWindow::updateDockTabBars() for the replica."""
    docks = {shiboken6.getCppPointer(dock)[0]: dock
             for dock in window.findChildren(QDockWidget, options=Qt.FindDirectChildrenOnly)}
    for bar in window.findChildren(QTabBar, options=Qt.FindDirectChildrenOnly):
        area = Qt.NoDockWidgetArea
        for i in range(bar.count()):
            dock = docks.get(bar.tabData(i))
            if dock is not None:
                area = window.dockWidgetArea(dock)
                break
        style = {Qt.LeftDockWidgetArea: "segmented", Qt.RightDockWidgetArea: "underline"}.get(area, "")
        bar.setProperty("grafitoTabs", style)
        bar.style().unpolish(bar)
        bar.style().polish(bar)
        QApplication.sendEvent(bar, QEvent(QEvent.StyleChange))
        bar.update()


class TestPhase6Media(CodeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.dock = read(PLAYLISTDOCK_CPP)
        cls.view = read(ICONVIEW_CPP)
        cls.model = read(PLAYLISTMODEL_CPP)

    # M1 -----------------------------------------------------------------
    def test_m1_header_search_and_import(self):
        header = self.dock[self.dock.index("// Grafito Media header"):self.dock.index("// Dashed dropzone")]
        for needle in ('header->setObjectName("mediaHeader");',
                       'm_searchField->setObjectName("mediaSearchField");',
                       'QIcon::fromTheme("edit-find"', "QLineEdit::LeadingPosition",
                       'importButton->setObjectName("mediaImportButton");',
                       "connect(importButton, &QPushButton::clicked, this, &PlaylistDock::onAddFilesActionTriggered);",
                       "ui->verticalLayout->insertWidget(0, header);"):
            self.assertIn(needle, header)
        # The header is outside the stacked widget: visible with an empty playlist too.
        self.assertNotIn("ui->filtersLayout->addWidget(m_searchField", self.dock)
        self.assertIn("dark/32x32/edit-find.png", read(RESOURCES_QRC))

    def test_m1_search_still_filters_the_playlist(self):
        self.assertIn("m_proxyModel->setFilterFixedString(search);", self.dock)
        self.assertIn('tr("Only show files whose name, path, or comment contains some text")', self.dock)
        self.assertIn('m_searchField->setPlaceholderText(tr("search"));', self.dock)

    # M2 -----------------------------------------------------------------
    def test_m2_card_mode_is_the_default_icons_view(self):
        self.assertIn("m_iconsView->setCardMode(true);", self.dock)
        self.assertIn("return m_cardMode && palette().color(QPalette::Window).lightnessF() < 0.5;",
                      self.view)
        # Icons is the default view mode (Settings.viewMode() empty).
        self.assertIn("} else { /* if (Settings.viewMode() == kIconsMode) */", self.dock)
        header = read(ICONVIEW_H)
        self.assertIn("void setCardMode(bool enabled);", header)

    def test_m2_two_columns_of_16_9_cards(self):
        gap = cpp_constant(self.view, "kCardGap")
        margin = cpp_constant(self.view, "kCardMargin")
        minimum = cpp_constant(self.view, "kCardMinWidth")
        text = cpp_constant(self.view, "kCardTextHeight")
        updates = block(self.view, "void PlaylistIconView::updateSizes()")
        self.assertIn("m_itemsPerRow = qMax(1, (width + kCardGap) / (kCardMinWidth + kCardGap));", updates)

        def columns(viewport):
            width = max(1, viewport - 2 * margin)
            return max(1, int((width + gap) // (minimum + gap)))

        # 300 px Media panel: the viewport is 260-290 px wide (scroll bar, bins closed).
        for viewport in range(260, 291):
            self.assertEqual(columns(viewport), 2, viewport)
        self.assertEqual(columns(200), 1)
        self.assertEqual(columns(600), 4)
        # Thumbnails keep 16:9 inside the card border.
        for card_width in (120, 131, 139, 144):
            thumb = q_round((card_width - 2) * 9.0 / 16.0)
            self.assertAlmostEqual((card_width - 2) / thumb, 16 / 9, delta=0.02)
        self.assertGreaterEqual(text, 40)
        self.assertIn("qRound((card.width() - 2) * 9.0 / 16.0)", self.view)

    def test_m2_card_tokens(self):
        paint = block(self.view, "void PlaylistIconView::paintCard(")
        for token in ("kCardSurface(0x1D, 0x20, 0x27)", "kCardBorder(0x22, 0x25, 0x2D)",
                      "kCardHoverSurface(0x26, 0x2A, 0x33)", "kCardHoverBorder(0x34, 0x39, 0x44)",
                      "kCardRadius = 8.0", "kCardWaveform(0x3D, 0xD6, 0xB0, 217)"):
            self.assertIn(token, self.view)
        # Selected: accent border and a soft (18 %) accent ring; accent from the palette.
        self.assertIn("palette().color(QPalette::Highlight)", paint)
        self.assertIn("ring.setAlphaF(0.18);", paint)
        # Duration chip in the corner, name and type below.
        self.assertIn("PlaylistModel::FIELD_DURATION", paint)
        self.assertIn("chip.moveBottomRight(thumbRect.bottomRight()", paint)
        self.assertIn("PlaylistModel::FIELD_MEDIA_TYPE)", paint)
        self.assertIn("m_elideMode", paint)
        # Rounded top corners: a union, not an odd-even path with a hole.
        self.assertIn("roundedTop.united(squareBottom)", paint)

    def test_m2_short_duration_chip_text(self):
        body = block(self.view, "static QString shortDuration(const QString &duration)")
        for needle in ('split(QRegularExpression("[:;]"))', "section('.', 0, 0)",
                       "if (parts[0].toInt() == 0)"):
            self.assertIn(needle, body)

        def short_duration(duration):  # port
            parts = re.split(r"[:;]", duration)
            if len(parts) < 3:
                return duration
            parts = parts[:3]
            parts[2] = parts[2].split(".")[0].split(",")[0]
            if int(parts[0]) == 0:
                parts = parts[1:]
            return ":".join(parts)

        self.assertEqual(short_duration("00:00:08.000"), "00:08")
        self.assertEqual(short_duration("00:00:06:15"), "00:06")
        self.assertEqual(short_duration("01:02:03.500"), "01:02:03")
        self.assertEqual(short_duration("240"), "240")

    def test_m2_card_thumbnail_role(self):
        header = read(PLAYLISTMODEL_H)
        self.assertRegex(header, r"FIELD_BIN,\s*FIELD_CARD_THUMBNAIL")
        role = block(self.model, "case FIELD_CARD_THUMBNAIL:")
        self.assertIn("parent.get_data(kThumbnailInProperty)", role)
        self.assertIn("kPlaylistIndexProperty", role)
        self.assertIn("PlaylistModel::FIELD_CARD_THUMBNAIL", self.view)

    # M3 -----------------------------------------------------------------
    def test_m3_dropzone(self):
        zone = self.dock[self.dock.index("// Dashed dropzone"):]
        for needle in ('m_mediaDropZone->setObjectName("mediaDropZone");',
                       "m_mediaDropZone->setAcceptDrops(true);",
                       "m_mediaDropZone->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);",
                       'tr("Drag files here")', 'tr("Video, audio or images")',
                       "ui->verticalLayout_4->addWidget(m_mediaDropZone);",
                       "m_mediaDropZone->installEventFilter(this);"):
            self.assertIn(needle, zone)
        events = block(self.dock, "bool PlaylistDock::eventFilter(QObject *watched, QEvent *event)")
        self.assertIn("watched == ui->dropZoneCard || watched == ui->page || watched == m_mediaDropZone",
                      events)
        self.assertIn("watched == ui->dropZoneCard || watched == m_mediaDropZone", events)
        self.assertIn("onDropped(dropEvent->mimeData(), -1);", events)

    # M4 -----------------------------------------------------------------
    def test_m4_flat_media_bars(self):
        self.assertIn('toolbar->setObjectName("playlistControlsToolbar");', self.dock)
        self.assertIn('toolbar->setObjectName("playlistBinToolbar");', self.dock)
        self.assertEqual(self.dock.count("Util::repolish(toolbar);"), 2)
        self.assertIn('toolbar->setProperty("compact", true);', self.dock)
        flat = block(read(DOCKTOOLBAR_CPP), "bool DockToolBar::isGrafitoFlat() const")
        for name in ("timelineToolbar", "playlistControlsToolbar", "playlistBinToolbar"):
            self.assertIn(f'QStringLiteral("{name}")', flat)

    def test_m4_invariance_of_the_media_controls(self):
        for action in PLAYLIST_TOOLBAR_ACTIONS:
            self.assertIn(f'Actions["{action}"]', self.dock, action)
        self.assertIn("toolbar->addWidget(menuButton);", self.dock)
        self.assertIn("menuButton->setMenu(m_mainMenu);", self.dock)
        # The Phase 1 empty state card stays for an empty playlist.
        self.assertIn("ui->dropZoneCard->installEventFilter(this);", self.dock)
        for view in ("ui->tableView", "ui->listView", "m_iconsView"):
            self.assertIn(f"views << {view};", self.dock)
        # The item count moved from the controls bar to the dropzone row.
        self.assertIn("dropLayout->addWidget(m_label, 0, Qt::AlignRight | Qt::AlignVCenter);", self.dock)
        self.assertIn('m_label->setText(n > 0 ? tr("%n item(s)", nullptr, n) : "");', self.dock)
        self.assertNotIn("toolbar->addWidget(m_label);", self.dock)


class TestPhase6Tabs(CodeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()
        cls.cpp = read(MAINWINDOW_CPP)

    def tearDown(self):
        self.app.setStyleSheet("")

    # T1 -----------------------------------------------------------------
    def test_t1_tab_bars_tagged_by_column(self):
        body = block(self.cpp, "void MainWindow::updateDockTabBars()")
        for needle in ("tabBar->tabData(i).value<quintptr>()", "dockWidgetArea(dock)",
                       'style = QStringLiteral("segmented");', 'style = QStringLiteral("underline");',
                       'tabBar->setProperty("grafitoTabs", style);', "Util::repolish(tabBar);"):
            self.assertIn(needle, body)
        # Retagged when docks move, change tabs or QMainWindow creates a tab bar.
        docks = block(self.cpp, "void MainWindow::setupAndConnectDocks()")
        for needle in ("&QDockWidget::dockLocationChanged", "&QDockWidget::visibilityChanged",
                       "&QMainWindow::tabifiedDockWidgetActivated", "scheduleDockTabBarsUpdate();"):
            self.assertIn(needle, docks)
        self.assertIn("scheduleDockTabBarsUpdate();", block(self.cpp, "void MainWindow::childEvent("))

    def test_t1_tab_data_is_the_dock(self):
        """updateDockTabBars() relies on QMainWindow storing each tab's dock in its data."""
        state = layout.read_states()[layout.WORKSPACE_CONSTANTS["Editing"]]
        ok, window, docks = layout.restore(self.app, state, "Editing", with_theme=False)
        self.addCleanup(window.close)
        self.assertTrue(ok)
        pointers = {shiboken6.getCppPointer(dock)[0]: name for name, dock in docks.items()}
        bars = [bar for bar in window.findChildren(QTabBar) if bar.isVisible() and bar.count() > 1]
        self.assertGreaterEqual(len(bars), 2)
        for bar in bars:
            for i in range(bar.count()):
                self.assertIn(bar.tabData(i), pointers)

    def test_t1_rendered_segmented_and_underline_tabs(self):
        state = layout.read_states()[layout.WORKSPACE_CONSTANTS["Editing"]]
        ok, window, docks = layout.restore(self.app, state, "Editing")
        self.addCleanup(window.close)
        self.assertTrue(ok)
        tag_tab_bars(window)
        self.app.processEvents()
        image = window.grab().toImage()
        bars = {bar.tabText(0): bar for bar in window.findChildren(QTabBar)
                if bar.isVisible() and bar.count() > 1}
        media, inspector = bars["Playlist"], bars["Inspector"]
        self.assertEqual(media.property("grafitoTabs"), "segmented")
        self.assertEqual(inspector.property("grafitoTabs"), "underline")

        def color(bar, x, y):
            point = bar.mapTo(window, bar.rect().topLeft())
            return image.pixelColor(point.x() + x, point.y() + y).name().upper()

        # Segmented control: #0F1115 container, #262A33 pill for the current tab.
        selected = media.tabRect(media.currentIndex())
        self.assertEqual(color(media, media.width() - 6, media.height() // 2), "#0F1115")
        self.assertEqual(color(media, selected.left() + 4, selected.center().y()), "#262A33")
        # Underline tabs: a 2 px #FF7A45 line under the current tab only.
        current = inspector.tabRect(inspector.currentIndex())
        self.assertEqual(inspector.tabText(inspector.currentIndex()), "Inspector")
        self.assertEqual(color(inspector, current.center().x(), current.bottom()), "#FF7A45")
        self.assertEqual(color(inspector, current.center().x(), current.bottom() - 1), "#FF7A45")
        other = inspector.tabRect(1)
        self.assertNotEqual(color(inspector, other.center().x(), other.bottom()), "#FF7A45")

    # T2 -----------------------------------------------------------------
    def test_t2_inspector_tabs_first(self):
        self.assertIn('m_propertiesDock = new QDockWidget(tr("Inspector"), this);', self.cpp)
        self.assertIn('m_propertiesDock->setObjectName("propertiesDock");', self.cpp)
        self.assertEqual(layout.INSPECTOR_TABS[:4], ["propertiesDock", "JobsDock", "historyDock", "FiltersDock"])
        version = int(re.search(r"static constexpr int kDockLayoutVersion = (\d+);", self.cpp).group(1))
        self.assertGreaterEqual(version, 3)
        state = layout.read_states()[layout.WORKSPACE_CONSTANTS["Effects"]]
        ok, window, docks = layout.restore(self.app, state, "Effects", with_theme=False)
        self.addCleanup(window.close)
        tabs = [tuple(bar.tabText(i) for i in range(bar.count())) for bar in window.findChildren(QTabBar)
                if bar.isVisible() and bar.count() > 1]
        # Effects keeps the Filters panel in front.
        self.assertIn(("Filters", "Inspector", "Jobs", "History"), tabs)


class TestPhase6Inspector(CodeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.cpp = read(MAINWINDOW_CPP)
        cls.inspector = read(INSPECTOR_CPP)
        cls.header = read(INSPECTOR_H)

    # I1 -----------------------------------------------------------------
    def test_i1_properties_dock_hosts_the_inspector(self):
        self.assertIn("m_inspector = new InspectorWidget(m_propertiesDock);", self.cpp)
        self.assertIn("m_propertiesDock->setWidget(m_inspector);", self.cpp)
        self.assertNotIn("(QScrollArea *) m_propertiesDock->widget()", self.cpp)
        load = block(self.cpp, "QWidget *MainWindow::loadProducerWidget(Mlt::Producer *producer)")
        self.assertNotIn("scrollArea", load)
        self.assertGreaterEqual(load.count("m_inspector->setProducerWidget(w);"), 5)
        for widget in PRODUCER_WIDGETS:
            self.assertIn(f"new {widget}(", load, widget)
        self.assertIn("m_inspector->setProducerWidget(nullptr);", block(self.cpp, "void MainWindow::hideProducer()"))
        self.assertIn("class InspectorWidget : public QScrollArea", self.header)
        for name in ("inspectorwidget.cpp", "toggleswitch.cpp"):
            self.assertIn(name, read(CMAKELISTS))

    def test_i1_producer_widget_replacement_semantics(self):
        body = block(self.inspector, "void InspectorWidget::setProducerWidget(QWidget *widget)")
        # Like QScrollArea::setWidget(): the previous widget is deleted.
        self.assertIn("delete m_producerWidget.data();", body)
        self.assertIn("connect(widget, &QObject::destroyed, this, &InspectorWidget::refresh);", body)

    def test_i1_header_of_the_selected_item(self):
        header = block(self.inspector, "void InspectorWidget::updateHeader(Mlt::Producer *producer)")
        for needle in ("Util::producerTitle(*producer)", 'meta.join(QStringLiteral(" · "))',
                       '"meta.media.width"', "shortDuration(out - in + 1)",
                       "ThumbnailProvider provider;", "QtConcurrent::run("):
            self.assertIn(needle, header)
        self.assertIn("static const QSize kThumbnailSize(64, 36);", self.inspector)

    # I2 -----------------------------------------------------------------
    def test_i2_transform_controls(self):
        for needle in ('createNumberField("inspectorPositionX", -99999, 99999, QString())',
                       'createNumberField("inspectorPositionY", -99999, 99999, QString())',
                       'createSlider("inspectorScaleSlider", 1, 400)',
                       'createSlider("inspectorRotationSlider", -180, 180)',
                       'createSlider("inspectorOpacitySlider", 0, 100)',
                       'createNumberField("inspectorScaleValue", 1, 1000, QStringLiteral("%"))',
                       'createNumberField("inspectorOpacityValue", 0, 100, QStringLiteral("%"))',
                       'createSectionLabel(tr("Transform"), "inspectorTransformLabel")'):
            self.assertIn(needle, self.inspector)
        label = block(self.inspector, "QLabel *InspectorWidget::createSectionLabel(")
        self.assertIn("text.toUpper()", label)
        self.assertIn("font.setLetterSpacing(QFont::AbsoluteSpacing, 0.8);", label)
        # Numeric fields apply on Enter, focus out or the arrow keys.
        self.assertIn("spinBox->setKeyboardTracking(false);", self.inspector)

    def test_i2_edits_are_undoable_through_the_current_filter(self):
        begin = block(self.inspector, "QmlFilter *InspectorWidget::beginEdit(")
        for needle in ("row = model->add(meta);", "m_controller->setCurrentFilter(row);",
                       "setFilterDefaults(id, filter->service());", "filter->startUndoTracking();",
                       "filter->startUndoParameterCommand(description);"):
            self.assertIn(needle, begin)
        for function in ("void InspectorWidget::applyGeometry(", "void InspectorWidget::applyRotation(",
                         "void InspectorWidget::applyOpacity("):
            self.assertIn("filter->endUndoCommand();", block(self.inspector, function))
        self.assertIn('kSizePositionId = QStringLiteral("affineSizePosition")', self.inspector)
        self.assertIn('kOpacityId = QStringLiteral("brightnessOpacity")', self.inspector)
        # The state kept by SizePositionUI.qml follows the edits.
        self.assertIn("filter->set(kMiddleValue, rect);", self.inspector)
        self.assertIn("filter->set(kRotationMiddleValue, double(degrees));", self.inspector)
        opacity = block(self.inspector, "void InspectorWidget::applyOpacity(")
        self.assertIn('filter->set("alpha", value);', opacity)
        self.assertIn('filter->set("opacity", value);', opacity)

    def test_i2_new_filters_get_the_ui_defaults(self):
        defaults = block(self.inspector, "void InspectorWidget::setFilterDefaults(")
        for needle in ('service.set("transition.fill", 1);', 'service.set("transition.distort", 0);',
                       'service.set("transition.halign", "center");', 'service.set("transition.valign", "middle");',
                       'service.set("background", "color:#00000000");', 'service.set("level", 1);'):
            self.assertIn(needle, defaults)
        # Same values as the filter user interfaces for a new filter.
        size_ui = read(SRC / "qml" / "filters" / "size_position" / "SizePositionUI.qml")
        self.assertIn("filter.set(fillProperty, 1);", size_ui)
        self.assertIn("filter.set(valignProperty, 'middle');", size_ui)
        opacity_ui = read(SRC / "qml" / "filters" / "opacity" / "ui.qml")
        self.assertIn("filter.set('level', 1);", opacity_ui)

    def test_i2_scaling_keeps_the_position(self):
        """Port of applyGeometry(): whole-pixel rectangles centered without drift."""
        self.assertIn("return qMax(reference - 2.0 * qRound((reference - target) / 2.0), "
                      "2.0 - std::fmod(reference, 2.0));", self.inspector)
        geometry = block(self.inspector, "void InspectorWidget::applyGeometry(")
        self.assertIn("rect.moveCenter(base.center() + QPointF(m_positionX->value(), m_positionY->value()));",
                      geometry)

        def same_parity(target, reference):
            return max(reference - 2.0 * q_round((reference - target) / 2.0), 2.0 - math.fmod(reference, 2.0))

        for base in ((0, 0, 1920, 1080), (240, 0, 1440, 1080), (0, 0, 1280, 720)):
            bx, by, bw, bh = base
            aspect = bw / bh
            for offset in ((0, 0), (37, -12), (-5, 3)):
                for scale in (274, 1, 50, 99, 101, 133, 400, 1000, 7):
                    w = same_parity(bw * scale / 100.0, bw)
                    h = same_parity(w / aspect, bh)
                    x = bx + bw / 2 + offset[0] - w / 2
                    y = by + bh / 2 + offset[1] - h / 2
                    self.assertEqual(x, int(x), (base, offset, scale))
                    self.assertEqual(y, int(y), (base, offset, scale))
                    # What updateTransform() shows back: the same offset.
                    self.assertEqual(q_round(x + w / 2 - (bx + bw / 2)), offset[0])
                    self.assertEqual(q_round(y + h / 2 - (by + bh / 2)), offset[1])
                    # Whole pixels: the aspect ratio is exact up to 2 px of height.
                    self.assertAlmostEqual(w / h, aspect, delta=max(0.01, 2.0 * aspect / h))

    def test_i2_keyframed_values_are_read_only(self):
        body = block(self.inspector, "void InspectorWidget::updateTransform(Mlt::Producer *producer)")
        self.assertIn("contains('=')", self.inspector)
        for needle in ("geometryKeyframed = simple || isKeyframed(*service, kRectProperty);",
                       "w->setEnabled(!geometryKeyframed);", "m_transformHint->setVisible(",
                       "if (!m_scaleSlider->isSliderDown())"):
            self.assertIn(needle, body)
        # Audio clips, tracks, the output and transitions have no TRANSFORM section.
        visual = block(self.inspector, "static bool isVisualClip(Mlt::Producer *producer)")
        for needle in ("mlt_service_playlist_type", "mlt_service_tractor_type", "kShotcutTransitionProperty",
                       "!isAudioOnly(*producer)"):
            self.assertIn(needle, visual)

    # I3 -----------------------------------------------------------------
    def test_i3_filter_rows(self):
        filters = block(self.inspector, "void InspectorWidget::updateFilters()")
        for needle in ("model->setData(model->index(index), QVariant(), Qt::CheckStateRole);",
                       "m_controller->setCurrentFilter(index);", "emit filtersPanelRequested();",
                       "row->setToggleVisible(!meta || meta->type() != QmlMetadata::Link);",
                       "row->setCurrent(i == m_controller->currentIndex());",
                       'QStringLiteral("%1 · %2").arg(title).arg(count)'):
            self.assertIn(needle, filters)
        paint = block(self.inspector, "void InspectorFilterRow::paintEvent(QPaintEvent *)")
        self.assertIn("p.fillRect(QRectF(0, 0, 2, height()), accent);", paint)
        for token in ("kSurface(0x1D, 0x20, 0x27)", "kSurfaceHover(0x26, 0x2A, 0x33)",
                      "kSurfacePressed(0x1F, 0x22, 0x29)"):
            self.assertIn(token, self.inspector)
        self.assertIn('if (QAction *action = Actions["filtersAddFilterAction"])', self.inspector)
        self.assertIn("onFiltersDockTriggered(true);", self.cpp)

    def test_i3_toggle_switch(self):
        toggle = read(TOGGLE_CPP)
        for token in ("kSwitchSize(32, 18)", "m_offColor(0x2A, 0x2E, 0x37)", "m_offHoverColor(0x34, 0x39, 0x44)",
                      "m_offPressedColor(0x26, 0x2A, 0x33)", "m_disabledColor(0x1F, 0x22, 0x29)",
                      "m_disabledKnobColor(0x5F, 0x66, 0x72)", "m_knobColor(Qt::white)"):
            self.assertIn(token, toggle)
        self.assertIn("palette().color(QPalette::Highlight)", block(toggle, "QColor ToggleSwitch::onColor() const"))
        self.assertIn("Q_PROPERTY(QColor onColor READ onColor WRITE setOnColor)", read(TOGGLE_H))

    def test_i3_reactivity_to_the_selection(self):
        setup = block(self.inspector, "void InspectorWidget::setFilterController(")
        for signal in ("&QAbstractItemModel::modelReset", "&QAbstractItemModel::rowsInserted",
                       "&QAbstractItemModel::rowsRemoved", "&QAbstractItemModel::rowsMoved",
                       "&QAbstractItemModel::dataChanged", "&AttachedFiltersModel::trackTitleChanged",
                       "&FilterController::currentFilterChanged", "&FilterController::filterChanged",
                       "&FilterController::undoOrRedo"):
            self.assertIn(signal, setup)
        self.assertIn("connect(m_undoStack, &QUndoStack::indexChanged, m_inspector, &InspectorWidget::refresh);",
                      self.cpp)
        self.assertIn("m_inspector->setFilterController(m_filterController);", self.cpp)
        # Coalesced: many changes in one event loop pass refresh once.
        self.assertIn("m_refreshTimer.setSingleShot(true);", self.inspector)

    def test_i3_filters_panel_tolerates_hidden_delegates(self):
        """AttachedFilters.qml: selecting a filter from the Inspector while Filters is hidden."""
        qml = read(ATTACHED_FILTERS_QML)
        self.assertEqual(validate_qml_content(qml), [])
        function = "function updateMobility() " + block(qml, "function updateMobility()")
        get_qapp()
        engine = QJSEngine()

        def run(items, current):
            script = ("var selectedCanMoveUp = true; var selectedCanMoveDown = true;"
                      f"var currentIndex = {current}; var count = {len(items)};"
                      "var attachedFiltersView = {count: count, itemAtIndex: function(i) {"
                      f"  var items = {items}; return items[i] === null ? null : "
                      "  {ListView: {section: items[i]}}; }};"
                      + function + "updateMobility(); [selectedCanMoveUp, selectedCanMoveDown];")
            result = engine.evaluate(script)
            self.assertFalse(result.isError(), result.toString())
            return [result.property(0).toBool(), result.property(1).toBool()]

        self.assertEqual(run("[null, null, null]", 1), [False, False])
        self.assertEqual(run("['Video', 'Video', 'Video']", 1), [True, True])
        self.assertEqual(run("['Audio', 'Video', 'Video']", 1), [False, True])
        self.assertEqual(run("[null, 'Video', 'Video']", 1), [False, True])


class TestPhase6StyleSheet(CodeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()
        cls.qss = read(CAPCUT_THEME_QSS)
        cls.cpp = read(MAINWINDOW_CPP)

    def tearDown(self):
        self.app.setStyleSheet("")

    def rule(self, selector):
        match = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", self.qss)
        self.assertIsNotNone(match, f"Missing QSS rule {selector}")
        return match.group(1)

    # Q1 -----------------------------------------------------------------
    def test_q1_rules(self):
        self.assertIn("background-color: #0F1115;", self.rule('QTabBar[grafitoTabs="segmented"]'))
        self.assertIn("background-color: #262A33;", self.rule('QTabBar[grafitoTabs="segmented"]::tab:selected'))
        self.assertIn("border-bottom: 2px solid #FF7A45;", self.rule('QTabBar[grafitoTabs="underline"]::tab:selected'))
        self.assertIn("background-color: #0F1115;", self.rule("QLineEdit#mediaSearchField"))
        self.assertIn("border: 1px solid #2A2E37;", self.rule("QPushButton#mediaImportButton"))
        self.assertIn("border: 1px dashed #343944;", self.rule("QFrame#mediaDropZone"))
        self.assertIn("border: 1px dashed #343944;", self.rule("QPushButton#inspectorAddFilterButton"))
        self.assertIn("background: #2A2E37;", self.rule("QWidget#inspectorTransform QSlider::groove:horizontal"))
        self.assertIn("background: #FF7A45;", self.rule("QWidget#inspectorTransform QSlider::sub-page:horizontal"))
        handle = self.rule("QWidget#inspectorTransform QSlider::handle:horizontal")
        self.assertIn("width: 12px;", handle)
        self.assertIn("background: #FFFFFF;", handle)

    def test_q1_fallback_style_sheet_in_sync(self):
        rules = phase6_qss_rules(self.qss)
        self.assertGreaterEqual(len(rules), 50)
        for rule in rules:
            escaped = '"' + rule.replace("\\", "\\\\").replace('"', '\\"') + '"'
            self.assertIn(escaped, self.cpp, f"Fallback style sheet lacks: {rule}")

    def test_q1_qss_parses_without_warnings(self):
        collector = _QtWarningCollector()
        previous = qInstallMessageHandler(collector)
        try:
            self.app.setStyleSheet(self.qss)
            widget = QWidget()
            widget.setObjectName("inspectorTransform")
            widget.ensurePolished()
            bar = QTabBar()
            bar.setProperty("grafitoTabs", "underline")
            bar.addTab("Inspector")
            bar.ensurePolished()
            self.app.processEvents()
        finally:
            qInstallMessageHandler(previous)
        parse_errors = [m for m in collector.messages if "style" in m.lower() and "parse" in m.lower()]
        self.assertEqual(parse_errors, [])

    def test_q1_viewer_status_message_does_not_squeeze_the_panels(self):
        self.assertIn("m_statusLabel->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Preferred);",
                      read(PLAYER_CPP))


if __name__ == "__main__":
    unittest.main()
