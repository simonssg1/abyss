import QtQuick
import QtQuick.Layouts
import theme

// Carte de preset : en-tête (icône, nom, sous-titre, lecture) + contenu libre en dessous.
Rectangle {
    id: root
    property string name: "Voix robot"
    property string subtitle: "Effet futuriste"
    property string iconName: "bot"
    property bool playing: false
    property bool playEnabled: true
    default property alias content: body.data
    signal playClicked()

    implicitWidth: 340
    implicitHeight: column.implicitHeight + Theme.s4 * 2
    radius: Theme.radiusCard
    color: Theme.card
    border.width: Theme.strokeThin
    border.color: Theme.border

    ColumnLayout {
        id: column
        anchors.fill: parent
        anchors.margins: Theme.s4
        spacing: Theme.s4
        RowLayout {
            spacing: Theme.s3
            Layout.fillWidth: true
            GradientTile { iconName: root.iconName; tileSize: 48 }
            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                AbyssText { text: root.name; role: "body"; font.weight: Theme.weightMedium; Layout.fillWidth: true }
                AbyssText { text: root.subtitle; role: "caption"; secondary: true; Layout.fillWidth: true; visible: text !== "" }
            }
            IconButton {
                diameter: 40
                variant: "neutral"
                enabled: root.playEnabled
                iconName: root.playing ? "pause" : "play"
                tooltip: root.playing ? "Arrêter l'aperçu" : "Écouter un aperçu"
                onClicked: root.playClicked()
                // icône lecture en accent, comme sur la charte
                contentItem: Item {
                    Icon {
                        anchors.centerIn: parent
                        name: root.playing ? "pause" : "play"
                        color: Theme.accent
                        size: 18
                    }
                }
            }
        }
        Rectangle {
            visible: body.children.length > 0
            Layout.fillWidth: true
            height: Theme.strokeThin
            color: Theme.border
        }
        ColumnLayout {
            id: body
            Layout.fillWidth: true
            spacing: Theme.s3
            visible: children.length > 0
        }
    }
}
