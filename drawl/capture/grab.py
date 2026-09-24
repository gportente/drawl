"""Freezing the screens, so the selection is drawn over a still image."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication, QImage, QScreen

from . import win


@dataclass
class Shot:
    """One screen, as it was the moment the capture started."""

    screen: QScreen
    image: QImage          # physical pixels

    @property
    def scale(self) -> float:
        """Physical pixels per logical pixel on this screen."""
        return self.image.width() / max(1, self.screen.geometry().width())

    def physical(self) -> QRect:
        """The screen's rectangle on the virtual desktop, in physical pixels.

        Qt keeps each screen's top-left corner in native coordinates and only
        scales the size, which is what makes this line up with the rectangles
        Win32 reports for windows, even across monitors with different scaling.
        """
        return QRect(self.screen.geometry().topLeft(), self.image.size())


def grab_screens() -> list[Shot]:
    shots = []
    for screen in QGuiApplication.screens():
        image = screen.grabWindow(0).toImage()
        if not image.isNull():
            shots.append(Shot(screen, image))
    return shots


def window_rects_on(shot: Shot) -> list[QRect]:
    """Windows visible on this screen, topmost first, in the shot's pixels."""
    area = shot.physical()
    rects = []
    for x, y, w, h in win.window_rects():
        r = QRect(x, y, w, h).intersected(area)
        if r.width() > 8 and r.height() > 8:
            rects.append(r.translated(-area.topLeft()))
    return rects
