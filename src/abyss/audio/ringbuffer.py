"""Ring buffer mono float32 préalloué, protégé par un verrou, avec compteur de xruns."""

from __future__ import annotations

import threading

import numpy as np


class RingBuffer:
    def __init__(self, capacity: int):
        self.capacity = int(capacity)
        self._buf = np.zeros(self.capacity, dtype=np.float32)
        self._lock = threading.Lock()
        self._read = 0
        self._count = 0
        self.overflows = 0
        self.underflows = 0

    @property
    def xruns(self) -> int:
        return self.overflows + self.underflows

    @property
    def available(self) -> int:
        return self._count

    def clear(self) -> None:
        with self._lock:
            self._read = 0
            self._count = 0

    def write(self, data: np.ndarray) -> None:
        """Écrit data ; en cas de débordement, les échantillons les plus anciens sont jetés."""
        n = len(data)
        with self._lock:
            if n >= self.capacity:
                data = data[n - self.capacity :]
                n = self.capacity
            free = self.capacity - self._count
            if n > free:  # débordement : on avance la lecture
                drop = n - free
                self._read = (self._read + drop) % self.capacity
                self._count -= drop
                self.overflows += 1
            w = (self._read + self._count) % self.capacity
            first = min(n, self.capacity - w)
            self._buf[w : w + first] = data[:first]
            if first < n:
                self._buf[: n - first] = data[first:]
            self._count += n

    def read_into(self, out: np.ndarray) -> int:
        """Remplit out ; ce qui manque est mis à zéro (silence) et compte un xrun. Renvoie le nb lu."""
        n = len(out)
        with self._lock:
            k = min(n, self._count)
            first = min(k, self.capacity - self._read)
            out[:first] = self._buf[self._read : self._read + first]
            if first < k:
                out[first:k] = self._buf[: k - first]
            self._read = (self._read + k) % self.capacity
            self._count -= k
            if k < n:
                out[k:] = 0.0
                self.underflows += 1
        return k
