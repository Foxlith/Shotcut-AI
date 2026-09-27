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
import QtQuick
import QtQuick.Controls
import Shotcut.Controls as Shotcut

Rectangle {
    id: rulerTop

    property real timeScale: 1
    // Labels at the shortest round interval (1, 2, 5, 10, 15, 30 s...) that keeps them at
    // least 90 px apart; at the default zoom of 60 px per second that is every 2 seconds.
    readonly property var labelSeconds: [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200]
    readonly property real intervalFrames: {
        for (let i = 0; i < labelSeconds.length; i++) {
            if (labelSeconds[i] * profile.fps * timeScale >= 90)
                return labelSeconds[i] * profile.fps;
        }
        return labelSeconds[labelSeconds.length - 1] * profile.fps;
    }
    readonly property real tickSpacing: intervalFrames * timeScale
    // Minor ticks between the labels while they stay at least 8 px apart.
    readonly property int minorTicks: tickSpacing / 10 >= 8 ? 10 : tickSpacing / 5 >= 8 ? 5 : tickSpacing / 2 >= 8 ? 2 : 1
    // Clamp to rulerTop.width (the actual timeline content width) so ticks do not render past the end of an empty/short timeline.
    readonly property real tickAreaEnd: Math.min(tracksFlickable.contentX + tracksFlickable.width + tickSpacing * 3, rulerTop.width)
    readonly property int firstTick: tickSpacing > 0 ? Math.max(0, Math.floor(tracksFlickable.contentX / tickSpacing) - 1) : 0
    readonly property int tickCount: (tickSpacing > 0 && tickAreaEnd > firstTick * tickSpacing) ? Math.ceil((tickAreaEnd - firstTick * tickSpacing) / tickSpacing) : 0
    // Grafito ruler (plan.md 3.3): 28 px on the panel color, Geist Mono labels.
    readonly property color tickColor: root.grafito ? '#3A3F4A' : activePalette.windowText
    readonly property color minorTickColor: root.grafito ? '#2A2E37' : activePalette.mid
    readonly property color labelColor: root.grafito ? '#858C98' : activePalette.windowText

    signal editMarkerRequested(int index)
    signal deleteMarkerRequested(int index)

    height: 28
    color: root.grafito ? '#15171C' : activePalette.base

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: root.dividerColor
    }

    Repeater {
        id: repeater

        model: rulerTop.tickCount

        Rectangle {
            readonly property int tickIndex: index + rulerTop.firstTick

            // right edge
            anchors.bottom: rulerTop.bottom
            height: 12
            width: 1
            color: rulerTop.tickColor
            x: tickIndex * rulerTop.tickSpacing

            Repeater {
                model: rulerTop.minorTicks - 1

                Rectangle {
                    anchors.bottom: parent.bottom
                    x: (index + 1) * rulerTop.tickSpacing / rulerTop.minorTicks
                    width: 1
                    height: (rulerTop.minorTicks === 10 && index === 4) ? 7 : 4
                    color: rulerTop.minorTickColor
                }
            }

            Label {
                anchors.left: parent.right
                anchors.leftMargin: 4
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 4
                color: rulerTop.labelColor
                font.family: 'Geist Mono'
                font.pixelSize: 10
                text: application.clockFromFrames(parent.tickIndex * rulerTop.intervalFrames + 2).substr(0, 8)
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        onExited: bubbleHelp.hide()
        property double currentPos: timeline.position * timeScale
        cursorShape: (mouseX >= currentPos - 8 && mouseX <= currentPos + 8) ? Qt.SizeHorCursor : Qt.ArrowCursor
        onPositionChanged: mouse => {
            var text = application.timeFromFrames(mouse.x / timeScale);
            bubbleHelp.show(text);
        }
    }

    Shotcut.MarkerBar {
        anchors.top: rulerTop.top
        anchors.left: parent.left
        anchors.right: parent.right
        timeScale: rulerTop.timeScale
        model: markers
        onExited: bubbleHelp.hide()
        onMouseStatusChanged: (mouseX, mouseY, text, start, end) => {
            var msg = "<center>" + text;
            if (start === end) {
                msg += "<br>" + application.timeFromFrames(start);
            } else {
                msg += "<br>" + application.timeFromFrames(start) + " - " + application.timeFromFrames(end);
                msg += "<br>" + application.timeFromFrames(end - start);
            }
            msg += "</center>";
            bubbleHelp.show(msg);
        }
        onSeekRequested: pos => timeline.position = pos

        snapper: QtObject {
            function getSnapPosition(position) {
                if (!settings.timelineSnap)
                    return position;
                var SNAP = 10;
                // Snap to clips on tracks.
                var timeline = root;
                for (var j = 0; j < timeline.trackCount; j++) {
                    var track = timeline.trackAt(j);
                    for (var i = 0; i < track.clipCount; i++) {
                        var item = track.clipAt(i);
                        if (item.isBlank)
                            continue;
                        var itemLeft = item.clipPx;
                        var itemRight = itemLeft + item.clipPxW;
                        if (position > itemLeft - SNAP && position < itemLeft + SNAP)
                            return itemLeft;
                        else if (position > itemRight - SNAP && position < itemRight + SNAP)
                            return itemRight;
                        else if (itemRight + SNAP > position)
                            continue;
                    }
                }
                // Snap around cursor/playhead.
                var cursorX = tracksFlickable.contentX + cursor.x;
                if (position > cursorX - SNAP && position < cursorX + SNAP)
                    return cursorX;
                return position;
            }
        }
    }

    Connections {
        function onTimeFormatChanged() {
            const m = repeater.model;
            repeater.model = 0;
            repeater.model = m;
        }

        target: settings
    }
}
