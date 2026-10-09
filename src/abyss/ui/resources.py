"""Ressources de l'interface QML : polices Inter et icônes Lucide recolorées par le thème."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

log = logging.getLogger("abyss.ui")

UI_DIR = Path(__file__).resolve().parent
QML_DIR = UI_DIR / "qml"
ASSETS_DIR = UI_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
ICONS_DIR = ASSETS_DIR / "icons"
ICON_DIR = ASSETS_DIR / "icon"


def load_fonts(app: QGuiApplication) -> str:
    """Charge Inter ; repli sur la police système si les fichiers sont absents ou illisibles."""
    families: set[str] = set()
    for ttf in sorted(FONTS_DIR.glob("*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(ttf))
        if fid >= 0:
            families.update(QFontDatabase.applicationFontFamilies(fid))
    family = "Inter" if "Inter" in families else app.font().family()
    if family != "Inter":
        log.warning("Police Inter introuvable, repli sur %s", family)
    font = QFont(family)
    font.setPixelSize(16)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)
    return family


class IconProvider(QQuickImageProvider):
    """image://icon/<nom>/<rrggbb ou aarrggbb> → icône Lucide rendue dans la couleur demandée."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._svg: dict[str, str] = {}

    def _source(self, name: str) -> str | None:
        if name not in self._svg:
            path = ICONS_DIR / f"{name}.svg"
            if not path.is_file():
                path = ICON_DIR / f"{name}.svg"
            self._svg[name] = path.read_text(encoding="utf-8") if path.is_file() else ""
        return self._svg[name] or None

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:  # noqa: A002
        name, _, color = id.partition("/")
        color = color.split("?")[0] or "E2E8FF"
        if len(color) == 8:  # aarrggbb → couleur + opacité
            opacity = int(color[:2], 16) / 255.0
            color = color[2:]
        else:
            opacity = 1.0
        w = requestedSize.width() if requestedSize.width() > 0 else 48
        h = requestedSize.height() if requestedSize.height() > 0 else w
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        src = self._source(name)
        if src is None:
            log.warning("Icône inconnue : %s", name)
            return img
        data = src.replace("currentColor", f"#{color}")
        renderer = QSvgRenderer(QByteArray(data.encode("utf-8")))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(opacity)
        renderer.render(p, QRectF(0, 0, w, h))
        p.end()
        return img
