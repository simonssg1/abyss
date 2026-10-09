import QtQuick
import QtQuick.Layouts
import theme

// Notification : kind = "success" | "error" ; disparaît seule après `timeout` ms.
Rectangle {
    id: root
    property string kind: "success"
    property string title: "Prêt à enregistrer !"
    property string message: "Parle dans ton micro pour commencer"
    property int timeout: 4500
    property bool autoHide: true
    property bool shown: true
    signal closed()

    function show(k, t, m) {
        kind = k; title = t; message = m
        shown = true
        if (autoHide) hideTimer.restart()
    }
    function hide() { shown = false; closed() }

    implicitWidth: 340
    implicitHeight: Math.max(64, row.implicitHeight + Theme.s4 * 2)
    radius: Theme.radiusCard
    color: Theme.bgDeep
    border.width: Theme.strokeThin
    border.color: kind === "error" ? Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.5) : Theme.border
    opacity: shown ? 1 : 0
    visible: opacity > 0
    transform: Translate { y: root.shown ? 0 : -Theme.s3; Behavior on y { NumberAnimation { duration: Theme.durNormal; easing.type: Theme.easing } } }
    Behavior on opacity { NumberAnimation { duration: Theme.durNormal; easing.type: Theme.easing } }

    // Fond de carte par-dessus le fond profond (lisible au-dessus de n'importe quel écran)
    Rectangle { anchors.fill: parent; radius: parent.radius; color: Theme.card }

    Timer { id: hideTimer; interval: root.timeout; onTriggered: root.hide() }

    RowLayout {
        id: row
        anchors.fill: parent
        anchors.leftMargin: Theme.s4
        anchors.rightMargin: Theme.s3
        spacing: Theme.s3
        Rectangle {
            visible: root.kind !== "error"
            width: 28; height: 28; radius: 14
            color: Theme.accent
            Icon { anchors.centerIn: parent; name: "check"; color: Theme.textOnAccent; size: 16 }
        }
        Icon { visible: root.kind === "error"; name: "triangle-alert"; color: Theme.danger; size: 28 }
        ColumnLayout {
            spacing: 2
            Layout.fillWidth: true
            AbyssText { text: root.title; role: "bodySmall"; font.weight: Theme.weightMedium; Layout.fillWidth: true }
            AbyssText {
                text: root.message; role: "caption"; secondary: true
                Layout.fillWidth: true; wrapMode: Text.WordWrap; elide: Text.ElideNone
                visible: text !== ""
            }
        }
        Item {
            implicitWidth: 32; implicitHeight: 32
            Icon { anchors.centerIn: parent; name: "x"; color: Theme.textSecondary; size: 18 }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.hide() }
        }
    }
}
