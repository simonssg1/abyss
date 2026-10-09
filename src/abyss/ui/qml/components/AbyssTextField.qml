import QtQuick
import QtQuick.Controls
import theme

TextField {
    id: control
    implicitHeight: Theme.controlHeight
    implicitWidth: 280
    leftPadding: Theme.s4
    rightPadding: Theme.s4
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
    }
}
