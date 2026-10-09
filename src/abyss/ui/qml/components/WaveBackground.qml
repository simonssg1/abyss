import QtQuick
import QtQuick.Shapes
import theme

// Vagues superposées en bas d'écran, ondulation lente.
Item {
    id: root
    property bool running: true
    property real phase: 0
    implicitHeight: 180
    clip: true

    NumberAnimation on phase {
        from: 0; to: 2 * Math.PI
        duration: 14000
        loops: Animation.Infinite
        running: root.running && root.visible
    }

    function wave(w, h, base, amp, freq, ph) {
        var n = 24, d = "M 0 " + h + " L 0 " + (base + amp * Math.sin(ph)).toFixed(1)
        for (var i = 1; i <= n; ++i) {
            var x = w * i / n
            var y = base + amp * Math.sin(ph + freq * 2 * Math.PI * i / n) + amp * 0.35 * Math.sin(2 * ph + 3.1 * i / n)
            d += " L " + x.toFixed(1) + " " + y.toFixed(1)
        }
        return d + " L " + w + " " + h + " Z"
    }

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: root.width; y2: root.height
                GradientStop { position: 0; color: Qt.rgba(Theme.principal.r, Theme.principal.g, Theme.principal.b, 0.55) }
                GradientStop { position: 1; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.25) }
            }
            PathSvg { path: root.wave(root.width, root.height, root.height * 0.35, root.height * 0.12, 1.2, root.phase) }
        }
        ShapePath {
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: root.width; y2: 0
                GradientStop { position: 0; color: Qt.rgba(Theme.indigo.r, Theme.indigo.g, Theme.indigo.b, 0.35) }
                GradientStop { position: 1; color: Qt.rgba(Theme.principal.r, Theme.principal.g, Theme.principal.b, 0.6) }
            }
            PathSvg { path: root.wave(root.width, root.height, root.height * 0.55, root.height * 0.1, 0.9, -root.phase + 1.3) }
        }
        ShapePath {
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: root.width; y2: root.height
                GradientStop { position: 0; color: Qt.rgba(Theme.surface.r, Theme.surface.g, Theme.surface.b, 0.9) }
                GradientStop { position: 1; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.35) }
            }
            PathSvg { path: root.wave(root.width, root.height, root.height * 0.75, root.height * 0.08, 1.6, root.phase + 2.4) }
        }
    }
}
