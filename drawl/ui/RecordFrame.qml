import QtQuick
import QtQuick.Window

// A red border around the area being recorded. It lets clicks through and is
// excluded from capture, so it never shows up in the video.
Window {
    property int margin: 3

    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
           | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
    color: "transparent"

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.width: 2
        border.color: "#F43F5E"
        radius: 2
    }
}
