"""Listing des périphériques audio, filtrage par host API et auto-détection."""

from __future__ import annotations

import sys
from dataclasses import dataclass

import sounddevice as sd

VIRTUAL_MARKERS = ("blackhole", "cable input")
SPEAKER_MARKERS = ("speaker", "haut-parleur", "macbook")


@dataclass
class Device:
    index: int
    name: str
    max_input: int
    max_output: int
    default_samplerate: float
    hostapi: str


def preferred_hostapi() -> str | None:
    if sys.platform == "win32":
        return "Windows WASAPI"
    if sys.platform == "darwin":
        return "Core Audio"
    return None  # Linux : on garde tout


def _hostapi_index() -> int | None:
    wanted = preferred_hostapi()
    for i, api in enumerate(sd.query_hostapis()):
        if wanted is None or api["name"] == wanted:
            return i
    return None


def list_devices() -> list[Device]:
    try:
        apis = sd.query_hostapis()
        devs = sd.query_devices()
    except Exception:  # PortAudio indisponible
        return []
    wanted = preferred_hostapi()
    out = []
    for i, d in enumerate(devs):
        api = apis[d["hostapi"]]["name"]
        if wanted is not None and api != wanted:
            continue
        out.append(Device(i, d["name"], d["max_input_channels"], d["max_output_channels"],
                          d["default_samplerate"], api))
    return out


def inputs(devices: list[Device] | None = None) -> list[Device]:
    return [d for d in (devices if devices is not None else list_devices()) if d.max_input > 0]


def outputs(devices: list[Device] | None = None) -> list[Device]:
    return [d for d in (devices if devices is not None else list_devices()) if d.max_output > 0]


def is_virtual(name: str) -> bool:
    low = name.lower()
    return any(m in low for m in VIRTUAL_MARKERS)


def is_speaker_like(name: str | None) -> bool:
    low = (name or "").lower()
    return any(m in low for m in SPEAKER_MARKERS)


def find_by_name(name: str | None, kind: str, devices: list[Device] | None = None) -> Device | None:
    """Retrouve un périphérique par nom (exact puis partiel). kind = 'input' ou 'output'."""
    if not name:
        return None
    pool = inputs(devices) if kind == "input" else outputs(devices)
    for d in pool:
        if d.name == name:
            return d
    low = name.lower()
    for d in pool:
        if low in d.name.lower():
            return d
    return None


def _default(kind: str, pool: list[Device]) -> Device | None:
    idx = None
    api = _hostapi_index()
    try:
        if api is not None:
            idx = sd.query_hostapis(api)["default_input_device" if kind == "input" else "default_output_device"]
        if idx is None or idx < 0:
            idx = sd.default.device[0 if kind == "input" else 1]
    except Exception:
        idx = None
    for d in pool:
        if d.index == idx:
            return d
    return None


def auto_detect(devices: list[Device] | None = None) -> dict[str, Device | None]:
    """Micro = entrée par défaut ; micro virtuel = BlackHole / CABLE Input ; casque = sortie par défaut."""
    devices = devices if devices is not None else list_devices()
    ins, outs = inputs(devices), outputs(devices)
    virtual = next((d for d in outs if is_virtual(d.name)), None)
    mic = _default("input", ins)
    if mic is None or is_virtual(mic.name):
        mic = next((d for d in ins if not is_virtual(d.name)), mic)
    monitor = _default("output", outs)
    if monitor is not None and is_virtual(monitor.name):
        monitor = next((d for d in outs if not is_virtual(d.name)), None)
    return {"input": mic, "virtual": virtual, "monitor": monitor}


def format_device_list() -> str:
    devices = list_devices()
    if not devices:
        return "Aucun périphérique audio trouvé."
    found = auto_detect(devices)
    lines = [f"Host API : {preferred_hostapi() or 'toutes'}", ""]
    for d in devices:
        tags = [k for k, v in found.items() if v is not None and v.index == d.index]
        lines.append(f"[{d.index:>2}] {d.name}  (in {d.max_input}, out {d.max_output}, "
                     f"{int(d.default_samplerate)} Hz){'  ← ' + ', '.join(tags) if tags else ''}")
    if found["virtual"] is None:
        lines += ["", "Aucun câble virtuel détecté (BlackHole 2ch sur macOS, VB-CABLE « CABLE Input » sur Windows)."]
    return "\n".join(lines)
