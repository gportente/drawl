"""Generates drawl.ico from the same drawing used for the tray icon.

A Windows shortcut wants an .ico file on disk, while the app draws its own icon
at runtime: this script keeps the two the same image.

    .venv\\Scripts\\python.exe tools\\make_icon.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, Qt
from PySide6.QtGui import QBrush, QColor, QGuiApplication, QLinearGradient, QPainter, QPixmap

SIZES = (16, 24, 32, 48, 64, 128, 256)
OUT = Path(__file__).resolve().parents[1] / "drawl" / "ui" / "drawl.ico"


def render(size: int) -> QPixmap:
    """The same drawing as drawl/ui/app.py:_app_icon(), scaled to `size`."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    k = size / 64.0
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor("#6EE7F9"))
    grad.setColorAt(1.0, QColor("#A78BFA"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawEllipse(4 * k, 4 * k, 56 * k, 56 * k)

    p.setPen(QColor("#0B0D12"))
    p.setBrush(QColor("#0B0D12"))
    p.drawRoundedRect(26 * k, 16 * k, 12 * k, 22 * k, 6 * k, 6 * k)
    p.end()
    return pm


def png_bytes(pm: QPixmap) -> bytes:
    # The QByteArray has to be held in a variable: passed as a temporary it is
    # collected while QBuffer is still using it.
    store = QByteArray()
    buf = QBuffer(store)
    buf.open(QBuffer.WriteOnly)
    pm.save(buf, "PNG")
    buf.close()
    return bytes(store)


def main() -> int:
    # The instance must be bound to a name: left unassigned it is collected
    # right away and the first QPixmap segfaults.
    app = QGuiApplication(sys.argv)  # noqa: F841 - must stay alive until the end

    images = [png_bytes(render(s)) for s in SIZES]

    # ICONDIR + one ICONDIRENTRY per size, then the PNGs appended.
    # An .ico carrying PNG payloads is valid from Windows Vista onwards.
    header = struct.pack("<HHH", 0, 1, len(SIZES))
    offset = len(header) + 16 * len(SIZES)
    entries, payload = b"", b""
    for size, data in zip(SIZES, images):
        dim = 0 if size >= 256 else size    # 0 means 256 in this format
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        payload += data

    OUT.write_bytes(header + entries + payload)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(SIZES)} resolutions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
