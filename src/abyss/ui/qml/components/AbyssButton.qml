import QtQuick
import QtQuick.Controls
import theme

// Bouton : variant = "primary" (plein accent) | "secondary" (contour accent) | "tertiary" (contour neutre)
Button {
    id: control
    property string variant: "primary"
    property bool showArrow: false
    property string iconName: ""

    readonly property color fg: variant === "primary" ? Theme.textOnAccent
                               : variant === "secondary" ? Theme.accent : Theme.textPrimary

    implicitHeight: Theme.controlHeight
    implicitWidth: Math.max(160, contentRow.implicitWidth + Theme.s6 * 2)
    hoverEnabled: true
    leftPadding: Theme.s4
    rightPadding: Theme.s4
    opacity: enabled ? 1 : 0.4
    scale: down ? 0.98 : 1
    Behavior on scale { NumberAnimation { duration: Theme.durFast; easing.type: Theme.easing } }

    contentItem: Item {
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: Theme.s2
            Icon {
                visible: control.iconName !== ""
                name: control.iconName
                color: control.fg
                size: 18
                anchors.verticalCenter: parent.verticalCenter
            }
            AbyssText {
                text: control.text
                role: "body"
                color: control.fg
                font.weight: Theme.weightMedium
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        Icon {
            visible: control.showArrow
            name: "arrow-right"
            color: control.fg
            size: 18
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    background: Rectangle {
        radius: Theme.radiusButton
        color: control.variant === "primary"
               ? (control.hovered ? Qt.lighter(Theme.accent, 1.08) : Theme.accent)
               : (control.hovered ? Theme.card : "transparent")
        border.width: control.variant === "primary" ? 0 : Theme.strokeThin
        border.color: control.variant === "secondary" ? Theme.accent : Theme.borderNeutral
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }
}
