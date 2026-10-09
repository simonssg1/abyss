"""Génération d'une « voix » synthétique pour les tests et les rendus."""

from __future__ import annotations

import numpy as np


def synthetic_voice(seconds: float = 5.0, sample_rate: int = 48000, f0_start: float = 100.0,
                    f0_end: float = 220.0, seed: int = 0) -> np.ndarray:
    """Signal harmonique type voyelle « a » : f0 glissant, formants, légère AM, bruit faible."""
    n = int(seconds * sample_rate)
    t = np.arange(n) / sample_rate
    f0 = np.geomspace(f0_start, f0_end, n)
    phase = 2 * np.pi * np.cumsum(f0) / sample_rate
    formants = [(700.0, 130.0), (1220.0, 70.0), (2600.0, 160.0)]  # (Hz, largeur)
    sig = np.zeros(n)
    for k in range(1, 40):
        fk = k * f0
        amp = sum(np.exp(-0.5 * ((fk - fc) / bw) ** 2) for fc, bw in formants) + 0.05 / k
        sig += np.where(fk < 0.45 * sample_rate, amp, 0.0) * np.sin(k * phase)
    sig *= 1.0 + 0.2 * np.sin(2 * np.pi * 4.0 * t)  # légère modulation d'amplitude
    sig /= np.max(np.abs(sig))
    sig = 0.5 * sig + 0.003 * np.random.default_rng(seed).standard_normal(n)
    return sig.astype(np.float32)
