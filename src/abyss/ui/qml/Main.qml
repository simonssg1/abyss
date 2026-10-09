import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components
import "screens"

ApplicationWindow {
    id: win
    width: 420
    height: 780
    minimumWidth: 380
    minimumHeight: 680
    visible: true
    title: "Abyss"
    color: Theme.bgDeep

    readonly property bool wide: width > 760
    property bool welcomeDone: !app.showWelcome
    property StackView nav: null          // pile de navigation courante (écran entier ou panneau de droite)

    Component.onCompleted: {
        var g = app.windowGeometry
        if (g.length === 4) {
            x = g[0]; y = g[1]
            width = Math.max(minimumWidth, g[2]); height = Math.max(minimumHeight, g[3])
        }
    }
    onClosing: app.saveWindowGeometry(x, y, width, height)

    Connections {
        target: app
        function onToast(kind, title, message) { toast.show(kind, title, message) }
        function onRaiseRequested() { win.show(); win.raise(); win.requestActivate() }
    }

    // ----- navigation -----
    function topName() { return nav && nav.currentItem ? nav.currentItem.objectName : "" }
    function startMain() { welcomeDone = true }
    function openVoices() {
        if (!nav) return
        if (wide) { nav.pop(null) } else if (topName() !== "voices") { nav.push(voicesComp) }
    }
    function openEditor(id, isNew) { if (nav) nav.push(editorComp, { presetId: id, isNew: isNew }) }
    function openSettings() { if (nav && topName() !== "settings") nav.push(settingsComp) }
    function goBack() { if (nav && nav.depth > 1) nav.pop() }

    Component { id: directComp; Direct { objectName: "direct"; onOpenVoices: win.openVoices() } }
    Component {
        id: voicesComp
        Voices {
            objectName: "voices"
            onPresetChosen: if (!win.wide) win.goBack()
            onEditPreset: (id) => win.openEditor(id, false)
            onNewPreset: win.openEditor("", true)
        }
    }
    Component { id: editorComp; PresetEditor { objectName: "editor"; onClosed: win.goBack() } }
    Component { id: settingsComp; Settings { objectName: "settings" } }

    Component { id: welcomeComp; Welcome { onStarted: win.startMain() } }
    Component {
        id: narrowComp
        StackView {
            id: stack
            readonly property StackView stackRef: stack
            initialItem: directComp
        }
    }
    Component {
        id: wideComp
        RowLayout {
            readonly property StackView stackRef: panel
            spacing: 0
            Direct {
                objectName: "direct"
                Layout.preferredWidth: Math.max(380, Math.min(460, win.width * 0.42))
                Layout.fillHeight: true
                onOpenVoices: win.openVoices()
            }
            Rectangle { Layout.fillHeight: true; Layout.preferredWidth: Theme.strokeThin; color: Theme.border }
            StackView {
                id: panel
                Layout.fillWidth: true
                Layout.fillHeight: true
                initialItem: voicesComp
            }
        }
    }

    // ----- en-tête : retour, logo, réglages -----
    Item {
        id: header
        visible: win.welcomeDone
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: visible ? 60 : 0
        IconButton {
            anchors.left: parent.left
            anchors.leftMargin: Theme.s4
            anchors.verticalCenter: parent.verticalCenter
            diameter: 36
            iconName: "chevron-left"
            visible: win.nav !== null && win.nav.depth > 1
            tooltip: "Retour"
            onClicked: win.goBack()
        }
        Logo { anchors.centerIn: parent; size: 26 }
        IconButton {
            anchors.right: parent.right
            anchors.rightMargin: Theme.s4
            anchors.verticalCenter: parent.verticalCenter
            diameter: 36
            iconName: "settings"
            tooltip: "Réglages"
            onClicked: win.openSettings()
        }
    }

    Loader {
        id: content
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        sourceComponent: !win.welcomeDone ? welcomeComp : (win.wide ? wideComp : narrowComp)
        onLoaded: win.nav = item.stackRef !== undefined ? item.stackRef : null
    }

    Toast {
        id: toast
        shown: false
        z: 10
        width: Math.min(420, win.width - Theme.s4 * 2)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: Theme.s3
    }
}
