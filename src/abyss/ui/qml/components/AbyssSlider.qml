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
    property real labelWidth: Theme.formLabelWidth
    property real valueWidth: Theme.formValueWidth
    // Par défaut : 0..1 affiché en %, sinon valeur + unité.
    property var formatValue: function(v) {
        return unit === "%" && slider.to <= 1 ? Math.round(v * 100) + " %"
             : v.toFixed(decimals) + (unit ? " " + unit : "")
    }
    signal moved(real value)

    // Étroit : libellé et valeur au-dessus, piste pleine largeur.
    readonly property bool stacked: label !== "" && width < labelWidth + valueWidth + 200
    implicitHeight: stacked ? grid.implicitHeight : Theme.controlHeight
    implicitWidth: 280
    opacity: enabled ? 1 : 0.4

    GridLayout {
        id: grid
        anchors.fill: parent
        columns: root.stacked ? 2 : 3
        columnSpacing: Theme.s3
        rowSpacing: 0
        AbyssText {
            visible: root.label !== ""
            text: root.label
            role: "bodySmall"
            Layout.row: 0; Layout.column: 0
            Layout.fillWidth: root.stacked
            Layout.preferredWidth: root.stacked ? -1 : root.labelWidth
        }
        Slider {
            id: slider
            Layout.row: root.stacked ? 1 : 0
            Layout.column: root.stacked ? 0 : 1
            Layout.columnSpan: root.stacked ? 2 : 1
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.controlHeight - (root.stacked ? Theme.s3 : 0)
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
            Layout.row: 0; Layout.column: root.stacked ? 1 : 2
            Layout.preferredWidth: root.valueWidth
        }
    }
}
