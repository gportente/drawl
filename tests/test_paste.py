"""Checks that the synthetic Ctrl+V really reaches the focused window."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drawl.output.inject import paste_into_active_window  # noqa: E402

EXPECTED = "però così è corretto: àèìòù"
result = {"ok": False}


def main() -> int:
    app = QApplication(sys.argv)
    field = QLineEdit()
    field.setWindowTitle("drawl paste test")
    field.resize(420, 40)
    field.show()
    field.raise_()
    field.activateWindow()
    field.setFocus()

    QApplication.clipboard().setText(EXPECTED)

    def force_foreground(hwnd: int) -> bool:
        """Windows denies the foreground to a background process, so for the
        test it is taken by attaching to the foreground thread's input queue.
        The real app never needs this, because it never steals focus."""
        import ctypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        fg = user32.GetForegroundWindow()
        fg_tid = user32.GetWindowThreadProcessId(fg, None)
        cur_tid = kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(cur_tid, fg_tid, True)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(cur_tid, fg_tid, False)
        return user32.GetForegroundWindow() == hwnd

    def do_paste() -> None:
        hwnd = int(field.winId())
        ok = force_foreground(hwnd)
        print(f"focus on the test window: {'yes' if ok else 'NOT acquired'}")
        field.setFocus()
        try:
            paste_into_active_window()
        except OSError as exc:
            print(f"SendInput failed: {exc}")

    def check() -> None:
        got = field.text()
        result["ok"] = got == EXPECTED
        print(f"expected: {EXPECTED!r}")
        print(f"got     : {got!r}")
        print("PASTE OK" if result["ok"] else "PASTE FAILED")
        app.quit()

    QTimer.singleShot(900, do_paste)
    QTimer.singleShot(1900, check)
    app.exec()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
