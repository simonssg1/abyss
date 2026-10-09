"""Configuration utilisateur : ~/.abyss/config.json (écriture atomique)."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger("abyss.config")

CONFIG_PATH = Path.home() / ".abyss" / "config.json"
LEGACY_CONFIG_PATH = Path.home() / ".vocoder" / "config.json"


def migrate_legacy_config(path: Path | None = None, legacy: Path | None = None) -> bool:
    """Copie (sans la déplacer) l'ancienne config ~/.vocoder si la nouvelle n'existe pas encore."""
    path = path or CONFIG_PATH
    legacy = legacy or LEGACY_CONFIG_PATH
    if path.exists() or not legacy.is_file():
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, path)
    except OSError as e:
        log.warning("Migration de %s impossible : %s", legacy, e)
        return False
    log.info("Config migrée depuis %s", legacy)
    return True


def default_hotkeys() -> dict[str, str]:
    keys = {f"preset_{i}": f"<ctrl>+<alt>+{i}" for i in range(1, 10)}
    keys["bypass"] = "<ctrl>+<alt>+0"
    keys["monitor"] = "<ctrl>+<alt>+m"
    return keys


@dataclass
class Config:
    input_device: str | None = None
    virtual_device: str | None = None
    monitor_device: str | None = None
    last_preset: str = "Normal"
    denoise: bool = True
    denoise_threshold_db: float = -45.0
    monitor: bool = False  # retour casque désactivé par défaut (risque de larsen)
    monitor_volume: float = 0.8
    output_gain_db: float = 0.0
    hotkeys: dict[str, str] = field(default_factory=default_hotkeys)
    show_welcome: bool = True
    window: list[int] | None = None  # [x, y, largeur, hauteur]


def load_config(path: Path | None = None) -> Config:
    if path is None:
        migrate_legacy_config()
    path = path or CONFIG_PATH
    cfg = Config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return cfg
    except (OSError, ValueError) as e:
        log.warning("Config illisible (%s), valeurs par défaut utilisées", e)
        return cfg
    for key, value in data.items():
        if key == "hotkeys" and isinstance(value, dict):
            cfg.hotkeys.update({str(k): str(v) for k, v in value.items()})
        elif hasattr(cfg, key):
            setattr(cfg, key, value)
    return cfg


def save_config(cfg: Config, path: Path | None = None) -> None:
    path = path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".config-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
