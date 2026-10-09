import QtQuick
import theme

// Barres verticales centrées, alimentées par l'historique du niveau d'entrée (le plus récent à droite).
Item {
    id: root
    property var levels: []
    property int bars: 41
    property real barWidth: 3
    property bool active: true

    implicitWidth: bars * (barWidth + 3)
    implicitHeight: 48

    Row {
        anchors.centerIn: parent
        spacing: (root.width - root.bars * root.barWidth) / Math.max(1, root.bars - 1)
        Repeater {
            model: root.bars
            Rectangle {
                required property int index
                readonly property int src: root.levels.length - root.bars + index
                readonly property real v: src >= 0 && src < root.levels.length ? root.levels[src] : 0
                width: root.barWidth
                height: Math.max(3, Math.min(1, v) * root.height)
                radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                color: root.active ? Theme.accent : Theme.muted
                opacity: 0.3 + 0.7 * Math.sin(Math.PI * (index + 0.5) / root.bars)
                Behavior on height { NumberAnimation { duration: 60 } }
            }
        }
    }
}
