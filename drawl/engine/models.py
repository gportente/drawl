"""Downloading and keeping track of the local ASR models."""
from __future__ import annotations

import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable

from ..paths import models_dir

PARAKEET_NAME = "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
PARAKEET_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    f"{PARAKEET_NAME}.tar.bz2"
)

ProgressFn = Callable[[str, float], None]


def parakeet_path() -> Path:
    return models_dir() / PARAKEET_NAME


def parakeet_ready() -> bool:
    d = parakeet_path()
    return all((d / f).exists() for f in ("encoder.int8.onnx", "decoder.int8.onnx",
                                          "joiner.int8.onnx", "tokens.txt"))


def ensure_parakeet(progress: ProgressFn | None = None) -> Path:
    """Fetch and unpack Parakeet v3 unless it is already there. Returns its folder."""
    dest = parakeet_path()
    if parakeet_ready():
        return dest

    def report(stage: str, frac: float) -> None:
        if progress:
            progress(stage, frac)

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "model.tar.bz2"
        report("download", 0.0)
        with urllib.request.urlopen(PARAKEET_URL) as resp, open(archive, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            while chunk := resp.read(1 << 20):
                out.write(chunk)
                done += len(chunk)
                if total:
                    report("download", done / total)

        report("extract", 0.0)
        with tarfile.open(archive, "r:bz2") as tar:
            tar.extractall(tmp, filter="data")
        extracted = Path(tmp) / PARAKEET_NAME
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(extracted), str(dest))
        report("extract", 1.0)

    return dest
