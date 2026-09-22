"""Guard against running more than one copy of drawl.

Without it a second instance starts but stays mute: only one process can own
the global hotkey, and the losing copy has no way to say so. With the shortcut
sitting in the Startup folder it is easy to launch a second one by hand without
noticing the first is already running.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = r"Local\drawl-single-instance"

# Message sent to the running instance asking it to show itself.
WM_DRAWL_SHOW = user32.RegisterWindowMessageW("drawl.show.window")
HWND_BROADCAST = 0xFFFF

_handle = None


def acquire() -> bool:
    """True if we are the first instance, False if another copy is running.

    The mutex stays open for the life of the process; Windows releases it on
    exit by itself, crashes included.
    """
    global _handle
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    _handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def ask_running_instance_to_show() -> None:
    """Ask the copy that is already running to show itself, then exit."""
    user32.PostMessageW(HWND_BROADCAST, WM_DRAWL_SHOW, 0, 0)
