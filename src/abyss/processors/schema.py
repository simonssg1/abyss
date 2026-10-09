"""Schéma des paramètres de chaque type d'effet (génère les curseurs de l'éditeur de presets)."""

from __future__ import annotations


def _p(key, label, lo, hi, step, unit, default, kind="float"):
    return {"key": key, "label": label, "min": lo, "max": hi, "step": step, "unit": unit,
            "default": default, "kind": kind}


EFFECT_SCHEMAS: dict[str, dict] = {
    "pitch_shift": {"label": "Hauteur", "params": [_p("semitones", "Hauteur", -12, 12, 1, "demi-tons", 0)]},
    "ring_mod": {"label": "Modulation en anneau", "params": [
        _p("frequency_hz", "Fréquence", 1, 2000, 1, "Hz", 60), _p("mix", "Mélange", 0, 1, 0.01, "%", 1.0)]},
    "vocoder": {"label": "Vocodeur", "params": [
        _p("bands", "Bandes", 16, 24, 1, "", 20, "int"), _p("carrier_hz", "Porteuse", 40, 440, 1, "Hz", 110),
        _p("chord", "Accord", 0, 1, 1, "", False, "bool"), _p("mix", "Mélange", 0, 1, 0.01, "%", 1.0)]},
    "reverb": {"label": "Réverbération", "params": [
        _p("room_size", "Taille de la salle", 0, 1, 0.01, "%", 0.5), _p("wet_level", "Niveau d'effet", 0, 1, 0.01, "%", 0.33),
        _p("dry_level", "Niveau direct", 0, 1, 0.01, "%", 0.4), _p("damping", "Amortissement", 0, 1, 0.01, "%", 0.5),
        _p("width", "Largeur", 0, 1, 0.01, "%", 1.0)]},
    "distortion": {"label": "Distorsion", "params": [_p("drive_db", "Saturation", 0, 40, 0.5, "dB", 25)]},
    "chorus": {"label": "Chorus", "params": [
        _p("rate_hz", "Vitesse", 0.1, 10, 0.1, "Hz", 1.0), _p("depth", "Profondeur", 0, 1, 0.01, "%", 0.25),
        _p("centre_delay_ms", "Délai central", 1, 30, 0.5, "ms", 7.0), _p("feedback", "Réinjection", -0.95, 0.95, 0.01, "", 0.0),
        _p("mix", "Mélange", 0, 1, 0.01, "%", 0.5)]},
    "delay": {"label": "Écho", "params": [
        _p("delay_seconds", "Retard", 0.01, 1.5, 0.01, "s", 0.5), _p("feedback", "Réinjection", 0, 0.95, 0.01, "%", 0.0),
        _p("mix", "Mélange", 0, 1, 0.01, "%", 0.5)]},
    "bitcrush": {"label": "Bitcrush", "params": [_p("bit_depth", "Résolution", 2, 16, 1, "bits", 8)]},
    "highpass": {"label": "Passe-haut", "params": [_p("cutoff_frequency_hz", "Coupure", 20, 2000, 10, "Hz", 200)]},
    "lowpass": {"label": "Passe-bas", "params": [_p("cutoff_frequency_hz", "Coupure", 500, 20000, 50, "Hz", 8000)]},
    "compressor": {"label": "Compresseur", "params": [
        _p("threshold_db", "Seuil", -60, 0, 0.5, "dB", -20), _p("ratio", "Ratio", 1, 20, 0.5, ":1", 4),
        _p("attack_ms", "Attaque", 0.1, 100, 0.1, "ms", 1.0), _p("release_ms", "Relâchement", 10, 1000, 5, "ms", 100)]},
    "noise_gate": {"label": "Noise gate", "params": [
        _p("threshold_db", "Seuil", -100, 0, 0.5, "dB", -45), _p("ratio", "Ratio", 1, 20, 0.5, ":1", 10),
        _p("attack_ms", "Attaque", 0.1, 100, 0.1, "ms", 1.0), _p("release_ms", "Relâchement", 10, 1000, 5, "ms", 100)]},
    "gain": {"label": "Gain", "params": [_p("gain_db", "Gain", -24, 24, 0.5, "dB", 0)]},
}


def default_effect(kind: str) -> dict:
    eff = {"type": kind}
    for prm in EFFECT_SCHEMAS[kind]["params"]:
        eff[prm["key"]] = prm["default"]
    return eff


def complete_effect(eff: dict) -> dict:
    """Ajoute les paramètres absents (valeurs par défaut) pour que l'éditeur ait un curseur par paramètre."""
    schema = EFFECT_SCHEMAS.get(eff.get("type", ""))
    if not schema:
        return dict(eff)
    out = default_effect(eff["type"])
    out.update(eff)
    return out
