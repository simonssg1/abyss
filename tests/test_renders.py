from pathlib import Path

import numpy as np
from scipy.io import wavfile

from vocoder.__main__ import main

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "synthetic_voice.wav"


def test_synthetic_sample_format():
    rate, x = wavfile.read(SAMPLE)
    assert rate == 48000 and len(x) == 5 * 48000 and x.ndim == 1


def test_render_all_not_silent_not_clipped(tmp_path):
    assert main(["--render-all", str(SAMPLE), "--renders-dir", str(tmp_path)]) == 0
    files = sorted(tmp_path.glob("*.wav"))
    assert len(files) == 8
    for f in files:
        rate, y = wavfile.read(f)
        assert rate == 48000 and np.all(np.isfinite(y))
        assert np.sqrt(np.mean(y.astype(np.float64) ** 2)) > 0.02, f"{f.name} silencieux"
        assert np.max(np.abs(y)) < 0.999, f"{f.name} écrêté"
