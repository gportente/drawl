"""Checks how long audio is split into chunks."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drawl.audio.segment import MAX_S, split_for_asr  # noqa: E402

SR = 16000


def speech_with_pauses(duration_s: float, pause_every_s: float = 40.0) -> np.ndarray:
    """Rough noise broken up by half-second silences."""
    rng = np.random.default_rng(0)
    pcm = rng.normal(0, 0.1, int(duration_s * SR)).astype(np.float32)
    for t in np.arange(pause_every_s, duration_s, pause_every_s):
        i = int(t * SR)
        pcm[i:i + SR // 2] = 0.0
    return pcm


def main() -> int:
    failures = []

    # Short audio: no splitting.
    short = speech_with_pauses(20)
    segs = split_for_asr(short, SR)
    if len(segs) != 1 or len(segs[0]) != len(short):
        failures.append(f"short audio split into {len(segs)} chunks")

    for duration in (80, 150, 300, 640, 1800):
        pcm = speech_with_pauses(duration)
        segs = split_for_asr(pcm, SR)
        total = sum(len(s) for s in segs)
        lengths = [len(s) / SR for s in segs]

        if total != len(pcm):
            failures.append(f"{duration}s: lost {len(pcm) - total} samples")
        if max(lengths) > MAX_S + 0.01:
            failures.append(f"{duration}s: {max(lengths):.1f}s chunk exceeds the maximum")
        if min(lengths) < 4.9:
            failures.append(f"{duration}s: {min(lengths):.1f}s chunk is too short")

        # Every cut should land in a pause, not mid-speech. The chosen point is
        # where the pause starts, so the silence opens the next chunk: that is
        # where to look for it.
        noisy = 0
        for s in segs[1:]:
            head = s[:int(0.05 * SR)]
            if float(np.sqrt(np.mean(head ** 2))) > 0.02:
                noisy += 1
        note = f" ({noisy} cuts outside a pause)" if noisy else ""
        print(f"{duration:>5}s -> {len(segs):>2} chunks, "
              f"{min(lengths):.1f}s to {max(lengths):.1f}s{note}")
        if noisy:
            failures.append(f"{duration}s: {noisy} cuts outside a pause")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
