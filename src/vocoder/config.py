"""Configuration utilisateur : ~/.vocoder/config.json (écriture atomique)."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger("vocoder.config")

CONFIG_PATH = Path.home() / ".vocoder" / "config.json"


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


def load_config(path: Path | None = None) -> Config:
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
