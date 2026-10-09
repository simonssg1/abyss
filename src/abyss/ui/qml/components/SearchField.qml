import QtQuick
import QtQuick.Controls
import theme

TextField {
    id: control
    placeholderText: "Entrez un texte…"
    implicitHeight: Theme.controlHeight
    implicitWidth: 280
    leftPadding: Theme.s4
    rightPadding: Theme.s4 + Theme.iconSize + Theme.s2
    color: Theme.textPrimary
    placeholderTextColor: Theme.textSecondary
    selectionColor: Theme.accentSoft
    selectedTextColor: Theme.textPrimary
    font.family: Theme.fontFamily
    font.pixelSize: Theme.bodySmall
    verticalAlignment: TextInput.AlignVCenter

    background: Rectangle {
        radius: Theme.radiusButton
        color: Theme.card
        border.width: Theme.strokeThin
        border.color: control.activeFocus ? Theme.accent : Theme.borderNeutral
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }
        Icon {
            name: control.text.length ? "x" : "search"
            color: Theme.textSecondary
            anchors.right: parent.right
            anchors.rightMargin: Theme.s4
            anchors.verticalCenter: parent.verticalCenter
            MouseArea {
                anchors.fill: parent
                anchors.margins: -Theme.s2
                enabled: control.text.length > 0
                cursorShape: Qt.PointingHandCursor
                onClicked: control.clear()
            }
        }
    }
}
