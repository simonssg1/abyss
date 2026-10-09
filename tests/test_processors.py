import numpy as np
import pytest

from conftest import BLOCK, SR, stream
from abyss.processors.base import BlockAdapter, Chain, ChainSwitcher
from abyss.processors.denoise import Denoiser
from abyss.processors.fx import FX_TYPES, PitchShift, make_fx
from abyss.processors.robot import RingModulator
from abyss.processors.rvc import RVCProcessor
from abyss.processors.vocoder import ChannelVocoder
from abyss.synth import synthetic_voice

FX_PARAMS = {
    "pitch_shift": {"semitones": -6}, "reverb": {"room_size": 0.9, "wet_level": 0.4},
    "distortion": {"drive_db": 12}, "chorus": {}, "delay": {"delay_seconds": 0.2},
    "bitcrush": {"bit_depth": 8}, "highpass": {"cutoff_frequency_hz": 400},
    "lowpass": {"cutoff_frequency_hz": 3000}, "compressor": {"threshold_db": -20, "ratio": 4},
    "noise_gate": {"threshold_db": -45}, "gain": {"gain_db": -3},
}


def all_processors():
    procs = [make_fx(k, FX_PARAMS[k], SR) for k in FX_TYPES]
    procs += [RingModulator(60, 1.0, SR), ChannelVocoder(20, 110, True, 1.0, SR), Denoiser(-45, SR)]
    return procs


@pytest.mark.parametrize("proc", all_processors(), ids=lambda p: p.name)
def test_processor_streaming(proc, voice5):
    y = stream(proc, voice5)
    assert np.all(np.isfinite(y))
    assert np.sqrt(np.mean(y[SR:] ** 2)) > 1e-3, "sortie silencieuse"


def test_chain_output_bounded_at_plus_6db(voice5):
    hot = voice5 / np.max(np.abs(voice5)) * 2.0  # +6 dB au-dessus de la pleine échelle
    for effects in (all_processors(), [], [make_fx("distortion", {"drive_db": 30}, SR)]):
        chain = Chain(effects, SR, output_gain_db=12.0)
        y = stream(chain, hot.astype(np.float32))
        assert np.all(np.isfinite(y))
        assert np.max(np.abs(y)) <= 1.0


def _max_step(x):
    return np.max(np.abs(np.diff(x)))


def test_ring_mod_phase_continuity():
    blocky = RingModulator(60.0, 1.0, SR)
    once = RingModulator(60.0, 1.0, SR)
    ones = np.ones(SR, dtype=np.float32)
    a = stream(blocky, ones)
    b = once.process(ones)[: len(a)]
    assert np.allclose(a, b, atol=1e-4)
    # pas de saut aux frontières de bloc : le pas max reste celui d'un sinus continu
    assert _max_step(a) <= 2 * np.pi * 60 / SR * 1.01


