pragma Singleton
import QtQuick

// Jetons de design Abyss (charte docs/charte-abyss.png). Aucune couleur ni taille en dur ailleurs.
QtObject {
    // Palette
    readonly property color bgDeep: "#0B1220"
    readonly property color principal: "#355070"
    readonly property color surface: "#2A3B5E"
    readonly property color accent: "#06D6A0"
    readonly property color textPrimary: "#E2E8FF"
    readonly property color textSecondary: "#8BA0C6"
    readonly property color indigo: "#6366F1"
    readonly property color danger: "#E5484D"

    // Dérivés (transparences de la palette, pour les cartes et contours de la charte)
    readonly property color card: Qt.rgba(surface.r, surface.g, surface.b, 0.38)
    readonly property color cardHover: Qt.rgba(surface.r, surface.g, surface.b, 0.55)
    readonly property color border: Qt.rgba(surface.r, surface.g, surface.b, 0.95)
    readonly property color borderNeutral: Qt.rgba(textSecondary.r, textSecondary.g, textSecondary.b, 0.45)
    readonly property color accentSoft: Qt.rgba(accent.r, accent.g, accent.b, 0.16)
    readonly property color accentGlow: Qt.rgba(accent.r, accent.g, accent.b, 0.55)
    readonly property color dangerSoft: Qt.rgba(danger.r, danger.g, danger.b, 0.16)
    readonly property color textOnAccent: bgDeep
    readonly property color track: Qt.rgba(surface.r, surface.g, surface.b, 0.9)
    readonly property color muted: Qt.rgba(textSecondary.r, textSecondary.g, textSecondary.b, 0.6)

    // Dégradés
    readonly property color gradPrincipalStart: principal
    readonly property color gradPrincipalEnd: accent
    readonly property color gradSecondaryStart: indigo
    readonly property color gradSecondaryEnd: accent

    // Rayons
    readonly property int radiusCard: 16
    readonly property int radiusButton: 12
    readonly property int radiusChip: 999

    // Espacements
    readonly property int s1: 4
    readonly property int s2: 8
    readonly property int s3: 12
    readonly property int s4: 16
    readonly property int s5: 24
    readonly property int s6: 32

    // Tailles de contrôles
    readonly property int controlHeight: 44
    readonly property int iconSize: 20
    readonly property int iconButton: 52
    readonly property int strokeThin: 1

    // Animation
    readonly property int durFast: 150
    readonly property int durNormal: 250
    readonly property int easing: Easing.OutCubic

    // Typographie (Inter, repli sur la police système chargée par Python)
    readonly property string fontFamily: Qt.application.font.family
    readonly property int h1: 32
    readonly property int h2: 20
    readonly property int body: 16
    readonly property int bodySmall: 14
    readonly property int caption: 12
    readonly property int weightMedium: Font.Medium
    readonly property int weightRegular: Font.Normal
    readonly property real labelSpacing: 3
}
