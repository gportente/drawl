"""System-wide hotkey (Windows RegisterHotKey) on a thread of its own."""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable

from ..i18n import t

user32 = ctypes.WinDLL("user32", use_last_error=True)

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x0001, 0x0002, 0x0004, 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

_MODS = {"alt": MOD_ALT, "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
         "shift": MOD_SHIFT, "win": MOD_WIN, "super": MOD_WIN}

_KEYS = {"space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B,
         "escape": 0x1B, "backspace": 0x08, "insert": 0x2D, "delete": 0x2E,
         "printscreen": 0x2C, "prtsc": 0x2C, "pause": 0x13,
         **{f"f{i}": 0x6F + i for i in range(1, 13)}}


def parse(spec: str) -> tuple[int, int]:
    """'ctrl+alt+space' -> (modifiers, virtual key code)."""
    mods, vk = 0, None
    for part in spec.lower().split("+"):
        part = part.strip()
        if part in _MODS:
            mods |= _MODS[part]
        elif part in _KEYS:
            vk = _KEYS[part]
        elif len(part) == 1:
            vk = ord(part.upper())
        else:
            raise ValueError(f"unrecognised key in hotkey: {part!r}")
    if vk is None:
        raise ValueError(f"hotkey has no main key: {spec!r}")
    return mods | MOD_NOREPEAT, vk


class GlobalHotkey:
    """Register a hotkey and call `callback` (from a worker thread) on each press."""

    def __init__(self, spec: str, callback: Callable[[], None]):
        self._mods, self._vk = parse(spec)
        self._callback = callback
        self._thread: threading.Thread | None = None
        self._tid: int | None = None
        self._ready = threading.Event()
        self.error: str | None = None

    def _run(self) -> None:
        self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 1, self._mods, self._vk):
            self.error = t("error.hotkeyInUse", code=ctypes.get_last_error())
            self._ready.set()
            return
        self._ready.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    self._callback()
        finally:
            user32.UnregisterHotKey(None, 1)

    def start(self) -> bool:
        self._thread = threading.Thread(target=self._run, daemon=True, name="hotkey")
        self._thread.start()
        self._ready.wait(timeout=2.0)
        return self.error is None

    def stop(self) -> None:
        if self._tid is not None:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
