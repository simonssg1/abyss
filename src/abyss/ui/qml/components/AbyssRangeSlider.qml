import QtQuick
import QtQuick.Controls as C
import QtQuick.Layouts
import theme

// Curseur à deux poignées (« Égaliseur ») sur une échelle logarithmique optionnelle.
Item {
    id: root
    property string label: ""
    property real from: 50
    property real to: 12000
    property bool logarithmic: true
    property real first: 80
    property real second: 8000
    property real labelWidth: Theme.formLabelWidth
    property real valueWidth: Theme.formValueWidth
    property var formatValue: function(v) { return v >= 1000 ? (v / 1000).toFixed(v >= 10000 ? 0 : 1) + " kHz" : Math.round(v) + " Hz" }
    signal edited(real first, real second)

    function toPos(v) { return logarithmic ? Math.log(v / from) / Math.log(to / from) : (v - from) / (to - from) }
    function fromPos(p) { return logarithmic ? from * Math.pow(to / from, p) : from + p * (to - from) }

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
        C.RangeSlider {
            id: range
            Layout.row: root.stacked ? 1 : 0
            Layout.column: root.stacked ? 0 : 1
            Layout.columnSpan: root.stacked ? 2 : 1
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.controlHeight - (root.stacked ? Theme.s3 : 0)
            from: 0; to: 1
            first.value: root.toPos(root.first)
            second.value: root.toPos(root.second)
            first.onMoved: { root.first = root.fromPos(first.value); root.edited(root.first, root.second) }
            second.onMoved: { root.second = root.fromPos(second.value); root.edited(root.first, root.second) }
            background: Rectangle {
                x: range.leftPadding
                y: range.topPadding + range.availableHeight / 2 - height / 2
                width: range.availableWidth
                height: 4
                radius: 2
                color: Theme.track
                Rectangle {
                    x: range.first.visualPosition * parent.width
                    width: (range.second.visualPosition - range.first.visualPosition) * parent.width
                    height: parent.height
                    radius: 2
                    color: Theme.accent
                }
            }
            first.handle: Rectangle {
                x: range.leftPadding + range.first.visualPosition * (range.availableWidth - width)
                y: range.topPadding + range.availableHeight / 2 - height / 2
                width: 6; height: 16; radius: 3
                color: Theme.accent
            }
            second.handle: Rectangle {
                x: range.leftPadding + range.second.visualPosition * (range.availableWidth - width)
                y: range.topPadding + range.availableHeight / 2 - height / 2
                width: 6; height: 16; radius: 3
                color: Theme.accent
            }
        }
        AbyssText {
            text: root.formatValue(root.first) + " – " + root.formatValue(root.second)
            role: "caption"
            secondary: true
            horizontalAlignment: Text.AlignRight
            Layout.row: 0; Layout.column: root.stacked ? 1 : 2
            Layout.preferredWidth: root.valueWidth
        }
    }
}
