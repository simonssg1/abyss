"""Presets perso : ~/.abyss/presets.toml, superposé aux presets par défaut du dépôt.

- Un preset du fichier perso dont l'`id` est celui d'un preset par défaut le remplace (preset modifié).
- Les autres sont des presets créés par l'utilisateur (`is_user`).
- Écriture atomique, copie `.bak` avant chaque écriture, et refus d'écrire un contenu invalide.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import shutil
import tempfile
import tomllib
from pathlib import Path

from abyss.presets import Preset, load_presets, parse_presets, preset_to_dict

log = logging.getLogger("abyss.presets")

USER_PRESETS_PATH = Path.home() / ".abyss" / "presets.toml"
HEADER = ("# Presets perso d'Abyss (écrit par l'éditeur). Superposés aux presets par défaut du dépôt :\n"
          "# un preset portant l'id d'un preset par défaut le remplace.\n")


# ----- sérialisation TOML (sous-ensemble utilisé par les presets ; pas de dépendance) -----
def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(round(v, 6))
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)  # chaînes de base TOML = échappements JSON
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_toml_value(x)}" for k, x in v.items()) + " }"
    raise TypeError(f"valeur non sérialisable : {v!r}")


def dumps_presets(entries: list[dict]) -> str:
    out = [HEADER]
    for d in entries:
        out.append("\n[[preset]]\n")
        for key, value in d.items():
            if key == "effects":
                continue
            out.append(f"{key} = {_toml_value(value)}\n")
        effects = d.get("effects", [])
        if effects:
            out.append("effects = [\n" + "".join(f"  {_toml_value(e)},\n" for e in effects) + "]\n")
        else:
            out.append("effects = []\n")
    return "".join(out)


# ----- lecture -----
def load_user_entries(path: Path | None = None) -> tuple[list[Preset], list[str]]:
    path = path or USER_PRESETS_PATH
    if not path.is_file():
        return [], []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        msg = f"Presets perso illisibles ({path}) : {e}"
        log.warning(msg)
        return [], [msg]
    presets, warnings = parse_presets(data)
    raw = [p for p in data.get("preset", []) if isinstance(p, dict) and isinstance(p.get("name"), str)]
    # L'id enregistré prime sur l'id déduit du nom (un preset renommé garde son identité).
    for preset, table in zip(presets, raw):
        if isinstance(table.get("id"), str) and table["id"]:
            preset.id = table["id"]
    return presets, warnings


def load_all_presets(defaults_path: str | Path | None = None, user_path: Path | None = None,
                     sample_rate: int = 48000) -> tuple[list[Preset], list[Preset], list[str]]:
    """→ (presets fusionnés, presets par défaut d'origine, avertissements)."""
    defaults, warnings = load_presets(defaults_path, sample_rate)
    user, uw = load_user_entries(user_path)
    merged = [copy.deepcopy(p) for p in defaults]
    index = {p.id: i for i, p in enumerate(merged)}
    for p in user:
        if p.id in index:
            p.is_user = False
            merged[index[p.id]] = p
        else:
            p.is_user = True
            merged.append(p)
    return merged, defaults, warnings + uw


# ----- écriture -----
def _entry(p: Preset) -> dict:
    d = {"id": p.id}
    d.update(preset_to_dict(p))
    return d


def _comparable(p: Preset) -> dict:
    """Forme normalisée pour comparer à un preset par défaut (paramètres complétés, nombres en float)."""
    from abyss.processors.schema import complete_effect

    d = preset_to_dict(p)
    d["effects"] = [{k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                     for k, v in complete_effect(e).items()} for e in d["effects"]]
    return d


def user_entries(presets: list[Preset], defaults: dict[str, Preset]) -> list[dict]:
    """Ce qui doit être écrit : presets perso + presets par défaut modifiés."""
    out = []
    for p in presets:
        base = defaults.get(p.id)
        if p.is_user or base is None or _comparable(p) != _comparable(base):
            out.append(_entry(p))
    return out


def save_user_presets(presets: list[Preset], defaults: dict[str, Preset], path: Path | None = None) -> tuple[bool, str]:
    """Écrit le fichier perso. → (succès, message d'erreur). N'écrase jamais un fichier valide par du contenu invalide."""
    path = path or USER_PRESETS_PATH
    entries = user_entries(presets, defaults)
    text = dumps_presets(entries)
    try:
        parsed, warnings = parse_presets(tomllib.loads(text))
    except tomllib.TOMLDecodeError as e:
        return False, f"contenu généré invalide ({e})"
    if len(parsed) != len(entries) or warnings:
        return False, warnings[0] if warnings else "preset invalide"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".presets-", suffix=".toml")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
    except OSError as e:
        return False, str(e)
    return True, ""
