"""Raccourcis globaux : pynput (thread dédié) → signaux Qt (traités dans le thread principal)."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QObject, Signal

log = logging.getLogger("vocoder.hotkeys")

PERMISSION_HINT = ("Autorise ton terminal dans Réglages Système → Confidentialité et sécurité → "
                   "Accessibilité et Surveillance de l'entrée")


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
        if sys.platform == "darwin" and not getattr(self._listener, "IS_TRUSTED", True):
            self.stop()
            return self._fail("permissions manquantes")
        if not self._listener.is_alive():
            return self._fail("le listener s'est arrêté")
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
