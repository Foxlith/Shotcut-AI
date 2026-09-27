/*
 * Copyright (c) 2013-2026 Meltytech, LLC
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
import QtQml.Models
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window
import org.shotcut.qml as Shotcut
import Shotcut.Controls as Shotcut
import "Timeline.js" as Logic

Rectangle {
    id: root

    property int headerWidth: multitrack.trackHeaderWidth
    // Grafito timeline tokens (plan.md 2.1, 2.4 and 3.3) with dark themes; the classic
    // palette colors with light themes.
    readonly property bool grafito: application.grafito
    property color trackBgDark: grafito ? '#111317' : activePalette.window
    property color laneColor: grafito ? '#15171C' : activePalette.base
    property color alternateLaneColor: grafito ? '#15171C' : activePalette.alternateBase
    property color selectedTrackColor: grafito ? '#1D2027' : Qt.rgba(0.8, 0.8, 0, 0.3)
    property color trackHeadColor: grafito ? '#1B1E24' : activePalette.base
    property color trackHeadHoverColor: grafito ? '#262A33' : Qt.darker(activePalette.base, 1.05)
    property color trackHeadActiveColor: grafito ? '#22252D' : Qt.darker(activePalette.base, 1.1)
    property color dividerColor: grafito ? '#1F2229' : activePalette.mid
    property color secondaryTextColor: grafito ? '#C9CED6' : activePalette.windowText
    property color labelTextColor: grafito ? '#858C98' : activePalette.windowText
    property color disabledTextColor: grafito ? '#5F6672' : activePalette.mid
    property color dropZoneColor: grafito ? '#343944' : activePalette.mid
    property color accentColor: application.playheadColor
    property color groupSelectionColor: '#E8EAEE'
    property int trackSpacing: 4
    // Counts the track items created, also when a model reset creates the same number again.
    property int tracksEpoch: 0
    property alias trackCount: tracksRepeater.count
    property bool stopScrolling: false
    property color adjustmentClipColor: Qt.rgba(92 / 255, 72 / 255, 23 / 255, 1)
    property var dragDelta
    // Per track header: two lines (badge and name above the buttons) from 44 px and the
    // inline meter and volume slider from 80 px.
    property int inlineAudioControlsThreshold: 80
    property int separateTrackHeaderRowsThreshold: 44
    property real pendingZoomContentX: -1
    property int zoomScrollRetries: 0

    signal clipClicked
    signal timelineRightClicked
    signal clipRightClicked

    function snapToDevicePixel(value) {
        var dpr = Screen.devicePixelRatio;
        return Math.round(value * dpr) / dpr;
    }

    function applyPendingZoomScroll() {
        if (pendingZoomContentX < 0)
            return;
        const maxX = Logic.scrollMax().x;
        if (pendingZoomContentX > maxX + 1 && zoomScrollRetries < 10) {
            zoomScrollRetries++;
            applyZoomScrollTimer.restart();
            return;
        }
        tracksFlickable.contentX = Logic.clamp(pendingZoomContentX, 0, maxX);
        pendingZoomContentX = -1;
        zoomScrollRetries = 0;
    }

    function scheduleZoomScroll(x) {
        pendingZoomContentX = Math.max(x, 0);
        zoomScrollRetries = 0;
        applyPendingZoomScroll();
    }

    function setZoom(value, targetX) {
        if (!targetX) {
            let playheadX = timeline.position * multitrack.scaleFactor;
            if (playheadX >= tracksFlickable.contentX && playheadX <= tracksFlickable.contentX + tracksFlickable.width)
                targetX = playheadX;
            else
                targetX = tracksFlickable.contentX + tracksFlickable.width / 2;
        }
        let offset = targetX - tracksFlickable.contentX;
        let before = multitrack.scaleFactor;
        if (isNaN(value))
            value = 0;
        let playheadVisualX = timeline.position * before - tracksFlickable.contentX;
        let playheadWasVisible = playheadVisualX >= 0 && playheadVisualX <= tracksFlickable.width;
        const newScale = Math.pow(Math.max(value, 0), 3) + 0.01;
        let newContentX = -1;
        if (settings.timelineScrolling !== Shotcut.Settings.CenterPlayhead) {
            if (settings.timelineScrollZoom) {
                if (playheadWasVisible)
                    newContentX = Math.max(timeline.position * newScale - playheadVisualX, 0);
                else
                    scrollZoomTimer.restart();
            } else {
                newContentX = (targetX * newScale / before) - offset;
            }
        }
        multitrack.scaleFactor = newScale;
        if (newContentX >= 0)
            scheduleZoomScroll(newContentX);
        for (let i = 0; i < tracksRepeater.count; i++)
            tracksRepeater.itemAt(i).redrawWaveforms(false);
    }

    function adjustZoom(by, targetX) {
        let value = Math.pow(multitrack.scaleFactor - 0.01, 1 / 3);
        setZoom(value + by, targetX);
    }

    function pulseLockButtonOnTrack(index) {
        trackHeaderRepeater.itemAt(index).pulseLockButton();
    }

    function selectMultitrack() {
        for (let i = 0; i < trackHeaderRepeater.count; i++)
            trackHeaderRepeater.itemAt(i).selected = false;
        cornerstone.selected = true;
    }

    function trackAt(index) {
        return tracksRepeater.itemAt(index);
    }

    function resetDrag() {
        dragDelta = Qt.point(0, 0);
    }

    function insertTrackPrompt() {
        trackTypeDialog.show();
    }

    color: trackBgDark

    SystemPalette {
        id: activePalette
        property color scrollBar: (windowText.hsvValue > window.hsvValue) ? Qt.lighter(window) : Qt.darker(window)
    }

    Timer {
        id: scrollZoomTimer

        interval: 100
        onTriggered: {
            let playheadX = timeline.position * multitrack.scaleFactor;
            if (playheadX < tracksFlickable.contentX || playheadX > tracksFlickable.contentX + tracksFlickable.width)
                Logic.scrollIfNeeded(true);
        }
    }

    Timer {
        id: applyZoomScrollTimer

        interval: 10
        onTriggered: applyPendingZoomScroll()
    }

    Timer {
        id: zoomToFitTimer

        property int loopCount: 0
        property double lastContainerWidth: tracksContainer.width
        interval: 10
        triggeredOnStart: true
        repeat: true
        function startZoomFit() {
            loopCount = 0;
            start();
        }
        onTriggered: {
            setZoom(Math.pow((tracksFlickable.width - 50) * multitrack.scaleFactor / tracksContainer.width - 0.01, 1 / 3));
            loopCount++;
            // Sometimes the zoom needs to be calculated again
            if (loopCount > 3 || tracksContainer.width !== lastContainerWidth) {
                stop();
            }
            lastContainerWidth = tracksContainer.width;
        }
    }

    FontMetrics {
        id: fontMetrics
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: root.timelineRightClicked()
    }

    DropArea {
        anchors.fill: parent
        onEntered: drag => {
            if (drag.formats.indexOf('application/vnd.mlt+xml') >= 0 || drag.hasUrls)
                drag.acceptProposedAction();
        }
        onExited: Logic.dropped()
        onPositionChanged: drag => {
            if (drag.formats.indexOf('application/vnd.mlt+xml') >= 0 || drag.hasUrls)
                Logic.dragging(drag, drag.hasUrls ? 0 : parseInt(drag.text));
        }
        onDropped: drop => {
            if (drop.formats.indexOf('application/vnd.mlt+xml') >= 0) {
                if (timeline.currentTrack >= 0) {
                    Logic.acceptDrop(drop.getDataAsString('application/vnd.mlt+xml'));
                    drop.acceptProposedAction();
                }
            } else if (drop.hasUrls) {
                Logic.acceptDrop(drop.urls);
                drop.acceptProposedAction();
            }
            Logic.dropped();
        }
    }

    Row {
        anchors.fill: parent

        Column {
            z: 1

            Rectangle {
                id: cornerstone

                property bool selected: false

                width: headerWidth
                height: rulerFlickable.height
                color: selected ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.18) : (grafito ? '#15171C' : activePalette.window)
                border.color: selected ? accentColor : 'transparent'
                border.width: selected ? 1 : 0
                visible: trackHeaderRepeater.count
                z: 1

                Label {
                    text: qsTr('Output')
                    color: cornerstone.selected ? accentColor : labelTextColor
                    elide: Qt.ElideRight
                    x: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 10
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.capitalization: Font.AllUppercase
                    font.letterSpacing: 0.8
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: dividerColor
                }

                MouseArea {
                    anchors.fill: parent
                    anchors.rightMargin: 10
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onClicked: mouse => {
                        timeline.selectMultitrack();
                        if (mouse.button == Qt.RightButton)
                            root.timelineRightClicked();
                    }
                }

                ToolButton {
                    visible: multitrack.filtered
                    anchors.right: parent.right
                    anchors.rightMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: {
                        timeline.selectMultitrack();
                        timeline.filteredClicked();
                    }

                    Shotcut.HoverTip {
                        text: qsTr('Filters')
                    }

                    action: Action {
                        icon.name: 'view-filter'
                        icon.source: 'qrc:///icons/dark/32x32/view-filter.png'
                    }
                }
            }

            Flickable {
                // Non-slider scroll area for the track headers.
                contentY: tracksFlickable.contentY
                width: headerWidth
                height: trackHeaders.height
                interactive: false

                Column {
                    id: trackHeaders

                    spacing: root.trackSpacing

                    Repeater {
                        id: trackHeaderRepeater

                        model: multitrack

                        TrackHead {
                            id: trackHead

                            property var trackIndex: index

                            trackName: model.name
                            trackGain: typeof model.gain !== 'undefined' ? model.gain : 0
                            trackAudioLevel: typeof model.audioLevel !== 'undefined' ? model.audioLevel : -100
                            trackAudioLevelSupported: multitrack.trackLevelIndicatorSupported
                            inlineAudioControlsEnabled: height >= root.inlineAudioControlsThreshold
                            stackedHeaderLayout: height >= root.separateTrackHeaderRowsThreshold
                            trackCode: model.audio ? 'A' + (index - multitrack.videoTrackCount + 1) : 'V' + (multitrack.videoTrackCount - index)
                            isMute: model.mute
                            isHidden: model.hidden
                            isComposite: model.composite
                            isLocked: model.locked
                            isVideo: !model.audio
                            isFiltered: model.filtered
                            isTopVideo: model.isTopVideo
                            isBottomVideo: model.isBottomVideo
                            isTopAudio: model.isTopAudio
                            isBottomAudio: model.isBottomAudio
                            width: headerWidth
                            height: Logic.trackHeight(model.audio, model.audio ? model.isTopAudio : model.isBottomVideo)
                            current: index === timeline.currentTrack
                            onIsLockedChanged: tracksRepeater.itemAt(index).isLocked = isLocked
                            onClicked: {
                                timeline.currentTrack = index;
                                timeline.selectTrackHead(timeline.currentTrack);
                            }

                            MouseArea {
                                id: dragMouseArea

                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                anchors.left: parent.left
                                hoverEnabled: true
                                cursorShape: Qt.DragMoveCursor
                                drag.target: dragItem
                                drag.axis: Drag.YAxis
                                drag.maximumY: trackHeaders.height - y - height / 2
                                drag.minimumY: -y - height / 2
                                width: containsMouse | drag.active ? Math.max(parent.width, dragItemText.contentWidth + 20) : 8
                                onReleased: {
                                    if (drag.active)
                                        dragItem.Drag.drop();
                                }

                                Rectangle {
                                    id: dragItem

                                    property var trackHead: trackHead

                                    anchors.left: dragMouseArea.left
                                    anchors.top: dragMouseArea.top
                                    anchors.bottom: dragMouseArea.bottom
                                    width: dragMouseArea.width
                                    color: 'white'
                                    Drag.active: dragMouseArea.drag.active
                                    Drag.hotSpot.y: height / 2
                                    Drag.keys: ["trackHeader"]
                                    opacity: dragMouseArea.containsMouse | dragMouseArea.drag.active ? 0.7 : 0
                                    states: [
                                        State {
                                            when: dragMouseArea.drag.active | dragMouseArea.containsMouse

                                            ParentChange {
                                                target: dragItem
                                                parent: trackHeaders.parent
                                            }
                                        },
                                        State {
                                            when: !dragMouseArea.drag.active & !dragMouseArea.containsMouse

                                            ParentChange {
                                                target: dragItem
                                                parent: trackHead
                                            }
                                        }
                                    ]

                                    Text {
                                        id: dragItemText

                                        anchors.fill: parent
                                        text: qsTr("Move %1").arg(trackHead.trackName)
                                        style: Text.Outline
                                        styleColor: 'white'
                                        font.pixelSize: Math.min(Math.max(parent.height * 0.7, 15), 30)
                                        verticalAlignment: Text.AlignVCenter
                                        leftPadding: 10
                                    }

                                    Behavior on opacity {
                                        NumberAnimation {}
                                    }
                                }

                                Behavior on width {
                                    PropertyAnimation {
                                        easing.type: Easing.InOutCubic
                                    }
                                }
                            }

                            DropArea {
                                id: dropArea

                                property var trackHead: trackHead
                                property bool containsValidDrag: false

                                anchors.fill: parent
                                keys: ["trackHeader"]
                                onEntered: drag => {
                                    if (trackHead.isVideo == drag.source.trackHead.isVideo) {
                                        containsValidDrag = true;
                                        timeline.currentTrack = trackHead.trackIndex;
                                    } else {
                                        containsValidDrag = false;
                                    }
                                }
                                onExited: {
                                    containsValidDrag = false;
                                }
                                onDropped: drop => {
                                    if (drop.proposedAction == Qt.MoveAction) {
                                        if (trackHead.isVideo && !drop.source.trackHead.isVideo) {
                                            application.showStatusMessage(qsTr('Can not move audio track above video track'));
                                        } else if (!trackHead.isVideo && drop.source.trackHead.isVideo) {
                                            application.showStatusMessage(qsTr('Can not move video track below audio track'));
                                        } else if (trackHead.trackIndex == drop.source.trackHead.trackIndex) {
                                            application.showStatusMessage(qsTr('Track %1 was not moved').arg(drop.source.trackHead.trackName));
                                        } else {
                                            drop.acceptProposedAction();
                                            timeline.moveTrack(drop.source.trackHead.trackIndex, trackHead.trackIndex);
                                        }
                                    }
                                    containsValidDrag = false;
                                }

                                Rectangle {
                                    anchors.fill: parent
                                    color: "transparent"
                                    border.color: "green"
                                    border.width: 3
                                    visible: dropArea.containsValidDrag
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    // thin dividing line between headers and tracks
                    color: dividerColor
                    width: 1
                    x: parent.x + parent.width
                    anchors.top: parent.top
                    anchors.topMargin: -rulerFlickable.height
                    anchors.bottom: parent.bottom

                    MouseArea {
                        anchors.fill: parent
                        anchors.leftMargin: -10
                        acceptedButtons: Qt.LeftButton
                        drag.target: parent
                        drag.axis: Drag.XAxis
                        drag.minimumX: 150
                        drag.maximumX: 500
                        cursorShape: Qt.SizeHorCursor
                        onPositionChanged: multitrack.trackHeaderWidth = Math.max(drag.minimumX, Math.min(drag.maximumX, parent.x))
                    }
                }
            }
        }

        Item {
            id: tracksArea

            width: root.width - headerWidth
            height: root.height
            focus: true

            MouseArea {
                id: scrubMouseArea
                property bool skim: false
                property bool scrub: false
                property real startX
                property real startY

                // This provides skimming and continuous scrubbing at the left/right edges.
                anchors.fill: parent
                hoverEnabled: true
                onWheel: wheel => Logic.onMouseWheel(wheel)
                onPressed: mouse => {
                    if (mouse.y <= rulerFlickable.height || cursorBox.contains(mapToItem(cursorBox, mouse.x, mouse.y)) || (!settings.timelineRectangleSelect === !(mouse.modifiers & Qt.ShiftModifier))) {
                        timeline.position = (tracksFlickable.contentX + mouse.x) / multitrack.scaleFactor;
                        scrub = true;
                        bubbleHelp.hide();
                    } else {
                        startX = mouse.x;
                        selectionBox.x = startX + tracksFlickable.contentX;
                        startY = mouse.y;
                        selectionBox.y = startY + tracksFlickable.contentY - rulerFlickable.height;
                        selectionBox.width = selectionBox.height = 0;
                        selectionBox.visible = true;
                    }
                }
                onReleased: {
                    if (!skim && !scrub)
                        Logic.selectClips();
                    skim = false;
                    scrub = false;
                    selectionBox.visible = false;
                }
                onExited: skim = false
                onPositionChanged: mouse => {
                    if (!selectionBox.visible && (mouse.modifiers === (Qt.ShiftModifier | Qt.AltModifier) || (containsPress && scrub))) {
                        timeline.position = (tracksFlickable.contentX + mouse.x) / multitrack.scaleFactor;
                        bubbleHelp.hide();
                        skim = true;
                    } else {
                        skim = false;
                        if (mouse.x - startX < 0) {
                            selectionBox.x = mouse.x + tracksFlickable.contentX;
                        }
                        if (mouse.y - startY < 0) {
                            selectionBox.y = mouse.y + tracksFlickable.contentY - rulerFlickable.height;
                        }
                        selectionBox.width = Math.abs(mouse.x - startX);
                        selectionBox.height = Math.abs(mouse.y - startY);
                    }
                }
            }

            Timer {
                id: scrubTimer

                interval: 25
                repeat: true
                running: parent.skim && parent.containsMouse && (parent.mouseX < 50 || parent.mouseX > parent.width - 50) && (timeline.position * multitrack.scaleFactor >= 50)
                onTriggered: {
                    if (parent.mouseX < 50)
                        timeline.position -= 10;
                    else
                        timeline.position += 10;
                }
            }

            MouseArea {
                property real startX: mouseX
                property real startY: mouseY

                // This provides drag-scrolling the timeline with the middle mouse button.
                anchors.fill: parent
                acceptedButtons: Qt.MiddleButton
                cursorShape: drag.active ? Qt.ClosedHandCursor : (scrubMouseArea.mouseY < ruler.height || cursorBox.contains(scrubMouseArea.mapToItem(cursorBox, scrubMouseArea.mouseX, scrubMouseArea.mouseY))) ? Qt.SizeHorCursor : Qt.ArrowCursor
                drag.axis: Drag.XAndYAxis
                drag.filterChildren: true
                onPressed: mouse => {
                    startX = mouse.x;
                    startY = mouse.y;
                }
                onPositionChanged: mouse => {
                    let n = mouse.x - startX;
                    startX = mouse.x;
                    tracksFlickable.contentX = Logic.clamp(tracksFlickable.contentX - n, 0, Logic.scrollMax().x);
                    n = mouse.y - startY;
                    startY = mouse.y;
                    tracksFlickable.contentY = Logic.clamp(tracksFlickable.contentY - n, 0, Logic.scrollMax().y);
                }
            }

            Item {
                Flickable {
                    // Non-slider scroll area for the Ruler.
                    id: rulerFlickable

                    contentX: tracksFlickable.contentX
                    width: root.width - headerWidth
                    height: ruler.height + subtitleBar.height
                    interactive: false
                    // workaround to fix https://github.com/mltframework/shotcut/issues/777
                    onContentXChanged: {
                        if (contentX === 0)
                            contentX = tracksFlickable.contentX;
                    }

                    Ruler {
                        id: ruler

                        width: tracksContainer.width
                        timeScale: multitrack.scaleFactor
                        onEditMarkerRequested: {
                            timeline.editMarker(index);
                        }
                        onDeleteMarkerRequested: {
                            timeline.deleteMarker(index);
                        }
                    }

                    SubtitleBar {
                        id: subtitleBar
                        anchors.top: ruler.bottom
                        height: subtitlesModel.trackCount > 0 ? 24 : 0
                        timeScale: multitrack.scaleFactor
                    }
                }

                Flickable {
                    id: tracksFlickable

                    y: rulerFlickable.height
                    width: root.width - headerWidth - 16
                    height: root.height - rulerFlickable.height - 16
                    clip: true
                    // workaround to fix https://github.com/mltframework/shotcut/issues/777
                    onContentXChanged: rulerFlickable.contentX = contentX
                    interactive: false
                    contentWidth: tracksContainer.width + headerWidth
                    contentHeight: trackHeaders.height + 30 // 30 is padding

                    Item {
                        id: tracksLayers

                        anchors.fill: parent

                        Column {
                            // These make the striped background for the tracks.
                            // It is important that these are not part of the track visual hierarchy;
                            // otherwise, the clips will be obscured by the Track's background.
                            spacing: root.trackSpacing

                            Repeater {
                                model: multitrack

                                delegate: Rectangle {
                                    width: Math.max(tracksContainer.width, tracksFlickable.width)
                                    color: (index === timeline.currentTrack) ? selectedTrackColor : (index % 2) ? alternateLaneColor : laneColor
                                    height: Logic.trackHeight(model.audio, model.audio ? model.isTopAudio : model.isBottomVideo)
                                }
                            }
                        }

                        Column {
                            id: tracksContainer

                            spacing: root.trackSpacing
                            onWidthChanged: applyPendingZoomScroll()

                            Repeater {
                                id: tracksRepeater

                                model: trackDelegateModel
                                onItemAdded: root.tracksEpoch++
                            }
                        }

                        Item {
                            // Accent ring 1 px outside each selected clip (plan.md 2.4). The
                            // clip draws the inner 1 px border; hidden while dragging.
                            visible: !selectionContainer.visible

                            Repeater {
                                model: timeline.selection

                                Rectangle {
                                    // The counts make the bindings update when the timeline
                                    // reloads (for example after a palette change) and creates
                                    // the tracks and clips again.
                                    property var track: (tracksRepeater.count > modelData.y && root.tracksEpoch >= 0) ? trackAt(modelData.y) : null
                                    property var clipN: (track && track.clipCount > modelData.x && track.clipsEpoch >= 0) ? track.clipAt(modelData.x) : null

                                    visible: !!clipN && !clipN.isBlank && !clipN.offScreen
                                    x: clipN ? clipN.x - 2 : 0
                                    y: track ? track.y - 2 : 0
                                    width: clipN ? clipN.width + 4 : 0
                                    height: track ? track.height + 4 : 0
                                    color: 'transparent'
                                    border.width: 1
                                    border.color: (clipN && clipN.group >= 0) ? groupSelectionColor : accentColor
                                    topLeftRadius: (clipN && clipN.topLeftRadius > 0) ? clipN.topLeftRadius + 2 : 2
                                    bottomLeftRadius: topLeftRadius
                                    topRightRadius: (clipN && clipN.topRightRadius > 0) ? clipN.topRightRadius + 2 : 2
                                    bottomRightRadius: topRightRadius
                                }
                            }
                        }

                        Item {
                            id: selectionContainer

                            visible: false

                            Repeater {
                                id: selectionRepeater

                                model: timeline.selection

                                Rectangle {
                                    property var clipN: trackAt(modelData.y).clipAt(modelData.x)
                                    property var track: typeof clipN !== 'undefined' && clipN && typeof dragDelta !== 'undefined' ? trackAt(clipN.trackIndex + dragDelta.y) : 0

                                    x: clipN && typeof dragDelta !== 'undefined' ? clipN.x + dragDelta.x : 0
                                    y: track ? track.y : 0
                                    width: clipN ? clipN.width : 0
                                    height: track ? track.height : 0
                                    color: 'transparent'
                                    border.color: (clipN && clipN.group < 0) ? accentColor : 'white'
                                    visible: clipN && !clipN.Drag.active && clipN.trackIndex === clipN.originalTrackIndex
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: selectionBox
                        color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.14)
                        border.color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.8)
                        border.width: 1
                        visible: false
                    }

                    Rectangle {
                        id: cursorBox

                        visible: false
                        width: playhead.width
                        height: root.height - horizontalScrollBar.height
                        x: timeline.position * multitrack.scaleFactor - width / 2
                        y: 0
                    }

                    ScrollBar.horizontal: Shotcut.HorizontalScrollBar {
                        id: horizontalScrollBar

                        policy: ScrollBar.AlwaysOn
                        visible: tracksContainer.width > tracksFlickable.width
                        parent: tracksFlickable.parent
                        anchors.top: tracksFlickable.bottom
                        anchors.left: tracksFlickable.left
                        anchors.right: tracksFlickable.right
                    }

                    ScrollBar.vertical: Shotcut.VerticalScrollBar {
                        policy: ScrollBar.AlwaysOn
                        visible: tracksFlickable.contentHeight > tracksFlickable.height
                        parent: tracksFlickable.parent
                        anchors.top: tracksFlickable.top
                        anchors.left: tracksFlickable.right
                        anchors.bottom: tracksFlickable.bottom
                        anchors.bottomMargin: -16
                    }
                }
            }

            CornerSelectionShadow {
                y: tracksRepeater.count ? tracksRepeater.itemAt(timeline.currentTrack).y + rulerFlickable.height - tracksFlickable.contentY : 0
                clipN: timeline.selection.length ? tracksRepeater.itemAt(timeline.selection[0].y).clipAt(timeline.selection[0].x) : null
                opacity: clipN && clipN.x + clipN.width < tracksFlickable.contentX ? 1 : 0
            }

            CornerSelectionShadow {
                y: tracksRepeater.count ? tracksRepeater.itemAt(timeline.currentTrack).y + rulerFlickable.height - tracksFlickable.contentY : 0
                clipN: timeline.selection.length ? tracksRepeater.itemAt(timeline.selection[timeline.selection.length - 1].y).clipAt(timeline.selection[timeline.selection.length - 1].x) : null
                opacity: clipN && clipN.x > tracksFlickable.contentX + tracksFlickable.width ? 1 : 0
                anchors.right: parent.right
                mirrorGradient: true
            }

            Rectangle {
                id: loopIndicator

                visible: trackHeaderRepeater.count > 0 && timeline.loopStart != timeline.loopEnd
                color: activePalette.highlight
                opacity: 0.25
                width: (timeline.loopEnd - timeline.loopStart) * multitrack.scaleFactor
                height: rulerFlickable.height - 10
                x: timeline.loopStart * multitrack.scaleFactor - tracksFlickable.contentX
                y: ruler.y + 10
            }

            Rectangle {
                id: cursor

                visible: timeline.position > -1
                color: accentColor
                width: root.snapToDevicePixel(2)
                height: root.height - horizontalScrollBar.height
                x: root.snapToDevicePixel(timeline.position * multitrack.scaleFactor - tracksFlickable.contentX) - root.snapToDevicePixel(1)
                y: 0

                Rectangle {
                    width: root.snapToDevicePixel(0.5)
                    height: parent.height
                    color: "black"
                    x: parent.width
                }
            }

            Shotcut.TimelinePlayhead {
                id: playhead

                visible: timeline.position > -1
                x: root.snapToDevicePixel(timeline.position * multitrack.scaleFactor - tracksFlickable.contentX) - width / 2
                y: 0
                width: 12
                height: 16
            }
        }
    }

    Rectangle {
        id: dropTarget

        height: multitrack.trackHeight
        opacity: 0.5
        visible: false

        Text {
            anchors.fill: parent
            anchors.leftMargin: 100
            text: settings.timelineRipple ? qsTr('Insert') : qsTr('Overwrite')
            style: Text.Outline
            styleColor: 'white'
            font.pixelSize: Math.min(Math.max(parent.height * 0.8, 15), 30)
            verticalAlignment: Text.AlignVCenter
        }
    }

    Rectangle {
        id: bubbleHelp

        property alias text: bubbleHelpLabel.text

        function show(text) {
            let point = application.mousePos;
            point = parent.mapFromGlobal(point.x, point.y);
            bubbleHelp.x = point.x + 20;
            bubbleHelp.y = Math.max(point.y - 20, 0);
            bubbleHelp.text = text;
            if (bubbleHelp.state !== 'visible')
                bubbleHelp.state = 'visible';
        }

        function hide() {
            bubbleHelp.state = 'invisible';
            bubbleHelp.opacity = 0;
        }

        color: application.toolTipBaseColor
        width: bubbleHelpLabel.width + 8
        height: bubbleHelpLabel.height + 8
        radius: 4
        state: 'invisible'
        states: [
            State {
                name: 'invisible'

                PropertyChanges {
                    target: bubbleHelp
                    opacity: 0
                }
            },
            State {
                name: 'visible'

                PropertyChanges {
                    target: bubbleHelp
                    opacity: 1
                }
            }
        ]
        transitions: [
            Transition {
                from: 'invisible'
                to: 'visible'

                OpacityAnimator {
                    target: bubbleHelp
                    duration: 200
                    easing.type: Easing.InOutQuad
                }
            },
            Transition {
                from: 'visible'
                to: 'invisible'

                OpacityAnimator {
                    target: bubbleHelp
                    duration: 200
                    easing.type: Easing.InOutQuad
                }
            }
        ]

        Label {
            id: bubbleHelpLabel

            textFormat: Text.RichText
            color: application.toolTipTextColor
            anchors.centerIn: parent
        }
    }

    DelegateModel {
        id: trackDelegateModel

        model: multitrack

        Track {

            // Only allow one blank to be selected
            // select one
            //  Clear previous blank selection
            model: multitrack
            rootIndex: trackDelegateModel.modelIndex(index)
            height: Logic.trackHeight(audio, audio ? isTopAudio : isBottomVideo)
            isAudio: audio
            isMute: mute
            isCurrentTrack: timeline.currentTrack === index
            timeScale: multitrack.scaleFactor
            onClipClicked: (clip, track, mouse) => {
                let trackIndex = track.DelegateModel.itemsIndex;
                let clipIndex = clip.DelegateModel.itemsIndex;
                timeline.currentTrack = trackIndex;
                if (timeline.selection.length === 1) {
                    let clip2 = tracksRepeater.itemAt(timeline.selection[0].y).clipAt(timeline.selection[0].x);
                    if (clip2 === null || clip2.isBlank)
                        timeline.selection = [];
                }
                if (tracksRepeater.itemAt(trackIndex).clipAt(clipIndex).isBlank)
                    timeline.selection = [Qt.point(clipIndex, trackIndex)];
                else if (mouse && mouse.modifiers & Qt.ControlModifier && mouse.modifiers & Qt.AltModifier)
                    timeline.selection = Logic.toggleSelection(trackIndex, clipIndex, false);
                else if (mouse && mouse.modifiers & Qt.ControlModifier)
                    timeline.selection = Logic.toggleSelection(trackIndex, clipIndex, true);
                else if (mouse && mouse.modifiers & Qt.ShiftModifier)
                    timeline.selection = Logic.selectRange(trackIndex, clipIndex);
                else if (mouse && mouse.modifiers & Qt.AltModifier && !Logic.selectionContains(trackIndex, clipIndex))
                    timeline.selection = [Qt.point(clipIndex, trackIndex)];
                else if (!Logic.selectionContains(trackIndex, clipIndex))
                    timeline.selection = timeline.getGroupForClip(trackIndex, clipIndex);
                root.clipClicked();
            }
            onClipRightClicked: root.clipRightClicked()
            onClipDragged: (clip, x, y) => {
                // This provides continuous scrolling at the left/right edges.
                if (x > tracksFlickable.contentX + tracksFlickable.width - 50) {
                    scrollTimer.item = clip;
                    scrollTimer.backwards = false;
                    scrollTimer.start();
                } else if (x < 50) {
                    tracksFlickable.contentX = 0;
                    scrollTimer.stop();
                } else if (x < tracksFlickable.contentX + 50) {
                    scrollTimer.item = clip;
                    scrollTimer.backwards = true;
                    scrollTimer.start();
                } else {
                    scrollTimer.stop();
                }
                dragDelta = Qt.point(clip.x - clip.originalX, clip.trackIndex - clip.originalTrackIndex);
                selectionContainer.visible = true;
            }
            onClipDropped: {
                scrollTimer.running = false;
                bubbleHelp.hide();
                selectionContainer.visible = false;
            }
            onClipDraggedToTrack: (clip, direction) => {
                let i = clip.trackIndex + direction;
                let track = trackAt(i);
                clip.reparent(track);
                clip.trackIndex = track.DelegateModel.itemsIndex;
            }
            onCheckSnap: clip => {
                for (let i = 0; i < tracksRepeater.count; i++)
                    tracksRepeater.itemAt(i).snapClip(clip);
            }

            Item {
                // Empty track: a dashed drop area with a hint (plan.md 3.3).
                visible: root.grafito && parent.isEmpty
                x: tracksFlickable.contentX + 8
                y: 3
                width: Math.max(0, tracksFlickable.width - 16)
                height: Math.max(0, parent.height - 6)

                Canvas {
                    anchors.fill: parent
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onPaint: {
                        const ctx = getContext('2d');
                        ctx.reset();
                        ctx.strokeStyle = root.dropZoneColor;
                        ctx.lineWidth = 1;
                        ctx.setLineDash([4, 3]);
                        ctx.beginPath();
                        ctx.roundedRect(0.5, 0.5, width - 1, height - 1, 6, 6);
                        ctx.stroke();
                    }
                }

                Label {
                    anchors.centerIn: parent
                    visible: parent.height >= 18
                    text: isAudio ? qsTr('Drag audio here') : qsTr('Drag video here')
                    color: root.disabledTextColor
                    font.pixelSize: 11
                }
            }

            Image {
                anchors.fill: parent
                source: "qrc:///icons/light/16x16/track-locked.png"
                fillMode: Image.Tile
                opacity: parent.isLocked
                visible: opacity

                MouseArea {
                    anchors.fill: parent
                    onPressed: {
                        mouse.accepted = true;
                        trackHeaderRepeater.itemAt(index).pulseLockButton();
                    }
                }

                Behavior on opacity {
                    NumberAnimation {}
                }
            }
        }
    }

    Connections {
        function onPositionChanged() {
            if (!stopScrolling && settings.timelineScrolling !== Shotcut.Settings.NoScrolling) {
                let smooth = settings.timelineScrolling === Shotcut.Settings.SmoothScrolling || scrubMouseArea.containsPress || scrubMouseArea.skim;
                Logic.scrollIfNeeded(settings.timelineScrolling === Shotcut.Settings.CenterPlayhead, smooth);
            }
        }

        function onDragging(pos, duration) {
            Logic.dragging(pos, duration);
        }

        function onDropped() {
            Logic.dropped();
        }

        function onDropAccepted(xml) {
            Logic.acceptDrop(xml);
        }

        function onSelectionChanged() {
            cornerstone.selected = timeline.isMultitrackSelected();
            let selectedTrack = timeline.selectedTrack();
            for (let i = 0; i < trackHeaderRepeater.count; i++)
                trackHeaderRepeater.itemAt(i).selected = (i === selectedTrack);
        }

        function onZoomIn() {
            adjustZoom(0.0625);
        }

        function onZoomOut() {
            adjustZoom(-0.0625);
        }

        function onZoomToFit() {
            scrollZoomTimer.stop();
            tracksFlickable.contentX = 0;
            zoomToFitTimer.startZoomFit();
        }

        function onSetZoom(value) {
            setZoom(value);
        }

        function onWarnTrackLocked(trackIndex) {
            pulseLockButtonOnTrack(trackIndex);
        }

        function onMultitrackSelected() {
            selectMultitrack();
        }

        function onRefreshWaveforms() {
            if (!settings.timelineShowWaveforms) {
                for (let i = 0; i < tracksRepeater.count; i++)
                    tracksRepeater.itemAt(i).redrawWaveforms();
            } else {
                for (let i = 0; i < tracksRepeater.count; i++)
                    tracksRepeater.itemAt(i).remakeWaveforms(false);
            }
        }

        function onUpdateThumbnails(trackIndex, clipIndex) {
            if (trackIndex >= 0 && trackIndex < tracksRepeater.count)
                tracksRepeater.itemAt(trackIndex).updateThumbnails(clipIndex);
        }

        function onCurrentTrackChanged() {
            if (timeline.currentTrack >= 0) {
                // Put the positions in order to find the current track position
                var posArray = Array();
                for (let i = 0; i < tracksRepeater.count; i++) {
                    posArray.push(tracksRepeater.itemAt(i).y);
                }
                posArray.sort(function (a, b) {
                    return a - b;
                });
                let trackY = posArray[timeline.currentTrack];
                let trackH = 0;
                for (let i = 0; i < tracksRepeater.count; i++) {
                    if (tracksRepeater.itemAt(i).y == trackY) {
                        trackH = tracksRepeater.itemAt(i).height;
                        break;
                    }
                }
                if (trackY < tracksFlickable.contentY) {
                    tracksFlickable.contentY = trackY;
                } else if ((trackY + trackH) > tracksFlickable.contentY + tracksFlickable.height) {
                    tracksFlickable.contentY = trackY + trackH - tracksFlickable.height;
                }
            }
        }

        target: timeline
    }

    Connections {
        function onScaleFactorChanged() {
            if (settings.timelineScrolling === Shotcut.Settings.CenterPlayhead)
                Logic.scrollIfNeeded(true);
        }

        target: multitrack
    }

    // This provides continuous scrolling at the left/right edges.
    Timer {
        id: scrollTimer

        property var item
        property bool backwards

        interval: 25
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            let delta = backwards ? -10 : 10;
            if (item)
                item.x += delta;
            tracksFlickable.contentX += delta;
            if (tracksFlickable.contentX <= 0)
                stop();
        }
    }

    Window {
        id: trackTypeDialog

        width: 400
        height: 80
        flags: Qt.Dialog
        color: activePalette.window
        modality: Qt.ApplicationModal

        GridLayout {
            columns: 4
            anchors.fill: parent
            anchors.margins: 8

            Label {
                text: qsTr('Do you want to insert an audio or video track?')
                Layout.columnSpan: 4
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                Layout.fillWidth: true
            }

            RadioButton {
                text: qsTr("Audio")
                onClicked: {
                    timeline.insertAudioTrack();
                    trackTypeDialog.close();
                }
            }

            RadioButton {
                text: qsTr("Video")
                onClicked: {
                    timeline.insertVideoTrack();
                    trackTypeDialog.close();
                }
            }

            Label {
                Layout.fillWidth: true
            }
        }
    }
}
