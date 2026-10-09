"""Génère les PNG (16 à 1024 px) de l'icône Abyss depuis le SVG, abyss.ico (Windows) et Abyss.icns (macOS)."""

from __future__ import annotations

import shutil
import struct
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ICON_DIR = Path(__file__).resolve().parents[1] / "src" / "abyss" / "ui" / "assets" / "icon"
SIZES = (16, 32, 48, 64, 128, 256, 512, 1024)
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def write_ico(png_dir: Path, path: Path) -> None:
    """Fichier .ico multi-tailles à entrées PNG (format accepté par Windows Vista et suivants)."""
    blobs = [(s, (png_dir / f"abyss-{s}.png").read_bytes()) for s in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    entries, data = b"", b""
    for size, blob in blobs:
        dim = 0 if size >= 256 else size  # 0 = 256 px dans le format ICO
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset + len(data))
        data += blob
    path.write_bytes(header + entries + data)


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
    write_ico(png_dir, ICON_DIR / "abyss.ico")
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
