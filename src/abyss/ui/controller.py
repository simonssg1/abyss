"""AppController : pont entre le moteur audio (Python) et l'interface QML."""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from abyss import __version__
from abyss.audio import devices as dv
from abyss.audio.engine import AudioEngine
from abyss.config import Config, save_config
from abyss.hotkeys import PERMISSION_HINT, HotkeyBridge
from abyss.platform.permissions import microphone_status
from abyss.presets import Preset, apply_live
from abyss.ui.models import PresetFilterModel, PresetModel

log = logging.getLogger("abyss.ui")

REPO_URL = "https://github.com/simonssg1/abyss"
HISTORY = 64
MUTE_DB = -120.0


def level_from_rms(rms: float) -> float:
    """RMS linéaire → niveau 0..1 (échelle -60 dB … 0 dB)."""
    return min(1.0, max(0.0, (20.0 * math.log10(rms + 1e-9) + 60.0) / 60.0))


def _ro(type_, attr: str, signal: Signal):
    return Property(type_, lambda self: getattr(self, attr), notify=signal)


class AppController(QObject):
    toast = Signal(str, str, str)  # kind ("success" | "error"), titre, message
    raiseRequested = Signal()
    _startFinished = Signal(bool)

    liveChanged = Signal()
    startingChanged = Signal()
    bypassChanged = Signal()
    outputMutedChanged = Signal()
    activePresetIdChanged = Signal()
    levelsChanged = Signal()
    sessionSecondsChanged = Signal()
    statsChanged = Signal()
    hotkeysChanged = Signal()
    settingsChanged = Signal()
    devicesChanged = Signal()
    permissionChanged = Signal()
    previewChanged = Signal()

    def __init__(self, presets: list[Preset], cfg: Config, audio: bool = True, hotkeys: bool = True,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.cfg = cfg
        self.audio = audio
        self.presetModel = PresetModel(presets, cfg.hotkeys, self)
        self.presetFilter = PresetFilterModel(self.presetModel, self)

        start = self.presetModel.find(self._initial_preset_id(presets)) or (presets[0] if presets else None)
        self.engine = AudioEngine(presets, cfg.denoise, cfg.denoise_threshold_db, cfg.monitor,
                                  cfg.monitor_volume, cfg.output_gain_db)
        self.engine.set_preset(start)

        self._live = False
        self._starting = False
        self._bypass = False
        self._muted = False
        self._active_id = start.id if start else ""
        self._in_level = 0.0
        self._out_level = 0.0
        self._history: deque[float] = deque([0.0] * HISTORY, maxlen=HISTORY)
        self._session = 0
        self._session_t0 = 0.0
        self._latency = 0.0
        self._xruns = 0
        self._xrun_marks: deque[tuple[float, int]] = deque()
        self._last_xrun_toast = 0.0
        self._silent_since: float | None = None
        self._silence_warned = False
        self._hotkeys_ok = False
        self._hotkeys_status = "inactifs"
        self._mic_permission = microphone_status()
        self._preview_playing = False
        self._input_devices: list[str] = []
        self._output_devices: list[str] = []
        self._virtual_found = False

        self.hotkeys = HotkeyBridge(self)
        self.hotkeys.preset_requested.connect(self._on_hotkey_preset)
        self.hotkeys.bypass_requested.connect(self.toggleBypass)
        self.hotkeys.monitor_requested.connect(self.toggleMonitor)
        self._want_hotkeys = hotkeys
        self._startFinished.connect(self._on_start_finished)

        self._refresh_device_lists(initial=True)

        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ≤ 30 Hz vers le QML
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._device_timer = QTimer(self)
        self._device_timer.setInterval(3000)
        self._device_timer.timeout.connect(self._watch_devices)
        self._device_timer.start()

    def _initial_preset_id(self, presets: list[Preset]) -> str:
        for p in presets:
            if p.name == self.cfg.last_preset or p.id == self.cfg.last_preset:
                return p.id
        return presets[0].id if presets else ""

    def start_hotkeys(self) -> None:
        """À appeler une fois l'interface chargée (signale l'échec par un toast)."""
        if not self._want_hotkeys:
            self._set_hotkeys(False, "désactivés")
            return
        ok = self.hotkeys.start(self.cfg.hotkeys)
        self._set_hotkeys(ok, self.hotkeys.status)
        if not ok:
            self.toast.emit("error", "Raccourcis désactivés", PERMISSION_HINT + ".")

    def _set_hotkeys(self, ok: bool, status: str) -> None:
        self._hotkeys_ok, self._hotkeys_status = ok, status
        self.hotkeysChanged.emit()

    # ----- propriétés exposées -----
    live = _ro(bool, "_live", liveChanged)
    starting = _ro(bool, "_starting", startingChanged)
    bypass = _ro(bool, "_bypass", bypassChanged)
    outputMuted = _ro(bool, "_muted", outputMutedChanged)
    activePresetId = _ro(str, "_active_id", activePresetIdChanged)
    inputLevel = _ro(float, "_in_level", levelsChanged)
    outputLevel = _ro(float, "_out_level", levelsChanged)
    sessionSeconds = _ro(int, "_session", sessionSecondsChanged)
    latencyMs = _ro(float, "_latency", statsChanged)
    xruns = _ro(int, "_xruns", statsChanged)
    hotkeysOk = _ro(bool, "_hotkeys_ok", hotkeysChanged)
    hotkeysStatus = _ro(str, "_hotkeys_status", hotkeysChanged)
    micPermission = _ro(str, "_mic_permission", permissionChanged)
    previewPlaying = _ro(bool, "_preview_playing", previewChanged)
    inputDevices = _ro(list, "_input_devices", devicesChanged)
    outputDevices = _ro(list, "_output_devices", devicesChanged)
    virtualFound = _ro(bool, "_virtual_found", devicesChanged)

    @Property(list, notify=levelsChanged)
    def inputHistory(self) -> list:
        return list(self._history)

    @Property(bool, notify=settingsChanged)
    def denoiseOn(self) -> bool:
        return self.cfg.denoise

    @Property(float, notify=settingsChanged)
    def denoiseThreshold(self) -> float:
        return float(self.cfg.denoise_threshold_db)

    @Property(bool, notify=settingsChanged)
    def monitorOn(self) -> bool:
        return self.cfg.monitor

    @Property(float, notify=settingsChanged)
    def monitorVolume(self) -> float:
        return float(self.cfg.monitor_volume)

    @Property(float, notify=settingsChanged)
    def outputGain(self) -> float:
        return float(self.cfg.output_gain_db)

    @Property(bool, notify=settingsChanged)
    def showWelcome(self) -> bool:
        return self.cfg.show_welcome

    @Property(str, notify=devicesChanged)
    def inputDevice(self) -> str:
        return self.cfg.input_device or ""

    @Property(str, notify=devicesChanged)
    def virtualDevice(self) -> str:
        return self.cfg.virtual_device or ""

    @Property(str, notify=devicesChanged)
    def monitorDevice(self) -> str:
        return self.cfg.monitor_device or ""

    @Property(bool, notify=devicesChanged)
    def speakerWarning(self) -> bool:
        return dv.is_speaker_like(self.cfg.monitor_device)

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(str, constant=True)
    def repoUrl(self) -> str:
        return REPO_URL

    @Property(QObject, constant=True)
    def presets(self) -> QObject:
        return self.presetModel

    @Property(QObject, constant=True)
    def presetFilterModel(self) -> QObject:
        return self.presetFilter

    # ----- direct -----
    @Slot()
    def toggleLive(self) -> None:
        self.stopLive() if self._live else self.startLive()

    @Slot()
    def startLive(self) -> None:
        if self._live or self._starting:
            return
        if not self.audio:
            self._set_live(True)  # mode démo / tests : pas de streams
            return
        if not self._virtual_found or not self.cfg.virtual_device:
            self.toast.emit("error", "Micro virtuel introuvable",
                            "Installe BlackHole 2ch (macOS) ou VB-CABLE (Windows), puis rafraîchis les périphériques.")
        self._starting = True
        self.startingChanged.emit()
        idx = self._device_indices()
        # Ouverture des streams hors du thread de l'interface (macOS peut bloquer le temps d'autoriser le micro).
        threading.Thread(target=self._start_worker, args=idx, name="abyss-start", daemon=True).start()

    def _start_worker(self, mic, virt, mon) -> None:
        self.engine.start(mic, virt, mon)
        self._startFinished.emit(self.engine.metrics.running)

    def _on_start_finished(self, ok: bool) -> None:
        self._starting = False
        self.startingChanged.emit()
        self._update_permission()
        if ok:
            self._apply_mute()
            self._set_live(True)
            return
        err = self.engine.metrics.error or "Erreur inconnue"
        if self._mic_permission == "denied":
            self.toast.emit("error", "Accès au micro refusé",
                            "Autorise Abyss dans Réglages Système → Confidentialité et sécurité → Micro.")
        else:
            self.toast.emit("error", "Impossible de démarrer le direct", err)

    @Slot()
    def stopLive(self) -> None:
        if not self._live:
            return
        if self.audio:
            self.engine.stop()
        self._set_live(False)

    def _set_live(self, on: bool) -> None:
        self._live = on
        self._session_t0 = time.monotonic()
        self._session = 0
        self._silent_since = None
        self._xrun_marks.clear()
        self.sessionSecondsChanged.emit()
        self.liveChanged.emit()

    def _device_indices(self) -> tuple[int | None, int | None, int | None]:
        devs = dv.list_devices()

        def idx(name, kind):
            d = dv.find_by_name(name, kind, devs) if name else None
            return d.index if d else None

        return (idx(self.cfg.input_device, "input"), idx(self.cfg.virtual_device, "output"),
                idx(self.cfg.monitor_device, "output"))

    def _restart_if_live(self) -> None:
        if self._live and self.audio:
            self.engine.stop()
            self._live = False
            self.startLive()

    # ----- presets -----
    @Slot(str)
    def selectPreset(self, preset_id: str) -> None:
        p = self.presetModel.find(preset_id)
        if p is None:
            return
        self.engine.set_preset(p)
        self._active_id = p.id
        self.cfg.last_preset = p.name
        self.activePresetIdChanged.emit()

    def _on_hotkey_preset(self, index: int) -> None:
        for p in self.presetModel.presets():
            if p.hotkey_index == index:
                self.selectPreset(p.id)
                return

    @Slot(str, float)
    def setIntensity(self, preset_id: str, value: float) -> None:
        p = self.presetModel.find(preset_id)
        if p is None:
            return
        p.intensity = min(1.0, max(0.0, float(value)))
        self.apply_preset_live(p)
        self.presetModel.refresh(p.id)

    def apply_preset_live(self, p: Preset, rebuild: bool = False) -> None:
        """Répercute les réglages d'un preset sur le direct s'il est actif."""
        if p.id != self._active_id:
            return
        if rebuild or not apply_live(self.engine.pipeline.switcher.current, p):
            self.engine.set_preset(p)

    # ----- contrôles -----
    @Slot(bool)
    def setBypass(self, on: bool) -> None:
        if on != self._bypass:
            self._bypass = on
            self.engine.set_bypass(on)
            self.bypassChanged.emit()

    @Slot()
    def toggleBypass(self) -> None:
        self.setBypass(not self._bypass)

    @Slot(bool)
    def setOutputMuted(self, on: bool) -> None:
        if on != self._muted:
            self._muted = on
            self._apply_mute()
            self.outputMutedChanged.emit()

    @Slot()
    def toggleOutputMuted(self) -> None:
        self.setOutputMuted(not self._muted)

    def _apply_mute(self) -> None:
        self.engine.set_output_gain(MUTE_DB if self._muted else self.cfg.output_gain_db)

    @Slot(bool)
    def setDenoise(self, on: bool) -> None:
        self.cfg.denoise = on
        self.engine.set_denoise(enabled=on)
        self.settingsChanged.emit()

    @Slot(float)
    def setDenoiseThreshold(self, db: float) -> None:
        self.cfg.denoise_threshold_db = float(db)
        self.engine.set_denoise(threshold_db=float(db))
        self.settingsChanged.emit()

    @Slot(bool)
    def setMonitor(self, on: bool) -> None:
        self.cfg.monitor = on
        self.engine.set_monitor(enabled=on)
        self.settingsChanged.emit()

    @Slot()
    def toggleMonitor(self) -> None:
        self.setMonitor(not self.cfg.monitor)

    @Slot(float)
    def setMonitorVolume(self, v: float) -> None:
        self.cfg.monitor_volume = float(min(1.0, max(0.0, v)))
        self.engine.set_monitor(volume=self.cfg.monitor_volume)
        self.settingsChanged.emit()

    @Slot(float)
    def setOutputGain(self, db: float) -> None:
        self.cfg.output_gain_db = float(db)
        self._apply_mute()
        self.settingsChanged.emit()

    @Slot(bool)
    def setShowWelcome(self, on: bool) -> None:
        self.cfg.show_welcome = on
        self.settingsChanged.emit()

    # ----- périphériques -----
    @Slot()
    def refreshDevices(self) -> None:
        self._refresh_device_lists()

    def _refresh_device_lists(self, initial: bool = False) -> None:
        devs = dv.list_devices()
        found = dv.auto_detect(devs)
        self._input_devices = [d.name for d in dv.inputs(devs)]
        self._output_devices = [d.name for d in dv.outputs(devs)]
        self._virtual_found = found["virtual"] is not None
        # Périphériques retenus : ceux de la config s'ils existent, sinon l'auto-détection.
        for attr, kind, key in (("input_device", "input", "input"), ("virtual_device", "output", "virtual"),
                                ("monitor_device", "output", "monitor")):
            current = dv.find_by_name(getattr(self.cfg, attr), kind, devs)
            if current is None and (initial or getattr(self.cfg, attr) is None):
                current = found[key]
            if current is not None:
                setattr(self.cfg, attr, current.name)
        self.devicesChanged.emit()

    @Slot(str)
    def setInputDevice(self, name: str) -> None:
        self._set_device("input_device", name)

    @Slot(str)
    def setVirtualDevice(self, name: str) -> None:
        self._set_device("virtual_device", name)

    @Slot(str)
    def setMonitorDevice(self, name: str) -> None:
        self._set_device("monitor_device", name)

    def _set_device(self, attr: str, name: str) -> None:
        name = name or None
        if getattr(self.cfg, attr) == name:
            return
        setattr(self.cfg, attr, name)
        self.devicesChanged.emit()
        self._restart_if_live()

    def _watch_devices(self) -> None:
        names = {d.name for d in dv.list_devices()}
        if not self._live:
            return
        for label, name in (("micro", self.cfg.input_device), ("micro virtuel", self.cfg.virtual_device)):
            if name and name not in names:
                self.toast.emit("error", "Périphérique débranché",
                                f"Le {label} « {name} » n'est plus disponible. Le direct est arrêté.")
                self.stopLive()
                self._refresh_device_lists()
                return

    # ----- statut -----
    def _update_permission(self) -> None:
        status = microphone_status()
        if status != self._mic_permission:
            self._mic_permission = status
            self.permissionChanged.emit()

    def _tick(self) -> None:
        m = self.engine.metrics
        live = self._live and self.audio
        in_lvl = level_from_rms(m.rms_in) if live else 0.0
        out_lvl = level_from_rms(m.rms_out) if live else 0.0
        if self._live or any(self._history):
            self._history.append(in_lvl)
        if (in_lvl, out_lvl) != (self._in_level, self._out_level) or self._live:
            self._in_level, self._out_level = in_lvl, out_lvl
            self.levelsChanged.emit()
        if self._live:
            secs = int(time.monotonic() - self._session_t0)
            if secs != self._session:
                self._session = secs
                self.sessionSecondsChanged.emit()
        if live:
            if round(m.latency_ms) != round(self._latency) or m.xruns != self._xruns:
                self._latency, self._xruns = m.latency_ms, m.xruns
                self.statsChanged.emit()
            self._watch_xruns(m.xruns)
            self._watch_silence(m.rms_in)

    def _watch_xruns(self, xruns: int) -> None:
        now = time.monotonic()
        self._xrun_marks.append((now, xruns))
        while self._xrun_marks and now - self._xrun_marks[0][0] > 5.0:
            self._xrun_marks.popleft()
        if xruns - self._xrun_marks[0][1] >= 20 and now - self._last_xrun_toast > 60.0:
            self._last_xrun_toast = now
            self.toast.emit("error", "Le son saute",
                            "Les coupures audio augmentent. Ferme les apps gourmandes ou essaie un autre micro.")

    def _watch_silence(self, rms_in: float) -> None:
        # Micro refusé par macOS : le flux s'ouvre mais ne contient que des zéros.
        if rms_in > 0.0 or self._silence_warned:
            self._silent_since = None
            return
        now = time.monotonic()
        self._silent_since = self._silent_since or now
        if now - self._silent_since > 3.0:
            self._silence_warned = True
            self._update_permission()
            self.toast.emit("error", "Aucun son du micro",
                            "Vérifie l'accès au micro : Réglages Système → Confidentialité et sécurité → Micro.")

    # ----- fermeture -----
    @Slot()
    def saveConfig(self) -> None:
        try:
            save_config(self.cfg)
        except OSError as e:
            log.warning("Sauvegarde de la config impossible : %s", e)

    @Slot()
    def shutdown(self) -> None:
        self._timer.stop()
        self._device_timer.stop()
        if self.audio:
            self.engine.stop()
        self.hotkeys.stop()
        self.saveConfig()
