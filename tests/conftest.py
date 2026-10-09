import numpy as np
import pytest

from vocoder.synth import synthetic_voice

SR = 48000
BLOCK = 256


def stream(proc, x, block=BLOCK):
    """Traite x par blocs ; vérifie longueur et dtype de chaque bloc."""
    out = []
    for i in range(0, len(x) - len(x) % block, block):
        y = proc.process(x[i : i + block])
        assert len(y) == block, f"{proc.name}: longueur {len(y)} != {block}"
        assert y.dtype == np.float32, f"{proc.name}: dtype {y.dtype}"
        out.append(y)
    return np.concatenate(out)


@pytest.fixture(scope="session")
def voice5():
    return synthetic_voice(5.0, SR)
