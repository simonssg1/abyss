import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import theme

// Ligne de preset : icône sur dégradé, nom, description, badge et raccourci optionnels, chevron.
AbstractButton {
    id: control
    property string name: "Nom du preset"
    property string description: "Description courte"
    property string iconName: "mic"
    property string badge: ""      // "", "new", "beta", "active", "soon"
    property string hotkey: ""
    property bool active: false

    implicitHeight: 72
    implicitWidth: 340
    hoverEnabled: true
    opacity: enabled ? 1 : 0.5

    background: Rectangle {
        radius: Theme.radiusCard
        color: control.hovered && control.enabled ? Theme.cardHover : Theme.card
        border.width: Theme.strokeThin
        border.color: control.active ? Theme.accent : Theme.border
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }
    contentItem: RowLayout {
        spacing: Theme.s3
        anchors.fill: parent
        anchors.leftMargin: Theme.s4
        anchors.rightMargin: Theme.s3
        GradientTile { iconName: control.iconName; dimmed: !control.enabled }
        ColumnLayout {
            spacing: 2
            Layout.fillWidth: true
            AbyssText { text: control.name; role: "body"; font.weight: Theme.weightMedium; Layout.fillWidth: true }
            AbyssText { text: control.description; role: "caption"; secondary: true; Layout.fillWidth: true; visible: text !== "" }
        }
        Badge { visible: control.badge !== ""; variant: control.badge || "new" }
        Rectangle {
            visible: control.hotkey !== ""
            implicitHeight: 22
            implicitWidth: hk.implicitWidth + Theme.s2 * 2
            radius: 6
            color: "transparent"
            border.width: Theme.strokeThin
            border.color: Theme.borderNeutral
            AbyssText { id: hk; anchors.centerIn: parent; text: control.hotkey; role: "caption"; secondary: true }
        }
        Icon { name: "chevron-right"; color: Theme.textSecondary; size: 18; visible: control.enabled }
    }
}
