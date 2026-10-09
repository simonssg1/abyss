import QtQuick
import theme

// Badge : variant = "new" (Nouveau) | "beta" (Bêta) | "active" (point accent) | "soon" (point gris)
Rectangle {
    id: root
    property string variant: "new"
    property string text: variant === "new" ? "Nouveau" : variant === "beta" ? "Bêta"
                        : variant === "active" ? "Actif" : "Bientôt"
    readonly property bool dotted: variant === "active" || variant === "soon"

    implicitHeight: 24
    implicitWidth: row.implicitWidth + Theme.s3 * 2
    radius: height / 2
    color: variant === "new" ? Theme.accent : variant === "beta" ? Theme.indigo : Theme.card
    border.width: dotted ? Theme.strokeThin : 0
    border.color: Theme.border

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Rectangle {
            visible: root.dotted
            width: 6; height: 6; radius: 3
            anchors.verticalCenter: parent.verticalCenter
            color: root.variant === "active" ? Theme.accent : Theme.muted
        }
        AbyssText {
            text: root.text
            role: "caption"
            font.weight: Theme.weightMedium
            color: root.variant === "new" ? Theme.textOnAccent
                   : root.variant === "soon" ? Theme.textSecondary : Theme.textPrimary
        }
    }
}
