import os
import subprocess
import sys

import pytest

from vocoder.hotkeys import pretty


def test_gui_smoke_offscreen(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    proc = subprocess.run([sys.executable, "-m", "vocoder", "--no-audio", "--quit-after", "2"],
                          env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr
    assert (tmp_path / ".vocoder" / "config.json").exists()  # config sauvegardée à la fermeture


def test_window_interactions(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    import vocoder.config as config

    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from vocoder.gui import main_window
    from vocoder.presets import load_presets

    monkeypatch.setattr(main_window, "save_config", lambda cfg: config.save_config(cfg, tmp_path / "config.json"))
    presets, _ = load_presets()
    w = main_window.MainWindow(presets, config.Config(), audio=False)
    w.show()
    w.preset_buttons["Robot"].click()
    assert w.engine.preset.name == "Robot" and w.cfg.last_preset == "Robot"
    w.hotkeys.preset_requested.emit(4)  # comme si pynput avait capté Ctrl+Alt+4
    w.hotkeys.bypass_requested.emit()
    w.hotkeys.monitor_requested.emit()
    app.processEvents()
    assert w.engine.preset.name == "Démon" and w.preset_buttons["Démon"].isChecked()
    assert w.engine.bypass and w.cfg.monitor
    w.gain_slider.setValue(-6)
    assert w.engine.pipeline.output_gain_db == -6
    w._tick()
    w.close()
    assert (tmp_path / "config.json").exists()


def test_pretty_hotkey():
    assert pretty("<ctrl>+<alt>+m") == "Ctrl+Alt+M"
