import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

// Écran principal : preset actuel, anneau du micro (démarre/arrête le direct), forme d'onde, chrono, commandes.
Item {
    id: root
    signal openVoices()

    readonly property var preset: { app.presetsRevision; app.activePresetId; return app.presets.get(app.activePresetId) }

    function clock(s) {
        var m = Math.floor(s / 60), r = s % 60
        return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s5
        anchors.rightMargin: Theme.s5
        anchors.topMargin: Theme.s3
        anchors.bottomMargin: Theme.s5
        spacing: Theme.s4

        // Menu « Preset actuel »
        AbstractButton {
            id: presetMenu
            Layout.fillWidth: true
            implicitHeight: 60
            hoverEnabled: true
            onClicked: root.openVoices()
            background: Rectangle {
                radius: Theme.radiusCard
                color: presetMenu.hovered ? Theme.cardHover : Theme.card
                border.width: Theme.strokeThin
                border.color: Theme.border
            }
            contentItem: RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.s3
                anchors.rightMargin: Theme.s4
                spacing: Theme.s3
                GradientTile { iconName: root.preset.icon || "mic"; tileSize: 36 }
                ColumnLayout {
                    spacing: 0
                    Layout.fillWidth: true
                    AbyssText { text: "Preset actuel"; role: "caption"; secondary: true }
                    AbyssText { text: root.preset.name || ""; role: "body"; font.weight: Theme.weightMedium; Layout.fillWidth: true }
                }
                Icon { name: "chevron-down"; color: Theme.textSecondary; size: 18 }
            }
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: Theme.s2 }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 24
            Badge { anchors.centerIn: parent; variant: "active"; visible: app.live }
            AbyssText {
                anchors.centerIn: parent
                visible: !app.live
                text: app.starting ? "Démarrage…" : "Touche l'anneau pour démarrer"
                role: "caption"; secondary: true
            }
        }

        MicRing {
            id: ring
            readonly property real side: Math.max(150, Math.min(root.width - Theme.s6 * 2, root.height * 0.36, 260))
            Layout.preferredWidth: side
            Layout.preferredHeight: side
            Layout.alignment: Qt.AlignHCenter
            active: app.live
            level: app.outputLevel
            onClicked: app.toggleLive()
        }

        Waveform {
            Layout.fillWidth: true
            Layout.maximumWidth: 320
            Layout.preferredHeight: 44
            Layout.alignment: Qt.AlignHCenter
            levels: app.inputHistory
            active: app.live
        }

        AbyssText {
            text: root.clock(app.sessionSeconds)
            font.pixelSize: Theme.h1
            font.weight: Theme.weightRegular
            font.features: { "tnum": 1 }
            color: app.live ? Theme.textPrimary : Theme.textSecondary
            Layout.alignment: Qt.AlignHCenter
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: Theme.s2 }

        AbyssSlider {
            Layout.fillWidth: true
            label: "Intensité"
            labelWidth: 80
            value: root.preset.intensity !== undefined ? root.preset.intensity : 1
            enabled: !app.bypass && (root.preset.effects || []).length > 0
            onMoved: (v) => app.setIntensity(app.activePresetId, v)
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.s6
            ColumnLayout {
                spacing: Theme.s1
                Layout.alignment: Qt.AlignBottom
                IconButton {
                    Layout.alignment: Qt.AlignHCenter
                    variant: app.outputMuted ? "danger" : "neutral"
                    iconName: app.outputMuted ? "volume-x" : "x"
                    tooltip: app.outputMuted ? "Rétablir la sortie" : "Couper la sortie vers le micro virtuel"
                    onClicked: app.toggleOutputMuted()
                }
                AbyssText {
                    text: app.outputMuted ? "Sortie coupée" : "Couper"
                    role: "caption"; secondary: !app.outputMuted
                    color: app.outputMuted ? Theme.danger : Theme.textSecondary
                    Layout.alignment: Qt.AlignHCenter
                }
            }
            ColumnLayout {
                spacing: Theme.s1
                Layout.alignment: Qt.AlignBottom
                IconButton {
                    Layout.alignment: Qt.AlignHCenter
                    diameter: 64
                    variant: "active"
                    iconName: app.bypass ? "play" : "pause"
                    tooltip: app.bypass ? "Réactiver les effets" : "Bypass : voix sans effets"
                    onClicked: app.toggleBypass()
                }
                AbyssText {
                    text: app.bypass ? "Effets en pause" : "Bypass"
                    role: "caption"; secondary: true
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
    }
}
