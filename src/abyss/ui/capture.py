"""Captures d'écran hors écran des vues QML (vérification visuelle)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def grab(window, path: str | Path, settle_ms: int = 600) -> None:
    wait(settle_ms)
    img = window.grabWindow()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))


def main(argv: list[str]) -> int:
    from abyss.ui.app import create_app, create_engine, qml_warnings
    from abyss.ui.resources import QML_DIR

    target, out, size = argv[0], argv[1], argv[2] if len(argv) > 2 else "1200x860"
    w, h = (int(v) for v in size.split("x"))
    app = create_app([])
    engine = create_engine()
    engine.load(str(QML_DIR / f"{target}.qml"))
    win = engine.rootObjects()[0]
    win.setWidth(w)
    win.setHeight(h)
    grab(win, out)
    for warn in qml_warnings():
        print("QML WARNING:", warn)
    app.quit()
    return 1 if qml_warnings() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
