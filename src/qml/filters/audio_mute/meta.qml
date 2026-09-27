import QtQuick
import org.shotcut.qml

Metadata {
    type: Metadata.Filter
    objectName: 'muteVolume'
    isAudio: true
    name: qsTr("Mute")
    keywords: qsTr('silent silence volume', 'search keywords for the Mute audio filter') + ' mute'
    mlt_service: "volume"
    qml: "ui.qml"
    icon: 'qrc:///icons/dark/32x32/audio-volume-muted.png'
    isFavorite: true
    help: 'https://forum.shotcut.org/t/mute-audio-filter/12910/1'
}
