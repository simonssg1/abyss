import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

// Curseur simple : libellé optionnel à gauche, valeur formatée à droite (par défaut en %).
Item {
    id: root
    property string label: ""
    property alias from: slider.from
    property alias to: slider.to
    property alias stepSize: slider.stepSize
    property alias value: slider.value
    property alias pressed: slider.pressed
    property string unit: "%"
    property int decimals: 0
    property real labelWidth: 96
    // Par défaut : 0..1 affiché en %, sinon valeur + unité.
    property var formatValue: function(v) {
        return unit === "%" && slider.to <= 1 ? Math.round(v * 100) + " %"
             : v.toFixed(decimals) + (unit ? " " + unit : "")
    }
    signal moved(real value)

    implicitHeight: Theme.controlHeight
    implicitWidth: 280
    opacity: enabled ? 1 : 0.4

    RowLayout {
        anchors.fill: parent
        spacing: Theme.s3
        AbyssText {
            visible: root.label !== ""
            text: root.label
            role: "bodySmall"
            Layout.preferredWidth: root.labelWidth
        }
        Slider {
            id: slider
            Layout.fillWidth: true
            from: 0; to: 1; value: 0.5
            onMoved: root.moved(value)
            background: Rectangle {
                x: slider.leftPadding
                y: slider.topPadding + slider.availableHeight / 2 - height / 2
                width: slider.availableWidth
                height: 4
                radius: 2
                color: Theme.track
                Rectangle {
                    width: slider.visualPosition * parent.width
                    height: parent.height
                    radius: 2
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: Theme.principal }
                        GradientStop { position: 1; color: Theme.accent }
                    }
                }
            }
            handle: Rectangle {
                x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                y: slider.topPadding + slider.availableHeight / 2 - height / 2
                width: 14; height: 14; radius: 7
                color: Theme.accent
                border.width: slider.pressed ? 4 : 0
                border.color: Theme.accentSoft
                scale: slider.pressed ? 1.2 : 1
                Behavior on scale { NumberAnimation { duration: Theme.durFast; easing.type: Theme.easing } }
            }
        }
        AbyssText {
            text: root.formatValue(slider.value)
            role: "caption"
            secondary: true
            horizontalAlignment: Text.AlignRight
            Layout.preferredWidth: 56
        }
    }
}
