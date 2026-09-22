"""faster-whisper fallback, for languages outside Parakeet's 25."""
from __future__ import annotations

import numpy as np

from ..paths import models_dir
from .base import SttEngine


class WhisperEngine(SttEngine):
    name = "whisper"

    def __init__(self, model: str = "large-v3-turbo", language: str | None = "it",
                 num_threads: int = 10):
        self._model_name = model
        self._language = language
        self._num_threads = num_threads
        self._model = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def unload(self) -> None:
        self._model = None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self._model_name,
            device="cpu",
            compute_type="int8",
            cpu_threads=self._num_threads,
            download_root=str(models_dir() / "whisper"),
        )

    def transcribe(self, pcm: np.ndarray, sample_rate: int = 16000) -> str:
        if self._model is None:
            raise RuntimeError("engine not loaded")
        segments, _ = self._model.transcribe(
            pcm, language=self._language, beam_size=1, vad_filter=True
        )
        return " ".join(s.text.strip() for s in segments).strip()
