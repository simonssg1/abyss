import QtQuick
import QtQuick.Controls
import theme

Switch {
    id: control
    hoverEnabled: true
    spacing: Theme.s3
    opacity: enabled ? 1 : 0.4

    indicator: Rectangle {
        implicitWidth: 44
        implicitHeight: 24
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: height / 2
        color: control.checked ? Theme.accent : Theme.track
        Behavior on color { ColorAnimation { duration: Theme.durNormal; easing.type: Theme.easing } }

        Rectangle {
            width: 18
            height: 18
            radius: 9
            y: 3
            x: control.checked ? parent.width - width - 3 : 3
            color: Theme.textPrimary
            Behavior on x { NumberAnimation { duration: Theme.durNormal; easing.type: Theme.easing } }
        }
    }
    contentItem: AbyssText {
        text: control.text
        role: "bodySmall"
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
    }
}
