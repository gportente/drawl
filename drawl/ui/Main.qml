import QtQuick
import QtQuick.Window
import QtQuick.Shapes

Window {
    id: root

    // The window is the pill itself: it grows to the right and downwards, so
    // the top-left corner stays exactly where the user put it.
    readonly property int orbSize: 60
    readonly property int padding: 8
    readonly property int barH: orbSize + padding * 2          // 76
    readonly property int collapsedW: barH
    readonly property int buttons: 4
    readonly property int expandedW: barH + buttons * 40 + (buttons - 1) * 8 + padding
    readonly property int expandedH: barH + 30

    // A screen recording keeps the pill open too, so the stop button is in
    // reach; the pill itself never appears in the video (see app.py).
    readonly property bool busy: ctl.state === "recording" || ctl.state === "transcribing"
                                 || cap.recording
    // Several hover sources: the backing MouseArea covers the window, but when
    // the pointer is over a button that button receives the event instead.
    readonly property bool open: hover.containsMouse || orbMouse.containsMouse
                                 || copyBtn.hovered || pasteBtn.hovered
                                 || shotBtn.hovered || recBtn.hovered || busy

    // Palette
    readonly property color glass:   "#0E1014"
    readonly property color txt:     "#E6E8EC"
    readonly property color muted:   "#8A8F98"
    readonly property color accentA: "#6EE7F9"
    readonly property color accentB: "#A78BFA"
    readonly property color recA:    "#FB7185"
    readonly property color recB:    "#F43F5E"

    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
           | Qt.WindowDoesNotAcceptFocus
    color: "transparent"
    visible: true

    width: open ? expandedW : collapsedW
    height: open ? expandedH : barH
    Behavior on width  { NumberAnimation { duration: 260; easing.type: Easing.OutBack; easing.overshoot: 0.7 } }
    Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    // Hover area covering the whole window, status bar included, so moving down
    // towards the status does not collapse the pill.
    // This has to be a MouseArea rather than a HoverHandler: with these window
    // flags (Tool + WindowDoesNotAcceptFocus) the handler never receives hover
    // events, while the MouseArea does. Declared first it sits underneath
    // everything, and with NoButton it does not swallow the orb's clicks.
    MouseArea {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    // ------------------------------------------------------------------ pill
    Rectangle {
        id: pill
        width: root.width
        height: root.barH
        radius: height / 2
        color: Qt.rgba(root.glass.r, root.glass.g, root.glass.b, 0.88)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, root.open ? 0.14 : 0.08)
        Behavior on border.color { ColorAnimation { duration: 200 } }

        // Halo pulsing with the microphone level.
        // Its size is bound directly rather than driven by `scale`, so the
        // border does not thicken along with it and, more importantly, the
        // growth stays within the room available. The orb is centred in a pill
        // of height barH with `padding` on each side, so the outer diameter
        // must not exceed barH, border included.
        Rectangle {
            id: halo
            // A base gap that is always visible, plus growth with the level.
            readonly property real base: 6
            readonly property real maxGrowth: 6

            anchors.centerIn: orbButton
            width: root.orbSize
                   + (ctl.state === "recording" ? base + ctl.level * maxGrowth : 0)
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 2
            border.color: root.recB
            // Intensity follows the level too: with so little room to grow, it
            // is what actually makes the voice readable on the orb.
            opacity: ctl.state === "recording" ? 0.45 + ctl.level * 0.45 : 0
            Behavior on width   { NumberAnimation { duration: 90 } }
            Behavior on opacity { NumberAnimation { duration: 150 } }
        }

        // -------------------------------------------------------------- orb
        Rectangle {
            id: orbButton
            x: root.padding; y: root.padding
            width: root.orbSize; height: root.orbSize
            radius: width / 2
            scale: orbMouse.pressed ? 0.93 : (orbMouse.containsMouse ? 1.05 : 1.0)
            Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }

            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: ctl.state === "recording" ? root.recA : root.accentA }
                GradientStop { position: 1.0; color: ctl.state === "recording" ? root.recB : root.accentB }
            }

            // A film of glass over the gradient, so the colour is not flat
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.22) }
                    GradientStop { position: 0.6; color: Qt.rgba(1, 1, 1, 0.0) }
                }
            }

            // Microphone (hidden while transcribing)
            Icon {
                anchors.centerIn: parent
                size: 24
                color: "#0B0D12"
                opacity: ctl.state === "transcribing" ? 0 : 1
                Behavior on opacity { NumberAnimation { duration: 150 } }
                paths: [
                    "M12 3.2 m -2.6 2.6 a 2.6 2.6 0 0 1 5.2 0 l 0 5.4 a 2.6 2.6 0 0 1 -5.2 0 z",
                    "M5.6 11 a 6.4 6.4 0 0 0 12.8 0",
                    "M12 17.6 L 12 20.5"
                ]
            }

            // Spinner shown while transcribing
            Shape {
                anchors.centerIn: parent
                width: 26; height: 26
                visible: ctl.state === "transcribing"
                ShapePath {
                    strokeColor: "#0B0D12"
                    strokeWidth: 2.6
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathAngleArc {
                        centerX: 13; centerY: 13; radiusX: 10; radiusY: 10
                        startAngle: 0; sweepAngle: 280
                    }
                }
                RotationAnimator on rotation {
                    running: ctl.state === "transcribing"
                    from: 0; to: 360; duration: 900; loops: Animation.Infinite
                }
            }

            MouseArea {
                id: orbMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                property point grabCursor   // pointer on screen when pressed
                property point grabWindow   // window corner when pressed
                property bool dragging: false

                // Anchoring and release go through onPressedChanged rather than
                // onPressed/onReleased: it is a property-change handler, and
                // unlike those two signals it fires reliably for a MouseArea
                // nested this deep.
                onPressedChanged: {
                    if (pressed) {
                        grabCursor = ctl.cursorPos()
                        grabWindow = Qt.point(root.x, root.y)
                        dragging = false
                    } else if (dragging) {
                        ctl.saveOrbPosition(root.x, root.y)
                    } else {
                        ctl.toggleRecord()   // a plain click starts or stops dictation
                    }
                }

                onPositionChanged: {
                    if (!pressed)
                        return
                    // Moved directly instead of through root.startSystemMove():
                    // the system drag honours the Windows setting "show window
                    // contents while dragging", and with that switched off all
                    // you see is a dashed outline moving.
                    var c = ctl.cursorPos()
                    var dx = c.x - grabCursor.x
                    var dy = c.y - grabCursor.y
                    if (!dragging && Math.hypot(dx, dy) > 5)
                        dragging = true
                    if (dragging) {
                        // Absolute rather than incremental: moving the window is
                        // asynchronous, and summing relative deltas would leave
                        // the pill trailing behind the pointer.
                        root.x = grabWindow.x + dx
                        root.y = grabWindow.y + dy
                    }
                }
            }
        }

        // ------------------------------------------------- secondary buttons
        Row {
            id: actions
            anchors.verticalCenter: orbButton.verticalCenter
            x: orbButton.x + orbButton.width + root.padding
            spacing: 8
            opacity: root.open ? 1 : 0
            visible: opacity > 0.01
            Behavior on opacity { NumberAnimation { duration: 180 } }

            SatelliteButton {
                id: copyBtn
                dimmed: ctl.lastText.length === 0
                tip: i18n.t("tip.copy")
                paths: ["M9.5 9.5 L 17.7 9.5 L 17.7 17.7 L 9.5 17.7 Z",
                        "M6.3 14.5 L 6.3 6.3 L 14.5 6.3"]
                onActivated: ctl.copyLast()
            }

            SatelliteButton {
                id: pasteBtn
                property bool on: true
                tip: on ? i18n.t("tip.autoPasteOn") : i18n.t("tip.autoPasteOff")
                accent: on
                paths: on ? ["M7 12.5 L 10.2 15.7 L 17 9"]
                          : ["M8 8 L 16 16", "M16 8 L 8 16"]
                onActivated: on = ctl.toggleAutoPaste()
                Component.onCompleted: on = ctl.autoPasteEnabled()
            }

            SatelliteButton {
                id: shotBtn
                tip: i18n.t("tip.screenshot")
                paths: ["M4 8.5 L 4 18.5 L 20 18.5 L 20 8.5 L 16.2 8.5 L 14.7 6 L 9.3 6 L 7.8 8.5 Z",
                        "M9 13 a 3 3 0 1 0 6 0 a 3 3 0 1 0 -6 0"]
                onActivated: cap.screenshot()
            }

            SatelliteButton {
                id: recBtn
                tip: cap.recording ? i18n.t("tip.stopRecording") : i18n.t("tip.record")
                accent: cap.recording
                accentColor: root.recA
                paths: cap.recording
                       ? ["M8.5 8.5 L 15.5 8.5 L 15.5 15.5 L 8.5 15.5 Z"]
                       : ["M5 12 a 7 7 0 1 0 14 0 a 7 7 0 1 0 -14 0",
                          "M10 12 a 2 2 0 1 0 4 0 a 2 2 0 1 0 -4 0"]
                onActivated: cap.toggleRecording()
            }
        }
    }

    // --------------------------------------------------------------- status
    Rectangle {
        y: root.barH + 2
        x: 6
        width: root.width - 12
        height: 24
        radius: 12
        color: Qt.rgba(root.glass.r, root.glass.g, root.glass.b, 0.82)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.07)
        opacity: root.open ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: 180 } }

        Text {
            id: statusText
            anchors.centerIn: parent
            width: parent.width - 16
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight

            readonly property string hoveredTip:
                copyBtn.hovered ? copyBtn.tip : pasteBtn.hovered ? pasteBtn.tip
                : shotBtn.hovered ? shotBtn.tip : recBtn.hovered ? recBtn.tip : ""

            text: hoveredTip.length > 0 ? hoveredTip
                  : cap.recording ? "●  " + cap.elapsed + "   " + i18n.t("capture.recording")
                  : ctl.status
            color: ctl.state === "error" || (cap.recording && hoveredTip.length === 0)
                   ? root.recA : root.muted
            font.pixelSize: 11
            font.family: "Segoe UI"
        }
    }
}
