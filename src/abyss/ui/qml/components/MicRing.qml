import QtQuick
import QtQuick.Shapes
import QtQuick.Effects
import theme

// Grand anneau lumineux autour du micro. Actif : arc dégradé + halo qui pulse avec `level`.
// Au repos : anneau sombre et immobile.
Item {
    id: root
    property bool active: false
    property real level: 0          // niveau de sortie 0..1
    property int segments: 36
    property real startAngle: 120
    property real sweep: 300
    signal clicked()

    implicitWidth: 220
    implicitHeight: 220

    readonly property real smoothLevel: active ? Math.min(1, level) : 0
    property real shown: smoothLevel
    Behavior on shown { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }

    function mix(a, b, t) { return Qt.rgba(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t, 1) }

    // Halo doux (fonctionne aussi en rendu logiciel) ; MultiEffect y ajoute une lueur sur GPU.
    Shape {
        anchors.centerIn: parent
        width: parent.width * 1.25
        height: width
        visible: root.active
        opacity: 0.35 + 0.65 * root.shown
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: root.width * 0.625; centerY: centerX; centerRadius: root.width * 0.625
                focalX: centerX; focalY: centerY
                GradientStop { position: 0.5; color: Theme.accentSoft }
                GradientStop { position: 0.68; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.22) }
                GradientStop { position: 1.0; color: "transparent" }
            }
            PathAngleArc {
                centerX: root.width * 0.625; centerY: centerX
                radiusX: root.width * 0.625; radiusY: radiusX
                startAngle: 0; sweepAngle: 360
            }
        }
    }

    Item {
        id: ringLayer
        anchors.fill: parent
        scale: 1 + 0.05 * root.shown

        // Piste
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: Theme.track
                strokeWidth: 10
                fillColor: "transparent"
                PathAngleArc {
                    centerX: ringLayer.width / 2; centerY: ringLayer.height / 2
                    radiusX: ringLayer.width / 2 - 14; radiusY: radiusX
                    startAngle: 0; sweepAngle: 360
                }
            }
        }
        // Arc dégradé, découpé en segments
        Repeater {
            model: root.active ? root.segments : 0
            Shape {
                required property int index
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeColor: root.mix(Theme.principal, Theme.accent, Math.min(1, index / (root.segments * 0.6)))
                    strokeWidth: 10
                    fillColor: "transparent"
                    capStyle: (index === 0 || index === root.segments - 1) ? ShapePath.RoundCap : ShapePath.FlatCap
                    PathAngleArc {
                        centerX: ringLayer.width / 2; centerY: ringLayer.height / 2
                        radiusX: ringLayer.width / 2 - 14; radiusY: radiusX
                        startAngle: root.startAngle + index * root.sweep / root.segments
                        sweepAngle: root.sweep / root.segments + (index === root.segments - 1 ? 0 : 0.6)
                    }
                }
            }
        }
    }

    MultiEffect {
        source: ringLayer
        anchors.fill: ringLayer
        visible: root.active
        shadowEnabled: root.active
        shadowColor: Theme.accent
        shadowBlur: 0.6 + 0.4 * root.shown
        shadowOpacity: 0.35 + 0.65 * root.shown
        shadowHorizontalOffset: 0
        shadowVerticalOffset: 0
        blurMax: 48
        autoPaddingEnabled: true
    }

    // Disque intérieur
    Rectangle {
        anchors.centerIn: parent
        width: parent.width * 0.66
        height: width
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.surface }
            GradientStop { position: 1; color: Theme.bgDeep }
        }
        opacity: root.active ? 1 : 0.7
        Behavior on opacity { NumberAnimation { duration: Theme.durNormal } }
        Image {
            anchors.centerIn: parent
            width: parent.width * 0.5
            height: width
            source: "image://icon/mic-capsule/E2E8FF"
            sourceSize: Qt.size(width * 3, height * 3)
            mipmap: true
            opacity: root.active ? 1 : 0.55
            Behavior on opacity { NumberAnimation { duration: Theme.durNormal } }
        }
    }

    MouseArea {
        anchors.centerIn: parent
        width: parent.width * 0.85
        height: width
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
