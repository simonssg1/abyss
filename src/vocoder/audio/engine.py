"""Moteur audio : 3 streams indépendants + thread de traitement + ring buffers."""

from __future__ import annotations

import logging
import sys
import threading
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from vocoder.audio.ringbuffer import RingBuffer
from vocoder.presets import Preset, build_chain
from vocoder.processors.base import Chain, ChainSwitcher
from vocoder.processors.denoise import Denoiser

log = logging.getLogger("vocoder.engine")

BLOCK = 256
RATES = (48000, 44100)


class Pipeline:
    """Débruitage (optionnel) → chaîne du preset (avec crossfade) → gain + limiteur.

    Partagé par le moteur temps réel et le rendu de fichiers.
    """

    def __init__(self, sample_rate: int = 48000, denoise: bool = True, threshold_db: float = -45.0,
                 output_gain_db: float = 0.0):
        self.sample_rate = sample_rate
        self.denoiser = Denoiser(threshold_db, sample_rate)
        self.denoise_enabled = denoise
        self.output_gain_db = output_gain_db
        self.preset: Preset | None = None
        self.bypass = False
        self.switcher = ChainSwitcher(Chain([], sample_rate, output_gain_db, "bypass"), sample_rate)

    def set_preset(self, preset: Preset | None) -> None:
        self.preset = preset
        if not self.bypass:
            self._swap(preset)

    def set_bypass(self, on: bool) -> None:
        self.bypass = on
        self._swap(None if on else self.preset)

    def set_output_gain(self, db: float) -> None:
        self.output_gain_db = db
        self.switcher.current.output_gain_db = db

    def _swap(self, preset: Preset | None) -> None:
        # Construction hors thread audio, puis échange atomique avec crossfade de 20 ms.
        self.switcher.swap(build_chain(preset, self.sample_rate, self.output_gain_db))

    @property
    def latency_samples(self) -> int:
        return self.switcher.current.latency_samples

    def process(self, block: np.ndarray) -> np.ndarray:
        x = self.denoiser.process(block) if self.denoise_enabled else block
        cur = self.switcher.current
        if cur.output_gain_db != self.output_gain_db:
            cur.output_gain_db = self.output_gain_db
        return self.switcher.process(x)


@dataclass
class Metrics:
    rms_in: float = 0.0
    rms_out: float = 0.0
    latency_ms: float = 0.0
    xruns: int = 0
    running: bool = False
    sample_rate: int = 0
    error: str = ""


def _extra_settings():
    # WASAPI partagé : laisser Windows convertir la fréquence si le périphérique tourne à une autre.
    if sys.platform == "win32":
        return sd.WasapiSettings(auto_convert=True)
    return None


def pick_samplerate(input_idx: int | None, output_idxs: list[int | None]) -> int:
    """48 kHz si tous les périphériques l'acceptent, sinon 44,1 kHz pour tous."""
    extra = _extra_settings()
    for rate in RATES:
        try:
            if input_idx is not None:
                sd.check_input_settings(input_idx, channels=1, dtype="float32", samplerate=rate,
                                        extra_settings=extra)
            for idx, ch in zip(output_idxs, (2, 2)):
                if idx is not None:
                    sd.check_output_settings(idx, channels=ch, dtype="float32", samplerate=rate,
                                             extra_settings=extra)
            return rate
        except Exception:
            continue
    return RATES[-1]


