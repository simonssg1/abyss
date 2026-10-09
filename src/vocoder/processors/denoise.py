"""Débruitage léger : passe-haut 80 Hz + noise gate (seuil modifiable à chaud)."""

from __future__ import annotations

import numpy as np
from pedalboard import HighpassFilter, NoiseGate, Pedalboard


class Denoiser:
    name = "denoise"
    preferred_block = None
    latency_samples = 0

    def __init__(self, threshold_db: float = -45.0, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self._gate = NoiseGate(threshold_db=threshold_db, ratio=10.0, attack_ms=2.0, release_ms=120.0)
        self._board = Pedalboard([HighpassFilter(cutoff_frequency_hz=80.0), self._gate])

    @property
    def threshold_db(self) -> float:
        return float(self._gate.threshold_db)

    @threshold_db.setter
    def threshold_db(self, value: float) -> None:
        self._gate.threshold_db = float(value)

    def process(self, block: np.ndarray) -> np.ndarray:
        return self._board.process(block[np.newaxis, :], self.sample_rate, reset=False)[0]

    def reset(self) -> None:
        self._board.reset()
