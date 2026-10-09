"""Fenêtre principale PySide6 : périphériques, voix, contrôles, statut."""

from __future__ import annotations

import logging
import math
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QMainWindow, QProgressBar,
                               QPushButton, QSlider, QVBoxLayout, QWidget)

from vocoder.audio import devices as dv
from vocoder.audio.engine import AudioEngine
from vocoder.config import Config, save_config
from vocoder.hotkeys import PERMISSION_HINT, HotkeyBridge, pretty
from vocoder.presets import Preset, find_preset

log = logging.getLogger("vocoder.gui")

NONE_LABEL = "(aucun)"
STYLE = """
QPushButton[preset="true"] { padding: 4px; min-height: 40px; }
QPushButton[preset="true"]:checked {
    background: palette(highlight); color: palette(highlighted-text); font-weight: bold;
}
QLabel#warning { color: #d9822b; font-weight: bold; }
QLabel#error { color: #d64545; }
"""


def _db(x: float) -> float:
    return 20.0 * math.log10(max(x, 1e-6))


class MainWindow(QMainWindow):
    def __init__(self, presets: list[Preset], cfg: Config, audio: bool = True,
                 initial_preset: str | None = None):
        super().__init__()
        self.presets = presets
        self.cfg = cfg
        self.audio = audio
        self.setWindowTitle("Vocoder")
        self.resize(420, 640)
        self.setStyleSheet(STYLE)

        self.engine = AudioEngine(presets, cfg.denoise, cfg.denoise_threshold_db, cfg.monitor,
                                  cfg.monitor_volume, cfg.output_gain_db)
        start = find_preset(presets, initial_preset or cfg.last_preset) or presets[0]
        self.engine.set_preset(start)

        central = QWidget()
        root = QVBoxLayout(central)
        root.addWidget(self._build_devices())
        root.addWidget(self._build_voices())
        root.addWidget(self._build_controls())
        root.addWidget(self._build_status())
        root.addStretch(1)
        self.setCentralWidget(central)

        self.hotkeys = HotkeyBridge(self)
        self.hotkeys.preset_requested.connect(self._on_hotkey_preset)
        self.hotkeys.bypass_requested.connect(self.bypass_box.toggle)
        self.hotkeys.monitor_requested.connect(self.monitor_box.toggle)
        if not self.hotkeys.start(cfg.hotkeys):
            self.hotkey_hint.setText(PERMISSION_HINT)
            self.hotkey_hint.show()

        self._select_preset_button(start)
        self.refresh_devices(restart=True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)  # ~30 Hz

    # ----- construction -----
    def _build_devices(self) -> QGroupBox:
        box = QGroupBox("Périphériques")
        grid = QGridLayout(box)
        self.input_combo, self.virtual_combo, self.monitor_combo = QComboBox(), QComboBox(), QComboBox()
        for row, (label, combo) in enumerate([("Micro", self.input_combo),
                                              ("Micro virtuel", self.virtual_combo),
                                              ("Casque", self.monitor_combo)]):
            grid.addWidget(QLabel(label), row, 0)
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(18)
            combo.currentIndexChanged.connect(self._on_device_changed)
            grid.addWidget(combo, row, 1)
        refresh = QPushButton("Rafraîchir")
        refresh.clicked.connect(lambda: self.refresh_devices(restart=True))
        grid.addWidget(refresh, 3, 1, alignment=Qt.AlignmentFlag.AlignRight)
        self.speaker_warning = QLabel("⚠ Retour sur haut-parleurs : risque de larsen !")
        self.speaker_warning.setObjectName("warning")
        self.speaker_warning.setWordWrap(True)
        self.speaker_warning.hide()
        grid.addWidget(self.speaker_warning, 4, 0, 1, 2)
        self.virtual_warning = QLabel("⚠ Aucun micro virtuel (BlackHole 2ch / VB-CABLE)")
        self.virtual_warning.setObjectName("warning")
        self.virtual_warning.setWordWrap(True)
        self.virtual_warning.hide()
        grid.addWidget(self.virtual_warning, 5, 0, 1, 2)
        return box

    def _build_voices(self) -> QGroupBox:
        box = QGroupBox("Voix")
        grid = QGridLayout(box)
        self.preset_group = QButtonGroup(self)
        self.preset_group.setExclusive(True)
        self.preset_buttons: dict[str, QPushButton] = {}
        for i, p in enumerate(self.presets):
            text = p.name
            combo = self.cfg.hotkeys.get(f"preset_{p.hotkey_index}") if p.hotkey_index else None
            if combo:
                text += f"\n{pretty(combo)}"
            btn = QPushButton(text)
            btn.setProperty("preset", True)
            btn.setMinimumHeight(44)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, preset=p: self.select_preset(preset))
            self.preset_group.addButton(btn)
            self.preset_buttons[p.name] = btn
            grid.addWidget(btn, i // 2, i % 2)
        return box

    def _slider(self, lo: int, hi: int, value: float, slot) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(int(round(value)))
        s.valueChanged.connect(slot)
        return s

    def _build_controls(self) -> QGroupBox:
        box = QGroupBox("Contrôles")
        grid = QGridLayout(box)
        self.bypass_box = QCheckBox(f"Bypass ({pretty(self.cfg.hotkeys.get('bypass', ''))})")
        self.bypass_box.toggled.connect(self._on_bypass)
        grid.addWidget(self.bypass_box, 0, 0, 1, 3)

        self.denoise_box = QCheckBox("Débruitage")
        self.denoise_box.setChecked(self.cfg.denoise)
        self.denoise_box.toggled.connect(self._on_denoise)
        self.threshold_label = QLabel()
        self.threshold_slider = self._slider(-80, -20, self.cfg.denoise_threshold_db, self._on_threshold)
        grid.addWidget(self.denoise_box, 1, 0)
        grid.addWidget(self.threshold_slider, 1, 1)
        grid.addWidget(self.threshold_label, 1, 2)

        self.monitor_box = QCheckBox(f"Retour casque ({pretty(self.cfg.hotkeys.get('monitor', ''))})")
        self.monitor_box.setChecked(self.cfg.monitor)
        self.monitor_box.toggled.connect(self._on_monitor)
        self.volume_label = QLabel()
        self.volume_slider = self._slider(0, 100, self.cfg.monitor_volume * 100, self._on_volume)
        grid.addWidget(self.monitor_box, 2, 0)
        grid.addWidget(self.volume_slider, 2, 1)
        grid.addWidget(self.volume_label, 2, 2)

        self.gain_label = QLabel()
        self.gain_slider = self._slider(-12, 12, self.cfg.output_gain_db, self._on_gain)
        grid.addWidget(QLabel("Gain de sortie"), 3, 0)
        grid.addWidget(self.gain_slider, 3, 1)
        grid.addWidget(self.gain_label, 3, 2)
        for lbl in (self.threshold_label, self.volume_label, self.gain_label):
            lbl.setMinimumWidth(56)
        self._on_threshold(self.threshold_slider.value())
        self._on_volume(self.volume_slider.value())
        self._on_gain(self.gain_slider.value())
        self.threshold_slider.setEnabled(self.cfg.denoise)
        return box

    def _build_status(self) -> QGroupBox:
        box = QGroupBox("Statut")
        grid = QGridLayout(box)
        self.vu_in, self.vu_out = QProgressBar(), QProgressBar()
        for row, (label, bar) in enumerate([("Entrée", self.vu_in), ("Sortie", self.vu_out)]):
            bar.setRange(0, 600)  # -60 dB … 0 dB, au dixième
            bar.setTextVisible(False)
            bar.setFixedHeight(12)
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(bar, row, 1)
        self.latency_label = QLabel("Latence : –")
        self.xruns_label = QLabel("Xruns : 0")
        line = QHBoxLayout()
        line.addWidget(self.latency_label)
        line.addStretch(1)
        line.addWidget(self.xruns_label)
        grid.addLayout(line, 2, 0, 1, 2)
        self.hotkey_label = QLabel("Raccourcis : –")
        grid.addWidget(self.hotkey_label, 3, 0, 1, 2)
        self.hotkey_hint = QLabel()
        self.hotkey_hint.setObjectName("warning")
        self.hotkey_hint.setWordWrap(True)
        self.hotkey_hint.hide()
        grid.addWidget(self.hotkey_hint, 4, 0, 1, 2)
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)
        grid.addWidget(self.error_label, 5, 0, 1, 2)
        return box

    # ----- périphériques -----
    def refresh_devices(self, restart: bool = False) -> None:
        devs = dv.list_devices()
        found = dv.auto_detect(devs)

        def fill(combo: QComboBox, pool: list, wanted: str | None, auto, allow_none: bool):
            combo.blockSignals(True)
            combo.clear()
            if allow_none:
                combo.addItem(NONE_LABEL, None)
            for d in pool:
                combo.addItem(d.name, d.name)
            target = dv.find_by_name(wanted, "output" if allow_none else "input", devs) or auto
            i = combo.findData(target.name) if target else -1
            combo.setCurrentIndex(i if i >= 0 else 0)
            combo.blockSignals(False)

        fill(self.input_combo, dv.inputs(devs), self.cfg.input_device, found["input"], False)
        fill(self.virtual_combo, dv.outputs(devs), self.cfg.virtual_device, found["virtual"], True)
        fill(self.monitor_combo, dv.outputs(devs), self.cfg.monitor_device, found["monitor"], True)
        if restart:
            self._restart_audio()

    def _on_device_changed(self, *_):
        self._restart_audio()

    def _restart_audio(self) -> None:
        self.cfg.input_device = self.input_combo.currentData()
        self.cfg.virtual_device = self.virtual_combo.currentData()
        self.cfg.monitor_device = self.monitor_combo.currentData()
        self.speaker_warning.setVisible(dv.is_speaker_like(self.cfg.monitor_device))
        self.virtual_warning.setVisible(self.cfg.virtual_device is None)
        if not self.audio:
            return
        devs = dv.list_devices()

        def idx(name, kind):
            d = dv.find_by_name(name, kind, devs)
            return d.index if d else None

        self.engine.start(idx(self.cfg.input_device, "input"), idx(self.cfg.virtual_device, "output"),
                          idx(self.cfg.monitor_device, "output"))

    # ----- voix -----
    def select_preset(self, preset: Preset) -> None:
        self.engine.set_preset(preset)
        self.cfg.last_preset = preset.name
        self._select_preset_button(preset)

    def _select_preset_button(self, preset: Preset) -> None:
        btn = self.preset_buttons.get(preset.name)
        if btn:
            btn.setChecked(True)

    def _on_hotkey_preset(self, index: int) -> None:
        for p in self.presets:
            if p.hotkey_index == index:
                self.select_preset(p)
                return

    # ----- contrôles -----
    def _on_bypass(self, on: bool) -> None:
        self.engine.set_bypass(on)

    def _on_denoise(self, on: bool) -> None:
        self.cfg.denoise = on
        self.engine.set_denoise(enabled=on)
        self.threshold_slider.setEnabled(on)

    def _on_threshold(self, v: int) -> None:
        self.cfg.denoise_threshold_db = float(v)
        self.engine.set_denoise(threshold_db=float(v))
        self.threshold_label.setText(f"{v} dB")

    def _on_monitor(self, on: bool) -> None:
        self.cfg.monitor = on
        self.engine.set_monitor(enabled=on)

    def _on_volume(self, v: int) -> None:
        self.cfg.monitor_volume = v / 100.0
        self.engine.set_monitor(volume=v / 100.0)
        self.volume_label.setText(f"{v} %")

    def _on_gain(self, v: int) -> None:
        self.cfg.output_gain_db = float(v)
        self.engine.set_output_gain(float(v))
        self.gain_label.setText(f"{v:+d} dB")

    # ----- statut -----
    def _tick(self) -> None:
        m = self.engine.metrics
        self.vu_in.setValue(int(max(0.0, _db(m.rms_in) + 60.0) * 10))
        self.vu_out.setValue(int(max(0.0, _db(m.rms_out) + 60.0) * 10))
        if m.running:
            self.latency_label.setText(f"Latence : {m.latency_ms:.0f} ms ({m.sample_rate} Hz)")
        else:
            self.latency_label.setText("Latence : – (audio arrêté)")
        self.xruns_label.setText(f"Xruns : {m.xruns}")
        self.hotkey_label.setText(f"Raccourcis : {self.hotkeys.status}")
        self.error_label.setText(m.error)

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.engine.stop()
        self.hotkeys.stop()
        try:
            save_config(self.cfg)
        except OSError as e:
            log.warning("Sauvegarde de la config impossible : %s", e)
        super().closeEvent(event)


def run_gui(presets: list[Preset], cfg: Config, audio: bool = True, quit_after: float | None = None,
            initial_preset: str | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Vocoder")
    win = MainWindow(presets, cfg, audio=audio, initial_preset=initial_preset)
    win.show()
    if quit_after:
        QTimer.singleShot(int(quit_after * 1000), win.close)
    return app.exec()
