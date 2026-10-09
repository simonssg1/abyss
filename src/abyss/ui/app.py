"""Démarrage de l'interface Qt Quick : application, polices, icônes, moteur QML."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from abyss.ui.resources import QML_DIR, IconProvider, load_fonts

log = logging.getLogger("abyss.ui")

_QML_WARNINGS: list[str] = []


def _message_handler(mode, context, message) -> None:
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        cat = context.category or ""
        if cat.startswith("qt.qml") or cat in ("qml", "js") or ".qml" in (context.file or "") \
                or ".qml:" in message:
            _QML_WARNINGS.append(message)
    sys.stderr.write(message + "\n")


def qml_warnings() -> list[str]:
    return list(_QML_WARNINGS)


def create_app(argv: list[str] | None = None) -> QGuiApplication:
    app = QGuiApplication.instance()
    if app is None:
        QQuickStyle.setStyle("Basic")  # style personnalisable, identique sur macOS et Windows
        app = QGuiApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Abyss")
    app.setOrganizationName("Abyss")
    load_fonts(app)
    qInstallMessageHandler(_message_handler)
    return app


def create_engine(context: dict | None = None) -> QQmlApplicationEngine:
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    engine.addImageProvider("icon", IconProvider())
    engine.warnings.connect(lambda ws: _QML_WARNINGS.extend(w.toString() for w in ws))
    for name, obj in (context or {}).items():
        engine.rootContext().setContextProperty(name, obj)
    return engine


def run_gallery(quit_after: float | None = None) -> int:
    from PySide6.QtCore import QTimer

    app = create_app()
    engine = create_engine()
    engine.load(str(QML_DIR / "GalleryWindow.qml"))
    if not engine.rootObjects():
        return 1
    if quit_after:
        QTimer.singleShot(int(quit_after * 1000), app.quit)
    return app.exec()


def load_main(engine, controller):
    engine.rootContext().setContextProperty("app", controller)
    engine.load(str(QML_DIR / "Main.qml"))
    roots = engine.rootObjects()
    return roots[0] if roots else None


def run_app(presets, cfg, audio: bool = True, quit_after: float | None = None,
            initial_preset: str | None = None, defaults=None) -> int:
    from PySide6.QtCore import QTimer

    from abyss.ui.controller import AppController

    app = create_app()
    controller = AppController(presets, cfg, audio=audio, defaults=defaults)
    if initial_preset:
        p = controller.presetModel.find(initial_preset.lower()) or next(
            (q for q in presets if q.name.lower() == initial_preset.lower()), None)
        if p:
            controller.selectPreset(p.id)
    engine = create_engine()
    window = load_main(engine, controller)
    if window is None:
        return 1
    app.aboutToQuit.connect(controller.shutdown)
    QTimer.singleShot(0, controller.start_hotkeys)
    if quit_after:
        QTimer.singleShot(int(quit_after * 1000), window.close)
    return app.exec()
