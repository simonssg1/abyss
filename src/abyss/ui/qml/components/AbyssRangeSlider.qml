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
    property real labelWidth: 96
    property var formatValue: function(v) { return v >= 1000 ? (v / 1000).toFixed(v >= 10000 ? 0 : 1) + " k" : Math.round(v) + "" }
    signal edited(real first, real second)

    function toPos(v) { return logarithmic ? Math.log(v / from) / Math.log(to / from) : (v - from) / (to - from) }
    function fromPos(p) { return logarithmic ? from * Math.pow(to / from, p) : from + p * (to - from) }

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
        C.RangeSlider {
            id: range
            Layout.fillWidth: true
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
            Layout.preferredWidth: 72
        }
    }
}