class AudioEngine:
    def __init__(self, presets: list[Preset], denoise: bool = True, threshold_db: float = -45.0,
                 monitor: bool = False, monitor_volume: float = 0.8, output_gain_db: float = 0.0):
        self.presets = presets
        self.metrics = Metrics()
        self._state = dict(denoise=denoise, threshold_db=threshold_db, output_gain_db=output_gain_db)
        self.monitor_enabled = monitor
        self.monitor_volume = monitor_volume
        self._preset: Preset | None = presets[0] if presets else None
        self._bypass = False
        self.pipeline = self._make_pipeline(48000)
        self._streams: list[sd._StreamBase] = []
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self.devices: dict[str, int | None] = {"input": None, "virtual": None, "monitor": None}

    # ----- réglages (appelables depuis n'importe quel thread) -----
    def _make_pipeline(self, rate: int) -> Pipeline:
        p = Pipeline(rate, self._state["denoise"], self._state["threshold_db"], self._state["output_gain_db"])
        p.bypass = self._bypass
        p.preset = self._preset
        p.switcher.current = build_chain(None if self._bypass else self._preset, rate,
                                         self._state["output_gain_db"])
        return p

    def set_preset(self, preset: Preset | None) -> None:
        self._preset = preset
        self.pipeline.set_preset(preset)

    @property
    def preset(self) -> Preset | None:
        return self._preset

    def set_bypass(self, on: bool) -> None:
        self._bypass = on
        self.pipeline.set_bypass(on)

    @property
    def bypass(self) -> bool:
        return self._bypass

    def set_denoise(self, enabled: bool | None = None, threshold_db: float | None = None) -> None:
        if enabled is not None:
            self._state["denoise"] = enabled
            self.pipeline.denoise_enabled = enabled
        if threshold_db is not None:
            self._state["threshold_db"] = threshold_db
            self.pipeline.denoiser.threshold_db = threshold_db

    def set_output_gain(self, db: float) -> None:
        self._state["output_gain_db"] = db
        self.pipeline.output_gain_db = db

    def set_monitor(self, enabled: bool | None = None, volume: float | None = None) -> None:
        if enabled is not None:
            self.monitor_enabled = enabled
        if volume is not None:
            self.monitor_volume = float(volume)

    # ----- cycle de vie -----
    def start(self, input_idx: int | None, virtual_idx: int | None, monitor_idx: int | None) -> None:
        """Ouvre les streams (chacun indépendant) et lance le thread de traitement."""
        self.stop()
        with self._lock:
            self.devices = {"input": input_idx, "virtual": virtual_idx, "monitor": monitor_idx}
            self.metrics = Metrics()
            if input_idx is None:
                self.metrics.error = "Aucun micro sélectionné"
                return
            rate = pick_samplerate(input_idx, [virtual_idx, monitor_idx])
            self._prepare(rate)
            extra = _extra_settings()
            try:
                self._streams.append(sd.InputStream(
                    device=input_idx, channels=1, samplerate=rate, blocksize=BLOCK, dtype="float32",
                    latency="low", callback=self._in_cb, extra_settings=extra))
                if virtual_idx is not None:
                    self._streams.append(sd.OutputStream(
                        device=virtual_idx, channels=2, samplerate=rate, blocksize=BLOCK, dtype="float32",
                        latency="low", callback=self._virtual_cb, extra_settings=extra))
                if monitor_idx is not None:
                    self._streams.append(sd.OutputStream(
                        device=monitor_idx, channels=2, samplerate=rate, blocksize=BLOCK, dtype="float32",
                        latency="low", callback=self._monitor_cb, extra_settings=extra))
            except Exception as e:
                log.error("Ouverture des streams impossible : %s", e)
                self.metrics.error = f"Erreur audio : {e}"
                self._close_streams()
                return
            self._start_thread()
            for s in self._streams:
                s.start()
            self.metrics.running = True
            self.metrics.sample_rate = rate

    def _prepare(self, rate: int) -> None:
        """Préalloue pipeline et ring buffers pour une fréquence donnée."""
        self.pipeline = self._make_pipeline(rate)
        self._rate = rate
        self._ring_in = RingBuffer(BLOCK * 16)
        self._ring_virtual = RingBuffer(BLOCK * 4)
        self._ring_monitor = RingBuffer(BLOCK * 4)
        self._scratch_v = np.zeros(BLOCK * 8, dtype=np.float32)
        self._scratch_m = np.zeros(BLOCK * 8, dtype=np.float32)
        # Niveau cible ≈ 2 blocs : on amorce les sorties avec 2 blocs de silence.
        self._ring_virtual.write(np.zeros(BLOCK * 2, dtype=np.float32))
        self._ring_monitor.write(np.zeros(BLOCK * 2, dtype=np.float32))

    def _start_thread(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="vocoder-dsp", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop.set()
            self._wake.set()
            self._close_streams()
            if self._thread is not None:
                self._thread.join(timeout=2.0)
                self._thread = None
            self.metrics.running = False

    def _close_streams(self) -> None:
        for s in self._streams:
            try:
                s.stop()
                s.close()
            except Exception:
                pass
        self._streams = []

    # ----- callbacks audio : copie uniquement -----
    def _in_cb(self, indata, frames, time, status):
        self._ring_in.write(indata[:, 0])
        self._wake.set()

    def _virtual_cb(self, outdata, frames, time, status):
        mono = self._scratch_v[:frames]
        self._ring_virtual.read_into(mono)
        outdata[:, 0] = mono
        outdata[:, 1] = mono

    def _monitor_cb(self, outdata, frames, time, status):
        mono = self._scratch_m[:frames]
        self._ring_monitor.read_into(mono)
        outdata[:, 0] = mono
        outdata[:, 1] = mono

    # ----- thread de traitement -----
    def _run(self) -> None:
        buf = np.zeros(BLOCK, dtype=np.float32)
        while not self._stop.is_set():
            self._wake.wait(timeout=0.2)
            self._wake.clear()
            while self._ring_in.available >= BLOCK and not self._stop.is_set():
                self._ring_in.read_into(buf)
                try:
                    y = self.pipeline.process(buf)
                except Exception as e:  # ne jamais tuer le thread audio
                    log.exception("Erreur de traitement")
                    self.metrics.error = f"Erreur DSP : {e}"
                    y = np.zeros(BLOCK, dtype=np.float32)
                self._ring_virtual.write(y)
                if self.monitor_enabled:
                    self._ring_monitor.write(y * np.float32(self.monitor_volume))
                self._update_metrics(buf, y)

    def _update_metrics(self, x: np.ndarray, y: np.ndarray) -> None:
        m = self.metrics
        m.rms_in = float(np.sqrt(np.mean(x * x)))
        m.rms_out = float(np.sqrt(np.mean(y * y)))
        m.xruns = self._ring_in.xruns + self._ring_virtual.overflows + self._ring_monitor.overflows \
            + (self._ring_virtual.underflows if self.devices["virtual"] is not None else 0)
        stream_lat = 0.0
        for s in self._streams[:2]:
            lat = s.latency
            stream_lat += lat if isinstance(lat, float) else float(lat[0])
        buffered = self._ring_in.available + self._ring_virtual.available + BLOCK
        m.latency_ms = 1000.0 * (stream_lat + (buffered + self.pipeline.latency_samples) / self._rate)
