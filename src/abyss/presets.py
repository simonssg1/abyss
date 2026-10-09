"""Lecture de presets.toml et construction des chaînes d'effets."""

from __future__ import annotations

import logging
import re
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from abyss.processors.base import Chain
from abyss.processors.fx import FX_TYPES, make_fx
from abyss.processors.mix import DryWet
from abyss.processors.robot import RingModulator
from abyss.processors.vocoder import ChannelVocoder

log = logging.getLogger("abyss.presets")

DEFAULT_PRESETS = Path(__file__).resolve().parents[2] / "presets.toml"
EFFECT_TYPES = FX_TYPES + ("ring_mod", "vocoder", "rvc")
CATEGORIES = ("Robot", "Sci-Fi", "Gaming", "Fun", "Ambiance", "IA")
BADGES = ("", "new", "beta")
TONE_MIN_HZ = 50.0     # « coupe-bas » au minimum = désactivé
TONE_MAX_HZ = 12000.0  # « coupe-haut » au maximum = désactivé


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-") or "preset"


@dataclass
class Preset:
    name: str
    hotkey_index: int | None
    effects: list[dict] = field(default_factory=list)
    description: str = ""
    categories: list[str] = field(default_factory=list)
    icon: str = ""
    badge: str = ""
    intensity: float = 1.0
    tone_low_hz: float = TONE_MIN_HZ
    tone_high_hz: float = TONE_MAX_HZ
    is_user: bool = False
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = slugify(self.name)


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
        preset = Preset(name, hk, kept, **_extended_fields(name, p, warnings))
        while preset.id in {q.id for q in presets}:
            preset.id += "-2"
        presets.append(preset)
    return presets, warnings


def _extended_fields(name: str, p: dict, warnings: list[str]) -> dict:
    """Champs du format étendu (tous optionnels) ; une valeur invalide reprend sa valeur par défaut."""
    out: dict = {}

    def bad(field_name: str, why: str) -> None:
        msg = f"Preset « {name} » : champ « {field_name} » ignoré ({why})"
        log.warning(msg)
        warnings.append(msg)

    for key in ("description", "icon"):
        if key in p:
            if isinstance(p[key], str):
                out[key] = p[key]
            else:
                bad(key, "texte attendu")
    if "badge" in p:
        if p["badge"] in BADGES:
            out["badge"] = p["badge"]
        else:
            bad("badge", f"valeurs possibles : {', '.join(b for b in BADGES if b)}")
    if "categories" in p:
        cats = p["categories"]
        if isinstance(cats, list) and all(isinstance(c, str) for c in cats):
            out["categories"] = [c for c in cats if c in CATEGORIES]
            if len(out["categories"]) != len(cats):
                bad("categories", f"catégories connues : {', '.join(CATEGORIES)}")
        else:
            bad("categories", "liste de textes attendue")
    for key, lo, hi in (("intensity", 0.0, 1.0), ("tone_low_hz", TONE_MIN_HZ, TONE_MAX_HZ),
                        ("tone_high_hz", TONE_MIN_HZ, TONE_MAX_HZ)):
        if key in p:
            v = p[key]
            if isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi:
                out[key] = float(v)
            else:
                bad(key, f"nombre entre {lo:g} et {hi:g} attendu")
    if out.get("tone_low_hz", TONE_MIN_HZ) >= out.get("tone_high_hz", TONE_MAX_HZ):
        bad("tone_low_hz", "doit être inférieur à tone_high_hz")
        out.pop("tone_low_hz", None)
        out.pop("tone_high_hz", None)
    return out


def preset_to_dict(p: Preset) -> dict:
    """Preset → table TOML (format étendu, seuls les champs utiles)."""
    d: dict = {"name": p.name}
    if p.hotkey_index is not None:
        d["hotkey_index"] = p.hotkey_index
    for key in ("description", "icon", "badge"):
        if getattr(p, key):
            d[key] = getattr(p, key)
    d["categories"] = list(p.categories)
    if p.intensity != 1.0:
        d["intensity"] = round(p.intensity, 3)
    if p.tone_low_hz != TONE_MIN_HZ:
        d["tone_low_hz"] = round(p.tone_low_hz, 1)
    if p.tone_high_hz != TONE_MAX_HZ:
        d["tone_high_hz"] = round(p.tone_high_hz, 1)
    d["effects"] = [dict(e) for e in p.effects]
    return d


def preset_from_dict(data: dict, sample_rate: int = 48000) -> tuple[Preset | None, list[str]]:
    """Valide une table de preset (même règles que le fichier). None si le preset est invalide."""
    presets, warnings = parse_presets({"preset": [data]}, sample_rate)
    return (presets[0] if presets else None), warnings


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


def tone_cutoffs(low_hz: float, high_hz: float, sample_rate: int) -> tuple[float, float]:
    """Fréquences réelles des filtres : aux extrémités de l'échelle, le filtre devient transparent."""
    low = 20.0 if low_hz <= TONE_MIN_HZ else float(low_hz)
    high = 0.45 * sample_rate if high_hz >= TONE_MAX_HZ else float(high_hz)
    return low, high


def build_chain(preset: Preset | None, sample_rate: int = 48000, output_gain_db: float = 0.0) -> Chain:
    """Construit une chaîne neuve (à faire hors thread audio). None = chaîne vide (bypass).

    Preset : effets → dosage dry/wet (`intensity`) → égaliseur coupe-bas / coupe-haut.
    `chain.controls` donne accès aux réglages modifiables à chaud (intensité, égaliseur).
    """
    if preset is None:
        chain = Chain([], sample_rate, output_gain_db, name="bypass")
        chain.controls = {}
        return chain
    procs = []
    for eff in preset.effects:
        params = {k: v for k, v in eff.items() if k != "type"}
        try:
            procs.append(make_effect(eff["type"], params, sample_rate))
        except (KeyError, TypeError, ValueError) as e:  # déjà validé, par sécurité
            log.warning("Effet ignoré dans « %s » : %s", preset.name, e)
    low, high = tone_cutoffs(preset.tone_low_hz, preset.tone_high_hz, sample_rate)
    drywet = DryWet(procs, sample_rate, preset.intensity)
    hp = make_fx("highpass", {"cutoff_frequency_hz": low}, sample_rate)
    lp = make_fx("lowpass", {"cutoff_frequency_hz": high}, sample_rate)
    chain = Chain([drywet, hp, lp], sample_rate, output_gain_db, name=preset.name)
    chain.controls = {"intensity": drywet, "tone_low": hp.plugin, "tone_high": lp.plugin}
    return chain


def apply_live(chain: Chain, preset: Preset) -> bool:
    """Applique intensité et égaliseur du preset à une chaîne déjà en service (sans la reconstruire)."""
    controls = getattr(chain, "controls", None)
    if not controls:
        return False
    low, high = tone_cutoffs(preset.tone_low_hz, preset.tone_high_hz, chain.sample_rate)
    controls["intensity"].mix = preset.intensity
    controls["tone_low"].cutoff_frequency_hz = low
    controls["tone_high"].cutoff_frequency_hz = high
    return True


def find_preset(presets: list[Preset], name: str) -> Preset | None:
    low = name.strip().lower()
    for p in presets:
        if p.name.lower() == low or p.id == low:
            return p
    return None
