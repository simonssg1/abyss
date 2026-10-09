import QtQuick
import QtQuick.Controls
import theme
import "screens"

ApplicationWindow {
    width: 1200
    height: 860
    visible: true
    title: "Abyss — Galerie"
    color: Theme.bgDeep
    Gallery { anchors.fill: parent }
}
