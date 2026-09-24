import QtQuick

// A square toolbar button for the screenshot editor.
Rectangle {
    id: btn

    property var paths: []
    property string tip: ""
    property bool checked: false
    property bool available: true
    readonly property bool hovered: mouse.containsMouse

    signal activated()

    width: 34
    height: 34
    radius: 8
    color: checked       ? Qt.rgba(0.43, 0.91, 0.98, 0.16)
         : mouse.pressed ? Qt.rgba(1, 1, 1, 0.14)
         : hovered       ? Qt.rgba(1, 1, 1, 0.08)
                         : "transparent"
    border.width: checked ? 1 : 0
    border.color: Qt.rgba(0.43, 0.91, 0.98, 0.45)
    opacity: available ? 1 : 0.35
    Behavior on color { ColorAnimation { duration: 120 } }

    Icon {
        anchors.centerIn: parent
        size: 20
        weight: 1.8
        paths: btn.paths
        color: btn.checked ? "#6EE7F9" : "#E6E8EC"
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: btn.available ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (btn.available) btn.activated()
    }
}
