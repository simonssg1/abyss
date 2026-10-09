import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

// Bibliothèque des voix : recherche, catégories, liste ; ligne = utiliser, chevron = éditer.
Item {
    id: root
    signal presetChosen(string id)
    signal editPreset(string id)
    signal newPreset()

    readonly property var categories: ["Toutes", "Robot", "Sci-Fi", "Gaming", "Fun", "Ambiance", "IA"]

    ColumnLayout {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - Theme.s5 * 2, 640)
        anchors.topMargin: Theme.s3
        anchors.bottomMargin: Theme.s5
        spacing: Theme.s4

        AbyssText { text: "Voix"; role: "h2" }

        SearchField {
            Layout.fillWidth: true
            placeholderText: "Rechercher une voix…"
            text: app.presetFilterModel.search
            onTextEdited: app.presetFilterModel.search = text
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Repeater {
                model: root.categories
                Chip {
                    required property string modelData
                    text: modelData
                    checked: app.presetFilterModel.category === modelData
                    onClicked: app.presetFilterModel.category = modelData
                }
            }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: Theme.s3
            model: app.presetFilterModel
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: PresetListItem {
                required property var model
                width: list.width
                name: model.name
                description: model.description
                iconName: model.icon
                hotkey: model.hotkey
                enabled: model.enabled
                active: model.id === app.activePresetId
                badge: model.enabled ? model.badge : "soon"
                separateChevron: true
                onClicked: { app.selectPreset(model.id); root.presetChosen(model.id) }
                onChevronClicked: root.editPreset(model.id)
            }
            AbyssText {
                anchors.centerIn: parent
                visible: list.count === 0
                text: "Aucune voix ne correspond."
                role: "bodySmall"; secondary: true
            }
        }

        AbyssButton {
            Layout.fillWidth: true
            variant: "secondary"
            iconName: "plus"
            text: "Nouveau preset"
            onClicked: root.newPreset()
        }
    }
}
