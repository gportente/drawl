"""Persistent settings, stored as JSON next to the models."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .paths import config_file

DEFAULTS = {
    "engine": "parakeet",      # parakeet | whisper
    "language": "it",          # whisper only; parakeet detects the language itself
    "ui_language": "en",       # en | it | auto (follow the system)
    "hotkey": "ctrl+shift+space",
    "auto_paste": True,        # paste into the active window once transcribed
    "sample_rate": 16000,
    # Input device index or name; null means the system default. Useful for
    # picking one microphone out of several.
    "input_device": None,
    "num_threads": 10,
    # Seconds of inactivity after which the model leaves memory.
    # 0 keeps it loaded for good (idle ~820 MB instead of ~125).
    "unload_after_s": 180,
    "whisper_model": "large-v3-turbo",
    # Screenshots and screen recordings. PrintScreen rather than letters, so
    # the hotkeys do not steal a shortcut from the application in front
    # (Ctrl+Shift+4 and 5 are number formats in Excel).
    "screenshot_hotkey": "ctrl+printscreen",
    "record_hotkey": "shift+printscreen",
    "screenshot_dir": None,    # null: Pictures\drawl
    "recording_dir": None,     # null: Videos\drawl
    "record_fps": 30,
    "orb_x": -1,               # -1 means "place it automatically"
    "orb_y": -1,
}


@dataclass
class Config:
    values: dict = field(default_factory=lambda: dict(DEFAULTS))

    @classmethod
    def load(cls) -> "Config":
        path = config_file()
        values = dict(DEFAULTS)
        if path.exists():
            try:
                values.update(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass  # corrupt settings: fall back to the defaults
        return cls(values)

    def save(self) -> None:
        config_file().write_text(
            json.dumps(self.values, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def __getitem__(self, key: str):
        return self.values.get(key, DEFAULTS.get(key))

    def __setitem__(self, key: str, value) -> None:
        self.values[key] = value
