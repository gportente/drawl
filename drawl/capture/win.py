"""The Win32 pieces capture needs and Qt does not offer."""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")

WDA_NONE = 0x00
WDA_EXCLUDEFROMCAPTURE = 0x11     # Windows 10 2004 and later
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x2

# The desktop itself: clicking on it means "the whole screen", not a window.
_DESKTOP_CLASSES = {"Progman", "WorkerW"}

user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]


def exclude_from_capture(win_id: int, exclude: bool = True) -> bool:
    """Leave a window out of every screenshot and recording, ours included.

    The pill sits on top of everything, so without this it would end up in the
    middle of every capture. Screenshots and screen recordings both honour it,
    whether they go through GDI or Windows.Graphics.Capture.
    """
    return bool(user32.SetWindowDisplayAffinity(
        wintypes.HWND(win_id), WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE))


def _frame_bounds(hwnd) -> tuple[int, int, int, int] | None:
    """The visible frame, without the invisible resize borders of Windows 10+."""
    rect = wintypes.RECT()
    if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                                    ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
    w, h = rect.right - rect.left, rect.bottom - rect.top
    return (rect.left, rect.top, w, h) if w > 0 and h > 0 else None


def _cloaked(hwnd) -> bool:
    # Windows on other virtual desktops, and suspended UWP apps, are "visible"
    # yet not on screen: DWM keeps them cloaked.
    value = wintypes.DWORD()
    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(value),
                                 ctypes.sizeof(value))
    return value.value != 0


def _invisible(hwnd) -> bool:
    """Click-through or fully transparent overlays: on screen, but not a target."""
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    if ex & WS_EX_TRANSPARENT:
        return True
    if ex & WS_EX_LAYERED:
        alpha, flags = ctypes.c_ubyte(), wintypes.DWORD()
        if user32.GetLayeredWindowAttributes(hwnd, None, ctypes.byref(alpha),
                                             ctypes.byref(flags)):
            return bool(flags.value & LWA_ALPHA) and alpha.value == 0
    return False


def window_rects() -> list[tuple[int, int, int, int]]:
    """Top-level windows on screen, topmost first, in physical pixels.

    Used to snap the selection to the window under the pointer. Our own windows
    are skipped: the selector overlay would otherwise cover everything.
    """
    own_pid = os.getpid()
    rects: list[tuple[int, int, int, int]] = []
    class_name = ctypes.create_unicode_buffer(64)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == own_pid:
            return True
        user32.GetClassNameW(hwnd, class_name, len(class_name))
        if class_name.value in _DESKTOP_CLASSES:
            return True
        if _cloaked(hwnd) or _invisible(hwnd):
            return True
        bounds = _frame_bounds(hwnd)
        if bounds:
            rects.append(bounds)
        return True

    user32.EnumWindows(visit, 0)   # EnumWindows walks the Z order, top first
    return rects

