import QtQuick
import QtQuick.Controls
import theme

// Puce sélectionnable
AbstractButton {
    id: control
    checkable: true
    hoverEnabled: true
    implicitHeight: 32
    implicitWidth: label.implicitWidth + Theme.s4 * 2
    opacity: enabled ? 1 : 0.4

    background: Rectangle {
        radius: height / 2
        color: control.checked ? Theme.accent : (control.hovered ? Theme.cardHover : Theme.card)
        border.width: control.checked ? 0 : Theme.strokeThin
        border.color: Theme.border
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }
    contentItem: AbyssText {
        id: label
        text: control.text
        role: "bodySmall"
        color: control.checked ? Theme.textOnAccent : Theme.textPrimary
        font.weight: control.checked ? Theme.weightMedium : Theme.weightRegular
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
