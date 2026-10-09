"""Vocodeur à canaux : la voix module une porteuse en dents de scie (ou un accord)."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt


class ChannelVocoder:
    preferred_block = None
    latency_samples = 0

    def __init__(self, bands: int = 20, carrier_hz: float = 110.0, chord: bool = False,
                 mix: float = 1.0, sample_rate: int = 48000, env_cutoff_hz: float = 40.0,
                 low_hz: float = 100.0, high_hz: float = 8000.0):
        if not 16 <= int(bands) <= 24:
            raise ValueError("vocoder : bands doit être entre 16 et 24")
        if carrier_hz <= 0 or not 0.0 <= mix <= 1.0:
            raise ValueError("vocoder : carrier_hz > 0 et 0 <= mix <= 1")
        self.name = "vocoder"
        self.sample_rate = sample_rate
        self.bands = int(bands)
        self.carrier_hz = float(carrier_hz)
        self.chord = bool(chord)
        self.mix = float(mix)

        high = min(high_hz, 0.45 * sample_rate)
        edges = np.geomspace(low_hz, high, self.bands + 1)
        nyq = sample_rate / 2.0
        self._band_sos = [butter(2, [lo / nyq, hi / nyq], btype="bandpass", output="sos")
                          for lo, hi in zip(edges[:-1], edges[1:])]
        self._env_sos = butter(2, env_cutoff_hz / nyq, btype="lowpass", output="sos")
        # Multiplicateurs de fréquence de la porteuse : fondamentale, quinte, octave.
        self._ratios = np.array([1.0, 1.5, 2.0] if self.chord else [1.0])
        self.reset()

    def reset(self) -> None:
        # zi par bande, pour 2 signaux (ligne 0 = voix, ligne 1 = porteuse).
        self._band_zi = [np.zeros((sos.shape[0], 2, 2)) for sos in self._band_sos]
        self._env_zi = np.zeros((self._env_sos.shape[0], self.bands, 2))
        self._osc_phase = np.zeros(len(self._ratios))  # en cycles, [0, 1)
        self._makeup = 1.0

    def carrier(self, n: int) -> np.ndarray:
        """Porteuse (dent de scie ou accord) pour les n prochains échantillons, phase conservée."""
        incs = self.carrier_hz * self._ratios / self.sample_rate
        ph = (self._osc_phase[:, None] + incs[:, None] * np.arange(n)[None, :]) % 1.0
        self._osc_phase = (self._osc_phase + incs * n) % 1.0
        return (2.0 * ph - 1.0).mean(axis=0)

    def process(self, block: np.ndarray) -> np.ndarray:
        n = len(block)
        x = block.astype(np.float64)
        pair = np.empty((2, n))
        pair[0] = x
        pair[1] = self.carrier(n)
        envs = np.empty((self.bands, n))
        carriers = np.empty((self.bands, n))
        for i, sos in enumerate(self._band_sos):
            y, self._band_zi[i] = sosfilt(sos, pair, axis=1, zi=self._band_zi[i])
            envs[i] = np.abs(y[0])
            carriers[i] = y[1]
        envs, self._env_zi = sosfilt(self._env_sos, envs, axis=1, zi=self._env_zi)
        voc = np.sum(np.maximum(envs, 0.0) * carriers, axis=0)

        # Normalisation : on ramène le niveau du vocodeur vers celui de la voix (gain lissé).
        rms_in = np.sqrt(np.mean(x * x))
        rms_out = np.sqrt(np.mean(voc * voc))
        if rms_in > 1e-4 and rms_out > 1e-9:
            target = min(rms_in / rms_out, 200.0)
            self._makeup += 0.1 * (target - self._makeup)
        voc *= self._makeup
        return ((1.0 - self.mix) * x + self.mix * voc).astype(np.float32)

