"""Lecture de presets.toml et construction des chaînes d'effets."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from vocoder.processors.base import Chain
from vocoder.processors.fx import FX_TYPES, make_fx
from vocoder.processors.robot import RingModulator
from vocoder.processors.vocoder import ChannelVocoder

log = logging.getLogger("vocoder.presets")

DEFAULT_PRESETS = Path(__file__).resolve().parents[2] / "presets.toml"
EFFECT_TYPES = FX_TYPES + ("ring_mod", "vocoder", "rvc")


@dataclass
class Preset:
    name: str
    hotkey_index: int | None
    effects: list[dict] = field(default_factory=list)


def make_effect(kind: str, params: dict, sample_rate: int):
    if kind == "ring_mod":
        return RingModulator(sample_rate=sample_rate, **params)
    if kind == "vocoder":
        return ChannelVocoder(sample_rate=sample_rate, **params)
    if kind in FX_TYPES:
        return make_fx(kind, params, sample_rate)
    raise KeyError(kind)


def _check_effect(preset_name: str, i: int, eff, sample_rate: int, warnings: list[str]) -> dict | None:
    def warn(msg: str) -> None:
        text = f"Preset « {preset_name} », effet #{i + 1} ignoré : {msg}"
        log.warning(text)
        warnings.append(text)

    if not isinstance(eff, dict) or not isinstance(eff.get("type"), str):
        warn("table avec un champ « type » attendue")
        return None
    kind = eff["type"]
    params = {k: v for k, v in eff.items() if k != "type"}
    if kind == "rvc":
        warn("type « rvc » disponible en v2")
        return None
    if kind not in EFFECT_TYPES:
        warn(f"type inconnu « {kind} » (types valides : {', '.join(EFFECT_TYPES)})")
        return None
    try:
        make_effect(kind, params, sample_rate)  # validation des paramètres
    except (TypeError, ValueError) as e:
        warn(f"paramètres invalides pour « {kind} » ({e})")
        return None
    return eff


def parse_presets(data: dict, sample_rate: int = 48000) -> tuple[list[Preset], list[str]]:
    warnings: list[str] = []
    presets: list[Preset] = []
    raw = data.get("preset", [])
    if not isinstance(raw, list):
        raw = []
        warnings.append("presets.toml : [[preset]] attendu")
    for n, p in enumerate(raw):
        name = p.get("name") if isinstance(p, dict) else None
        if not isinstance(name, str) or not name.strip():
            msg = f"Preset #{n + 1} ignoré : champ « name » manquant ou invalide"
            log.warning(msg)
            warnings.append(msg)
            continue
        hk = p.get("hotkey_index")
        effects = p.get("effects", [])
        if (hk is not None and (not isinstance(hk, int) or isinstance(hk, bool) or not 0 <= hk <= 9)) \
                or not isinstance(effects, list):
            msg = f"Preset « {name} » ignoré : hotkey_index (entier 0–9) ou effects (liste) invalide"
            log.warning(msg)
            warnings.append(msg)
            continue
        kept = [e for i, e in enumerate(effects)
                if _check_effect(name, i, e, sample_rate, warnings) is not None]
        presets.append(Preset(name, hk, kept))
    return presets, warnings


def load_presets(path: str | Path | None = None, sample_rate: int = 48000) -> tuple[list[Preset], list[str]]:
    path = Path(path) if path else DEFAULT_PRESETS
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        msg = f"Impossible de lire {path} : {e} — seul le preset « Normal » est disponible"
        log.warning(msg)
        return [Preset("Normal", 1, [])], [msg]
    presets, warnings = parse_presets(data, sample_rate)
    if not presets:
        presets = [Preset("Normal", 1, [])]
    return presets, warnings


def build_chain(preset: Preset | None, sample_rate: int = 48000, output_gain_db: float = 0.0) -> Chain:
    """Construit une chaîne neuve (à faire hors thread audio). None = chaîne vide (bypass)."""
    procs = []
    if preset is not None:
        for eff in preset.effects:
            params = {k: v for k, v in eff.items() if k != "type"}
            try:
                procs.append(make_effect(eff["type"], params, sample_rate))
            except (KeyError, TypeError, ValueError) as e:  # déjà validé, par sécurité
                log.warning("Effet ignoré dans « %s » : %s", preset.name, e)
    return Chain(procs, sample_rate, output_gain_db, name=preset.name if preset else "bypass")


def find_preset(presets: list[Preset], name: str) -> Preset | None:
    low = name.strip().lower()
    for p in presets:
        if p.name.lower() == low:
            return p
    return None
