import QtQuick
import theme

// Pastille d'icône sur fond dégradé (listes et cartes de presets)
Rectangle {
    id: root
    property string iconName: "mic"
    property int tileSize: 44
    property bool dimmed: false
    width: tileSize
    height: tileSize
    radius: Theme.radiusButton
    gradient: Gradient {
        orientation: Gradient.Vertical
        GradientStop { position: 0; color: root.dimmed ? Theme.surface : Theme.indigo }
        GradientStop { position: 1; color: root.dimmed ? Theme.surface : Theme.principal }
    }
    Icon {
        anchors.centerIn: parent
        name: root.iconName
        size: Math.round(root.tileSize * 0.5)
        color: root.dimmed ? Theme.textSecondary : Theme.textPrimary
    }
}
