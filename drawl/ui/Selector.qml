import QtQuick
import QtQuick.Window

// Covers one screen with a still of itself. Hovering highlights the window
// under the pointer, dragging draws a free area; a click takes what is
// highlighted (the whole screen when over the desktop). Esc or a right click
// cancels, Enter takes the whole screen.
Window {
    id: sel

    property url source
    property var windows: []            // [{x, y, width, height}], topmost first
    property string mode: "shot"        // shot | record
    property real pixelScale: 1
    property string hint: ""
    property point startCursor: Qt.point(-1, -1)

    signal chosen(real x, real y, real w, real h)
    signal cancelled()

    readonly property color accent: mode === "record" ? "#F43F5E" : "#6EE7F9"
    readonly property rect whole: Qt.rect(0, 0, width, height)

    property bool dragging: false
    property point anchor
    property rect dragRect
    property rect hovered: whole
    readonly property rect area: dragging ? dragRect : hovered

    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "black"

    function windowAt(x, y) {
        for (var i = 0; i < windows.length; i++) {
            var w = windows[i]
            if (x >= w.x && y >= w.y && x < w.x + w.width && y < w.y + w.height)
                return Qt.rect(w.x, w.y, w.width, w.height)
        }
        return whole
    }

    Component.onCompleted: if (startCursor.x >= 0) hovered = windowAt(startCursor.x, startCursor.y)

    Image {
        anchors.fill: parent
        source: sel.source
        cache: false
        smooth: false
    }

    // Shade everything outside the area, in four pieces around it.
    Item {
        anchors.fill: parent
        readonly property color shade: Qt.rgba(0.02, 0.03, 0.05, 0.55)
        Rectangle { color: parent.shade; x: 0; y: 0; width: parent.width; height: sel.area.y }
        Rectangle { color: parent.shade; x: 0; y: sel.area.y + sel.area.height
                    width: parent.width; height: parent.height - y }
        Rectangle { color: parent.shade; x: 0; y: sel.area.y
                    width: sel.area.x; height: sel.area.height }
        Rectangle { color: parent.shade; x: sel.area.x + sel.area.width; y: sel.area.y
                    width: parent.width - x; height: sel.area.height }
    }

    Rectangle {
        x: sel.area.x; y: sel.area.y
        width: sel.area.width; height: sel.area.height
        color: "transparent"
        border.width: 2
        border.color: sel.accent
    }

    // Size in real pixels, which is what the file will have.
    Rectangle {
        readonly property bool below: sel.area.y < height + 8
        x: Math.min(sel.area.x, sel.width - width - 4)
        y: below ? sel.area.y + 6 : sel.area.y - height - 6
        width: sizeText.implicitWidth + 16
        height: 22
        radius: 11
        color: Qt.rgba(0.055, 0.063, 0.078, 0.9)
        Text {
            id: sizeText
            anchors.centerIn: parent
            text: Math.round(sel.area.width * sel.pixelScale) + " × "
                  + Math.round(sel.area.height * sel.pixelScale)
            color: "#E6E8EC"
            font.pixelSize: 11
            font.family: "Segoe UI"
        }
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 24
        width: hintText.implicitWidth + 32
        height: 36
        radius: 18
        color: Qt.rgba(0.055, 0.063, 0.078, 0.92)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.1)
        // Out of the way when the pointer comes close.
        opacity: mouse.mouseY < 90 && Math.abs(mouse.mouseX - sel.width / 2) < width / 2 + 40 ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: 150 } }
        Row {
            anchors.centerIn: parent
            spacing: 10
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 8; height: 8; radius: 4
                color: sel.accent
            }
            Text {
                id: hintText
                text: sel.hint
                color: "#E6E8EC"
                font.pixelSize: 12
                font.family: "Segoe UI"
            }
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.CrossCursor

        onPressed: function(e) {
            if (e.button === Qt.RightButton) {
                sel.cancelled()
                return
            }
            sel.anchor = Qt.point(e.x, e.y)
        }
        onPositionChanged: function(e) {
            if (pressed && (e.buttons & Qt.LeftButton)) {
                if (!sel.dragging && Math.hypot(e.x - sel.anchor.x, e.y - sel.anchor.y) > 4)
                    sel.dragging = true
                if (sel.dragging)
                    sel.dragRect = Qt.rect(Math.min(sel.anchor.x, e.x), Math.min(sel.anchor.y, e.y),
                                           Math.abs(e.x - sel.anchor.x), Math.abs(e.y - sel.anchor.y))
            } else {
                sel.hovered = sel.windowAt(e.x, e.y)
            }
        }
        onReleased: function(e) {
            if (e.button !== Qt.LeftButton)
                return
            // Copied out first: a rect read from a property is a live reference,
            // and clearing `dragging` would turn it into the hovered window.
            var x = sel.area.x, y = sel.area.y, w = sel.area.width, h = sel.area.height
            sel.dragging = false
            if (w >= 2 && h >= 2)
                sel.chosen(x, y, w, h)
        }
    }

    Item {
        focus: true
        Keys.onEscapePressed: sel.cancelled()
        Keys.onReturnPressed: sel.chosen(0, 0, sel.width, sel.height)
        Keys.onEnterPressed: sel.chosen(0, 0, sel.width, sel.height)
    }
}
