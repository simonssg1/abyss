# Mission : refonte de l'interface — l'app devient « Abyss »

L'app existe dans ce dépôt et fonctionne (moteur audio, presets, raccourcis, interface PySide6 Widgets).
Ta mission : **renommer l'app en Abyss**, **remplacer l'interface par une interface Qt Quick / QML complète fidèle à la charte graphique**, ajouter **l'aperçu audio**, **l'éditeur de presets**, **l'écran d'accueil**, et rendre l'app **lançable depuis le Bureau macOS**.

La charte graphique est l'image `docs/charte-abyss.png`. **Ouvre-la et étudie-la avant toute chose**, puis reviens-y à chaque vérification visuelle.

---

## Protocole de décision — à respecter tout au long de la mission

Je veux être consulté à chaque vraie décision. **Ne tranche pas seul ce qui me concerne.**

**C'est une décision → tu t'arrêtes et tu me poses la question :**
- tout ce qui se voit ou s'entend : mise en page, comportement, textes affichés, écart avec la charte ;
- tout nom que je verrai : commandes, fichiers de config, dépôt GitHub ;
- toute action hors du dépôt : fichiers dans `~`, Dock, Bureau, réglages système ;
- toute nouvelle dépendance ;
- toute suppression ou modification d'une fonctionnalité existante ;
- tout risque de perte de données (presets, config) ;
- toute opération GitHub autre que commit/push.

**Ce n'est pas une décision → tu choisis et tu notes une ligne dans `DECISIONS.md` :**
détails d'implémentation internes (découpage des fichiers, noms de variables, structure des classes).

