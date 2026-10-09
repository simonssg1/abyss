import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

// Accueil : logo, phrase, checklist de démarrage, bouton « Commencer », vagues.
Item {
    id: root
    signal started()

    component CheckRow: RowLayout {
        id: row
        property string status: "ok"   // "ok" | "fail" | "pending"
        property string label
        property string help
        spacing: Theme.s3
        Layout.fillWidth: true
        Item {
            Layout.preferredWidth: 24; Layout.preferredHeight: 24
            Layout.alignment: Qt.AlignTop
            Rectangle {
                anchors.fill: parent; radius: 12
                color: row.status === "ok" ? Theme.accent : "transparent"
                border.width: row.status === "ok" ? 0 : Theme.strokeThin
                border.color: row.status === "fail" ? Theme.danger : Theme.borderNeutral
            }
            Icon {
                anchors.centerIn: parent
                size: 14
                name: row.status === "ok" ? "check" : row.status === "fail" ? "x" : "ellipsis"
                color: row.status === "ok" ? Theme.textOnAccent
                     : row.status === "fail" ? Theme.danger : Theme.textSecondary
            }
        }
        ColumnLayout {
            spacing: 2
            Layout.fillWidth: true
            AbyssText {
                text: row.label; role: "bodySmall"; Layout.fillWidth: true
                color: row.status === "ok" ? Theme.accent : Theme.textPrimary
            }
            AbyssText {
                visible: row.status !== "ok" && text !== ""
                text: row.help; role: "caption"; secondary: true
                Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone
            }
        }
    }

    WaveBackground {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Math.min(220, root.height * 0.28)
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -Math.min(80, root.height * 0.08)
        width: Math.min(360, root.width - Theme.s6 * 2)
        spacing: Theme.s4

        Logo { size: 88; wordmark: false; Layout.alignment: Qt.AlignHCenter }
        AbyssText {
            text: "Abyss"; font.pixelSize: 44; font.weight: Theme.weightMedium
            Layout.alignment: Qt.AlignHCenter
        }
        AbyssText {
            text: "Transforme ta voix en infinies possibilités."
            role: "body"
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap; elide: Text.ElideNone
            Layout.fillWidth: true
            Layout.bottomMargin: Theme.s4
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: checks.implicitHeight + Theme.s4 * 2
            radius: Theme.radiusCard
            color: Theme.card
            border.width: Theme.strokeThin
            border.color: Theme.border
            ColumnLayout {
                id: checks
                anchors.fill: parent
                anchors.margins: Theme.s4
                spacing: Theme.s3
                CheckRow {
                    status: app.virtualFound ? "ok" : "fail"
                    label: "Micro virtuel détecté"
                    help: "Installe BlackHole 2ch (macOS) ou VB-CABLE (Windows), puis relance Abyss."
                }
                CheckRow {
                    status: app.micPermission === "authorized" ? "ok"
                         : app.micPermission === "denied" ? "fail" : "pending"
                    label: "Accès au micro"
                    help: app.micPermission === "denied"
                          ? "Autorise " + app.permissionTarget + " dans Réglages Système → Confidentialité et sécurité → Micro."
                          : "L'accès sera demandé au premier démarrage du direct."
                }
                CheckRow {
                    status: app.hotkeysOk ? "ok" : "fail"
                    label: "Raccourcis clavier actifs"
                    help: "Autorise " + app.permissionTarget + " dans Accessibilité et Surveillance de l'entrée (Réglages Système)."
                }
            }
        }

        AbyssButton {
            text: "Commencer"
            variant: "primary"
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 240
            Layout.topMargin: Theme.s3
            onClicked: root.started()
        }
    }
}
