"""Parakeet TDT 0.6B v3 through sherpa-onnx (the default: ~15x realtime on CPU)."""
from __future__ import annotations

import numpy as np

from ..audio.segment import split_for_asr
from .base import SttEngine
from .models import ensure_parakeet


class ParakeetEngine(SttEngine):
    name = "parakeet"

    def __init__(self, num_threads: int = 10, progress=None):
        self._num_threads = num_threads
        self._progress = progress
        self._rec = None

    def prepare(self) -> None:
        ensure_parakeet(self._progress)

    @property
    def loaded(self) -> bool:
        return self._rec is not None

    def unload(self) -> None:
        self._rec = None

    def load(self) -> None:
        import sherpa_onnx

        d = ensure_parakeet(self._progress)
        self._rec = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(d / "encoder.int8.onnx"),
            decoder=str(d / "decoder.int8.onnx"),
            joiner=str(d / "joiner.int8.onnx"),
            tokens=str(d / "tokens.txt"),
            num_threads=self._num_threads,
            model_type="nemo_transducer",
        )

    def _decode(self, pcm: np.ndarray, sample_rate: int) -> str:
        stream = self._rec.create_stream()
        stream.accept_waveform(sample_rate, pcm)
        self._rec.decode_stream(stream)
        return stream.result.text.strip()

    def transcribe(self, pcm: np.ndarray, sample_rate: int = 16000) -> str:
        if self._rec is None:
            raise RuntimeError("engine not loaded")
        # Long audio has to be split: see drawl/audio/segment.py for the model's
        # limits and the measurements behind the chunk length.
        pieces = [self._decode(seg, sample_rate)
                  for seg in split_for_asr(pcm, sample_rate)]
        return " ".join(p for p in pieces if p).strip()
