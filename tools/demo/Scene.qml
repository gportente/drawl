import QtQuick
import QtQuick.Window
import QtQuick.Shapes

// Backdrop for the demo: a document the dictated text appears in.
// drawl's real pill is laid over this window rather than drawn here, so the
// recording shows the actual interface and not a reproduction of it.
Window {
    id: scene

    property string text: ""
    property bool flash: false

    width: 900
    height: 520
    // Always on top, or other windows would cover the capture region.
    // The pill is created afterwards and still sits above this.
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
    visible: true
    color: "#07080B"

    // Safety marker: three pixels in a colour found nowhere else in the scene.
    // Whoever captures the screen checks for it before keeping a frame, so
    // whatever lies under this window cannot end up in the recording if the
    // scene has not been drawn yet. It is cropped away afterwards.
    Rectangle {
        x: 0; y: 0; width: 3; height: 3
        color: "#FF00FF"
        z: 999
    }

    // Backdrop with a soft glow in the top-left corner.
    // The glow is a radial gradient drawn with Shape: a Rectangle with a linear
    // gradient would leave the hard edge of the circle visible.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0F1219" }
            GradientStop { position: 1.0; color: "#07080B" }
        }

        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "transparent"
                fillGradient: RadialGradient {
                    centerX: 140; centerY: 40; centerRadius: 520
                    focalX: 140; focalY: 40
                    GradientStop { position: 0.0;  color: Qt.rgba(0.43, 0.91, 0.98, 0.22) }
                    GradientStop { position: 0.45; color: Qt.rgba(0.65, 0.55, 0.98, 0.07) }
                    GradientStop { position: 1.0;  color: "transparent" }
                }
                PathRectangle { width: scene.width; height: scene.height }
            }
        }
    }

    // The "window" being typed into
    Rectangle {
        id: document
        anchors.centerIn: parent
        width: 760
        height: 400
        radius: 14
        color: "#12151C"
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.09)

        // Title bar
        Item {
            id: titleBar
            width: parent.width; height: 42
            Row {
                x: 18; anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Repeater {
                    model: ["#FF5F57", "#FEBC2E", "#28C840"]
                    Rectangle { width: 11; height: 11; radius: 6; color: modelData; opacity: 0.85 }
                }
            }
            Text {
                anchors.centerIn: parent
                text: "notes.txt"
                color: "#6B7280"
                font.pixelSize: 12
                font.family: "Segoe UI"
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width; height: 1
                color: Qt.rgba(1, 1, 1, 0.06)
            }
        }

        // Text area
        Item {
            anchors.top: titleBar.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 26

            Text {
                id: body
                width: parent.width
                text: scene.text
                color: "#E6E8EC"
                font.pixelSize: 19
                font.family: "Segoe UI"
                lineHeight: 1.45
                wrapMode: Text.WordWrap

                // A brief flash as the text is pasted in
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -6
                    radius: 6
                    color: "#6EE7F9"
                    opacity: scene.flash ? 0.16 : 0
                    Behavior on opacity { NumberAnimation { duration: 260 } }
                }
            }

            // Blinking caret, while the text is still empty
            Rectangle {
                x: body.text.length === 0 ? 0 : body.contentWidth + 3
                y: body.text.length === 0 ? 3 : body.contentHeight - 26
                width: 2; height: 22
                color: "#6EE7F9"
                SequentialAnimation on opacity {
                    running: true; loops: Animation.Infinite
                    NumberAnimation { to: 0.15; duration: 520 }
                    NumberAnimation { to: 1.0; duration: 520 }
                }
            }
        }
    }
}
