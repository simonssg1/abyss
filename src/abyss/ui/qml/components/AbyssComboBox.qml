import QtQuick
import QtQuick.Controls
import theme

// Liste déroulante (modèle : tableau de textes)
ComboBox {
    id: control
    implicitHeight: Theme.controlHeight
    implicitWidth: 280
    leftPadding: Theme.s4
    rightPadding: Theme.s4 + Theme.iconSize
    font.family: Theme.fontFamily
    font.pixelSize: Theme.bodySmall
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radiusButton
        color: control.hovered ? Theme.cardHover : Theme.card
        border.width: Theme.strokeThin
        border.color: control.popup.visible ? Theme.accent : Theme.borderNeutral
    }
    contentItem: AbyssText {
        text: control.displayText
        role: "bodySmall"
        verticalAlignment: Text.AlignVCenter
    }
    indicator: Icon {
        name: "chevron-down"
        color: Theme.textSecondary
        size: 18
        x: control.width - width - Theme.s3
        y: (control.height - height) / 2
    }
    delegate: ItemDelegate {
        id: item
        required property int index
        required property var modelData
        width: control.width - Theme.s2
        height: 40
        highlighted: control.highlightedIndex === index
        contentItem: AbyssText {
            text: item.modelData
            role: "bodySmall"
            color: control.currentIndex === item.index ? Theme.accent : Theme.textPrimary
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: Theme.radiusButton - 4
            color: item.highlighted ? Theme.cardHover : "transparent"
        }
    }
    popup: Popup {
        y: control.height + Theme.s1
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + Theme.s2, 320)
        padding: Theme.s1
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle {
            radius: Theme.radiusButton
            color: Theme.bgDeep
            border.width: Theme.strokeThin
            border.color: Theme.border
            Rectangle { anchors.fill: parent; radius: parent.radius; color: Theme.card }
        }
    }
}
