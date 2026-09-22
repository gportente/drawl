import QtQuick
import QtQuick.Shapes

// A vector icon drawn from SVG paths on a 24x24 grid, scaled to `size`.
// Repeater can only instantiate Items and ShapePath is not one, so four fixed
// slots bound to paths[i] do the same job while staying declarative.
Item {
    id: icon

    property int size: 24
    property color color: "#FFFFFF"
    property real weight: 1.9
    property var paths: []

    function at(i) { return i < paths.length ? paths[i] : "" }

    width: size
    height: size

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        transform: Scale { xScale: icon.size / 24; yScale: icon.size / 24 }

        ShapePath {
            strokeColor: icon.color; strokeWidth: icon.weight; fillColor: "transparent"
            capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
            PathSvg { path: icon.at(0) }
        }
        ShapePath {
            strokeColor: icon.color; strokeWidth: icon.weight; fillColor: "transparent"
            capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
            PathSvg { path: icon.at(1) }
        }
        ShapePath {
            strokeColor: icon.color; strokeWidth: icon.weight; fillColor: "transparent"
            capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
            PathSvg { path: icon.at(2) }
        }
        ShapePath {
            strokeColor: icon.color; strokeWidth: icon.weight; fillColor: "transparent"
            capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
            PathSvg { path: icon.at(3) }
        }
    }
}
