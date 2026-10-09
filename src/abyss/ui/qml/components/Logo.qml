import QtQuick
import theme

// Logo : micro stylisé avec ses arcs + mot « Abyss »
Row {
    id: root
    property int size: 48
    property bool wordmark: true
    spacing: Math.round(size * 0.25)

    Image {
        width: root.size
        height: root.size
        source: "image://icon/mic-glyph/FFFFFF"
        sourceSize: Qt.size(root.size * 3, root.size * 3)
        mipmap: true
        anchors.verticalCenter: parent.verticalCenter
    }
    AbyssText {
        visible: root.wordmark
        text: "Abyss"
        font.pixelSize: Math.round(root.size * 0.78)
        font.weight: Theme.weightMedium
        anchors.verticalCenter: parent.verticalCenter
    }
}
