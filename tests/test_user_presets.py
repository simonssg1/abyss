import copy
import tomllib

import pytest

from abyss.presets import Preset, load_presets, parse_presets
from abyss.user_presets import dumps_presets, load_all_presets, save_user_presets, user_entries


@pytest.fixture
def defaults():
    presets, _ = load_presets()
    return presets


def test_old_and_new_format_load():
    old = tomllib.loads('[[preset]]\nname = "Ancien"\nhotkey_index = 3\neffects = [{ type = "gain", gain_db = -2 }]\n')
    new = tomllib.loads('[[preset]]\nname = "Nouveau"\ndescription = "d"\ncategories = ["Fun", "Inconnue"]\n'
                        'icon = "wind"\nbadge = "new"\nintensity = 0.4\ntone_low_hz = 200\ntone_high_hz = 5000\n'
                        'effects = []\n')
    (a,), wa = parse_presets(old)
    assert wa == [] and a.intensity == 1.0 and a.categories == [] and a.description == ""
    (b,), wb = parse_presets(new)
    assert (b.description, b.icon, b.badge, b.intensity, b.tone_low_hz, b.tone_high_hz) == ("d", "wind", "new", 0.4, 200, 5000)
    assert b.categories == ["Fun"] and len(wb) == 1  # catégorie inconnue signalée, preset conservé
    (c,), wc = parse_presets(tomllib.loads('[[preset]]\nname = "X"\nintensity = 3\ntone_low_hz = 900\ntone_high_hz = 100\n'))
    assert c.intensity == 1.0 and c.tone_low_hz == 50 and len(wc) == 2


def test_roundtrip_overlay_and_user_presets(tmp_path, defaults):
    path = tmp_path / "presets.toml"
    base = {p.id: p for p in defaults}
    merged = copy.deepcopy(defaults)
    merged[1].intensity = 0.5  # Robot modifié
    merged.append(Preset("Ma voix", None, [{"type": "gain", "gain_db": -3.0}], description="perso",
                         categories=["Fun"], badge="new", is_user=True, id="ma-voix"))
    ok, err = save_user_presets(merged, base, path)
    assert ok, err
    entries = tomllib.loads(path.read_text(encoding="utf-8"))["preset"]
    assert [e["id"] for e in entries] == ["robot", "ma-voix"]  # seuls les presets modifiés ou perso
    loaded, defs, warnings = load_all_presets(user_path=path)
    assert warnings == []
    assert [p.name for p in loaded][:8] == [p.name for p in defaults]
    robot = next(p for p in loaded if p.id == "robot")
    assert robot.intensity == 0.5 and not robot.is_user
    mine = next(p for p in loaded if p.id == "ma-voix")
    assert mine.is_user and mine.badge == "new" and mine.effects == [{"type": "gain", "gain_db": -3.0}]


def test_backup_and_atomic_write(tmp_path, defaults):
    path = tmp_path / "presets.toml"
    base = {p.id: p for p in defaults}
    user = [Preset("Un", None, [], is_user=True, id="un")]
    assert save_user_presets(defaults + user, base, path)[0]
    first = path.read_text(encoding="utf-8")
    user[0].description = "modifié"
    assert save_user_presets(defaults + user, base, path)[0]
    assert (tmp_path / "presets.toml.bak").read_text(encoding="utf-8") == first
    assert sorted(p.name for p in tmp_path.iterdir()) == ["presets.toml", "presets.toml.bak"]  # pas de temporaire


def test_invalid_preset_never_overwrites_valid_file(tmp_path, defaults):
    path = tmp_path / "presets.toml"
    base = {p.id: p for p in defaults}
    good = [Preset("Bon", None, [], is_user=True, id="bon")]
    assert save_user_presets(defaults + good, base, path)[0]
    before = path.read_text(encoding="utf-8")
    bad = [Preset("Mauvais", None, [{"type": "inconnu"}], is_user=True, id="mauvais")]
    ok, err = save_user_presets(defaults + good + bad, base, path)
    assert not ok and "inconnu" in err
    assert path.read_text(encoding="utf-8") == before
    nameless = [Preset("", None, [], is_user=True, id="vide")]
    assert not save_user_presets(defaults + nameless, base, path)[0]
    assert path.read_text(encoding="utf-8") == before


def test_unmodified_defaults_are_not_written(defaults):
    base = {p.id: p for p in defaults}
    from abyss.processors.schema import complete_effect

    edited = copy.deepcopy(defaults)
    for p in edited:  # l'éditeur complète les paramètres absents : ce n'est pas une modification
        p.effects = [complete_effect(e) for e in p.effects]
    assert user_entries(edited, base) == []


def test_dumps_escapes_strings():
    text = dumps_presets([{"id": "x", "name": 'Voix "spéciale" \\ test', "effects": []}])
    assert tomllib.loads(text)["preset"][0]["name"] == 'Voix "spéciale" \\ test'
