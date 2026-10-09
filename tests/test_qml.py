import os
import subprocess
import sys

import pytest

ENV = dict(os.environ, QT_QPA_PLATFORM="offscreen")


def _capture(target, tmp_path, size="1200x860"):
    out = tmp_path / f"{target}.png"
    proc = subprocess.run([sys.executable, "-m", "abyss.ui.capture", target, str(out), size],
                          env=ENV, capture_output=True, text=True, timeout=90)
    return proc, out


@pytest.mark.parametrize("size", ["1200x1500", "420x780"])
def test_gallery_loads_without_qml_warnings(tmp_path, size):
    proc, out = _capture("GalleryWindow", tmp_path, size)
    assert proc.returncode == 0, proc.stdout + proc.stderr  # tout warning QML fait échouer
    assert out.stat().st_size > 10_000


def test_icon_provider_recolors():
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QApplication

    from abyss.ui.resources import IconProvider

    app = QApplication.instance() or QApplication([])  # noqa: F841
    img = IconProvider().requestImage("check/06D6A0", QSize(), QSize(48, 48))
    colors = {img.pixelColor(x, y).name() for x in range(48) for y in range(48) if img.pixelColor(x, y).alpha() == 255}
    assert colors == {"#06d6a0"}


def test_all_screens_load_without_qml_warnings(tmp_path):
    proc = subprocess.run([sys.executable, "-m", "abyss.ui.capture", "--screens", str(tmp_path)],
                          env=ENV, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    names = {p.name for p in tmp_path.glob("*.png")}
    for screen in ("accueil", "direct-repos", "direct-actif", "voix", "editeur", "reglages", "galerie"):
        for size in ("420x780", "1200x780"):
            assert f"{screen}-{size}.png" in names
