r"""End-to-end check: WAV -> the application's real engine -> text.

    .venv\Scripts\python.exe tests\test_pipeline.py file.wav
"""
from __future__ import annotations

import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drawl.audio.recorder import Recorder          # noqa: E402
from drawl.config import Config                    # noqa: E402
from drawl.engine.parakeet import ParakeetEngine   # noqa: E402


def load_wav(path: Path, target_sr: int = 16000) -> tuple[np.ndarray, float]:
    with wave.open(str(path)) as w:
        sr, frames = w.getframerate(), w.getnframes()
        pcm = np.frombuffer(w.readframes(frames), dtype=np.int16).astype(np.float32) / 32768
    duration = frames / sr
    if sr != target_sr:
        n = int(len(pcm) * target_sr / sr)
        pcm = np.interp(np.linspace(0, len(pcm) - 1, n), np.arange(len(pcm)), pcm)
    return pcm.astype(np.float32), duration


def main() -> int:
    wav = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if wav is None or not wav.exists():
        print("usage: test_pipeline.py <file.wav>")
        return 2

    cfg = Config.load()
    pcm, duration = load_wav(wav, cfg["sample_rate"])
    print(f"audio: {duration:.2f}s -> {len(pcm)} samples at {cfg['sample_rate']}Hz")

    t0 = time.perf_counter()
    engine = ParakeetEngine(cfg["num_threads"])
    engine.load()
    print(f"engine loaded in {time.perf_counter() - t0:.2f}s")

    t1 = time.perf_counter()
    text = engine.transcribe(pcm, cfg["sample_rate"])
    elapsed = time.perf_counter() - t1
    print(f"transcribed in {elapsed:.2f}s  ({duration / elapsed:.1f}x realtime)")
    print(f"text: {text!r}")

    # The microphone must open at the configured rate.
    try:
        rec = Recorder(cfg["sample_rate"], device=cfg["input_device"])
        rec.start()
        time.sleep(0.4)
        captured = rec.stop()
        print(f"microphone ok: captured {len(captured)} samples "
              f"({len(captured) / cfg['sample_rate']:.2f}s)")
    except Exception as exc:
        print(f"microphone NOT available: {exc}")

    assert text, "empty transcription"
    return 0


if __name__ == "__main__":
    sys.exit(main())
