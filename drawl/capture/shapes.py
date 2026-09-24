"""Annotations drawn on a screenshot: the model, hit testing and painting.

Everything is in the image's own pixels, so the same `paint` serves the editor
(scaled to fit the window) and the export (at 1:1): what is saved is exactly
what was on screen, with no second renderer to drift out of step.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QPainter,
                           QPainterPath, QPainterPathStroker, QPen, QPolygonF)

# Drawn by dragging from one corner, or one end, to the other.
TWO_POINT = {"arrow", "line", "rect", "ellipse", "pixelate"}
BOXES = {"rect", "ellipse", "pixelate"}
# Drawn by following the pointer.
FREEHAND = {"pen", "marker"}
KINDS = TWO_POINT | FREEHAND | {"text", "step"}

# Stroke widths for the three sizes, before scaling to the screen's density.
SIZES = (3.0, 6.0, 10.0)
FONT_FAMILY = "Segoe UI"


@dataclass
class Shape:
    kind: str
    pts: list[tuple[float, float]]
    color: str = "#F43F5E"
    width: float = 6.0
    fill: bool = False
    text: str = ""
    number: int = 0

    def copy(self) -> "Shape":
        return replace(self, pts=list(self.pts))


# --- geometry derived from the width -----------------------------------------------
# One size control drives every tool, so each derives its own proportions from
# the stroke width rather than having a setting of its own.

def font_px(s: Shape) -> float:
    return 2.5 * s.width + 10


def step_radius(s: Shape) -> float:
    return 1.5 * s.width + 10


def marker_width(s: Shape) -> float:
    return 3 * s.width + 10


def pixel_block(s: Shape) -> int:
    return int(2 * s.width + 6)


def font(s: Shape) -> QFont:
    face = QFont(FONT_FAMILY)
    face.setPixelSize(max(1, round(font_px(s) if s.kind == "text" else step_radius(s))))
    face.setBold(s.kind == "step")
    return face


def _p(pt: tuple[float, float]) -> QPointF:
    return QPointF(pt[0], pt[1])


def box(s: Shape) -> QRectF:
    """The rectangle spanned by the first two points, whichever way it was drawn."""
    return QRectF(_p(s.pts[0]), _p(s.pts[1])).normalized()


def text_lines(s: Shape) -> list[str]:
    return s.text.split("\n") if s.text else [""]


def text_rect(s: Shape) -> QRectF:
    fm = QFontMetricsF(font(s))
    lines = text_lines(s)
    width = max(fm.horizontalAdvance(line) for line in lines)
    return QRectF(_p(s.pts[0]), QPointF(s.pts[0][0] + max(width, 2),
                                        s.pts[0][1] + fm.lineSpacing() * len(lines)))


def contrast(color: QColor) -> QColor:
    """Black or white, whichever reads better on `color`."""
    luma = 0.299 * color.redF() + 0.587 * color.greenF() + 0.114 * color.blueF()
    return QColor("#111318") if luma > 0.62 else QColor("#FFFFFF")


def bounds(s: Shape) -> QRectF:
    if s.kind in TWO_POINT:
        r = box(s)
    elif s.kind in FREEHAND:
        xs = [p[0] for p in s.pts]
        ys = [p[1] for p in s.pts]
        r = QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    elif s.kind == "text":
        r = text_rect(s)
    else:  # step
        rad = step_radius(s)
        r = QRectF(s.pts[0][0] - rad, s.pts[0][1] - rad, 2 * rad, 2 * rad)
    pad = (marker_width(s) if s.kind == "marker" else s.width) / 2
    return r.adjusted(-pad, -pad, pad, pad)


# --- handles -----------------------------------------------------------------------

def handles(s: Shape) -> list[QPointF]:
    """Points that can be dragged to reshape: the ends of a line, the corners of a box."""
    if s.kind in ("arrow", "line"):
        return [_p(s.pts[0]), _p(s.pts[1])]
    if s.kind in BOXES:
        r = box(s)
        return [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]
    return []


def drag_handle(s: Shape, index: int, pos: QPointF) -> None:
    if s.kind in ("arrow", "line"):
        s.pts[index] = (pos.x(), pos.y())
        return
    r = box(s)
    # The corner opposite the one being dragged stays put.
    opposite = [r.bottomRight(), r.bottomLeft(), r.topLeft(), r.topRight()][index]
    s.pts[0] = (opposite.x(), opposite.y())
    s.pts[1] = (pos.x(), pos.y())


def normalise(s: Shape) -> None:
    """Store a box as top-left / bottom-right, so its handles keep their order."""
    if s.kind in BOXES:
        r = box(s)
        s.pts[:2] = [(r.left(), r.top()), (r.right(), r.bottom())]


def move(s: Shape, dx: float, dy: float) -> None:
    s.pts = [(x + dx, y + dy) for x, y in s.pts]


def constrain(origin: QPointF, pos: QPointF, kind: str) -> QPointF:
    """With Shift: lines snap to 45°, boxes become squares and circles."""
    d = pos - origin
    if kind in BOXES:
        side = max(abs(d.x()), abs(d.y()))
        return origin + QPointF(math.copysign(side, d.x() or 1), math.copysign(side, d.y() or 1))
    angle = round(math.atan2(d.y(), d.x()) / (math.pi / 4)) * (math.pi / 4)
    length = math.hypot(d.x(), d.y())
    return origin + QPointF(math.cos(angle) * length, math.sin(angle) * length)


# --- hit testing -------------------------------------------------------------------

def _stroke_hit(path: QPainterPath, pos: QPointF, width: float) -> bool:
    stroker = QPainterPathStroker()
    stroker.setWidth(width)
    stroker.setCapStyle(Qt.RoundCap)
    return stroker.createStroke(path).contains(pos)


def hit(s: Shape, pos: QPointF, tolerance: float) -> bool:
    if s.kind in ("arrow", "line"):
        path = QPainterPath(_p(s.pts[0]))
        path.lineTo(_p(s.pts[1]))
        return _stroke_hit(path, pos, s.width + 2 * tolerance)
    if s.kind in FREEHAND:
        w = marker_width(s) if s.kind == "marker" else s.width
        return _stroke_hit(_freehand_path(s), pos, w + 2 * tolerance)
    if s.kind == "pixelate" or (s.kind in BOXES and s.fill):
        r = box(s)
        if s.kind == "ellipse":
            path = QPainterPath()
            path.addEllipse(r)
            return path.contains(pos)
        return r.adjusted(-tolerance, -tolerance, tolerance, tolerance).contains(pos)
    if s.kind in BOXES:
        path = QPainterPath()
        if s.kind == "ellipse":
            path.addEllipse(box(s))
        else:
            path.addRect(box(s))
        return _stroke_hit(path, pos, s.width + 2 * tolerance)
    if s.kind == "text":
        return text_rect(s).adjusted(-tolerance, -tolerance, tolerance, tolerance).contains(pos)
    # step
    return QLineF(_p(s.pts[0]), pos).length() <= step_radius(s) + tolerance


def topmost_at(shapes: list[Shape], pos: QPointF, tolerance: float) -> int | None:
    for i in range(len(shapes) - 1, -1, -1):
        if hit(shapes[i], pos, tolerance):
            return i
    return None


def next_step(shapes: list[Shape]) -> int:
    return max((s.number for s in shapes if s.kind == "step"), default=0) + 1


# --- painting ----------------------------------------------------------------------

def _freehand_path(s: Shape) -> QPainterPath:
    """Through the midpoints of the samples: smooths the jitter of the mouse."""
    pts = [_p(p) for p in s.pts]
    path = QPainterPath(pts[0])
    if len(pts) == 1:
        path.lineTo(pts[0] + QPointF(0.01, 0))   # a dot still gets drawn
        return path
    for a, b in zip(pts[1:-1], pts[2:]):
        path.quadTo(a, (a + b) / 2)
    path.lineTo(pts[-1])
    return path


def _pen(color: QColor, width: float, cap=Qt.RoundCap, join=Qt.RoundJoin) -> QPen:
    pen = QPen(color, width)
    pen.setCapStyle(cap)
    pen.setJoinStyle(join)
    return pen


def _paint_arrow(p: QPainter, s: Shape, color: QColor) -> None:
    a, b = _p(s.pts[0]), _p(s.pts[1])
    line = QLineF(a, b)
    length = line.length()
    if length < 0.5:
        return
    head_len = min(3 * s.width + 10, length)
    head_half = 1.5 * s.width + 5
    ux, uy = (b.x() - a.x()) / length, (b.y() - a.y()) / length
    base = b - QPointF(ux, uy) * head_len
    normal = QPointF(-uy, ux) * head_half
    # The shaft stops inside the head, so its round cap does not poke through
    # the tip at large widths.
    p.setPen(_pen(color, s.width))
    p.drawLine(a, base + QPointF(ux, uy) * min(head_len * 0.5, s.width))
    p.setPen(_pen(color, max(1.0, s.width * 0.4)))
    p.setBrush(color)
    p.drawPolygon(QPolygonF([b, base + normal, base - normal]))


_pixel_cache: dict[tuple, QImage] = {}


def _pixelated(base: QImage, r: QRectF, block: int) -> QImage:
    rect = r.toAlignedRect().intersected(base.rect())
    key = (base.cacheKey(), rect.x(), rect.y(), rect.width(), rect.height(), block)
    if key not in _pixel_cache:
        if len(_pixel_cache) > 64:
            _pixel_cache.clear()
        small = base.copy(rect).scaled(max(1, rect.width() // block),
                                       max(1, rect.height() // block),
                                       Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        _pixel_cache[key] = small.scaled(rect.size(), Qt.IgnoreAspectRatio,
                                         Qt.FastTransformation)
    return _pixel_cache[key]


def _paint_text(p: QPainter, s: Shape, color: QColor) -> None:
    face = font(s)
    fm = QFontMetricsF(face)
    path = QPainterPath()
    x, y = s.pts[0]
    for i, line in enumerate(text_lines(s)):
        path.addText(QPointF(x, y + fm.ascent() + i * fm.lineSpacing()), face, line)
    # A halo in the opposite tone keeps the text legible on any background.
    halo = max(2.0, font_px(s) / 7)
    p.setPen(_pen(contrast(color), halo))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPath(path)


def _paint_step(p: QPainter, s: Shape, color: QColor) -> None:
    c = _p(s.pts[0])
    rad = step_radius(s)
    p.setPen(_pen(QColor("#FFFFFF"), max(1.5, rad / 8)))
    p.setBrush(color)
    p.drawEllipse(c, rad, rad)
    p.setPen(contrast(color))
    p.setFont(font(s))
    p.drawText(QRectF(c.x() - rad, c.y() - rad, 2 * rad, 2 * rad), Qt.AlignCenter,
               str(s.number))


def paint_shape(p: QPainter, s: Shape, base: QImage) -> None:
    color = QColor(s.color)
    p.save()
    if s.kind == "arrow":
        _paint_arrow(p, s, color)
    elif s.kind == "line":
        p.setPen(_pen(color, s.width))
        p.drawLine(_p(s.pts[0]), _p(s.pts[1]))
    elif s.kind in ("rect", "ellipse"):
        p.setPen(_pen(color, s.width, Qt.SquareCap, Qt.MiterJoin))
        p.setBrush(color if s.fill else Qt.NoBrush)
        (p.drawEllipse if s.kind == "ellipse" else p.drawRect)(box(s))
    elif s.kind == "pixelate":
        r = box(s)
        if r.width() >= 1 and r.height() >= 1:
            p.drawImage(r.toAlignedRect().intersected(base.rect()).topLeft(),
                        _pixelated(base, r, pixel_block(s)))
    elif s.kind == "pen":
        p.setPen(_pen(color, s.width))
        p.drawPath(_freehand_path(s))
    elif s.kind == "marker":
        # One path, stroked once: where the stroke crosses itself the colour
        # does not build up, as it would with a segment at a time.
        color.setAlphaF(0.42)
        p.setPen(_pen(color, marker_width(s), Qt.FlatCap if len(s.pts) > 1 else Qt.RoundCap))
        p.drawPath(_freehand_path(s))
    elif s.kind == "text":
        _paint_text(p, s, color)
    elif s.kind == "step":
        _paint_step(p, s, color)
    p.restore()


def paint(p: QPainter, shapes: list[Shape], base: QImage) -> None:
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)
    for s in shapes:
        if s.kind == "text" and not s.text:
            continue
        paint_shape(p, s, base)


def render(base: QImage, shapes: list[Shape]) -> QImage:
    """The screenshot with its annotations burned in, at full resolution."""
    out = base.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    painter = QPainter(out)
    paint(painter, shapes, base)
    painter.end()
    return out.convertToFormat(QImage.Format_RGB32)
