"""Effets en flux : wrappers pedalboard + pitch shift natif basse latence."""

from __future__ import annotations

import numpy as np
import pedalboard as pb


class PedalboardFX:
    """Un effet pedalboard. Dans une `Chain`, les effets consécutifs partagent un seul `Pedalboard`.

    Utilisé seul, il a son propre `Pedalboard` (appelé avec reset=False à chaque bloc).
    """

    preferred_block = None
    latency_samples = 0

    def __init__(self, name: str, plugin, sample_rate: int = 48000):
        self.name = name
        self.plugin = plugin
        self.sample_rate = sample_rate
        self._board = pb.Pedalboard([plugin])

    def process(self, block: np.ndarray) -> np.ndarray:
        return self._board.process(block[np.newaxis, :], self.sample_rate, reset=False)[0]

    def reset(self) -> None:
        self._board.reset()


class PitchShift:
    """Pitch shift temps réel à deux lectures de ligne à retard en fondu (Hann complémentaires).

    `pedalboard.PitchShift` (Rubber Band) rend du silence en flux avec reset=False et a ~1 s de
    latence : inutilisable en temps réel (voir DECISIONS.md). Celui-ci a ~window/2 de latence.
    """

    preferred_block = None

    def __init__(self, semitones: float = 0.0, sample_rate: int = 48000, window_ms: float = 40.0,
                 max_block: int = 8192):
        self.max_block = max_block
        self.name = "pitch_shift"
        self.sample_rate = sample_rate
        self.semitones = float(semitones)
        self.window = max(64, int(sample_rate * window_ms / 1000.0))
        self.latency_samples = self.window // 2
        self._size = 1 << int(np.ceil(np.log2(self.window + max_block + 4)))
        self._buf = np.zeros(self._size, dtype=np.float32)
        self.reset()

    @property
    def semitones(self) -> float:
        return self._semitones

    @semitones.setter
    def semitones(self, value: float) -> None:
        self._semitones = float(value)
        self._ratio = 2.0 ** (self._semitones / 12.0)

    def reset(self) -> None:
        self._buf[:] = 0.0
        self._t = 0  # nombre absolu d'échantillons écrits
        self._phase = 0.0

    def process(self, block: np.ndarray) -> np.ndarray:
        if len(block) > self.max_block:
            return np.concatenate([self.process(block[i : i + self.max_block])
                                   for i in range(0, len(block), self.max_block)])
        n = len(block)
        mask = self._size - 1
        idx = (self._t + np.arange(n)) & mask
        self._buf[idx] = block
        if self._ratio == 1.0:
            self._t += n
            return block.astype(np.float32, copy=True)
        step = (1.0 - self._ratio) / (self.window - 2)
        p1 = (self._phase + step * np.arange(1, n + 1)) % 1.0
        p2 = (p1 + 0.5) % 1.0
        t_abs = self._t + np.arange(n, dtype=np.float64)
        out = self._tap(t_abs, p1, mask) * np.sin(np.pi * p1) ** 2
        out += self._tap(t_abs, p2, mask) * np.sin(np.pi * p2) ** 2
        self._phase = float(p1[-1])
        self._t += n
        return out.astype(np.float32)

    def _tap(self, t_abs: np.ndarray, phase: np.ndarray, mask: int) -> np.ndarray:
        pos = t_abs - 1.0 - phase * (self.window - 2)
        i0 = np.floor(pos)
        frac = (pos - i0).astype(np.float32)
        i0 = i0.astype(np.int64)
        a = self._buf[i0 & mask]
        b = self._buf[(i0 + 1) & mask]
        return a + (b - a) * frac


_PLUGINS = {
    "reverb": pb.Reverb,
    "distortion": pb.Distortion,
    "chorus": pb.Chorus,
    "delay": pb.Delay,
    "bitcrush": pb.Bitcrush,
    "highpass": pb.HighpassFilter,
    "lowpass": pb.LowpassFilter,
    "compressor": pb.Compressor,
    "noise_gate": pb.NoiseGate,
    "gain": pb.Gain,
}

FX_TYPES = tuple(_PLUGINS) + ("pitch_shift",)


def make_fx(kind: str, params: dict, sample_rate: int = 48000):
    """Crée un effet. Lève KeyError (type inconnu) ou TypeError/ValueError (paramètres invalides)."""
    if kind == "pitch_shift":
        return PitchShift(sample_rate=sample_rate, **params)
    cls = _PLUGINS[kind]
    return PedalboardFX(kind, cls(**params), sample_rate)
