import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

// Détail / éditeur de preset. Les valeurs sont modifiées en place dans `draft` (pas de reconstruction
// des curseurs pendant un glissement) ; les changements de structure (effets) réassignent `draft`.
Item {
    id: root
    property string presetId: ""
    property bool isNew: false
    property var draft: ({})
    property bool dirty: false
    property bool confirmDelete: false
    signal closed()

    readonly property var schemas: app.effectSchemas
    readonly property var editableCategories: ["Robot", "Sci-Fi", "Gaming", "Fun", "Ambiance"]
    readonly property string previewKey: draft.id || "__draft__"

    function reload() {
        draft = isNew ? app.newPresetDraft() : app.editDraft(presetId)
        dirty = false
        confirmDelete = false
    }
    Component.onCompleted: reload()
    Component.onDestruction: if (dirty && draft.id) app.cancelEdit(draft.id)

    function touched() { dirty = true; livePreview.restart() }
    function setValue(key, v) { draft[key] = v; touched() }
    function setEffectParam(i, key, v) { draft.effects[i][key] = v; touched() }
    function restructure(effects) {
        var d = Object.assign({}, draft)
        d.effects = effects
        draft = d
        touched()
    }
    function moveEffect(i, delta) {
        var e = draft.effects.slice(), j = i + delta
        if (j < 0 || j >= e.length) return
        var t = e[i]; e[i] = e[j]; e[j] = t
        restructure(e)
    }
    function removeEffect(i) { var e = draft.effects.slice(); e.splice(i, 1); restructure(e) }
    function addEffect(kind) { restructure(draft.effects.concat([app.defaultEffect(kind)])) }
    function toggleCategory(cat, on) {
        var c = (draft.categories || []).filter(function(x) { return x !== cat })
        if (on) c.push(cat)
        setValue("categories", c)
    }
    function decimalsFor(step) { return step >= 1 ? 0 : step >= 0.1 ? 1 : 2 }

    Timer { id: livePreview; interval: 120; onTriggered: app.previewEdit(root.draft) }
    Timer { id: deleteTimeout; interval: 3500; onTriggered: root.confirmDelete = false }

    ScrollView {
        id: scroll
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: Math.min(scroll.availableWidth - Theme.s5 * 2, 640)
            x: (scroll.availableWidth - width) / 2
            spacing: Theme.s4

            AbyssText {
                text: root.isNew ? "Nouveau preset" : "Éditer le preset"
                role: "h2"
                Layout.topMargin: Theme.s3
            }

            PresetCard {
                Layout.fillWidth: true
                name: nameField.text || "Sans nom"
                subtitle: descField.text
                iconName: root.draft.icon || "sparkles"
                playing: app.previewPlaying && app.previewId === root.previewKey
                onPlayClicked: app.togglePreview(root.draft)

                AbyssSlider {
                    Layout.fillWidth: true
                    label: "Intensité"; labelWidth: 84
                    value: root.draft.intensity !== undefined ? root.draft.intensity : 1
                    onMoved: (v) => root.setValue("intensity", v)
                }
                AbyssRangeSlider {
                    Layout.fillWidth: true
                    label: "Égaliseur"; labelWidth: 84
                    from: 50; to: 12000
                    first: root.draft.toneLow || 50
                    second: root.draft.toneHigh || 12000
                    onEdited: (lo, hi) => { root.draft.toneLow = lo; root.draft.toneHigh = hi; root.touched() }
                }
                AbyssText { text: "Catégories"; role: "bodySmall" }
                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.s2
                    Repeater {
                        model: root.editableCategories
                        Chip {
                            required property string modelData
                            text: modelData
                            checked: (root.draft.categories || []).indexOf(modelData) >= 0
                            onToggled: root.toggleCategory(modelData, checked)
                        }
                    }
                }
            }

            AbyssText { text: "Identité"; role: "label"; Layout.topMargin: Theme.s2 }
            AbyssTextField {
                id: nameField
                Layout.fillWidth: true
                placeholderText: "Nom du preset"
                text: root.draft.name || ""
                maximumLength: 40
                onTextEdited: root.setValue("name", text)
            }
            AbyssTextField {
                id: descField
                Layout.fillWidth: true
                placeholderText: "Description courte"
                text: root.draft.description || ""
                maximumLength: 60
                onTextEdited: root.setValue("description", text)
            }

            AbyssText { text: "Effets"; role: "label"; Layout.topMargin: Theme.s2 }
            AbyssText {
                visible: (root.draft.effects || []).length === 0
                text: "Aucun effet : la voix passe telle quelle (débruitage seul)."
                role: "caption"; secondary: true
                Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone
            }

            Repeater {
                model: root.draft.effects || []
                Rectangle {
                    id: fxCard
                    required property var modelData
                    required property int index
                    readonly property var schema: root.schemas[modelData.type] || ({ label: modelData.type, params: [] })
                    Layout.fillWidth: true
                    implicitHeight: fxCol.implicitHeight + Theme.s4 * 2
                    radius: Theme.radiusCard
                    color: Theme.card
                    border.width: Theme.strokeThin
                    border.color: Theme.border

                    ColumnLayout {
                        id: fxCol
                        anchors.fill: parent
                        anchors.margins: Theme.s4
                        spacing: Theme.s2
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.s2
                            AbyssText { text: (fxCard.index + 1) + ". " + fxCard.schema.label; role: "body"; font.weight: Theme.weightMedium; Layout.fillWidth: true }
                            IconButton { diameter: 32; iconName: "arrow-up"; enabled: fxCard.index > 0; tooltip: "Monter"; onClicked: root.moveEffect(fxCard.index, -1) }
                            IconButton { diameter: 32; iconName: "arrow-down"; enabled: fxCard.index < root.draft.effects.length - 1; tooltip: "Descendre"; onClicked: root.moveEffect(fxCard.index, 1) }
                            IconButton { diameter: 32; iconName: "trash"; tooltip: "Retirer l'effet"; onClicked: root.removeEffect(fxCard.index) }
                        }
                        Repeater {
                            model: fxCard.schema.params
                            Item {
                                id: paramRow
                                required property var modelData
                                readonly property var param: modelData
                                readonly property bool isBool: param.kind === "bool"
                                Layout.fillWidth: true
                                implicitHeight: isBool ? toggle.implicitHeight + Theme.s1 : slider.implicitHeight
                                AbyssSlider {
                                    id: slider
                                    visible: !paramRow.isBool
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    label: paramRow.param.label
                                    labelWidth: 120
                                    from: paramRow.param.min; to: paramRow.param.max; stepSize: paramRow.param.step
                                    unit: paramRow.param.unit
                                    decimals: root.decimalsFor(paramRow.param.step)
                                    value: paramRow.isBool ? 0 : (fxCard.modelData[paramRow.param.key] !== undefined
                                                                  ? fxCard.modelData[paramRow.param.key] : paramRow.param["default"])
                                    onMoved: (v) => root.setEffectParam(fxCard.index, paramRow.param.key, v)
                                }
                                AbyssToggle {
                                    id: toggle
                                    visible: paramRow.isBool
                                    text: paramRow.param.label
                                    checked: !!fxCard.modelData[paramRow.param.key]
                                    onToggled: root.setEffectParam(fxCard.index, paramRow.param.key, checked)
                                }
                            }
                        }
                    }
                }
            }

            AbyssButton {
                id: addButton
                Layout.fillWidth: true
                variant: "tertiary"
                iconName: "plus"
                text: "Ajouter un effet"
                onClicked: addMenu.open()

                Popup {
                    id: addMenu
                    y: -height - Theme.s1
                    width: addButton.width
                    height: Math.min(360, fxList.contentHeight + Theme.s2)
                    padding: Theme.s1
                    background: Rectangle {
                        radius: Theme.radiusButton
                        color: Theme.bgDeep
                        border.width: Theme.strokeThin
                        border.color: Theme.border
                        Rectangle { anchors.fill: parent; radius: parent.radius; color: Theme.card }
                    }
                    contentItem: ListView {
                        id: fxList
                        clip: true
                        model: app.effectTypes
                        delegate: ItemDelegate {
                            id: fxItem
                            required property string modelData
                            width: fxList.width
                            height: 40
                            contentItem: AbyssText { text: root.schemas[fxItem.modelData].label; role: "bodySmall"; verticalAlignment: Text.AlignVCenter }
                            background: Rectangle { radius: Theme.radiusButton - 4; color: fxItem.hovered ? Theme.cardHover : "transparent" }
                            onClicked: { root.addEffect(fxItem.modelData); addMenu.close() }
                        }
                    }
                }
            }

            // Actions
            AbyssButton {
                Layout.fillWidth: true
                Layout.topMargin: Theme.s3
                variant: "primary"
                iconName: "check"
                text: "Enregistrer"
                enabled: nameField.text.trim().length > 0
                onClicked: {
                    var id = app.savePreset(root.draft)
                    if (id) { root.presetId = id; root.isNew = false; root.reload() }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.s3
                visible: !root.isNew
                AbyssButton {
                    Layout.fillWidth: true
                    implicitWidth: 100
                    variant: "tertiary"
                    iconName: "copy"
                    text: "Dupliquer"
                    onClicked: {
                        var id = app.duplicatePreset(root.presetId)
                        if (id) { root.presetId = id; root.reload() }
                    }
                }
                AbyssButton {
                    visible: !!root.draft.isUser
                    Layout.fillWidth: true
                    implicitWidth: 100
                    variant: "tertiary"
                    iconName: "trash"
                    text: root.confirmDelete ? "Confirmer" : "Supprimer"
                    onClicked: {
                        if (!root.confirmDelete) { root.confirmDelete = true; deleteTimeout.restart(); return }
                        if (app.deletePreset(root.presetId)) { root.dirty = false; root.closed() }
                    }
                }
                AbyssButton {
                    visible: !!root.draft.isDefault
                    Layout.fillWidth: true
                    implicitWidth: 100
                    variant: "tertiary"
                    iconName: "rotate-ccw"
                    text: "Réinitialiser"
                    onClicked: {
                        var d = app.resetPreset(root.presetId)
                        if (d.id) { root.draft = d; root.dirty = false }
                    }
                }
            }
            Item { Layout.preferredHeight: Theme.s5 }
        }
    }
}
