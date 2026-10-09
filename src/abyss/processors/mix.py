"""Dosage dry/wet d'un groupe d'effets (« Intensité » d'un preset)."""

from __future__ import annotations

import numpy as np

from abyss.processors.base import Chain


class DryWet:
    """Applique `processors` (le signal « wet ») et le mélange au signal d'origine.

    Le signal sec est retardé de la latence du groupe pour rester aligné (pas d'effet de phasing).
    `mix` (0 = voix d'origine, 1 = effet seul) est modifiable à chaud depuis n'importe quel thread.
    """

    name = "dry_wet"
    preferred_block = None

    def __init__(self, processors, sample_rate: int = 48000, mix: float = 1.0, max_block: int = 8192):
        self.sample_rate = sample_rate
        self.inner = Chain._assemble(list(processors), sample_rate)
        self.mix = mix
        self.latency_samples = sum(p.latency_samples for p in self.inner)
        self._size = self.latency_samples + max_block
        self._delay = np.zeros(self._size, dtype=np.float32)
        self._pos = 0

    @property
    def mix(self) -> float:
        return self._mix

    @mix.setter
    def mix(self, value: float) -> None:
        self._mix = float(min(1.0, max(0.0, value)))

    def process(self, block: np.ndarray) -> np.ndarray:
        wet = block
        for p in self.inner:
            wet = p.process(wet)
        dry = self._delayed(block)
        m = self._mix
        if m >= 1.0:
            return wet.astype(np.float32, copy=False)
        return (m * wet + (1.0 - m) * dry).astype(np.float32)

    def _delayed(self, block: np.ndarray) -> np.ndarray:
        if self.latency_samples == 0:
            return block
        n = len(block)
        idx = (self._pos + np.arange(n)) % self._size
        self._delay[idx] = block
        out = self._delay[(idx - self.latency_samples) % self._size]
        self._pos = (self._pos + n) % self._size
        return out

    def reset(self) -> None:
        for p in self.inner:
            p.reset()
        self._delay[:] = 0.0
        self._pos = 0
