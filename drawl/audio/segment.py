"""Splitting long audio into chunks, cutting where it is quiet.

Parakeet is an offline model: it processes the whole clip in one go, so memory
and time grow faster than linearly with duration, and past 5000 encoder frames
(400 s) it fails outright. Measured on a Ryzen AI 9 365:

    duration   time     RTF     RAM
        15s     0.9s   0.061   875 MB
        60s     4.3s   0.072   1.4 GB
       120s     9.2s   0.077   2.0 GB
       300s    35.7s   0.119   3.6 GB
       400s    55.5s   0.139   4.9 GB
       440s    error (broadcast 500 vs 5500 in the first self-attention layer)

Cutting into ~45 s chunks keeps the realtime factor near its peak and memory
below a gigabyte and a half, with no ceiling on total length.
"""
from __future__ import annotations

import numpy as np

# Past this duration the model fails: 5000 frames at 12.5 frames per second.
HARD_LIMIT_S = 400.0

TARGET_S = 45.0     # length to aim for in each chunk
MAX_S = 75.0        # never exceed it, even with no useful silence
SEARCH_S = 8.0      # how far around the target to look for the quietest point
FRAME_S = 0.02      # resolution of the energy analysis


def _rms_frames(pcm: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    """RMS energy over windows of FRAME_S seconds."""
    size = max(1, int(sr * FRAME_S))
    n = len(pcm) // size
    if n == 0:
        return np.zeros(0, dtype=np.float32), size
    frames = pcm[: n * size].reshape(n, size)
    return np.sqrt(np.mean(frames.astype(np.float32) ** 2, axis=1)), size


def split_for_asr(pcm: np.ndarray, sr: int, target_s: float = TARGET_S,
                  max_s: float = MAX_S) -> list[np.ndarray]:
    """Break `pcm` into chunks of at most `max_s`.

    Every cut lands on the quietest point near `target_s`, so it falls in a
    pause rather than halfway through a word. Audio that is already short
    enough comes back unchanged, as a single chunk.
    """
    if len(pcm) <= int(max_s * sr):
        return [pcm]

    rms, frame_size = _rms_frames(pcm, sr)
    if len(rms) == 0:
        return [pcm]

    segments: list[np.ndarray] = []
    start = 0
    while start < len(pcm):
        if len(pcm) - start <= int(max_s * sr):
            segments.append(pcm[start:])
            break

        target = start + int(target_s * sr)
        lo = max(start + int(sr * 5), target - int(SEARCH_S * sr))
        hi = min(start + int(max_s * sr), target + int(SEARCH_S * sr))

        lo_f, hi_f = lo // frame_size, min(hi // frame_size, len(rms))
        if hi_f <= lo_f:
            cut = hi
        else:
            cut = (lo_f + int(np.argmin(rms[lo_f:hi_f]))) * frame_size

        cut = max(cut, start + int(sr * 5))   # no chunk shorter than 5 seconds
        segments.append(pcm[start:cut])
        start = cut

    return segments
