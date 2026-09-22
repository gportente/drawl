"""Standard locations used by the application."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "drawl"


def data_dir() -> Path:
    """Per-user data folder (LOCALAPPDATA/drawl on Windows)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def models_dir() -> Path:
    p = data_dir() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_file() -> Path:
    return data_dir() / "config.json"
