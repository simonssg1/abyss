import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from abyss.audio.preview import pick_source, render_preview
from abyss.config import Config
from abyss.presets import find_preset, load_presets
from abyss.processors.tap import InputTap
from abyss.synth import synthetic_voice


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_tap_keeps_last_seconds_and_dedupes():
    tap = InputTap(seconds=1.0, sample_rate=1000)
    tap.enabled = True
    buf = np.zeros(250, dtype=np.float32)
    for k in range(6):  # même tableau réutilisé, contenu différent (comme le moteur)
        buf[:] = k + 1
        tap.process(buf)
        tap.process(buf)  # 2e chaîne pendant un crossfade : ignoré
    data, rate = tap.snapshot()
    assert rate == 1000 and len(data) == 1000
    assert list(np.unique(data)) == [3, 4, 5, 6]
    tap.enabled = False
    buf[:] = 99
    tap.process(buf)
    assert 99 not in tap.snapshot()[0]


def test_pick_source_fallback():
    sr = 48000
    src, origin = pick_source(np.zeros(100, dtype=np.float32), sr)
    assert origin == "synthétique" and len(src) <= 5 * sr
    voice = synthetic_voice(7.0, sr)
    src, origin = pick_source(voice, sr)
    assert origin == "micro" and len(src) == 5 * sr and np.array_equal(src, voice[-5 * sr:])


def test_render_preview_uses_separate_chain():
    presets, _ = load_presets()
    y = render_preview(find_preset(presets, "Robot"), synthetic_voice(2.0, 48000), 48000)
    assert len(y) == 96000 and np.all(np.isfinite(y)) and np.max(np.abs(y)) <= 1.0
    assert np.sqrt(np.mean(y ** 2)) > 0.01


def test_preview_never_touches_virtual_mic_buffer(qapp, tmp_path, monkeypatch):
    from abyss.ui.controller import AppController

    presets, _ = load_presets()
    cfg = Config(monitor_device="Casque test")
    ctrl = AppController(presets, cfg, audio=False, hotkeys=False, user_presets_path=tmp_path / "p.toml")
    ctrl.engine._prepare(48000)
    before = ctrl.engine._ring_virtual.available
    played = {}

    def fake_play(data, rate, device):
        played.update(data=data, rate=rate, device=device)

    monkeypatch.setattr(ctrl._player, "play", fake_play)
    monkeypatch.setattr(ctrl, "_monitor_index", lambda: 7)
    ctrl.togglePreview(ctrl.editDraft("robot"))
    assert ctrl.previewPlaying and ctrl.previewId == "robot"
    for _ in range(200):
        qapp.processEvents()
        if played:
            break
        import time
        time.sleep(0.02)
    assert played["device"] == 7 and len(played["data"]) <= 5 * 48000
    assert ctrl.engine._ring_virtual.available == before  # rien n'a été écrit vers le micro virtuel
    ctrl.togglePreview(ctrl.editDraft("robot"))  # 2e clic = arrêt
    assert not ctrl.previewPlaying
    ctrl.shutdown()


def test_preview_without_headphones_explains(qapp, tmp_path):
    from abyss.ui.controller import AppController

    presets, _ = load_presets()
    ctrl = AppController(presets, Config(monitor_device=None), audio=False, hotkeys=False,
                         user_presets_path=tmp_path / "p.toml")
    ctrl.cfg.monitor_device = None
    msgs = []
    ctrl.toast.connect(lambda k, t, m: msgs.append(t))
    ctrl.togglePreview(ctrl.editDraft("robot"))
    assert msgs == ["Casque non configuré"] and not ctrl.previewPlaying
    ctrl.shutdown()