def test_vocoder_carrier_phase_continuity():
    blocky = ChannelVocoder(20, 110.0, True, 1.0, SR)
    once = ChannelVocoder(20, 110.0, True, 1.0, SR)
    n = SR
    a = np.concatenate([blocky.carrier(BLOCK) for _ in range(n // BLOCK)])
    b = once.carrier(n // BLOCK * BLOCK)
    # identiques à l'arrondi près (un échantillon pile sur une retombée peut basculer d'un côté)
    assert np.mean(np.abs(a - b) < 1e-6) > 0.999
    d = (blocky._osc_phase - once._osc_phase + 0.5) % 1.0 - 0.5
    assert np.all(np.abs(d) < 1e-9)
    # aux frontières, le pas est un pas normal (pas un saut) sauf lors des retombées de la dent de scie
    edges = np.arange(BLOCK, len(a), BLOCK)
    normal = np.median(np.abs(np.diff(b)))
    steps = np.abs(a[edges] - a[edges - 1])
    wraps = np.abs(b[edges] - b[edges - 1])
    assert np.mean(np.abs(steps - wraps) < 1e-6) > 0.9
    assert np.mean(steps < 10 * normal) > 0.9


def test_vocoder_voiced_nonzero_and_stable():
    voc = ChannelVocoder(20, 110.0, True, 1.0, SR)
    x = synthetic_voice(10.0, SR)
    y = stream(voc, x)
    assert np.all(np.isfinite(y))
    rms = [np.sqrt(np.mean(y[i : i + SR] ** 2)) for i in range(0, len(y) - SR + 1, SR)]
    assert min(rms) > 0.01
    assert max(rms) < 2.0  # pas de divergence
    assert max(rms[-3:]) < 3 * min(rms[:3]) + 0.1


def _dominant_hz(x):
    w = np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x * w))
    return np.argmax(spec) * SR / len(x)


@pytest.mark.parametrize("semitones", [-6, 7])
def test_pitch_shift_after_warmup(semitones):
    t = np.arange(3 * SR) / SR
    x = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    ps = PitchShift(semitones, SR)
    y = stream(ps, x)
    warm = ps.latency_samples * 4
    seg = y[warm : warm + SR]
    expected = 220 * 2 ** (semitones / 12)
    assert abs(_dominant_hz(seg) - expected) < expected * 0.05
    # flux par blocs == traitement en une fois, après la chauffe
    ref = PitchShift(semitones, SR).process(x[: len(y)])
    assert np.allclose(y[warm:], ref[warm:], atol=1e-5)


def test_block_adapter_latency_and_identity():
    class Ident:
        name = "ident"
        preferred_block = 1000
        latency_samples = 0

        def process(self, b):
            assert len(b) == 1000
            return b.copy()

        def reset(self):
            pass

    ad = BlockAdapter(Ident())
    x = np.random.default_rng(1).standard_normal(SR).astype(np.float32)
    y = stream(ad, x)
    assert ad.latency_samples == 1000
    assert np.allclose(y[1000:], x[: len(y) - 1000])
    chain = Chain([Ident()], SR)
    assert chain.latency_samples == 1000


def test_denoiser_hot_threshold():
    d = Denoiser(-45, SR)
    d.threshold_db = -30
    assert d.threshold_db == pytest.approx(-30)
    quiet = (0.001 * np.random.default_rng(2).standard_normal(SR)).astype(np.float32)
    y = stream(d, quiet)
    assert np.sqrt(np.mean(y[SR // 2 :] ** 2)) < np.sqrt(np.mean(quiet ** 2))


def test_chain_swap_with_crossfade(voice5):
    import threading

    sw = ChainSwitcher(Chain([], SR), SR, fade_ms=20)
    errors = []
    outs = []

    def worker():
        try:
            for i in range(0, len(voice5) - BLOCK, BLOCK):
                outs.append(sw.process(voice5[i : i + BLOCK]))
        except Exception as e:  # pragma: no cover
            errors.append(e)

    th = threading.Thread(target=worker)
    th.start()
    for k in range(30):
        sw.swap(Chain([RingModulator(60 + k, 1.0, SR)] if k % 2 else [make_fx("bitcrush", {"bit_depth": 8}, SR)], SR))
    th.join()
    assert not errors
    y = np.concatenate(outs)
    assert np.all(np.isfinite(y)) and np.max(np.abs(y)) <= 1.0


def test_crossfade_is_progressive():
    sr = SR
    sw = ChainSwitcher(Chain([make_fx("gain", {"gain_db": -120}, sr)], sr), sr, fade_ms=20)
    dc = np.full(BLOCK, 0.5, dtype=np.float32)
    sw.process(dc)
    new = Chain([], sr)
    ref_chain = Chain([], sr)
    sw.swap(new)
    out = np.concatenate([sw.process(dc) for _ in range(6)])
    ref = np.concatenate([ref_chain.process(dc) for _ in range(6)])
    fade = int(0.02 * sr)
    assert out[0] < 0.01
    assert np.all(out[:fade] <= ref[:fade] + 1e-6)  # l'ancienne (muette) s'efface progressivement
    assert out[fade // 2] == pytest.approx(0.5 * ref[fade // 2], rel=0.05)
    assert np.allclose(out[fade:], ref[fade:], atol=1e-6)
    assert not sw.fading


def test_rvc_stub():
    with pytest.raises(NotImplementedError):
        RVCProcessor()
    assert "ContentVec" in RVCProcessor.__doc__
