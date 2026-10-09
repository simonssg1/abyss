# Mission : construire « Vocoder » v1 en une seule passe, en autonomie

Tu vas construire de A à Z un changeur de voix temps réel en Python, dans le dossier courant.
Travaille **en autonomie complète** : ne me pose aucune question. Quand un choix n'est pas couvert ici, prends la décision la plus simple et robuste, et note-la dans `DECISIONS.md` (une ligne par décision).
Ne me rends la main que lorsque **toutes les étapes de vérification (Phase 6) passent**.

Commence par créer une todo list avec les phases ci-dessous, puis exécute-les dans l'ordre (Phase 0 à Phase 6). À la fin de chaque phase : un commit (message court en français, préfixé `feat:`, `test:`, `docs:` ou `chore:`) puis `git push`.

---

## Contexte

- Usage personnel, 100 % local, gratuit. Parler avec une voix transformée sur Discord / en jeu.
- Machine de dev : macOS Apple Silicon (M1/M2). Cible finale : Windows avec GPU AMD Radeon. **Le même code doit tourner sur les deux.**
- L'app ne crée **aucun driver audio**. Elle écrit dans un câble virtuel déjà installé :
  - macOS : l'app écrit dans **« BlackHole 2ch »**, Discord lit « BlackHole 2ch »
  - Windows : l'app écrit dans **« CABLE Input »** (VB-CABLE), Discord lit « CABLE Output »

```
Micro réel ──> [débruitage → chaîne d'effets → limiteur] ──┬──> Micro virtuel ──> Discord / jeux
                                                            └──> Casque (retour, optionnel)
```

## Contraintes techniques non négociables

- Python **3.11**, projet **uv** (`pyproject.toml`, `.python-version`), lancement par `uv run vocoder`.
- Dépendances autorisées : `sounddevice`, `numpy`, `scipy`, `pedalboard`, `PySide6`, `pynput`. Dev : `pytest`. N'en ajoute aucune autre.
- **Pas de PyTorch.** L'IA (v2, hors périmètre) passera plus tard par ONNX Runtime ; tu prépares seulement les emplacements.
- Aucune allocation ni traitement lourd dans les callbacks audio.
- Aucune manipulation de widget Qt hors du thread principal.

## Arborescence attendue

```
pyproject.toml  .python-version  presets.toml  README.md  DECISIONS.md
src/vocoder/
  __main__.py            # CLI + GUI
  audio/engine.py        # streams, thread de traitement
  audio/ringbuffer.py
  audio/devices.py       # listing, filtrage host API, auto-détection
  processors/base.py     # Protocol Processor, Chain, adaptateur de blocs, crossfade
  processors/fx.py       # wrappers pedalboard
  processors/robot.py    # modulation en anneau
  processors/vocoder.py  # vocodeur à canaux
  processors/denoise.py  # passe-haut + noise gate
  processors/rvc.py      # STUB v2
  presets.py             # presets.toml -> Chain
  hotkeys.py             # pynput -> signaux Qt
  config.py              # ~/.vocoder/config.json
  gui/main_window.py
models/rvc/.gitkeep  models/shared/.gitkeep  samples/  renders/  tests/
```

---

## Phase 0 — Setup Git et GitHub

Le dépôt distant se crée avec le CLI GitHub (`gh`) sur mon compte personnel **`simonssg1`**.

1. Vérifie les prérequis : `git --version`, `gh --version`, `gh auth status`.
   - Si `gh` est authentifié sur un **autre compte** que `simonssg1`, ne crée rien : signale-le dans `DECISIONS.md`, travaille en local, et donne-moi les commandes à lancer dans le rapport final.
   - Si `gh` n'est pas authentifié : même chose (travail en local, commandes dans le rapport). Ne tente jamais de t'authentifier toi-même.
