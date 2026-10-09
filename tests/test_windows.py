import struct
from pathlib import Path

ICON_DIR = Path(__file__).resolve().parents[1] / "src" / "abyss" / "ui" / "assets" / "icon"


def test_ico_has_all_windows_sizes():
    data = (ICON_DIR / "abyss.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind, count) == (0, 1, 6)
    sizes = []
    for i in range(count):
        w, h, _, _, _, bpp, length, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i: 22 + 16 * i])
        assert data[offset:offset + 8] == b"\x89PNG\r\n\x1a\n" and offset + length <= len(data)
        sizes.append(w or 256)
    assert sizes == [16, 32, 48, 64, 128, 256]


def test_gui_script_declared():
    import tomllib

    meta = tomllib.loads((ICON_DIR.parents[4] / "pyproject.toml").read_text(encoding="utf-8"))
    assert meta["project"]["gui-scripts"]["abyss-gui"] == "abyss.__main__:main_gui"


def test_installer_is_windows_friendly():
    ps1 = (ICON_DIR.parents[4] / "scripts" / "install_windows.ps1").read_bytes()
    assert ps1.startswith(b"\xef\xbb\xbf")  # BOM : accents lisibles par PowerShell 5.1
    assert b"abyss-gui" in ps1 and b"winget install --id astral-sh.uv" in ps1
