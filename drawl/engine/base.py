"""The interface every recognition engine implements."""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class SttEngine(ABC):
    """An offline ASR engine. `transcribe` takes mono float32 PCM at 16 kHz.

    The lifecycle has three stages because the weights are heavy: `prepare`
    fetches what is needed onto disk without using memory, `load` brings it into
    RAM, `unload` frees it again. That lets the app sit idle for next to nothing
    and load the model only while someone is actually speaking.
    """

    name: str = "base"

    def prepare(self) -> None:
        """Download the model files if missing, without loading them."""

    @abstractmethod
    def load(self) -> None:
        """Bring the model into memory. Called off the UI thread."""

    def unload(self) -> None:
        """Free the memory. `load` must work again afterwards."""

    @property
    @abstractmethod
    def loaded(self) -> bool:
        ...

    @abstractmethod
    def transcribe(self, pcm: np.ndarray, sample_rate: int = 16000) -> str:
        ...
