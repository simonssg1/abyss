"""Raccourcis globaux : pynput (thread dédié) → signaux Qt (traités dans le thread principal)."""

from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import QObject, Signal

log = logging.getLogger("abyss.hotkeys")

BUNDLE_ID = "com.simonssg1.abyss"


def permission_target() -> str:
    """À qui macOS attribue les autorisations : l'app Abyss (lanceur) ou le terminal (uv run)."""
    return "Abyss" if os.environ.get("__CFBundleIdentifier") == BUNDLE_ID else "ton terminal"


if sys.platform == "darwin":
    PERMISSION_HINT = (f"Autorise {permission_target()} dans Réglages Système → Confidentialité et sécurité → "
                       "Surveillance de l'entrée")
else:
    PERMISSION_HINT = "Relance Abyss ; si ça persiste, un antivirus ou un autre logiciel bloque peut-être le clavier"


def pretty(combo: str) -> str:
    """'<ctrl>+<alt>+1' → 'Ctrl+Alt+1'."""
    parts = [p.strip("<>") for p in combo.split("+")]
    return "+".join(p.capitalize() if len(p) > 1 else p.upper() for p in parts)


class HotkeyBridge(QObject):
    preset_requested = Signal(int)  # hotkey_index du preset
    bypass_requested = Signal()
    monitor_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._listener = None
        self.active = False
        self.status = "inactifs"

    def start(self, hotkeys: dict[str, str]) -> bool:
        """Démarre le listener. En cas d'échec, l'app continue sans raccourcis."""
        self.stop()
        try:
            from pynput.keyboard import GlobalHotKeys, HotKey
        except Exception as e:  # pas de serveur X, etc.
            return self._fail(f"pynput indisponible ({e})")

        mapping = {}
        for action, combo in hotkeys.items():
            try:
                HotKey.parse(combo)
            except ValueError:
                log.warning("Raccourci invalide ignoré : %s = %s", action, combo)
                continue
            if action.startswith("preset_") and action[7:].isdigit():
                idx = int(action[7:])
                mapping[combo] = lambda i=idx: self.preset_requested.emit(i)
            elif action == "bypass":
                mapping[combo] = self.bypass_requested.emit
            elif action == "monitor":
                mapping[combo] = self.monitor_requested.emit
        try:
            self._listener = GlobalHotKeys(mapping)
            self._listener.daemon = True
            self._listener.start()
            self._listener.wait()
        except Exception as e:
            return self._fail(str(e))
        # macOS : si la « Surveillance de l'entrée » est refusée, pynput ne peut pas créer son
        # event tap et son thread s'arrête aussitôt. (Son avertissement « not trusted » ne concerne
        # que l'Accessibilité, inutile pour une écoute passive : on ne s'y fie pas.)
        self._listener.join(timeout=0.3)
        if not self._listener.is_alive():
            self._listener = None
            return self._fail("permissions manquantes" if sys.platform == "darwin" else "le listener s'est arrêté")
        self.active = True
        self.status = "actifs"
        return True

    def _fail(self, reason: str) -> bool:
        log.warning("Raccourcis désactivés : %s. %s", reason, PERMISSION_HINT)
        self.active = False
        self.status = f"désactivés ({reason})"
        return False

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
                self._listener.join(timeout=1.0)
            except Exception:
                pass
            self._listener = None
        self.active = False