**Format de chaque question** (utilise ton outil de question à choix multiples s'il est disponible) :
- 1–2 phrases de contexte ;
- 2 à 4 options, chacune avec son impact en une ligne ;
- ta recommandation en premier, marquée « (recommandé) ».

**Regroupe les questions.** Au début de chaque phase, pose en une fois toutes les questions prévisibles de la phase (4 maximum). Ensuite, ne m'interromps que pour un imprévu réel. Consigne chaque réponse dans `DECISIONS.md`.

**Points de décision déjà identifiés** (pose-les dans la phase indiquée) :

| # | Phase | Question |
|---|-------|----------|
| D1 | 1 | Renommer le dépôt GitHub `vocoder` → `abyss` (GitHub garde une redirection) ou le laisser tel quel ? |
| D2 | 1 | Garder la commande `vocoder` comme alias de `abyss`, ou la supprimer ? |
| D3 | 4 | Composition de la fenêtre en mode large : propose-moi 2 schémas ASCII. |
| D4 | 5 | Où enregistrer les presets créés ou modifiés dans l'éditeur : `presets.toml` du dépôt, ou un fichier perso `~/.abyss/presets.toml` superposé aux presets par défaut ? |
| D5 | 5 | Source sonore de l'aperçu audio (voir Phase 5). |
| D6 | 6 | Où placer le lanceur : `~/Applications` + alias Bureau seulement, ou aussi l'ajouter au Dock ? |
| D7 | 7 | Une fois la nouvelle interface validée : supprimer l'ancienne interface Widgets, ou la garder accessible via `abyss --classic` ? |

---

## Contraintes

- **Ne modifie pas le moteur temps réel** (streams, ring buffers, threads, timing). Tu peux ajouter des processors (par exemple un wrapper dry/wet) et étendre le format des presets, à condition de rester rétrocompatible.
- Qt Quick / QML via **PySide6**, déjà installé. Modules autorisés : `QtQuick`, `QtQuick.Controls`, `QtQuick.Layouts`, `QtQuick.Shapes`, `QtQuick.Effects`.
- Nouvelle dépendance Python : aucune sans passer par le protocole de décision.
- Le code d'interface doit rester multiplateforme (le PC Windows viendra ensuite). Seul le lanceur (Phase 6) est spécifique à macOS.
- Tous les tests existants doivent continuer à passer.
- Un commit + `git push` à la fin de chaque phase. Jamais de `--force`.

---

## Phase 0 — Audit et point d'étape

1. Lis le dépôt, `DECISIONS.md` et le README. Lance `uv run pytest`.
2. Fais une capture de l'interface actuelle dans `docs/screenshots/avant.png`.
3. **Point d'étape obligatoire** : présente-moi en 10 lignes maximum l'état actuel (architecture, ce qui marche, ce qui manque) et ton plan d'exécution. Attends mon « go ».

## Phase 1 — Renommage en Abyss

Pose d'abord D1 et D2.

- Paquet Python `vocoder` → `abyss`, commande `abyss`, titre de fenêtre « Abyss ».
- Dossier de config `~/.vocoder/` → `~/.abyss/`. **Migration automatique** au premier lancement : copie (ne déplace pas) l'ancienne config si la nouvelle n'existe pas.
- Mets à jour README, imports, tests et docs.
- Applique D1 et D2 selon mes réponses.

## Phase 2 — Design system QML

Arborescence suggérée :

```
src/abyss/ui/qml/
  Main.qml
  theme/Theme.qml + qmldir
  components/
  screens/
src/abyss/ui/assets/
  fonts/
  icons/
  icon/
```

**Theme.qml** — singleton contenant tous les jetons de design. Aucune couleur ni taille codée en dur ailleurs.

Couleurs :

| Jeton | Valeur | Usage |
|-------|--------|-------|
| `bgDeep` | `#0B1220` | fond des écrans |
| `principal` | `#355070` | fond, surfaces |
| `surface` | `#2A3B5E` | cartes, champs |
| `accent` | `#06D6A0` | boutons, liens, icônes |
| `textPrimary` | `#E2E8FF` | titres, contenu |
| `textSecondary` | `#8BA0C6` | labels, descriptions |
| `indigo` | `#6366F1` | dégradé secondaire, badge Bêta |
| `danger` | rouge cohérent avec la notification « Erreur » de la charte | erreurs |

Autres jetons :
- dégradé principal `#355070 → #06D6A0` ;
- dégradé secondaire `#6366F1 → #06D6A0` ;
- rayons : cartes 16, boutons 12, puces 999 ;
- espacements : 4 / 8 / 12 / 16 / 24 / 32 ;
- durées d'animation : 150 / 250 ms, courbe `OutCubic`.

**Typo : Inter.** Télécharge-la depuis le dépôt officiel `rsms/inter` (licence SIL OFL), place-la dans `assets/fonts/` et charge-la avec `QFontDatabase.addApplicationFont`. Prévois un repli sur la police système.
- H1 : 32 px Medium.
- H2 : 20 px Medium.
- Body : 16 px Regular.
- Caption : 12 px Regular.
- Libellés de section : capitales espacées, comme « PALETTE DE COULEURS » dans la charte.

**Icônes** : jeu **Lucide** (licence ISC) téléchargé en SVG dans `assets/icons/`. Il faut au minimum : mic, mic-off, play, pause, x, chevron-right, chevron-down, chevron-left, settings, search, more-horizontal, check, alert-triangle, plus, trash, copy. Les icônes sont colorées par le thème.

**Composants** (un fichier chacun, fidèles à la charte) :
- `AbyssButton` : variantes `primary` (plein accent, texte sombre), `secondary` (contour et texte accent), `tertiary` (contour neutre), flèche optionnelle à droite ;
- `IconButton` rond : variantes actif (plein accent), neutre, coupé (micro barré), menu (« … ») ;
- `AbyssToggle` ;
- `AbyssSlider` simple avec valeur en % à droite ;
- `RangeSlider` à deux poignées (« Égaliseur ») ;
- `SearchField` ;
- `Chip` sélectionnable ;
- `Badge` : variantes Nouveau (plein accent), Bêta (indigo), Actif (point accent), Bientôt (point gris) ;
- `PresetListItem` : icône sur fond dégradé, nom, description courte, chevron, badge et raccourci optionnels ;
- `PresetCard` : icône, nom, sous-titre, bouton lecture rond ;
- `Toast` : variantes succès (icône check sur cercle accent) et erreur (triangle), titre, texte, bouton de fermeture, disparition automatique ;
- `MicRing` : grand anneau lumineux autour d'un micro, arc dégradé accent, halo via `MultiEffect`. Il pulse avec le niveau de sortie. Au repos, l'anneau est sombre et immobile ;
- `Waveform` : barres verticales centrées alimentées par l'historique du niveau d'entrée ;
- `WaveBackground` : vagues superposées en bas d'écran (`QtQuick.Shapes`, dégradés bleu → turquoise, ondulation lente) ;
- `Logo` : micro stylisé et arcs, avec le mot « Abyss ».

**Galerie** : `abyss --gallery` ouvre un écran qui affiche tous les composants dans tous leurs états, organisé comme la charte. C'est ton banc de vérification visuelle.

## Phase 3 — Pont Python ↔ QML

- Un `AppController` (`QObject`) exposé au QML, avec :
  - `Property` + signaux de notification : `live` (bool), `bypass`, `outputMuted`, `activePresetId`, `inputLevel`, `outputLevel`, `sessionSeconds`, `latencyMs`, `xruns`, `hotkeysOk`, `denoiseOn`, `denoiseThreshold`, `monitorOn`, `monitorVolume`, `outputGain`, les listes de périphériques et les périphériques choisis ;
  - `Slot` : démarrer/arrêter le direct, choisir un preset, régler un paramètre, prévisualiser, etc.
- `PresetModel` (`QAbstractListModel`), avec les rôles : id, name, description, category, icon, badge, hotkey, intensity, toneLow, toneHigh, effects, isUser, enabled. Prévois un proxy de filtrage par catégorie et par texte de recherche.
- Les niveaux et le chrono sont poussés au QML **au maximum à 30 Hz**. Les raccourcis globaux passent par des signaux Qt, comme aujourd'hui.
- Erreurs → signal `toast(kind, title, message)` : BlackHole introuvable, permission micro ou raccourcis refusée, périphérique débranché, xruns en hausse.

## Phase 4 — Écrans et navigation

Format : fenêtre **verticale par défaut (420 × 780, minimum 380 × 680)**, **redimensionnable en large**. Au-delà de **760 px** de largeur, bascule en mode large selon D3 (pose D3 au début de la phase). La fenêtre mémorise sa taille et sa position.

Navigation par `StackView` en mode vertical. En-tête : retour (si besoin), logo « Abyss » au centre, roue des réglages à droite, comme sur la maquette.

1. **Accueil** (affiché à chaque lancement, désactivable dans Réglages) :
   - logo, « Abyss », phrase « Transforme ta voix en infinies possibilités. » ;
   - bouton principal « Commencer » ;
   - vagues en bas d'écran ;
   - au-dessus du bouton, une **checklist de démarrage** à 3 lignes qui passent en vert quand c'est bon : micro virtuel détecté (BlackHole / CABLE Input), accès au micro, raccourcis clavier actifs. Une ligne en échec affiche une aide d'une phrase.
2. **Direct** (écran principal) :
   - menu « Preset actuel » (icône, nom, chevron) qui ouvre la liste des voix ;
   - `MicRing` au centre : un clic démarre ou arrête le direct ;
   - `Waveform` en dessous, puis le chrono de session `00:00` ;
   - en bas : bouton rond « couper la sortie » (x) et bouton principal rond « bypass » (pause/lecture) ;
   - badge « Actif » quand le direct tourne ;
   - slider Intensité rapide pour le preset actif.
3. **Voix** (bibliothèque) :
   - `SearchField`, puces de catégorie (Toutes, Robot, Sci-Fi, Gaming, Fun, Ambiance, IA) ;
   - liste de `PresetListItem` avec le raccourci affiché ;
   - bouton « + Nouveau preset » ;
   - une entrée « Voix IA » grisée avec le badge **Bientôt** (catégorie IA), non cliquable.
4. **Détail / Éditeur de preset** :
   - `PresetCard` en tête, avec le bouton lecture (aperçu, Phase 5) ;
   - Intensité (dosage dry/wet global du preset) ;
   - Égaliseur à deux poignées (coupe-bas / coupe-haut, 50 Hz – 12 kHz) ;
   - catégories éditables en puces ;
   - nom et description ;
   - liste des effets du preset : chaque effet affiche ses paramètres en sliders, générés depuis un **schéma de paramètres** (min, max, pas, unité) déclaré pour chaque type d'effet. Possibilité d'ajouter, retirer et réordonner les effets ;
   - actions : Enregistrer, Dupliquer, Supprimer (preset perso uniquement), Réinitialiser (preset par défaut uniquement) ;
   - un preset créé reçoit le badge **Nouveau** ;
   - modifications appliquées en direct si ce preset est actif.
5. **Réglages** :
   - périphériques (micro, micro virtuel, casque) ;
   - débruitage et seuil ;
   - retour casque et volume, avec l'avertissement larsen ;
   - gain de sortie ;
   - raccourcis : affichage et état de la permission ;
   - « Afficher l'accueil au lancement » ;
   - à propos : version, lien vers le dépôt.

Exemples de catégories pour les presets par défaut :
- Robot : Robot, Vocodeur ;
- Sci-Fi : Alien, Vocodeur ;
- Gaming : Démon, Talkie-walkie ;
- Fun : Hélium ;
- Ambiance : Cathédrale.

Le preset Normal n'a pas de catégorie.

Format des presets étendu, rétrocompatible : `description`, `categories` (liste), `icon`, `badge`, `intensity` (0–1, défaut 1), `tone_low_hz`, `tone_high_hz`. Un preset ancien format se charge sans erreur.

## Phase 5 — Aperçu audio et persistance de l'éditeur

Pose d'abord D4 et D5.

- **Aperçu** :
  - rend un court extrait (≤ 5 s) à travers une **instance séparée** de la chaîne du preset, hors du thread audio ;
  - le joue **uniquement dans le casque, jamais dans le micro virtuel** : mes amis ne doivent pas l'entendre ;
  - le bouton lecture devient pause pendant la lecture ;
  - si le retour casque n'est pas configuré, affiche un toast explicatif.
- **Options à me proposer pour D5** :
  - (a) un fichier `samples/preview.wav` que j'enregistre avec ma voix, avec repli sur `synthetic_voice.wav` ;
  - (b) les 5 dernières secondes captées par le micro, gardées en mémoire uniquement, jamais écrites sur disque ;
  - (c) les deux, au choix dans Réglages.
- **Persistance** :
  - selon D4 ;
  - écriture atomique ;
  - sauvegarde `.bak` avant chaque écriture ;
  - un preset invalide n'écrase jamais un fichier valide.

## Phase 6 — Icône et lancement depuis le Bureau macOS

Pose d'abord D6.

**1. Icône** : `assets/icon/abyss.svg`, en reprenant « Icône principale (fond sombre) » de la charte :
- carré arrondi sombre (`#0B1220` → `#2A3B5E`) ;
- capsule de micro claire ;
- arcs turquoise `#06D6A0` de part et d'autre ;
- léger halo.

Génère les PNG (16 à 1024 px) avec `QSvgRenderer` de PySide6, puis `Abyss.icns` avec `iconutil` (outil intégré à macOS). Utilise aussi cette icône comme icône de fenêtre.

**2. Lanceur** : `scripts/build_macos_launcher.sh` construit `~/Applications/Abyss.app`.
- `Info.plist` contient :
  - `CFBundleName` = « Abyss » ;
  - `CFBundleIdentifier` = `com.simonssg1.abyss` ;
  - `CFBundleIconFile` ;
  - `NSMicrophoneUsageDescription` = « Abyss utilise ton micro pour transformer ta voix en temps réel. » ;
  - la version.
- `Contents/MacOS/abyss` est un script bash qui fait `exec <chemin absolu de uv> run --project <chemin absolu du dépôt> abyss`. Les deux chemins absolus sont résolus au moment du build, car une app lancée depuis le Finder n'hérite pas du PATH du terminal. Les logs vont dans `~/.abyss/logs/launcher.log`.
- Signature ad hoc : `codesign --force --deep -s - Abyss.app`.
- Alias sur le Bureau (via `osascript` / Finder), et Dock selon D6.
- Le script est relançable sans effet de bord : il remplace l'ancienne app proprement.

Comme le lanceur exécute toujours le code actuel du dépôt, il n'y a pas besoin de reconstruire l'app après une modification du code.

**3. Instance unique** : si Abyss tourne déjà, un second lancement remet la fenêtre existante au premier plan (`QLocalServer` / `QLocalSocket`).

**4. Permissions** :
- vérifie au premier lancement depuis le lanceur à quel nom macOS attribue les permissions micro et Accessibilité / Surveillance de l'entrée (Abyss ou Python) ;
- documente le résultat exact dans le README.

## Phase 7 — Vérification et finitions

Pose D7 une fois que tout le reste est vert.

1. `uv run pytest` vert. Ajoute des tests pour :
   - le `PresetModel` et son filtrage ;
   - le chargement des presets ancien et nouveau format ;
   - la persistance de l'éditeur (écriture atomique, `.bak`, refus d'un preset invalide) ;
   - le fait que l'aperçu n'écrit jamais dans le buffer du micro virtuel ;
   - la migration de config.
