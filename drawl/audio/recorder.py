"""Microphone capture at 16 kHz mono, with an RMS level for the interface."""
from __future__ import annotations

import threading
from typing import Callable

import numpy as np
import sounddevice as sd

LevelFn = Callable[[float], None]


class Recorder:
    """Push-to-talk recorder. Blocks arrive on PortAudio's own thread."""

    def __init__(self, sample_rate: int = 16000, on_level: LevelFn | None = None,
                 device: int | str | None = None):
        self.sample_rate = sample_rate
        self._on_level = on_level
        self._device = device
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def _callback(self, indata, frames, time_info, status) -> None:
        # Runs on PortAudio's real-time thread: no heavy allocation here.
        with self._lock:
            self._chunks.append(indata[:, 0].copy())
        if self._on_level is not None:
            rms = float(np.sqrt(np.mean(indata[:, 0] ** 2)))
            self._on_level(min(1.0, rms * 8.0))

    def start(self) -> None:
        if self._stream is not None:
            return
        with self._lock:
            self._chunks.clear()
        self._stream = sd.InputStream(
            device=self._device,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and hand back everything captured."""
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()
            stream.close()
        with self._lock:
            chunks = list(self._chunks)
            self._chunks.clear()
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks).astype(np.float32)
