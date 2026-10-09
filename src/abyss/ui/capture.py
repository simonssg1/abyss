"""Captures d'écran hors écran des vues QML (vérification visuelle).

    python -m abyss.ui.capture GalleryWindow out.png 1200x860     # un fichier QML
    python -m abyss.ui.capture --screens docs/screenshots          # tous les écrans, 420×780 et 1200×780
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QMetaObject, QTimer

SIZES = ((420, 780), (1200, 780))


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def grab(window, path: str | Path, settle_ms: int = 600) -> None:
    wait(settle_ms)
    img = window.grabWindow()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))


def _fake_levels():
    t = {"v": 0.0}

    def source():
        t["v"] += 0.033
        x = t["v"]
        lvl = 0.55 + 0.35 * abs(math.sin(x * 2.3)) * abs(math.sin(x * 0.9 + 1))
        return lvl, min(1.0, lvl * 1.05)

    return source


def capture_screens(outdir: str | Path) -> list[str]:
    """Capture Accueil, Direct (repos/actif), Voix, Éditeur, Réglages, Galerie dans les deux formats."""
    from abyss.config import Config
    from abyss.presets import load_presets
    from abyss.ui.app import create_app, create_engine, load_main, qml_warnings
    from abyss.ui.controller import AppController
    from abyss.ui.resources import QML_DIR

    outdir = Path(outdir)
    app = create_app([])
    written = []
    for w, h in SIZES:
        suffix = f"{w}x{h}"
        presets, _ = load_presets()
        import tempfile

        ctrl = AppController(presets, Config(), audio=False, hotkeys=False,
                             user_presets_path=Path(tempfile.mkdtemp()) / "presets.toml")
        ctrl.level_source = _fake_levels()
        engine = create_engine()
        win = load_main(engine, ctrl)
        win.setWidth(w)
        win.setHeight(h)

        def shot(name):
            path = outdir / f"{name}-{suffix}.png"
            grab(win, path)
            written.append(str(path))

        shot("accueil")
        QMetaObject.invokeMethod(win, "startMain")
        ctrl.selectPreset("robot")
        shot("direct-repos")
        ctrl.startLive()
        wait(1500)
        shot("direct-actif")
        ctrl.stopLive()
        QMetaObject.invokeMethod(win, "openVoices")
        shot("voix")
        if w < 760:
            QMetaObject.invokeMethod(win, "goBack")
        win.openEditor("robot", False)
        shot("editeur")
        QMetaObject.invokeMethod(win, "goBack")
        QMetaObject.invokeMethod(win, "openSettings")
        shot("reglages")
        win.close()
        ctrl.shutdown()
        engine.deleteLater()
        wait(100)

        gal = create_engine()
        gal.load(str(QML_DIR / "GalleryWindow.qml"))
        gwin = gal.rootObjects()[0]
        gwin.setWidth(w)
        gwin.setHeight(h)
        path = outdir / f"galerie-{suffix}.png"
        grab(gwin, path, 900)
        written.append(str(path))
        gwin.close()
        gal.deleteLater()
        wait(100)
    for warn in qml_warnings():
        print("QML WARNING:", warn)
    return written


def main(argv: list[str]) -> int:
    from abyss.ui.app import create_app, create_engine, qml_warnings
    from abyss.ui.resources import QML_DIR

    if argv and argv[0] == "--screens":
        files = capture_screens(argv[1] if len(argv) > 1 else "docs/screenshots")
        print("\n".join(files))
        return 1 if qml_warnings() else 0

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
