"""Voix robot : modulation en anneau par un sinus, phase conservée entre blocs."""

from __future__ import annotations

import numpy as np

TWO_PI = 2.0 * np.pi


class RingModulator:
    preferred_block = None
    latency_samples = 0

    def __init__(self, frequency_hz: float = 60.0, mix: float = 1.0, sample_rate: int = 48000):
        if frequency_hz <= 0 or not 0.0 <= mix <= 1.0:
            raise ValueError("ring_mod : frequency_hz > 0 et 0 <= mix <= 1")
        self.name = "ring_mod"
        self.sample_rate = sample_rate
        self.frequency_hz = float(frequency_hz)
        self.mix = float(mix)
        self.reset()

    def reset(self) -> None:
        self._phase = 0.0

    def carrier(self, n: int) -> np.ndarray:
        """Sinus de modulation pour les n prochains échantillons (fait avancer la phase)."""
        inc = TWO_PI * self.frequency_hz / self.sample_rate
        phases = self._phase + inc * np.arange(n)
        self._phase = float((self._phase + inc * n) % TWO_PI)
        return np.sin(phases).astype(np.float32)

    def process(self, block: np.ndarray) -> np.ndarray:
        mod = self.carrier(len(block))
        return ((1.0 - self.mix) * block + self.mix * block * mod).astype(np.float32)
