import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

// Réglages : périphériques, débruitage, retour casque, gain, raccourcis, accueil, à propos.
Item {
    id: root
    readonly property string noneLabel: "(aucun)"

    component SectionLabel: AbyssText { role: "label"; Layout.topMargin: Theme.s4 }
    component Card: Rectangle {
        default property alias content: col.data
        Layout.fillWidth: true
        implicitHeight: col.implicitHeight + Theme.s4 * 2
        radius: Theme.radiusCard
        color: Theme.card
        border.width: Theme.strokeThin
        border.color: Theme.border
        ColumnLayout { id: col; anchors.fill: parent; anchors.margins: Theme.s4; spacing: Theme.s3 }
    }
    component DeviceRow: ColumnLayout {
        id: dev
        property string label
        property var choices: []
        property string current
        signal picked(string name)
        spacing: Theme.s1
        Layout.fillWidth: true
        AbyssText { text: dev.label; role: "caption"; secondary: true }
        AbyssComboBox {
            Layout.fillWidth: true
            model: dev.choices
            currentIndex: Math.max(0, dev.choices.indexOf(dev.current || root.noneLabel))
            onActivated: (i) => dev.picked(dev.choices[i] === root.noneLabel ? "" : dev.choices[i])
        }
    }
    component Warning: RowLayout {
        property string text
        spacing: Theme.s2
        Layout.fillWidth: true
        Icon { name: "triangle-alert"; color: Theme.danger; size: 16; Layout.alignment: Qt.AlignTop }
        AbyssText { text: parent.text; role: "caption"; color: Theme.danger; wrapMode: Text.WordWrap; elide: Text.ElideNone; Layout.fillWidth: true }
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: Math.min(scroll.availableWidth - Theme.s5 * 2, 640)
            x: (scroll.availableWidth - width) / 2
            spacing: Theme.s3

            AbyssText { text: "Réglages"; role: "h2"; Layout.topMargin: Theme.s3 }

            SectionLabel { text: "Périphériques" }
            Card {
                DeviceRow {
                    label: "Micro"
                    choices: app.inputDevices
                    current: app.inputDevice
                    onPicked: (name) => app.setInputDevice(name)
                }
                DeviceRow {
                    label: "Micro virtuel (ce que Discord entend)"
                    choices: [root.noneLabel].concat(app.outputDevices)
                    current: app.virtualDevice
                    onPicked: (name) => app.setVirtualDevice(name)
                }
                Warning { visible: !app.virtualFound; text: "Aucun micro virtuel détecté : installe BlackHole 2ch (macOS) ou VB-CABLE (Windows)." }
                DeviceRow {
                    label: "Casque (retour)"
                    choices: [root.noneLabel].concat(app.outputDevices)
                    current: app.monitorDevice
                    onPicked: (name) => app.setMonitorDevice(name)
                }
                AbyssButton {
                    variant: "tertiary"
                    iconName: "refresh-cw"
                    text: "Rafraîchir"
                    Layout.alignment: Qt.AlignRight
                    onClicked: app.refreshDevices()
                }
            }

            SectionLabel { text: "Débruitage" }
            Card {
                AbyssToggle { text: "Débruitage"; checked: app.denoiseOn; onToggled: app.setDenoise(checked) }
                AbyssSlider {
                    Layout.fillWidth: true
                    label: "Seuil"; labelWidth: 72
                    from: -80; to: -20; stepSize: 1; unit: "dB"
                    value: app.denoiseThreshold
                    enabled: app.denoiseOn
                    onMoved: (v) => app.setDenoiseThreshold(v)
                }
            }

            SectionLabel { text: "Retour casque" }
            Card {
                AbyssToggle { text: "M'entendre dans le casque"; checked: app.monitorOn; onToggled: app.setMonitor(checked) }
                AbyssSlider {
                    Layout.fillWidth: true
                    label: "Volume"; labelWidth: 72
                    value: app.monitorVolume
                    enabled: app.monitorOn
                    onMoved: (v) => app.setMonitorVolume(v)
                }
                Warning { visible: app.speakerWarning; text: "Le retour sort sur des haut-parleurs : risque de larsen. Utilise un casque." }
            }

            SectionLabel { text: "Sortie" }
            Card {
                AbyssSlider {
                    Layout.fillWidth: true
                    label: "Gain"; labelWidth: 72
                    from: -12; to: 12; stepSize: 1; unit: "dB"
                    formatValue: function(v) { return (v > 0 ? "+" : "") + v.toFixed(0) + " dB" }
                    value: app.outputGain
                    onMoved: (v) => app.setOutputGain(v)
                }
            }

            SectionLabel { text: "Raccourcis" }
            Card {
                RowLayout {
                    spacing: Theme.s2
                    Badge { variant: app.hotkeysOk ? "active" : "soon"; text: app.hotkeysOk ? "Actifs" : "Inactifs" }
                    AbyssText { text: app.hotkeysOk ? "" : app.hotkeysStatus; role: "caption"; secondary: true; Layout.fillWidth: true }
                }
                Warning {
                    visible: !app.hotkeysOk
                    text: app.platform === "mac"
                          ? "Autorise " + app.permissionTarget + " dans Réglages Système → Confidentialité et sécurité → Surveillance de l'entrée."
                          : "Relance Abyss ; si ça persiste, un antivirus bloque peut-être l'écoute du clavier."
                }
                Repeater {
                    model: app.hotkeyList
                    RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        AbyssText { text: modelData.label; role: "bodySmall"; Layout.fillWidth: true }
                        Rectangle {
                            implicitHeight: 24
                            implicitWidth: combo.implicitWidth + Theme.s2 * 2
                            radius: 6
                            color: "transparent"
                            border.width: Theme.strokeThin
                            border.color: Theme.borderNeutral
                            AbyssText { id: combo; anchors.centerIn: parent; text: modelData.combo; role: "caption"; secondary: true }
                        }
                    }
                }
            }

            SectionLabel { text: "Accueil" }
            Card {
                AbyssToggle { text: "Afficher l'accueil au lancement"; checked: app.showWelcome; onToggled: app.setShowWelcome(checked) }
            }

            SectionLabel { text: "À propos" }
            Card {
                AbyssText { text: "Abyss " + app.version; role: "body"; font.weight: Theme.weightMedium }
                AbyssText {
                    text: "<a href=\"" + app.repoUrl + "\">" + app.repoUrl.replace("https://", "") + "</a>"
                    textFormat: Text.StyledText
                    linkColor: Theme.accent
                    role: "bodySmall"
                    onLinkActivated: (link) => Qt.openUrlExternally(link)
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
            Item { Layout.preferredHeight: Theme.s5 }
        }
    }
}
