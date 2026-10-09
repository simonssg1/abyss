import os
import subprocess
import sys

from abyss.hotkeys import pretty


def test_gui_smoke_offscreen(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    proc = subprocess.run([sys.executable, "-m", "abyss", "--no-audio", "--quit-after", "2"],
                          env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr
    assert (tmp_path / ".abyss" / "config.json").exists()  # config sauvegardée à la fermeture


def test_pretty_hotkey():
    assert pretty("<ctrl>+<alt>+m") == "Ctrl+Alt+M"
