"""STUB v2 — conversion de voix IA (RVC) via ONNX Runtime. Non implémenté en v1."""

from __future__ import annotations

from pathlib import Path

import numpy as np

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"


class RVCProcessor:
    """Conversion de voix RVC temps réel — prévue en v2.

    Pipeline prévu :
      1. Fenêtre glissante de 0,3–0,5 s (``preferred_block``) avec contexte gauche, recollée
         par fondu SOLA (recherche du décalage de corrélation maximale + crossfade).
      2. Rééchantillonnage 48 kHz → 16 kHz.
      3. ContentVec (ONNX) : extraction des features de contenu.
      4. f0 par RMVPE (ONNX) + transposition en demi-tons.
      5. Modèle RVC (ONNX) : synthèse à partir des features + f0.
      6. Retour à 48 kHz.

    Providers ONNX Runtime : ``CoreMLExecutionProvider`` / ``CPUExecutionProvider`` (Mac),
    ``DmlExecutionProvider`` (Windows, GPU AMD via DirectML).

    Fichiers attendus :
      - ``models/shared/contentvec.onnx``
      - ``models/shared/rmvpe.onnx``
      - ``models/rvc/<voix>/model.onnx`` + ``models/rvc/<voix>/voice.toml``
    """

    name = "rvc"
    latency_samples = 0

    def __init__(self, voice: str = "", transpose: float = 0.0, sample_rate: int = 48000,
                 block_seconds: float = 0.4):
        self.voice = voice
        self.transpose = transpose
        self.sample_rate = sample_rate
        self.preferred_block = int(sample_rate * block_seconds)
        raise NotImplementedError("RVC : disponible en v2")

    def process(self, block: np.ndarray) -> np.ndarray:
        raise NotImplementedError("RVC : disponible en v2")

    def reset(self) -> None:
        raise NotImplementedError("RVC : disponible en v2")
