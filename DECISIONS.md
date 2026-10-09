# Décisions

- Dossier du projet : `~/vocoder` plutôt que le dossier courant (`~`, le dossier personnel), pour ne pas transformer tout le home en dépôt git.
- GitHub : `gh` est actif sur le compte `sscheer1` (≠ `simonssg1`, connecté mais inactif) → aucun dépôt distant créé, travail en local ; commandes de création/push dans le README du rapport final. Pas de `git push` à la fin des phases.
- Identité git locale au dépôt : `simonssg1 <216600237+simonssg1@users.noreply.github.com>` alors que la config globale (compte pro) n'était pas vide — choix délibéré pour ne pas publier l'adresse pro sur un dépôt perso.
- Python : l'interpréteur pyenv 3.11 du système était cassé (shim) → premier `uv sync` lancé avec `UV_PYTHON_PREFERENCE=only-managed` (Python 3.11 géré par uv) ; ensuite `uv sync` simple fonctionne.
- Build backend : hatchling (layout `src/`), outil de build uniquement, pas une dépendance runtime.
