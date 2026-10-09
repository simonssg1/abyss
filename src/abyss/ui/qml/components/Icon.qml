import QtQuick
import theme

// Icône Lucide recolorée (rendue par IconProvider côté Python)
Item {
    id: root
    property string name: "mic"
    property color color: Theme.textPrimary
    property int size: Theme.iconSize
    implicitWidth: size
    implicitHeight: size

    Image {
        anchors.fill: parent
        source: root.name ? "image://icon/" + root.name + "/" + root.color.toString().slice(1) : ""
        sourceSize: Qt.size(root.size * 3, root.size * 3)
        smooth: true
        mipmap: true
        fillMode: Image.PreserveAspectFit
    }
}
