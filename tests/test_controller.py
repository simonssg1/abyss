import pytest
from PySide6.QtWidgets import QApplication

from abyss.config import Config
from abyss.presets import load_presets
from abyss.ui.controller import AppController, level_from_rms
from abyss.ui.models import ALL, PresetFilterModel, PresetModel


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctrl(qapp, tmp_path, monkeypatch):
    import abyss.config as config

    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")
    presets, _ = load_presets()
    c = AppController(presets, Config(), audio=False, hotkeys=False, user_presets_path=tmp_path / "presets.toml")
    yield c
    c.shutdown()


def test_level_mapping():
    assert level_from_rms(0.0) == 0.0
    assert level_from_rms(1.0) == pytest.approx(1.0)
    assert 0.4 < level_from_rms(0.05) < 0.6


def test_model_roles_and_placeholder(qapp):
    presets, _ = load_presets()
    model = PresetModel(presets, Config().hotkeys)
    assert model.rowCount() == len(presets) + 1  # + « Voix IA » (Bientôt)
    roles = {bytes(v).decode() for v in model.roleNames().values()}
    assert {"id", "name", "description", "category", "icon", "badge", "hotkey", "intensity", "toneLow",
            "toneHigh", "effects", "isUser", "enabled"} <= roles
    robot = model.get("robot")
    assert robot["hotkey"] == "Ctrl+Alt+2" and robot["enabled"] and robot["intensity"] == 1.0
    ai = model.get("ai-voice")
    assert ai["badge"] == "soon" and not ai["enabled"] and ai["category"] == "IA"


def test_filter_by_category_and_search(qapp):
    from abyss.presets import Preset

    presets = [Preset("Robot", 2, categories=["Robot"], description="Métallique"),
               Preset("Vocodeur", 3, categories=["Robot", "Sci-Fi"]),
               Preset("Démon", 4, categories=["Gaming"], description="Grave et sombre"),
               Preset("Normal", 1)]
    proxy = PresetFilterModel(PresetModel(presets))

    def names():
        return [proxy.data(proxy.index(i, 0)) for i in range(proxy.rowCount())]

    assert len(names()) == 5 and proxy.category == ALL
    proxy.category = "Robot"
    assert names() == ["Robot", "Vocodeur"]
    proxy.category = "IA"
    assert names() == ["Voix IA"]
    proxy.category = ALL
    proxy.search = "demon"  # insensible aux accents et à la casse
    assert names() == ["Démon"]
    proxy.search = "SOMBRE"
    assert names() == ["Démon"]


def test_controller_slots_drive_engine(ctrl):
    seen = []
    ctrl.activePresetIdChanged.connect(lambda: seen.append(ctrl.activePresetId))
    ctrl.selectPreset("robot")
    assert ctrl.engine.preset.name == "Robot" and seen == ["robot"] and ctrl.cfg.last_preset == "Robot"
    ctrl.selectPreset("inexistant")
    assert ctrl.activePresetId == "robot"
    ctrl.toggleBypass()
    assert ctrl.bypass and ctrl.engine.bypass
    ctrl.setOutputMuted(True)
    assert ctrl.engine.pipeline.output_gain_db == -120.0
    ctrl.setOutputGain(-3)
    assert ctrl.engine.pipeline.output_gain_db == -120.0  # reste coupé
    ctrl.setOutputMuted(False)
    assert ctrl.engine.pipeline.output_gain_db == -3
    ctrl.setDenoiseThreshold(-50)
    assert ctrl.engine.pipeline.denoiser.threshold_db == pytest.approx(-50)
    ctrl.setMonitorVolume(1.7)
    assert ctrl.monitorVolume == 1.0


def test_live_toggle_and_session(ctrl):
    assert not ctrl.live
    ctrl.toggleLive()
    assert ctrl.live and ctrl.sessionSeconds == 0
    ctrl.toggleLive()
    assert not ctrl.live


def test_intensity_applies_live(ctrl):
    ctrl.selectPreset("robot")
    ctrl.engine.pipeline.switcher.process(__import__("numpy").zeros(256, dtype="float32"))  # prend la chaîne
    ctrl.setIntensity("robot", 0.25)
    chain = ctrl.engine.pipeline.switcher.current
    assert chain.controls["intensity"].mix == 0.25
    assert ctrl.presetModel.get("robot")["intensity"] == 0.25


def test_toast_when_virtual_missing(ctrl):
    msgs = []
    ctrl.toast.connect(lambda k, t, m: msgs.append((k, t)))
    ctrl.audio = True
    ctrl._virtual_found = False
    ctrl._start_worker = lambda *a: ctrl._startFinished.emit(False)  # pas de vrai stream en test
    ctrl.startLive()
    QApplication.processEvents()
    assert ("error", "Micro virtuel introuvable") in msgs
    ctrl.audio = False


def test_editor_save_duplicate_delete_reset(ctrl, tmp_path):
    import tomllib

    path = tmp_path / "presets.toml"
    draft = ctrl.newPresetDraft()
    draft.update(name="Ma voix", categories=["Fun"], effects=[ctrl.defaultEffect("pitch_shift")])
    pid = ctrl.savePreset(draft)
    assert pid == "ma-voix" and ctrl.presetModel.get(pid)["isUser"] and ctrl.presetModel.get(pid)["badge"] == "new"
    assert tomllib.loads(path.read_text(encoding="utf-8"))["preset"][0]["id"] == "ma-voix"
    dup = ctrl.duplicatePreset(pid)
    assert dup and ctrl.presetModel.get(dup)["name"] == "Ma voix (copie)"
    assert ctrl.deletePreset(dup) and ctrl.presetModel.find(dup) is None
    assert not ctrl.deletePreset("robot")  # preset par défaut : non supprimable
    robot = ctrl.editDraft("robot")
    robot["intensity"] = 0.3
    assert ctrl.savePreset(robot) == "robot"
    assert ctrl.presetModel.get("robot")["intensity"] == 0.3
    reset = ctrl.resetPreset("robot")
    assert reset["intensity"] == 1.0
    ids = [e["id"] for e in tomllib.loads(path.read_text(encoding="utf-8"))["preset"]]
    assert ids == ["ma-voix"]  # Robot réinitialisé : plus de surcharge


def test_invalid_draft_is_refused(ctrl):
    msgs = []
    ctrl.toast.connect(lambda k, t, m: msgs.append(t))
    draft = ctrl.newPresetDraft()
    draft["name"] = "   "
    assert ctrl.savePreset(draft) == ""
    assert msgs == ["Preset non enregistré"]


def test_intensity_is_autosaved(ctrl, tmp_path, qapp):
    import time
    import tomllib

    ctrl.setIntensity("robot", 0.6)
    deadline = time.time() + 3
    path = tmp_path / "presets.toml"
    while not path.exists() and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.05)
    entry = tomllib.loads(path.read_text(encoding="utf-8"))["preset"][0]
    assert entry["id"] == "robot" and entry["intensity"] == 0.6
