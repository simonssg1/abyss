# Abyss : changeur de voix temps réel (macOS / Windows)

Micro réel → débruitage → effets → limiteur → **micro virtuel** (Discord, jeux) + retour casque optionnel.
100 % local, effets DSP (robot, vocodeur, démon, hélium…). Voix IA (RVC/ONNX) prévue en v2.

## Installation

**macOS (Apple Silicon)**

```sh
brew install blackhole-2ch uv
# redémarre le Mac pour que BlackHole apparaisse
git clone https://github.com/simonssg1/abyss.git && cd abyss
uv sync
```

**Windows (migration)** : installe [VB-CABLE](https://vb-audio.com/Cable/) (redémarrage) et [uv](https://docs.astral.sh/uv/), puis :

```sh
gh repo clone simonssg1/abyss
cd abyss
uv sync
uv run abyss
```

## Lancement

```sh
uv run abyss                       # interface graphique
uv run abyss --list-devices        # périphériques détectés
uv run abyss --headless --preset Robot          # sans interface (Ctrl+C pour quitter)
uv run abyss --render IN.wav --preset Démon --out OUT.wav
uv run abyss --render-all samples/synthetic_voice.wav   # un fichier par preset dans renders/
```

Le micro virtuel est détecté tout seul (« BlackHole 2ch » sur macOS, « CABLE Input » sur Windows).
Raccourcis globaux : `Ctrl+Alt+1…8` = presets, `Ctrl+Alt+0` = bypass, `Ctrl+Alt+M` = retour casque
(modifiables dans `~/.abyss/config.json`).

## Réglages Discord

- Périphérique d'entrée : **BlackHole 2ch** (macOS) ou **CABLE Output** (Windows).
- **Désactive** la suppression de bruit (Krisp), l'annulation d'écho et le contrôle automatique du gain :
  ils écrasent les effets.
- Mode de saisie : détection de la voix ou push-to-talk, au choix.

## Autorisations macOS

Réglages Système → Confidentialité et sécurité, pour ton terminal (Terminal, iTerm…) :
- **Micro** (sinon aucun son en entrée, voire un blocage au démarrage) ;
- **Accessibilité** et **Surveillance de l'entrée** (pour les raccourcis globaux ; sans ça l'app
  fonctionne mais sans raccourcis).

## Conseils

- **N'utilise pas le micro des AirPods** : ouvrir leur micro fait basculer le Bluetooth en qualité
  téléphone (16 kHz). Prends le micro du Mac ou un micro USB, et garde les AirPods pour le retour.
- Le retour casque est désactivé par défaut. Ne l'active pas sur des haut-parleurs (larsen).

## Ajouter un preset

Ajoute un bloc à `presets.toml` :

```toml
[[preset]]
name = "Géant"
hotkey_index = 9          # Ctrl+Alt+9
effects = [
  { type = "pitch_shift", semitones = -9 },
  { type = "reverb", room_size = 0.6, wet_level = 0.2 },
]
```

Types disponibles : `pitch_shift` (`semitones`), `ring_mod` (`frequency_hz`, `mix`),
`vocoder` (`bands` 16–24, `carrier_hz`, `chord`, `mix`), et les effets pedalboard avec leurs
paramètres d'origine : `reverb`, `distortion`, `chorus`, `delay`, `bitcrush`, `highpass`, `lowpass`,
`compressor`, `noise_gate`, `gain`. Un effet invalide est ignoré avec un avertissement. `rvc` est réservé à la v2.

## Développement

```sh
uv run pytest
```

Voir `DECISIONS.md` pour les choix techniques et `docs/PROMPT_CLAUDE_CODE.md` pour le cahier des charges.
