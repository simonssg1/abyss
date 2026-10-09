"""Point d'entrée : CLI (rendu, liste des périphériques, headless) et GUI."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from math import gcd
from pathlib import Path

import numpy as np

log = logging.getLogger("abyss")


def read_wav_mono(path: Path, target_rate: int) -> np.ndarray:
    from scipy.io import wavfile
    from scipy.signal import resample_poly

    rate, data = wavfile.read(path)
    if data.dtype.kind in "iu":
        info = np.iinfo(data.dtype)
        data = (data.astype(np.float64) - (info.max + info.min + 1) / 2) / (info.max + 1)
    data = data.astype(np.float64)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if rate != target_rate:
        g = gcd(rate, target_rate)
        data = resample_poly(data, target_rate // g, rate // g)
    return data.astype(np.float32)


def render(in_path: Path, preset, out_path: Path, sample_rate: int = 48000) -> np.ndarray:
    """Même chaîne que le temps réel (débruitage + preset + limiteur), par blocs de 256."""
    from scipy.io import wavfile

    from abyss.audio.engine import BLOCK, Pipeline

    x = read_wav_mono(in_path, sample_rate)
    pipe = Pipeline(sample_rate)
    pipe.set_preset(preset)
    pad = (-len(x)) % BLOCK
    xp = np.concatenate([x, np.zeros(pad, dtype=np.float32)])
    y = np.concatenate([pipe.process(xp[i : i + BLOCK]) for i in range(0, len(xp), BLOCK)])[: len(x)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(out_path, sample_rate, y.astype(np.float32))
    return y


def _safe_filename(name: str) -> str:
    import unicodedata

    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in ascii_name).strip("_").lower() or "preset"


def run_headless(presets, preset, cfg) -> int:
    from abyss.audio import devices as dv
    from abyss.audio.engine import AudioEngine

    devs = dv.list_devices()
    found = dv.auto_detect(devs)
    mic = dv.find_by_name(cfg.input_device, "input", devs) or found["input"]
    virt = dv.find_by_name(cfg.virtual_device, "output", devs) or found["virtual"]
    mon = dv.find_by_name(cfg.monitor_device, "output", devs) or found["monitor"]
    engine = AudioEngine(presets, cfg.denoise, cfg.denoise_threshold_db, cfg.monitor,
                         cfg.monitor_volume, cfg.output_gain_db)
    engine.set_preset(preset)
    engine.start(mic.index if mic else None, virt.index if virt else None,
                 mon.index if (mon and cfg.monitor) else None)
    if not engine.metrics.running:
        print(engine.metrics.error or "Impossible de démarrer l'audio", file=sys.stderr)
        return 1
    print(f"Micro : {mic.name if mic else '-'} | Micro virtuel : {virt.name if virt else 'aucun'} | "
          f"{engine.metrics.sample_rate} Hz | preset « {preset.name} » — Ctrl+C pour quitter")
    done = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: done.set())
    signal.signal(signal.SIGTERM, lambda *_: done.set())
    while not done.wait(1.0):
        m = engine.metrics
        print(f"\rin {20 * np.log10(m.rms_in + 1e-9):6.1f} dB  out {20 * np.log10(m.rms_out + 1e-9):6.1f} dB  "
              f"latence {m.latency_ms:5.1f} ms  xruns {m.xruns}   ", end="", flush=True)
    print("\nArrêt…")
    engine.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abyss", description="Changeur de voix temps réel")
    parser.add_argument("--list-devices", action="store_true", help="liste les périphériques audio")
    parser.add_argument("--render", metavar="IN.wav", type=Path, help="applique un preset à un fichier")
    parser.add_argument("--preset", metavar="NOM", help="nom du preset")
    parser.add_argument("--out", metavar="OUT.wav", type=Path, help="fichier de sortie pour --render")
    parser.add_argument("--render-all", metavar="IN.wav", type=Path, help="un rendu par preset dans renders/")
    parser.add_argument("--renders-dir", type=Path, default=Path("renders"), help=argparse.SUPPRESS)
    parser.add_argument("--headless", action="store_true", help="temps réel sans interface")
    parser.add_argument("--presets", type=Path, help="fichier presets.toml à utiliser")
    parser.add_argument("--gallery", action="store_true", help="galerie des composants de l'interface")
    parser.add_argument("--no-audio", action="store_true", help="GUI sans streams audio (tests)")
    parser.add_argument("--quit-after", type=float, metavar="S", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.list_devices:
        from abyss.audio.devices import format_device_list

        print(format_device_list())
        return 0

    if args.gallery:
        from abyss.ui.app import run_gallery

        return run_gallery(quit_after=args.quit_after)

    from abyss.config import load_config
    from abyss.presets import find_preset, load_presets

    if args.presets:
        presets, _ = load_presets(args.presets)
        defaults = presets
    else:
        from abyss.user_presets import load_all_presets

        presets, defaults, _ = load_all_presets()

    def pick(name: str | None):
        if not name:
            return presets[0]
        p = find_preset(presets, name)
        if p is None:
            parser.error(f"preset inconnu « {name} » (disponibles : {', '.join(x.name for x in presets)})")
        return p

    if args.render:
        if not args.out:
            parser.error("--render demande --out OUT.wav")
        render(args.render, pick(args.preset), args.out)
        print(f"Écrit : {args.out}")
        return 0

    if args.render_all:
        for p in presets:
            out = args.renders_dir / f"{args.render_all.stem}_{p.hotkey_index or 0}_{_safe_filename(p.name)}.wav"
            y = render(args.render_all, p, out)
            print(f"{p.name:<15} → {out}  (RMS {np.sqrt(np.mean(y ** 2)):.3f}, crête {np.max(np.abs(y)):.3f})")
        return 0

    cfg = load_config()
    if args.headless:
        name = args.preset or (cfg.last_preset if find_preset(presets, cfg.last_preset) else None)
        return run_headless(presets, pick(name), cfg)

    from abyss.ui.app import run_app

    return run_app(presets, cfg, audio=not args.no_audio, quit_after=args.quit_after,
                   initial_preset=args.preset, defaults=defaults)


def main_gui() -> int:
    """Point d'entrée sans console (`abyss-gui`) : les logs vont dans ~/.abyss/logs/abyss.log."""
    from logging.handlers import RotatingFileHandler

    log_dir = Path.home() / ".abyss" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "abyss.log"
    # Sans console (pythonw), stdout/stderr valent None : on les redirige vers le fichier de log.
    if sys.stdout is None or sys.stderr is None:
        stream = open(log_file, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    log.info("=== lancement d'Abyss (sans console)")
    try:
        return main(sys.argv[1:])
    except Exception:
        log.exception("Abyss s'est arrêté sur une erreur")
        return 1


if __name__ == "__main__":
    sys.exit(main())
