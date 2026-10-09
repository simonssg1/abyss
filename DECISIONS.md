# Décisions

- Dossier du projet : `~/vocoder` plutôt que le dossier courant (`~`, le dossier personnel), pour ne pas transformer tout le home en dépôt git.
- GitHub : `gh` est actif sur le compte `sscheer1` (≠ `simonssg1`, connecté mais inactif) → aucun dépôt distant créé, travail en local ; commandes de création/push dans le README du rapport final. Pas de `git push` à la fin des phases.
- Identité git locale au dépôt : `simonssg1 <216600237+simonssg1@users.noreply.github.com>` alors que la config globale (compte pro) n'était pas vide — choix délibéré pour ne pas publier l'adresse pro sur un dépôt perso.
- Python : l'interpréteur pyenv 3.11 du système était cassé (shim) → premier `uv sync` lancé avec `UV_PYTHON_PREFERENCE=only-managed` (Python 3.11 géré par uv) ; ensuite `uv sync` simple fonctionne.
- Build backend : hatchling (layout `src/`), outil de build uniquement, pas une dépendance runtime.
- PitchShift : `pedalboard.PitchShift` rend du silence en flux (`reset=False`, testé en blocs de 256 à 8192) et a ~1 s de latence → remplacé par un pitch shift natif numpy à deux lectures de ligne à retard en fondu Hann (fenêtre 40 ms, latence ~20 ms). Son un peu « granuleux », mais temps réel.
- « Un objet Pedalboard par chaîne » : la `Chain` fusionne les effets pedalboard consécutifs dans un seul `Pedalboard` ; les processors numpy (pitch, robot, vocodeur) s'intercalent entre ces étages.
- Limiteur de fin de chaîne : `pedalboard.Limiter(threshold_db=-1)` + `np.clip` de sécurité. Note : le Limiter JUCE ajoute ~+4,7 dB sous −10 dBFS et compresse au-dessus (son « compressé »), accepté tel quel.
- Vocodeur : filtres passe-bande Butterworth d'ordre 2 ; enveloppe = redressement + passe-bas Butterworth ordre 2 à 40 Hz (≈ 15 ms) ; normalisation par gain lissé ramenant le RMS du vocodeur à celui de la voix (plafonné à ×200). Dent de scie naïve (aliasing accepté).
- Le module `vocoder/synth.py` (génération de la voix synthétique) est ajouté pour les tests et le rendu.
- Presets : format TOML `[[preset]]` avec `effects` en tableau de tables inline ; paramètres des effets pedalboard = noms des arguments pedalboard ; un `presets.toml` illisible retombe sur le seul preset « Normal ». « Démon » : réverb room_size 0.3, wet 0.15.
- Fin de chaîne : après le Limiter JUCE (qui laisse passer quelques transitoires à 1,0 sur « Démon »), un plafond doux tanh (genou 0,85 → plafond 0,98) remplace le simple `clip` : jamais d'échantillon ≥ 0,98, donc aucun écrêtage.
- Windows/WASAPI : streams ouverts avec `sd.WasapiSettings(auto_convert=True)` (mode partagé, Windows convertit la fréquence si besoin) ; 48 kHz testé via `check_*_settings`, sinon 44,1 kHz pour tous.
- Ring buffers : entrée 16 blocs, sorties 4 blocs (débordement → on jette le plus ancien), sorties amorcées avec 2 blocs de silence (niveau cible). Le retour casque est un stream 2 canaux (mono dupliqué) pour sortir des deux côtés.
- Le rendu (`--render`) passe par le même `Pipeline` que le temps réel, débruitage inclus ; WAV de sortie en float32.
- `config.py` écrit dès la phase 4 (le mode `--headless` lit les périphériques et réglages enregistrés, sinon auto-détection).
- Raccourcis macOS : si pynput signale « process not trusted » (`IS_TRUSTED` faux), le listener est arrêté et l'interface affiche le message d'autorisation ; l'app continue sans raccourcis. Des raccourcis `preset_9` existent dans la config (pour un 9e preset éventuel).
- GUI : le stream casque reste ouvert dès qu'un casque est choisi ; la case « Retour casque » ne fait qu'activer l'écriture (pas de redémarrage des streams). Option `--no-audio` (et `--quit-after S`, cachée) pour le smoke test.
- La fenêtre dépasse un peu 640 px de haut quand des avertissements sont affichés (contenu prioritaire sur la taille).
- Vérification matérielle impossible depuis cette session : l'ouverture du micro (`check_input_settings`) reste bloquée sur l'autorisation micro de macOS pour ce processus. Les streams réels sont donc non testés ; le thread de traitement et les callbacks sont testés en simulation.

## Refonte « Abyss » (2026-10-09)

- D1 (choix utilisateur) : dépôt GitHub renommé `simonssg1/vocoder` → `simonssg1/abyss` (redirection GitHub conservée), remote local mis à jour.
- D2 (choix utilisateur) : commande `vocoder` supprimée, seule `abyss` existe.
- Renommage : paquet `src/abyss`, loggers `abyss.*`, thread `abyss-dsp`. Le type d'effet `vocoder` (vocodeur à canaux) et le module `processors/vocoder.py` gardent leur nom (c'est l'effet, pas l'app).
- Config : `~/.abyss/config.json` ; au premier `load_config()`, l'ancienne `~/.vocoder/config.json` est copiée (jamais déplacée ni écrasée).
- Le dossier local du dépôt reste `~/vocoder` (non renommé : hors périmètre, il n'a pas été demandé).