2. `git init -b main` dans le dossier courant (sauf si c'est déjà un dépôt).
3. Identité Git **locale au dépôt** (ne touche pas à la config globale) : si `git config user.name` est vide, utilise le login GitHub (`gh api user --jq .login`) ; si `git config user.email` est vide, utilise l'adresse noreply `<id>+<login>@users.noreply.github.com` (`gh api user --jq .id`).
4. Crée `.gitignore` : environnements Python (`.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`), `.DS_Store`, `renders/`, `samples/*.wav` **sauf** `samples/synthetic_voice.wav`, `models/**/*.onnx`, `models/**/*.pth`, `models/**/*.index` (garder les `.gitkeep`). Aucun fichier audio lourd ni modèle ne doit jamais être commité.
5. Vérifie si le dépôt existe déjà : `gh repo view simonssg1/vocoder`.
   - S'il n'existe pas : `gh repo create simonssg1/vocoder --private --source=. --remote=origin --description "Changeur de voix temps réel perso (macOS/Windows) — effets DSP, IA RVC en v2"`.
   - S'il existe déjà : ne l'écrase pas et n'y pousse rien ; crée `simonssg1/vocoder-app` à la place et note-le dans `DECISIONS.md`.
6. Copie ce prompt dans le dépôt sous `docs/PROMPT_CLAUDE_CODE.md` (traçabilité), crée un `README.md` provisoire d'une ligne, commit `chore: initialisation du projet`, puis `git push -u origin main`.
7. Ajoute les topics du dépôt : `gh repo edit --add-topic voice-changer,audio,python,realtime`.

Règles pour toute la suite : ne force jamais un push (`--force` interdit), ne réécris pas l'historique, ne change pas la visibilité du dépôt.

## Phase 1 — Squelette et dépendances

1. Crée le projet uv, l'arborescence, le point d'entrée `vocoder = "vocoder.__main__:main"`.
2. `uv sync` doit passer. Si un paquet n'a pas de wheel pour la plateforme, documente-le dans `DECISIONS.md` et trouve une solution sans ajouter de dépendance.

## Phase 2 — Processors (cœur DSP, testable sans matériel audio)

Interface :

```python
class Processor(Protocol):
    name: str
    preferred_block: int | None   # None = toute taille ; RVC (v2) demandera ~0,3–0,5 s
    latency_samples: int
    def process(self, block: np.ndarray) -> np.ndarray: ...  # float32 mono 1D, même longueur en sortie
    def reset(self) -> None: ...
```

- `Chain` : liste ordonnée de processors. Si un processor a un `preferred_block`, la chaîne l'enveloppe dans un adaptateur qui accumule / redécoupe (latence ajoutée comptée dans `latency_samples`).
- Fin de chaîne systématique : gain de sortie + limiteur (`pedalboard.Limiter`), jamais d'échantillon hors [-1, 1].
- **fx.py** : wrappers en flux autour de PitchShift, Reverb, Distortion, Chorus, Delay, Bitcrush, HighpassFilter, LowpassFilter, Compressor, NoiseGate, Gain. Un objet `Pedalboard` par chaîne, appelé avec `reset=False` à chaque bloc. pedalboard attend un tableau float32 de forme `(canaux, échantillons)` : passe `block[np.newaxis, :]` et récupère `[0]`.
- **robot.py** : modulation en anneau, sinus à fréquence réglable, **phase conservée entre blocs**, paramètre `mix`.
- **vocoder.py** : vocodeur à canaux. Modulateur = voix ; porteuse générée en interne = dent de scie (ou accord de 3 dents de scie : fondamentale, quinte, octave), phase conservée entre blocs. 16 à 24 bandes log entre 100 et 8 000 Hz, filtres passe-bande `scipy.signal.butter(..., output="sos")` appliqués avec `sosfilt` et **état `zi` conservé** par bande, pour la voix et pour la porteuse. Enveloppe par bande : redressement + passe-bas ~15 ms (avec état). Somme, normalisation, paramètre `mix`. Paramètres : `bands`, `carrier_hz`, `chord`, `mix`.
- **denoise.py** : passe-haut 80 Hz + NoiseGate (seuil défaut −45 dB, attack 2 ms, release 120 ms), seuil modifiable à chaud.
- **rvc.py** : `RVCProcessor` qui lève `NotImplementedError`, avec une docstring décrivant le pipeline v2 prévu : fenêtre glissante 0,3–0,5 s avec contexte + fondu SOLA → rééchantillonnage 48 k→16 k → ContentVec (ONNX) → f0 RMVPE (ONNX) + transposition → modèle RVC (ONNX) → retour à 48 k. Providers : `CoreMLExecutionProvider`/`CPUExecutionProvider` (Mac), `DmlExecutionProvider` (Windows AMD). Fichiers attendus : `models/shared/contentvec.onnx`, `models/shared/rmvpe.onnx`, `models/rvc/<voix>/model.onnx` + `voice.toml`.

Écris les tests de cette phase tout de suite (voir Phase 6) et fais-les passer avant de continuer.

## Phase 3 — Presets

`presets.toml` lu avec `tomllib`. Chaque preset : `name`, `hotkey_index`, liste ordonnée `effects` (type + paramètres). Contenu par défaut :

| # | Nom | Recette |
|---|-----|---------|
| 1 | Normal | aucun effet (débruitage seul) |
| 2 | Robot | modulation en anneau 60 Hz mix 1.0 + bitcrush 10 bits |
| 3 | Vocodeur | vocodeur 20 bandes, porteuse 110 Hz, accord activé |
| 4 | Démon | pitch −6 demi-tons, distorsion 12 dB, passe-bas 4 kHz, petite réverb |
| 5 | Hélium | pitch +7 demi-tons |
| 6 | Talkie-walkie | passe-haut 400 Hz, passe-bas 3 kHz, distorsion 15 dB, bitcrush 8 bits |
| 7 | Cathédrale | réverb room_size 0.9, wet 0.4 |
| 8 | Alien | pitch +4, chorus, modulation en anneau 400 Hz mix 0.3 |

- Un preset ou un effet invalide est ignoré avec un avertissement clair, sans crash.
- Le type d'effet `rvc` est reconnu mais ignoré en v1 avec le message « disponible en v2 ».

## Phase 4 — Moteur audio et CLI

- 48 000 Hz, mono float32 interne, blocs de 256. Si un périphérique refuse 48 kHz, ouvre **tous** les streams à 44 100 Hz.
- **Trois streams indépendants**, pas de stream duplex multi-périphériques :
  1. `InputStream` micro : le callback **copie** `indata[:, 0]` dans le ring buffer d'entrée, rien d'autre.
  2. **Thread de traitement** (réveillé par `threading.Event`, pas de boucle active) : lit l'entrée, applique la chaîne, écrit dans deux ring buffers de sortie.
  3. `OutputStream` micro virtuel (2 canaux, mono dupliqué) et `OutputStream` casque : les callbacks lisent leur ring buffer.
- Ring buffer préalloué, protégé par un `Lock`. Niveau cible ≈ 2 blocs. Sous-remplissage → silence ; débordement → jeter les plus anciens. Compte les xruns.
- Changement de preset : construction de la nouvelle chaîne hors thread audio, échange atomique, **crossfade 20 ms** entre l'ancienne et la nouvelle sortie.
- Bypass : chaîne vide (débruitage conservé s'il est actif).
- Métriques partagées : RMS entrée/sortie, latence estimée (buffers + `stream.latency`), xruns.
- `devices.py` : sur Windows, ne garder que les périphériques **Windows WASAPI** ; sur macOS, Core Audio. Auto-détection : sortie virtuelle = nom contenant « BlackHole » ou « CABLE Input » ; entrée = micro par défaut ; casque = sortie par défaut du système.
- CLI :
  - `vocoder` → GUI
  - `vocoder --list-devices`
  - `vocoder --render IN.wav --preset NOM --out OUT.wav` (même chaîne, par blocs de 256, rééchantillonne l'entrée avec `scipy.signal.resample_poly` si besoin ; lecture/écriture wav via `scipy.io.wavfile`)
  - `vocoder --render-all IN.wav` → un fichier par preset dans `renders/`
  - `vocoder --headless --preset NOM` (Ctrl+C pour quitter proprement)

## Phase 5 — Raccourcis, config et interface

**Raccourcis** (`hotkeys.py`) :
- `pynput.keyboard.GlobalHotKeys` dans son propre thread ; les callbacks émettent des signaux Qt.
- Défauts : `<ctrl>+<alt>+1` à `8` = presets, `<ctrl>+<alt>+0` = bypass, `<ctrl>+<alt>+m` = retour casque. Modifiables dans la config.
- Si le listener échoue (permissions macOS), l'app continue sans raccourcis et affiche : « Autorise ton terminal dans Réglages Système → Confidentialité et sécurité → Accessibilité et Surveillance de l'entrée ».

**Config** : `~/.vocoder/config.json` — périphériques (par nom), dernier preset, débruitage on/off + seuil, retour on/off + volume, gain de sortie, raccourcis. Écriture atomique (fichier temporaire + rename).

**Interface PySide6** (fenêtre ~420×640, sobre, lisible en thème sombre comme clair) :
1. **Périphériques** : 3 listes (micro, micro virtuel, casque) + bouton rafraîchir. Tout changement redémarre proprement les streams.
2. **Voix** : grille de boutons des presets, raccourci affiché sur chaque bouton, preset actif surligné.
3. **Contrôles** : Bypass, Débruitage + curseur de seuil, Retour casque + volume, Gain de sortie.
4. **Statut** : VU-mètres entrée/sortie, latence (ms), xruns, état des raccourcis.
- Avertissement visible si le périphérique de retour ressemble à des haut-parleurs (« Speakers », « Haut-parleurs », « MacBook ») : risque de larsen. Retour désactivé par défaut.
- Rafraîchissement par `QTimer` ~30 Hz qui lit les métriques partagées.
- Fermeture : arrêt propre des streams, du thread de traitement et du listener pynput, sauvegarde de la config.

## Phase 6 — Vérification (obligatoire, boucle jusqu'au vert)

Tu ne peux pas écouter l'audio : vérifie par le code. Corrige et relance jusqu'à ce que tout passe.

1. `uv sync` sans erreur.
2. `uv run pytest` vert, avec au minimum :
   - chaque processor en flux (blocs de 256 sur 5 s) : même longueur, float32, aucun NaN/inf ;
   - sortie de chaîne complète toujours dans [-1, 1] (avec un signal d'entrée à +6 dB) ;
   - continuité de phase du robot et de la porteuse du vocodeur entre blocs (pas de saut à la frontière) ;
   - le vocodeur produit un signal non nul sur un signal voisé et reste stable sur 10 s ;
   - pour les effets avec latence (PitchShift), compare après la période de chauffe ;
   - ring buffer : sous-remplissage, débordement, compteur de xruns ;
   - échange de chaîne pendant un traitement en cours, sans exception, avec crossfade ;
   - parsing de `presets.toml`, y compris un preset invalide et un effet `rvc`.
3. Génère `samples/synthetic_voice.wav` (5 s, 48 kHz : signal harmonique type voyelle, f0 glissant de 100 à 220 Hz, légère modulation d'amplitude, bruit faible), puis `uv run vocoder --render-all samples/synthetic_voice.wav` → 8 fichiers dans `renders/`, aucun silencieux (RMS > seuil), aucun écrêté.
4. `uv run vocoder --list-devices` s'exécute sans erreur.
5. Smoke test GUI : avec `QT_QPA_PLATFORM=offscreen`, ouvre la fenêtre, attends 2 s, ferme-la, sans exception (les streams peuvent être désactivés via une option de test si aucun périphérique n'est disponible).
6. Rédige `README.md` (court, en français) : installation (`brew install blackhole-2ch uv` + redémarrage ; VB-CABLE sur Windows), lancement, réglages Discord (entrée = BlackHole 2ch / CABLE Output ; **désactiver suppression de bruit Krisp, annulation d'écho et gain automatique**), autorisations macOS (micro + Accessibilité + Surveillance de l'entrée), ne pas utiliser un micro AirPods (bascule en basse qualité), migration Windows (`gh repo clone simonssg1/vocoder`, `uv sync`, `uv run vocoder`), comment ajouter un preset.
7. Git : `git status` propre, aucun fichier ignoré n'a été commité (`git ls-files | grep -E '\.(onnx|pth|index)$'` ne renvoie rien ; aucun `.wav` sauf `samples/synthetic_voice.wav`), dernier commit poussé (`git status -sb` n'indique pas d'avance sur `origin/main`).

## Hors périmètre — n'implémente pas

Soundboard, voix IA (au-delà du stub), réduction de bruit neuronale, packaging .app/.exe, mises à jour automatiques.

---

## Rapport final attendu

Quand tout est vert, rends-moi un rapport court :
0. L'URL du dépôt GitHub et le nombre de commits poussés — ou, si la Phase 0 n'a pas pu se connecter à GitHub, les commandes exactes à lancer pour créer le dépôt et pousser.
1. Ce qui fonctionne (une ligne par fonctionnalité).
2. Résultats des tests (nombre passés).
3. Les décisions de `DECISIONS.md` qui méritent mon attention.
4. Les 3 commandes à lancer pour tester moi-même dans l'ordre (rendu de fichiers, liste des périphériques, GUI).
5. Les limites connues.
