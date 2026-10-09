"""Génère les PNG (16 à 1024 px) de l'icône Abyss depuis le SVG, puis Abyss.icns (iconutil, macOS)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ICON_DIR = Path(__file__).resolve().parents[1] / "src" / "abyss" / "ui" / "assets" / "icon"
SIZES = (16, 32, 64, 128, 256, 512, 1024)


def render_png(renderer: QSvgRenderer, size: int, path: Path) -> None:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(p, QRectF(0, 0, size, size))
    p.end()
    img.save(str(path))


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841
    renderer = QSvgRenderer(str(ICON_DIR / "abyss.svg"))
    png_dir = ICON_DIR / "png"
    png_dir.mkdir(exist_ok=True)
    for s in SIZES:
        render_png(renderer, s, png_dir / f"abyss-{s}.png")
    if sys.platform == "darwin" and shutil.which("iconutil"):
        iconset = ICON_DIR / "Abyss.iconset"
        shutil.rmtree(iconset, ignore_errors=True)
        iconset.mkdir()
        for s in (16, 32, 128, 256, 512):
            shutil.copy(png_dir / f"abyss-{s}.png", iconset / f"icon_{s}x{s}.png")
            shutil.copy(png_dir / f"abyss-{s * 2}.png", iconset / f"icon_{s}x{s}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ICON_DIR / "Abyss.icns")], check=True)
        shutil.rmtree(iconset)
    print(f"Icônes générées dans {ICON_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
