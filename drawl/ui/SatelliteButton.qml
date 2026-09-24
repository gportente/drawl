import QtQuick

// Small round secondary button, revealed when the pill opens.
Rectangle {
    id: btn

    property var paths: []
    property string tip: ""
    property bool dimmed: false
    property bool accent: false
    property color accentColor: "#6EE7F9"
    readonly property bool hovered: mouse.containsMouse

    signal activated()

    width: 40
    height: 40
    radius: width / 2

    color: mouse.pressed  ? Qt.rgba(1, 1, 1, 0.16)
         : hovered        ? Qt.rgba(1, 1, 1, 0.10)
                          : Qt.rgba(1, 1, 1, 0.05)
    Behavior on color { ColorAnimation { duration: 140 } }

    border.width: 1
    border.color: Qt.rgba(1, 1, 1, hovered ? 0.16 : 0.07)

    opacity: dimmed ? 0.35 : 1.0
    Behavior on opacity { NumberAnimation { duration: 160 } }

    scale: mouse.pressed ? 0.92 : (hovered ? 1.06 : 1.0)
    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }

    Icon {
        anchors.centerIn: parent
        size: 20
        paths: btn.paths
        color: btn.accent ? btn.accentColor : "#E6E8EC"
        Behavior on color { ColorAnimation { duration: 160 } }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: btn.dimmed ? Qt.ArrowCursor : Qt.PointingHandCursor
        onClicked: if (!btn.dimmed) btn.activated()
    }
}
