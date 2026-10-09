from vocoder.config import Config, load_config, save_config


def test_roundtrip_and_atomic(tmp_path):
    path = tmp_path / "sub" / "config.json"
    assert load_config(path) == Config()
    cfg = Config(input_device="Micro", last_preset="Robot", monitor=True, output_gain_db=-3.0)
    cfg.hotkeys["bypass"] = "<ctrl>+<shift>+b"
    save_config(cfg, path)
    assert load_config(path) == cfg
    assert [p.name for p in path.parent.iterdir()] == ["config.json"]  # pas de fichier temporaire


def test_corrupt_config_falls_back(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{pas du json", encoding="utf-8")
    assert load_config(path) == Config()
