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
