import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

// Galerie : tous les composants dans tous leurs états, organisée comme la charte.
Rectangle {
    id: gallery
    color: Theme.bgDeep

    component Section: ColumnLayout {
        property string title
        default property alias items: inner.data
        spacing: Theme.s4
        Layout.alignment: Qt.AlignTop
        AbyssText { text: parent.title; role: "label" }
        ColumnLayout { id: inner; spacing: Theme.s3; Layout.fillWidth: true }
    }
    component Swatch: ColumnLayout {
        property color swatch
        property string hex
        property string name
        property string usage
        spacing: 2
        Layout.alignment: Qt.AlignTop
        Rectangle {
            Layout.preferredWidth: 96; Layout.preferredHeight: 52
            radius: Theme.radiusButton; color: parent.swatch
            border.width: Theme.strokeThin; border.color: Theme.border
        }
        AbyssText { text: parent.hex; role: "bodySmall" }
        AbyssText { text: parent.name; role: "caption" }
        AbyssText { text: parent.usage; role: "caption"; secondary: true; Layout.maximumWidth: 120; wrapMode: Text.WordWrap; elide: Text.ElideNone }
    }

    // Niveaux simulés pour animer l'anneau et la forme d'onde
    property real fakeLevel: 0
    property var history: []
    Timer {
        interval: 33; running: gallery.visible; repeat: true
        property real t: 0
        onTriggered: {
            t += 0.033
            var v = Math.abs(Math.sin(t * 3.1) * 0.6 + Math.sin(t * 7.3) * 0.3) * (0.6 + 0.4 * Math.sin(t * 0.7))
            gallery.fakeLevel = v
            var h = gallery.history.slice(-63); h.push(v); gallery.history = h
        }
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        Flow {
            width: scroll.availableWidth
            padding: Theme.s6
            spacing: Theme.s6

            Section {
                title: "Logo principal"
                Logo { size: 96 }
                AbyssText { text: "Logo secondaire"; role: "label"; Layout.topMargin: Theme.s4 }
                Logo { size: 40 }
            }

            Section {
                title: "Palette de couleurs"
                GridLayout {
                    columns: 3; columnSpacing: Theme.s4; rowSpacing: Theme.s4
                    Swatch { swatch: Theme.principal; hex: "#355070"; name: "Principal"; usage: "fond, surfaces" }
                    Swatch { swatch: Theme.accent; hex: "#06D6A0"; name: "Accent"; usage: "boutons, liens, icônes" }
                    Swatch { swatch: Theme.textPrimary; hex: "#E2E8FF"; name: "Texte principal"; usage: "titres, contenu" }
                    Swatch { swatch: Theme.textSecondary; hex: "#8BA0C6"; name: "Texte secondaire"; usage: "labels, descriptions" }
                    Swatch { swatch: Theme.bgDeep; hex: "#0B1220"; name: "Background profond"; usage: "écrans, modals" }
                    Swatch { swatch: Theme.surface; hex: "#2A3B5E"; name: "Surfaces"; usage: "cartes, champs" }
                    Swatch { swatch: Theme.indigo; hex: "#6366F1"; name: "Indigo"; usage: "dégradé secondaire, Bêta" }
                    Swatch { swatch: Theme.danger; hex: "#E5484D"; name: "Danger"; usage: "erreurs" }
                }
                AbyssText { text: "Dégradés"; role: "label"; Layout.topMargin: Theme.s4 }
                RowLayout {
                    spacing: Theme.s4
                    Repeater {
                        model: [[Theme.gradPrincipalStart, Theme.gradPrincipalEnd, "Dégradé principal", "#355070 → #06D6A0"],
                                [Theme.gradSecondaryStart, Theme.gradSecondaryEnd, "Dégradé secondaire", "#6366F1 → #06D6A0"]]
                        ColumnLayout {
                            required property var modelData
                            spacing: 2
                            Rectangle {
                                Layout.preferredWidth: 150; Layout.preferredHeight: 44; radius: Theme.radiusButton
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0; color: modelData[0] }
                                    GradientStop { position: 1; color: modelData[1] }
                                }
                            }
                            AbyssText { text: modelData[2]; role: "caption" }
                            AbyssText { text: modelData[3]; role: "caption"; secondary: true }
                        }
                    }
                }
            }

            Section {
                title: "Typographie"
                RowLayout {
                    spacing: Theme.s4
                    AbyssText { text: "Aa"; font.pixelSize: 64; font.weight: Theme.weightMedium }
                    ColumnLayout {
                        spacing: 0
                        AbyssText { text: Theme.fontFamily; role: "h2" }
                        AbyssText { text: "ABCDEFGHIJKLMNOPQRSTUVWXYZ"; role: "caption"; secondary: true }
                        AbyssText { text: "abcdefghijklmnopqrstuvwxyz 0123456789"; role: "caption"; secondary: true }
                    }
                }
                AbyssText { text: "H1 · Titre principal"; role: "h1" }
                AbyssText { text: "H2 · Sous-titre"; role: "h2" }
                AbyssText { text: "Body · Texte courant"; role: "body" }
                AbyssText { text: "Caption · Légende"; role: "caption"; secondary: true }
                AbyssText { text: "Libellé de section"; role: "label" }
            }

            Section {
                title: "Composants UI"
                AbyssButton { text: "Bouton principal"; variant: "primary"; showArrow: true; Layout.preferredWidth: 280 }
                AbyssButton { text: "Bouton secondaire"; variant: "secondary"; showArrow: true; Layout.preferredWidth: 280 }
                AbyssButton { text: "Bouton tertiaire"; variant: "tertiary"; showArrow: true; Layout.preferredWidth: 280 }
                AbyssButton { text: "Désactivé"; variant: "primary"; enabled: false; Layout.preferredWidth: 280 }
                RowLayout {
                    spacing: Theme.s4
                    IconButton { variant: "active" }
                    IconButton { variant: "neutral" }
                    IconButton { variant: "muted" }
                    IconButton { variant: "menu" }
                }
                RowLayout {
                    spacing: Theme.s5
                    AbyssToggle { text: "Actif"; checked: true }
                    AbyssToggle { text: "Inactif"; checked: false }
                }
                SearchField { Layout.preferredWidth: 280 }
                PresetListItem { Layout.preferredWidth: 280 }
            }

            Section {
                title: "Listes et badges"
                PresetListItem { name: "Robot"; description: "Métallique et saccadé"; iconName: "bot"; hotkey: "⌃⌥2"; Layout.preferredWidth: 340 }
                PresetListItem { name: "Mon preset"; description: "Créé dans l'éditeur"; iconName: "sparkles"; badge: "new"; Layout.preferredWidth: 340 }
                PresetListItem { name: "Démon"; description: "Preset actif"; iconName: "flame"; active: true; badge: "active"; Layout.preferredWidth: 340 }
                PresetListItem { name: "Voix IA"; description: "Conversion de voix RVC"; iconName: "sparkles"; badge: "soon"; enabled: false; Layout.preferredWidth: 340 }
                AbyssText { text: "Badges / états"; role: "label"; Layout.topMargin: Theme.s3 }
                RowLayout {
                    spacing: Theme.s3
                    Badge { variant: "new" }
                    Badge { variant: "beta" }
                    Badge { variant: "active" }
                    Badge { variant: "soon" }
                }
            }

            Section {
                title: "Style des cartes"
                PresetCard {
                    Layout.preferredWidth: 340
                    AbyssRangeSlider { label: "Égaliseur"; Layout.fillWidth: true }
                    AbyssSlider { label: "Intensité"; value: 0.7; Layout.fillWidth: true }
                    AbyssText { text: "Catégories"; role: "bodySmall" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.s2
                        Chip { text: "Robot"; checked: true }
                        Chip { text: "Sci-Fi" }
                        Chip { text: "Gaming" }
                        Chip { text: "Fun"; enabled: false }
                    }
                }
                PresetCard { name: "Démon"; subtitle: "Aperçu en cours"; iconName: "flame"; playing: true; Layout.preferredWidth: 340 }
                Toast { kind: "success"; autoHide: false; Layout.preferredWidth: 340 }
                Toast { kind: "error"; title: "Erreur"; message: "Une erreur est survenue. Réessaie."; autoHide: false; Layout.preferredWidth: 340 }
            }

            Section {
                title: "Éléments graphiques"
                RowLayout {
                    spacing: Theme.s5
                    ColumnLayout {
                        MicRing { active: false; Layout.preferredWidth: 160; Layout.preferredHeight: 160 }
                        AbyssText { text: "Au repos"; role: "caption"; secondary: true; Layout.alignment: Qt.AlignHCenter }
                    }
                    ColumnLayout {
                        MicRing { active: true; level: gallery.fakeLevel; Layout.preferredWidth: 160; Layout.preferredHeight: 160 }
                        AbyssText { text: "En direct"; role: "caption"; secondary: true; Layout.alignment: Qt.AlignHCenter }
                    }
                }
                Waveform { levels: gallery.history; Layout.preferredWidth: 340; Layout.preferredHeight: 48 }
                Waveform { levels: []; active: false; Layout.preferredWidth: 340; Layout.preferredHeight: 24 }
                Rectangle {
                    Layout.preferredWidth: 340; Layout.preferredHeight: 140
                    radius: Theme.radiusCard; color: Theme.bgDeep; clip: true
                    border.width: Theme.strokeThin; border.color: Theme.border
                    WaveBackground { anchors.fill: parent; anchors.topMargin: 20 }
                }
            }
        }
    }
}
