import tomllib

import numpy as np

from conftest import SR, stream
from abyss.presets import DEFAULT_PRESETS, build_chain, find_preset, load_presets, parse_presets


def test_default_presets_file():
    presets, warnings = load_presets(DEFAULT_PRESETS, SR)
    assert warnings == []
    names = [p.name for p in presets]
    assert names == ["Normal", "Robot", "Vocodeur", "Démon", "Hélium", "Talkie-walkie", "Cathédrale", "Alien"]
    assert [p.hotkey_index for p in presets] == list(range(1, 9))
    assert find_preset(presets, "démon").effects[0] == {"type": "pitch_shift", "semitones": -6}


def test_invalid_presets_and_rvc():
    data = tomllib.loads("""
[[preset]]
hotkey_index = 3
effects = []

[[preset]]
name = "Mauvais raccourci"
hotkey_index = "x"

[[preset]]
name = "Mixte"
hotkey_index = 2
effects = [
  { type = "rvc", voice = "test" },
  { type = "inconnu" },
  { type = "reverb", pas_un_param = 1 },
  { type = "vocoder", bands = 99 },
  "pas une table",
  { type = "gain", gain_db = -2 },
]
""")
    presets, warnings = parse_presets(data, SR)
    assert [p.name for p in presets] == ["Mixte"]
    assert presets[0].effects == [{"type": "gain", "gain_db": -2}]
    assert any("disponible en v2" in w for w in warnings)
    assert any("inconnu" in w for w in warnings)
    assert any("name" in w for w in warnings)
    assert len(warnings) == 7


def test_unreadable_file_falls_back(tmp_path):
    bad = tmp_path / "p.toml"
    bad.write_text("[[preset]\nname=", encoding="utf-8")
    presets, warnings = load_presets(bad, SR)
    assert [p.name for p in presets] == ["Normal"] and warnings


def test_every_preset_chain_streams(voice5):
    presets, _ = load_presets(None, SR)
    for p in presets:
        y = stream(build_chain(p, SR), voice5)
        assert np.all(np.isfinite(y)) and np.max(np.abs(y)) <= 1.0
        assert np.sqrt(np.mean(y ** 2)) > 0.01, p.name