2. Chargement QML **sans aucun warning** : transforme les warnings QML en échec pendant les tests.
3. **Vérification visuelle**. Avec `QT_QPA_PLATFORM=offscreen`, capture chaque écran (Accueil, Direct au repos, Direct actif, Voix, Éditeur, Réglages, Galerie) en 420 × 780 **et** 1200 × 780 dans `docs/screenshots/`. Ouvre chaque capture et compare-la à `docs/charte-abyss.png` sur ces points :
   - couleurs ;
   - typographie ;
   - rayons et espacements ;
   - lisibilité du texte secondaire ;
   - aucun texte tronqué ni élément qui déborde.

   Corrige, puis recommence. **3 passes maximum par écran.** Si un écart persiste, liste-le dans le rapport plutôt que de boucler.
4. `git diff` sur le moteur audio : seuls les imports liés au renommage ont changé.
5. README mis à jour : captures d'écran, construction du lanceur, permissions macOS, usage de l'éditeur et de l'aperçu.

## Rapport final

1. Les captures clés (chemins).
2. Les décisions prises (D1 à D7 et les imprévus).
3. Les écarts restants avec la charte.
4. Comment lancer Abyss : depuis le Bureau, et en ligne de commande.
5. Les limites connues et les pistes pour la version Windows.
