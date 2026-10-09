"""Aperçu audio d'un preset : rendu hors du thread audio, lecture uniquement dans le casque.

Le moteur temps réel n'est pas touché : l'aperçu passe par une instance séparée de la chaîne et
par son propre OutputStream ouvert sur le périphérique du casque, jamais sur le micro virtuel.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from abyss.presets import Preset, build_chain
from abyss.processors.denoise import Denoiser

log = logging.getLogger("abyss.preview")

MAX_SECONDS = 5.0
MIN_CAPTURE_SECONDS = 1.0
SAMPLE = Path(__file__).resolve().parents[3] / "samples" / "synthetic_voice.wav"
BLOCK = 256


def fallback_voice(sample_rate: int) -> np.ndarray:
    """Voix synthétique (fichier du dépôt, sinon générée)."""
    try:
        from abyss.__main__ import read_wav_mono

        return read_wav_mono(SAMPLE, sample_rate)
    except Exception:
        from abyss.synth import synthetic_voice

        return synthetic_voice(MAX_SECONDS, sample_rate)


def pick_source(captured: np.ndarray, sample_rate: int) -> tuple[np.ndarray, str]:
    """Dernières secondes du micro si assez de son, sinon voix synthétique. → (signal, origine)."""
    if len(captured) >= MIN_CAPTURE_SECONDS * sample_rate and np.sqrt(np.mean(captured ** 2)) > 1e-3:
        return captured[-int(MAX_SECONDS * sample_rate):], "micro"
    return fallback_voice(sample_rate)[: int(MAX_SECONDS * sample_rate)], "synthétique"


def render_preview(preset: Preset, source: np.ndarray, sample_rate: int, denoise: bool = True,
                   threshold_db: float = -45.0) -> np.ndarray:
    """Passe le signal dans une instance neuve de la chaîne du preset (blocs de 256)."""
    from abyss.processors.tap import VOICE_TAP

    chain = build_chain(preset, sample_rate)
    chain.processors = [p for p in chain.processors if p is not VOICE_TAP]  # l'aperçu ne s'enregistre pas
    den = Denoiser(threshold_db, sample_rate) if denoise else None
    pad = (-len(source)) % BLOCK
    x = np.concatenate([source.astype(np.float32), np.zeros(pad, dtype=np.float32)])
    out = np.empty_like(x)
    for i in range(0, len(x), BLOCK):
        b = x[i : i + BLOCK]
        if den is not None:
            b = den.process(b)
        out[i : i + BLOCK] = chain.process(b)
    return out[: len(source)]


class PreviewPlayer:
    """Joue un tableau mono sur un périphérique de sortie (stream dédié), arrêt possible à tout moment."""

    def __init__(self, on_finished=None):
        self._stream = None
        self._data = np.zeros(0, dtype=np.float32)
        self._pos = 0
        self._lock = threading.Lock()
        self.on_finished = on_finished

    @property
    def playing(self) -> bool:
        return self._stream is not None

    def play(self, data: np.ndarray, sample_rate: int, device: int) -> None:
        import sounddevice as sd

        self.stop()
        with self._lock:
            self._data = data.astype(np.float32)
            self._pos = 0
        self._stream = sd.OutputStream(device=device, channels=2, samplerate=sample_rate, dtype="float32",
                                       callback=self._callback, finished_callback=self._finished)
        self._stream.start()

    def _callback(self, outdata, frames, time, status):
        import sounddevice as sd

        with self._lock:
            chunk = self._data[self._pos : self._pos + frames]
            self._pos += len(chunk)
        outdata[: len(chunk), 0] = chunk
        outdata[: len(chunk), 1] = chunk
        if len(chunk) < frames:
            outdata[len(chunk):] = 0.0
            raise sd.CallbackStop

    def _finished(self) -> None:
        if self.on_finished:
            self.on_finished()

    def stop(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
