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
    property bool separateChevron: false   // true : le chevron émet chevronClicked (édition)
    signal chevronClicked()

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
            AbyssText { text: control.name; role: "body"; font.weight: Theme.weightMedium; Layout.fillWidth: true; color: control.active ? Theme.accent : Theme.textPrimary }
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
        Item {
            visible: control.enabled
            implicitWidth: control.separateChevron ? 36 : 18
            implicitHeight: 36
            Rectangle {
                anchors.fill: parent
                radius: Theme.radiusButton
                color: chevronArea.containsMouse ? Theme.cardHover : "transparent"
                visible: control.separateChevron
            }
            Icon { anchors.centerIn: parent; name: "chevron-right"; color: chevronArea.containsMouse ? Theme.accent : Theme.textSecondary; size: 18 }
            MouseArea {
                id: chevronArea
                anchors.fill: parent
                enabled: control.separateChevron
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: control.chevronClicked()
            }
        }
    }
}
