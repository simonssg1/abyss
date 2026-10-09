"""Démarrage de l'interface Qt Quick : application, polices, icônes, moteur QML."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from abyss.ui.resources import ICON_DIR, QML_DIR, IconProvider, load_fonts

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
    app.setApplicationDisplayName("Abyss")
    app.setOrganizationName("Abyss")
    from PySide6.QtGui import QIcon

    icon = QIcon()
    for size in (16, 32, 64, 128, 256, 512, 1024):
        png = ICON_DIR / "png" / f"abyss-{size}.png"
        if png.is_file():
            icon.addFile(str(png))
    if icon.isNull():
        icon = QIcon(str(ICON_DIR / "abyss.svg"))
    app.setWindowIcon(icon)  # icône de fenêtre (et du Dock sur macOS)
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


SERVER_NAME = "abyss-single-instance"


def _server_name() -> str:
    """Un nom par utilisateur (dossier personnel) : deux comptes, ou les tests, ne se gênent pas."""
    import hashlib
    from pathlib import Path

    return f"{SERVER_NAME}-{hashlib.sha1(str(Path.home()).encode()).hexdigest()[:10]}"


def notify_running_instance() -> bool:
    """True si une instance d'Abyss tourne déjà (elle est alors ramenée au premier plan)."""
    from PySide6.QtNetwork import QLocalSocket

    sock = QLocalSocket()
    sock.connectToServer(_server_name())
    if not sock.waitForConnected(300):
        return False
    sock.write(b"raise\n")
    sock.waitForBytesWritten(300)
    sock.disconnectFromServer()
    return True


def start_instance_server(controller):
    from PySide6.QtNetwork import QLocalServer

    server = QLocalServer(controller)
    QLocalServer.removeServer(_server_name())  # socket orphelin d'un lancement précédent
    if server.listen(_server_name()):
        def on_connection():
            conn = server.nextPendingConnection()
            if conn is not None:
                conn.readyRead.connect(lambda c=conn: (c.readAll(), controller.raiseRequested.emit()))
                conn.disconnected.connect(conn.deleteLater)
                controller.raiseRequested.emit()
        server.newConnection.connect(on_connection)
    return server


def run_app(presets, cfg, audio: bool = True, quit_after: float | None = None,
            initial_preset: str | None = None, defaults=None, single_instance: bool = True) -> int:
    from PySide6.QtCore import QTimer

    from abyss.platform.macos import set_process_name
    from abyss.platform.windows import set_app_user_model_id
    from abyss.ui.controller import AppController

    set_process_name("Abyss")
    set_app_user_model_id()
    app = create_app()
    if single_instance and notify_running_instance():
        log.info("Abyss tourne déjà : fenêtre existante ramenée au premier plan")
        return 0
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
    if single_instance:
        controller._instance_server = start_instance_server(controller)
    QTimer.singleShot(0, controller.start_hotkeys)
    if quit_after:
        QTimer.singleShot(int(quit_after * 1000), window.close)
    return app.exec()
