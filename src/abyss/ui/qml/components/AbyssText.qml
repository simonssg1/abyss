import QtQuick
import theme

// Texte typographié : role = "h1" | "h2" | "body" | "bodySmall" | "caption" | "label" (capitales espacées)
Text {
    property string role: "body"
    property bool secondary: false
    color: secondary || role === "label" ? Theme.textSecondary : Theme.textPrimary
    font.family: Theme.fontFamily
    font.pixelSize: role === "h1" ? Theme.h1 : role === "h2" ? Theme.h2
                  : role === "bodySmall" ? Theme.bodySmall
                  : (role === "caption" || role === "label") ? Theme.caption : Theme.body
    font.weight: (role === "h1" || role === "h2") ? Theme.weightMedium : Theme.weightRegular
    font.capitalization: role === "label" ? Font.AllUppercase : Font.MixedCase
    font.letterSpacing: role === "label" ? Theme.labelSpacing : 0
    elide: Text.ElideRight
    textFormat: Text.PlainText
}
