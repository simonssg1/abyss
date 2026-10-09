"""Réglages propres à Windows (ctypes, sans dépendance)."""

from __future__ import annotations

import sys

APP_USER_MODEL_ID = "simonssg1.Abyss"


def set_app_user_model_id() -> None:
    """Barre des tâches : Abyss a sa propre icône au lieu d'être regroupé sous « Python »."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass
