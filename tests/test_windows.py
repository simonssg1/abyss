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


def test_renamed_cable_mic_is_virtual_not_picked_as_mic(monkeypatch):
    from abyss.audio import devices as dv

    devs = [dv.Device(0, "Abyss (VB-Audio Virtual Cable)", 2, 0, 48000, "Windows WASAPI"),
            dv.Device(1, "Microphone (Realtek Audio)", 2, 0, 48000, "Windows WASAPI"),
            dv.Device(2, "CABLE In 16ch (VB-Audio Virtual Cable)", 0, 16, 48000, "Windows WASAPI"),
            dv.Device(3, "CABLE Input (VB-Audio Virtual Cable)", 0, 2, 48000, "Windows WASAPI"),
            dv.Device(4, "Casque (Realtek Audio)", 0, 2, 48000, "Windows WASAPI")]
    monkeypatch.setattr(dv, "_default", lambda kind, pool: pool[0])  # pire cas : défaut = micro virtuel
    found = dv.auto_detect(devs)
    assert found["input"].name == "Microphone (Realtek Audio)"
    assert found["virtual"].name == "CABLE Input (VB-Audio Virtual Cable)"
    assert dv.is_virtual("Abyss (VB-Audio Virtual Cable)")


def test_windows_scripts_are_consistent():
    root = ICON_DIR.parents[4] / "scripts"
    main = (root / "install_windows.ps1").read_text(encoding="utf-8-sig")
    helper = (root / "windows_audio_setup.ps1").read_text(encoding="utf-8-sig")
    cs = (root / "windows_audio.cs").read_text(encoding="utf-8")
    assert "VBCABLE_Driver_Pack45.zip" in main and "-Verb RunAs" in main and "windows_audio_setup.ps1" in main
    assert '"-i", "-h"' in helper and "RenameCable" in helper
    assert "RenameCable" in cs and "ListCaptures" in cs
    assert cs.count("[PreserveSig]") == 12  # méthodes COM : signature HRESULT native
    # parenthèses / accolades équilibrées (pas de PowerShell sur le Mac pour vérifier la syntaxe)
    for text in (main, helper, cs):
        assert text.count("{") == text.count("}") and text.count("(") == text.count(")")
