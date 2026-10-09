"""Interface Processor, chaîne d'effets, adaptateur de blocs et crossfade."""

from __future__ import annotations

import threading
from typing import Iterable, Protocol, runtime_checkable

import numpy as np
from pedalboard import Limiter, Pedalboard


@runtime_checkable
class Processor(Protocol):
    name: str
    preferred_block: int | None  # None = toute taille ; RVC (v2) demandera ~0,3–0,5 s
    latency_samples: int

    def process(self, block: np.ndarray) -> np.ndarray:  # float32 mono 1D, même longueur
        ...

    def reset(self) -> None: ...


class BlockAdapter:
    """Accumule / redécoupe les blocs pour un processor qui exige une taille fixe.

    La sortie est amorcée avec `preferred_block` zéros : latence ajoutée = preferred_block.
    Tampons préalloués : aucun redimensionnement en régime établi.
    """

    def __init__(self, inner: Processor, max_block: int = 4096):
        assert inner.preferred_block
        self.inner = inner
        self.name = f"{inner.name}[adapt]"
        self.preferred_block = None
        self.n = int(inner.preferred_block)
        self.latency_samples = inner.latency_samples + self.n
        cap = 2 * self.n + max_block
        self._in = np.zeros(cap, dtype=np.float32)
        self._out = np.zeros(cap, dtype=np.float32)
        self.reset()

    def reset(self) -> None:
        self.inner.reset()
        self._in_len = 0
        self._out[: self.n] = 0.0
        self._out_len = self.n

    def process(self, block: np.ndarray) -> np.ndarray:
        b = len(block)
        self._in[self._in_len : self._in_len + b] = block
        self._in_len += b
        while self._in_len >= self.n:
            y = self.inner.process(self._in[: self.n].copy())
            self._out[self._out_len : self._out_len + self.n] = y
            self._out_len += self.n
            rest = self._in_len - self.n
            self._in[:rest] = self._in[self.n : self._in_len]
            self._in_len = rest
        out = self._out[:b].copy()
        rest = self._out_len - b
        self._out[:rest] = self._out[b : self._out_len]
        self._out_len = rest
        return out


class PedalboardStage:
    """Regroupe des effets pedalboard consécutifs dans un seul objet `Pedalboard`."""

    def __init__(self, plugins: list, sample_rate: int, name: str = "pedalboard"):
        self.name = name
        self.preferred_block = None
        self.latency_samples = 0
        self.sample_rate = sample_rate
        self.board = Pedalboard(plugins)

    def process(self, block: np.ndarray) -> np.ndarray:
        out = self.board.process(block[np.newaxis, :], self.sample_rate, reset=False)[0]
        if len(out) != len(block):  # sécurité : un plugin à latence peut rendre moins d'échantillons
            fixed = np.zeros(len(block), dtype=np.float32)
            fixed[len(block) - len(out) :] = out[: len(block)]
            out = fixed
        return out.astype(np.float32, copy=False)

    def reset(self) -> None:
        self.board.reset()


KNEE = 0.85
CEILING = 0.98


def soft_ceiling(x: np.ndarray) -> np.ndarray:
    """Filet de sécurité après le limiteur : au-delà de 0,85, compression douce vers 0,98 (jamais 1)."""
    a = np.abs(x)
    over = a > KNEE
    if over.any():
        span = CEILING - KNEE
        x = np.where(over, np.sign(x) * (KNEE + span * np.tanh((a - KNEE) / span)), x)
    return x.astype(np.float32, copy=False)


class Chain:
    """Liste ordonnée de processors + gain de sortie + limiteur (sortie toujours dans [-1, 1])."""

    def __init__(self, processors: Iterable[Processor] = (), sample_rate: int = 48000,
                 output_gain_db: float = 0.0, name: str = "chain"):
        self.name = name
        self.sample_rate = sample_rate
        self.preferred_block = None
        self.processors: list[Processor] = self._assemble(list(processors), sample_rate)
        self.output_gain_db = output_gain_db
        self._limiter = Pedalboard([Limiter(threshold_db=-1.0, release_ms=100.0)])

    @staticmethod
    def _assemble(procs: list, sample_rate: int) -> list:
        """Fusionne les effets pedalboard consécutifs et enveloppe ceux à bloc imposé."""
        out: list = []
        pending: list = []
        names: list[str] = []

        def flush():
            if pending:
                out.append(PedalboardStage(list(pending), sample_rate, "+".join(names)))
                pending.clear()
                names.clear()

        for p in procs:
            plugin = getattr(p, "plugin", None)
            if plugin is not None:
                pending.append(plugin)
                names.append(p.name)
                continue
            flush()
            out.append(BlockAdapter(p) if getattr(p, "preferred_block", None) else p)
        flush()
        return out

    @property
    def output_gain_db(self) -> float:
        return self._gain_db

    @output_gain_db.setter
    def output_gain_db(self, db: float) -> None:
        self._gain_db = float(db)
        self._gain = np.float32(10.0 ** (self._gain_db / 20.0))

    @property
    def latency_samples(self) -> int:
        return sum(p.latency_samples for p in self.processors)

    def process(self, block: np.ndarray) -> np.ndarray:
        x = block
        for p in self.processors:
            x = p.process(x)
        x = x * self._gain
        x = self._limiter.process(x[np.newaxis, :].astype(np.float32, copy=False),
                                  self.sample_rate, reset=False)[0]
        return soft_ceiling(x)

    def reset(self) -> None:
        for p in self.processors:
            p.reset()
        self._limiter.reset()


class ChainSwitcher:
    """Exécute la chaîne courante ; un échange se fait par crossfade linéaire (20 ms par défaut).

    `swap()` peut être appelé depuis n'importe quel thread : la nouvelle chaîne (déjà construite)
    est déposée atomiquement et prise en compte au bloc suivant du thread de traitement.
    """

    def __init__(self, chain: Chain, sample_rate: int = 48000, fade_ms: float = 20.0):
        self.current = chain
        self._pending: Chain | None = None
        self._lock = threading.Lock()
        self.fade_len = max(1, int(sample_rate * fade_ms / 1000.0))
        self._ramp = np.linspace(0.0, 1.0, self.fade_len + 1, dtype=np.float32)[1:]
        self._old: Chain | None = None
        self._fade_pos = 0

    def swap(self, chain: Chain) -> None:
        with self._lock:
            self._pending = chain

    @property
    def fading(self) -> bool:
        return self._old is not None

    def process(self, block: np.ndarray) -> np.ndarray:
        with self._lock:
            pending, self._pending = self._pending, None
        if pending is not None:
            self._old = self.current  # si un fondu était en cours, l'ancienne chaîne est abandonnée
            self.current = pending
            self._fade_pos = 0
        new = self.current.process(block)
        if self._old is None:
            return new
        old = self._old.process(block)
        n = len(block)
        k = min(n, self.fade_len - self._fade_pos)
        g = np.ones(n, dtype=np.float32)
        g[:k] = self._ramp[self._fade_pos : self._fade_pos + k]
        out = old * (1.0 - g) + new * g
        self._fade_pos += k
        if self._fade_pos >= self.fade_len:
            self._old = None
        return out.astype(np.float32, copy=False)
