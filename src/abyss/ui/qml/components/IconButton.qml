import QtQuick
import QtQuick.Controls
import theme

// Bouton rond : variant = "active" (plein accent) | "neutral" | "muted" (micro barré) | "menu" (« … ») | "danger"
AbstractButton {
    id: control
    property string variant: "neutral"
    property string iconName: variant === "muted" ? "mic-off" : variant === "menu" ? "ellipsis" : "mic"
    property int diameter: Theme.iconButton
    property string tooltip: ""

    implicitWidth: diameter
    implicitHeight: diameter
    hoverEnabled: true
    opacity: enabled ? 1 : 0.4
    scale: down ? 0.94 : 1
    Behavior on scale { NumberAnimation { duration: Theme.durFast; easing.type: Theme.easing } }

    ToolTip.visible: tooltip !== "" && hovered
    ToolTip.text: tooltip
    ToolTip.delay: 600

    background: Rectangle {
        radius: width / 2
        color: control.variant === "active" ? (control.hovered ? Qt.lighter(Theme.accent, 1.08) : Theme.accent)
             : control.variant === "danger" ? Theme.dangerSoft
             : (control.hovered ? Theme.cardHover : Theme.card)
        border.width: control.variant === "active" ? 0 : Theme.strokeThin
        border.color: control.variant === "danger" ? Theme.danger : Theme.border
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }
    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            name: control.iconName
            size: Math.round(control.diameter * 0.42)
            color: control.variant === "active" ? Theme.textOnAccent
                   : control.variant === "danger" ? Theme.danger
                   : control.variant === "muted" ? Theme.textSecondary : Theme.textPrimary
        }
    }
}
