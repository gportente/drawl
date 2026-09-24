import QtQuick
import QtQuick.Window
import Drawl

// The screenshot editor: a toolbar over the picture, a status line under it.
// Everything about drawing happens in AnnotationCanvas; this file only lays
// out the controls and forwards their clicks.
Window {
    id: editor

    property string tip: ""          // the hovered control's description
    property string toast: ""        // the outcome of the last action
    property string savedPath: ""

    readonly property color glass: "#0E1014"
    readonly property color txt: "#E6E8EC"
    readonly property color muted: "#8A8F98"

    width: 1100
    height: 720
    minimumWidth: 640
    minimumHeight: 360
    color: "#08090C"
    visible: false

    readonly property var tools: [
        { id: "select",   key: "V", icon: ["M6.5 3.5 L 6.5 18 L 10.2 14.4 L 12.9 20.2 L 15.1 19.2 L 12.5 13.5 L 17.6 13.5 Z"] },
        { id: "arrow",    key: "A", icon: ["M5 19 L 18 6", "M10.5 6 L 18 6 L 18 13.5"] },
        { id: "line",     key: "L", icon: ["M5 19 L 19 5"] },
        { id: "rect",     key: "R", icon: ["M4.5 6.5 L 19.5 6.5 L 19.5 17.5 L 4.5 17.5 Z"] },
        { id: "ellipse",  key: "E", icon: ["M4 12 a 8 6.2 0 1 0 16 0 a 8 6.2 0 1 0 -16 0"] },
        { id: "pen",      key: "P", icon: ["M4.5 19.5 L 5.6 15.4 L 15.6 5.4 L 18.6 8.4 L 8.6 18.4 Z", "M13.6 7.4 L 16.6 10.4"] },
        { id: "marker",   key: "H", icon: ["M9.2 14.8 L 16.6 7.4 L 19.6 10.4 L 12.2 17.8 Z", "M9.2 14.8 L 6.5 19.5 L 10 19.5 L 12.2 17.8", "M14 20 L 20 20"] },
        { id: "text",     key: "T", icon: ["M5.5 6 L 18.5 6", "M12 6 L 12 19", "M9.5 19 L 14.5 19"] },
        { id: "step",     key: "N", icon: ["M4 12 a 8 8 0 1 0 16 0 a 8 8 0 1 0 -16 0", "M10.6 9.4 L 12.6 8 L 12.6 16"] },
        { id: "pixelate", key: "B", icon: ["M4.5 4.5 L 19.5 4.5 L 19.5 19.5 L 4.5 19.5 Z", "M4.5 12 L 19.5 12", "M12 4.5 L 12 19.5", "M8.2 4.5 L 8.2 12 M 15.8 12 L 15.8 19.5"] },
        { id: "crop",     key: "C", icon: ["M7 3 L 7 17 L 21 17", "M3 7 L 17 7 L 17 21"] }
    ]
    readonly property var colors: ["#F43F5E", "#F97316", "#FACC15", "#22C55E",
                                   "#3B82F6", "#A78BFA", "#FFFFFF", "#111318"]

    function say(result) {
        if (!result || !result.message)
            return
        toast = result.message
        savedPath = result.path || ""
        toastTimer.restart()
    }
    function hover(text, on) {
        if (on) tip = text
        else if (tip === text) tip = ""
    }

    Timer { id: toastTimer; interval: 5000; onTriggered: { editor.toast = ""; editor.savedPath = "" } }

    Shortcut { sequences: [StandardKey.Copy]; onActivated: editor.say(cap.copy(canvas)) }
    Shortcut { sequences: [StandardKey.Save]; onActivated: editor.say(cap.save(canvas)) }
    Shortcut { sequence: "Ctrl+Shift+S"; onActivated: editor.say(cap.saveAs(canvas)) }
    Shortcut { sequences: [StandardKey.Close]; onActivated: editor.close() }

    // ---------------------------------------------------------------- toolbar
    Rectangle {
        id: toolbar
        width: parent.width
        height: bar.implicitHeight + 16
        color: editor.glass
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1
                    color: Qt.rgba(1, 1, 1, 0.07) }

        Flow {
            id: bar
            x: 8; y: 8
            width: parent.width - 16
            spacing: 2

            Repeater {
                model: editor.tools
                EditorButton {
                    paths: modelData.icon
                    tip: i18n.t("tool." + modelData.id) + "  ·  " + modelData.key
                    checked: canvas.tool === modelData.id
                    onActivated: { canvas.tool = modelData.id; canvas.forceActiveFocus() }
                    onHoveredChanged: editor.hover(tip, hovered)
                }
            }

            Separator {}

            Repeater {
                model: editor.colors
                Rectangle {
                    id: swatch
                    readonly property bool current: canvas.color.toUpperCase() === modelData.toUpperCase()
                    readonly property string tip: i18n.t("editor.color")
                    width: 30; height: 34
                    color: "transparent"
                    Rectangle {
                        anchors.centerIn: parent
                        width: 26; height: 26; radius: 13
                        color: "transparent"
                        border.width: 2
                        border.color: swatch.current ? "#E6E8EC" : "transparent"
                    }
                    Rectangle {
                        anchors.centerIn: parent
                        width: swatchMouse.containsMouse ? 20 : 18
                        height: width; radius: width / 2
                        color: modelData
                        border.width: 1
                        border.color: Qt.rgba(1, 1, 1, 0.25)
                        Behavior on width { NumberAnimation { duration: 100 } }
                    }
                    MouseArea {
                        id: swatchMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { canvas.color = modelData; canvas.forceActiveFocus() }
                        onContainsMouseChanged: editor.hover(swatch.tip, containsMouse)
                    }
                }
            }

            Separator {}

            Repeater {
                model: 3
                Rectangle {
                    id: sizeBtn
                    readonly property string tip: i18n.t("editor.size" + (index + 1)) + "  ·  " + (index + 1)
                    width: 30; height: 34; radius: 8
                    color: canvas.size === index ? Qt.rgba(0.43, 0.91, 0.98, 0.16)
                         : sizeMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
                    Rectangle {
                        anchors.centerIn: parent
                        width: [5, 9, 14][index]; height: width; radius: width / 2
                        color: canvas.size === index ? "#6EE7F9" : "#E6E8EC"
                    }
                    MouseArea {
                        id: sizeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { canvas.size = index; canvas.forceActiveFocus() }
                        onContainsMouseChanged: editor.hover(sizeBtn.tip, containsMouse)
                    }
                }
            }

            EditorButton {
                tip: i18n.t("editor.fill")
                checked: canvas.fill
                paths: ["M4.5 4.5 L 19.5 4.5 L 19.5 19.5 L 4.5 19.5 Z",
                        "M4.5 12 L 12 4.5", "M4.5 19.5 L 19.5 4.5", "M12 19.5 L 19.5 12"]
                onActivated: { canvas.fill = !canvas.fill; canvas.forceActiveFocus() }
                onHoveredChanged: editor.hover(tip, hovered)
            }

            Separator {}

            EditorButton {
                tip: i18n.t("editor.undo") + "  ·  Ctrl+Z"
                available: canvas.canUndo
                paths: ["M9 6.5 L 5 10.5 L 9 14.5", "M5 10.5 L 14.5 10.5 a 4.5 4.5 0 0 1 0 9 L 11 19.5"]
                onActivated: canvas.undo()
                onHoveredChanged: editor.hover(tip, hovered)
            }
            EditorButton {
                tip: i18n.t("editor.redo") + "  ·  Ctrl+Y"
                available: canvas.canRedo
                paths: ["M15 6.5 L 19 10.5 L 15 14.5", "M19 10.5 L 9.5 10.5 a 4.5 4.5 0 0 0 0 9 L 13 19.5"]
                onActivated: canvas.redo()
                onHoveredChanged: editor.hover(tip, hovered)
            }
            EditorButton {
                tip: i18n.t("editor.delete") + "  ·  Del"
                available: canvas.hasSelection
                paths: ["M4.5 7 L 19.5 7", "M9.5 7 L 9.5 4.5 L 14.5 4.5 L 14.5 7",
                        "M6.5 7 L 7.5 19.5 L 16.5 19.5 L 17.5 7"]
                onActivated: canvas.deleteSelection()
                onHoveredChanged: editor.hover(tip, hovered)
            }

            Separator {}

            EditorButton {
                tip: i18n.t("editor.copy") + "  ·  Ctrl+C"
                paths: ["M9.5 9.5 L 17.7 9.5 L 17.7 17.7 L 9.5 17.7 Z",
                        "M6.3 14.5 L 6.3 6.3 L 14.5 6.3"]
                onActivated: editor.say(cap.copy(canvas))
                onHoveredChanged: editor.hover(tip, hovered)
            }
            EditorButton {
                tip: i18n.t("editor.save") + "  ·  Ctrl+S"
                paths: ["M12 4 L 12 15", "M7.5 10.5 L 12 15 L 16.5 10.5", "M5 19.5 L 19 19.5"]
                onActivated: editor.say(cap.save(canvas))
                onHoveredChanged: editor.hover(tip, hovered)
            }
            EditorButton {
                tip: i18n.t("editor.saveAs") + "  ·  Ctrl+Shift+S"
                paths: ["M3.5 7 L 3.5 18.5 L 20.5 18.5 L 20.5 8.8 L 11.8 8.8 L 9.8 6 L 3.5 6 Z"]
                onActivated: editor.say(cap.saveAs(canvas))
                onHoveredChanged: editor.hover(tip, hovered)
            }
        }
    }

    component Separator: Rectangle {
        width: 13; height: 34
        color: "transparent"
        Rectangle { anchors.centerIn: parent; width: 1; height: 20; color: Qt.rgba(1, 1, 1, 0.1) }
    }

    // ------------------------------------------------------------------ picture
    Item {
        id: area
        anchors.top: toolbar.bottom
        anchors.bottom: statusBar.top
        width: parent.width

        // Never enlarged beyond 100 %: a blown-up screenshot only looks blurry.
        readonly property real fit: canvas.naturalWidth > 0
            ? Math.min(1, (width - 32) / canvas.naturalWidth, (height - 32) / canvas.naturalHeight)
            : 1

        Rectangle {
            anchors.fill: canvas
            anchors.margins: -1
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.12)
        }

        AnnotationCanvas {
            id: canvas
            objectName: "canvas"
            anchors.centerIn: parent
            width: naturalWidth * area.fit
            height: naturalHeight * area.fit
            focus: true
        }
    }

    // ------------------------------------------------------------------- status
    Rectangle {
        id: statusBar
        anchors.bottom: parent.bottom
        width: parent.width
        height: 28
        color: editor.glass
        Rectangle { width: parent.width; height: 1; color: Qt.rgba(1, 1, 1, 0.07) }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: sizeLabel.left
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideMiddle
            text: editor.tip || editor.toast || i18n.t("editor.hint")
            color: editor.toast && !editor.tip ? editor.txt : editor.muted
            font.pixelSize: 11
            font.family: "Segoe UI"
            font.underline: revealMouse.containsMouse && editor.savedPath !== ""
            MouseArea {
                id: revealMouse
                anchors.fill: parent
                hoverEnabled: true
                enabled: editor.savedPath !== "" && !editor.tip
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: cap.reveal(editor.savedPath)
            }
        }

        Text {
            id: sizeLabel
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: canvas.pixelWidth + " × " + canvas.pixelHeight + "   " + Math.round(area.fit * 100) + " %"
            color: editor.muted
            font.pixelSize: 11
            font.family: "Segoe UI"
        }
    }
}
