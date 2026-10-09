import time

import numpy as np
from scipy.io import wavfile

from conftest import BLOCK, SR
from vocoder.__main__ import main
from vocoder.audio.engine import AudioEngine, Pipeline
from vocoder.presets import find_preset, load_presets


def test_engine_thread_with_simulated_callbacks(voice5):
    presets, _ = load_presets(None, SR)
    eng = AudioEngine(presets, monitor=True)
    eng._prepare(SR)
    eng.devices = {"input": 0, "virtual": 1, "monitor": 2}
    eng._start_thread()
    out_v = np.zeros((BLOCK, 2), dtype=np.float32)
    out_m = np.zeros((BLOCK, 2), dtype=np.float32)
    collected = []
    try:
        for k, i in enumerate(range(0, SR * 2, BLOCK)):
            eng._in_cb(voice5[i : i + BLOCK, None], BLOCK, None, None)
            if k == 50:
                eng.set_preset(find_preset(presets, "Robot"))  # échange en plein traitement
            if k == 120:
                eng.set_bypass(True)
            time.sleep(0.0005)
            eng._virtual_cb(out_v, BLOCK, None, None)
            eng._monitor_cb(out_m, BLOCK, None, None)
            assert np.array_equal(out_v[:, 0], out_v[:, 1])
            collected.append(out_v[:, 0].copy())
    finally:
        eng.stop()
    y = np.concatenate(collected)
    assert np.all(np.isfinite(y)) and np.max(np.abs(y)) <= 1.0
    assert np.sqrt(np.mean(y[SR // 2 :] ** 2)) > 0.01
    assert eng.metrics.rms_in > 0 and eng.metrics.latency_ms > 0
    assert eng.bypass and eng.preset.name == "Robot"


def test_pipeline_swap_uses_crossfade():
    presets, _ = load_presets(None, SR)
    pipe = Pipeline(SR)
    pipe.set_preset(presets[0])
    x = np.full(BLOCK, 0.3, dtype=np.float32)
    pipe.process(x)
    pipe.set_preset(find_preset(presets, "Robot"))
    pipe.process(x)
    assert pipe.switcher.fading


def test_render_cli(tmp_path):
    src = tmp_path / "in.wav"
    t = np.arange(22050) / 22050
    wavfile.write(src, 22050, (0.4 * np.sin(2 * np.pi * 150 * t) * 32767).astype(np.int16))  # rééchantillonnage
    out = tmp_path / "out.wav"
    assert main(["--render", str(src), "--preset", "robot", "--out", str(out)]) == 0
    rate, y = wavfile.read(out)
    assert rate == SR and len(y) == SR and y.dtype == np.float32
    assert main(["--render-all", str(src), "--renders-dir", str(tmp_path / "r")]) == 0
    assert len(list((tmp_path / "r").glob("*.wav"))) == 8


def test_list_devices_cli(capsys):
    assert main(["--list-devices"]) == 0
    assert capsys.readouterr().out.strip()
