import numpy as np

from abyss.audio.ringbuffer import RingBuffer


def test_roundtrip_with_wraparound():
    rb = RingBuffer(10)
    out = np.empty(4, dtype=np.float32)
    for k in range(20):
        data = np.arange(k * 4, k * 4 + 4, dtype=np.float32)
        rb.write(data)
        assert rb.read_into(out) == 4
        assert np.array_equal(out, data)
    assert rb.xruns == 0


def test_underflow_gives_silence_and_counts():
    rb = RingBuffer(16)
    rb.write(np.ones(3, dtype=np.float32))
    out = np.full(8, 9.0, dtype=np.float32)
    assert rb.read_into(out) == 3
    assert np.array_equal(out, [1, 1, 1, 0, 0, 0, 0, 0])
    assert rb.underflows == 1 and rb.xruns == 1


def test_overflow_drops_oldest_and_counts():
    rb = RingBuffer(8)
    rb.write(np.arange(6, dtype=np.float32))
    rb.write(np.arange(6, 12, dtype=np.float32))
    assert rb.overflows == 1 and rb.available == 8
    out = np.empty(8, dtype=np.float32)
    rb.read_into(out)
    assert np.array_equal(out, np.arange(4, 12))
    rb.write(np.arange(100, dtype=np.float32))  # plus grand que la capacité
    rb.read_into(out)
    assert np.array_equal(out, np.arange(92, 100))
    assert rb.xruns == 1  # écriture géante sur buffer vide : pas de perte de données en attente


def test_reads_into_strided_view():
    rb = RingBuffer(32)
    rb.write(np.arange(8, dtype=np.float32))
    stereo = np.zeros((8, 2), dtype=np.float32)
    rb.read_into(stereo[:, 0])
    assert np.array_equal(stereo[:, 0], np.arange(8)) and not stereo[:, 1].any()
