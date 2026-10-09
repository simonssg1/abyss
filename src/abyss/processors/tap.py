"""Prise d'écoute : garde en mémoire les dernières secondes de la voix (jamais écrites sur disque)."""

from __future__ import annotations

import threading

import numpy as np


class InputTap:
    """Processor transparent qui copie le signal dans un tampon circulaire partagé.

    La même instance peut figurer dans deux chaînes pendant un crossfade : un bloc identique au
    précédent n'est enregistré qu'une fois (le moteur réutilise le même tableau d'un bloc à l'autre,
    on compare donc le contenu et non l'objet).
    """

    name = "tap"
    preferred_block = None
    latency_samples = 0

    def __init__(self, seconds: float = 5.0, sample_rate: int = 48000):
        self.seconds = seconds
        self.enabled = False
        self._lock = threading.Lock()
        self._last = np.zeros(0, dtype=np.float32)
        self.configure(sample_rate)

    def configure(self, sample_rate: int) -> None:
        with self._lock:
            self.sample_rate = sample_rate
            self._buf = np.zeros(int(self.seconds * sample_rate), dtype=np.float32)
            self._pos = 0
            self._filled = 0

    def process(self, block: np.ndarray) -> np.ndarray:
        if self.enabled and not (len(block) == len(self._last) and np.array_equal(block, self._last)):
            self._last = block.copy()
            with self._lock:
                n = min(len(block), len(self._buf))
                idx = (self._pos + np.arange(n)) % len(self._buf)
                self._buf[idx] = block[-n:]
                self._pos = (self._pos + n) % len(self._buf)
                self._filled = min(len(self._buf), self._filled + n)
        return block

    def snapshot(self) -> tuple[np.ndarray, int]:
        """→ (dernières secondes captées, dans l'ordre, fréquence)."""
        with self._lock:
            if self._filled < len(self._buf):
                data = self._buf[: self._filled].copy()
            else:
                data = np.concatenate([self._buf[self._pos:], self._buf[: self._pos]])
            return data, self.sample_rate

    def clear(self) -> None:
        with self._lock:
            self._pos = 0
            self._filled = 0

    def reset(self) -> None:
        pass


VOICE_TAP = InputTap()
