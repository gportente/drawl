"""The editor's drawing surface: a screenshot plus the annotations drawn on it.

Input is handled here rather than in QML so that tools, selection, text entry
and undo live in one place. Painting goes through `shapes.paint`, the same code
that produces the exported image.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QPointF, QRectF, QSizeF, Qt, Signal, Slot
from PySide6.QtGui import (QColor, QCursor, QFontMetricsF, QImage, QKeySequence,
                           QPainter, QPen)
from PySide6.QtQuick import QQuickPaintedItem

from ..capture import shapes as S
from ..capture.shapes import Shape

# Keys that pick a tool while no text is being typed.
TOOL_KEYS = {
    Qt.Key_V: "select", Qt.Key_A: "arrow", Qt.Key_L: "line", Qt.Key_R: "rect",
    Qt.Key_E: "ellipse", Qt.Key_P: "pen", Qt.Key_H: "marker", Qt.Key_T: "text",
    Qt.Key_N: "step", Qt.Key_B: "pixelate", Qt.Key_C: "crop",
}
UNDO_LIMIT = 100
HANDLE_PX = 9          # handle size on screen, whatever the zoom
MIN_DRAG_PX = 3        # below this a drag is a click, and draws nothing
ACCENT = QColor("#6EE7F9")


class AnnotationCanvas(QQuickPaintedItem):
    toolChanged = Signal()
    styleChanged = Signal()
    historyChanged = Signal()
    selectionChanged = Signal()
    imageChanged = Signal()
    editingChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setActiveFocusOnTab(True)
        self.setAntialiasing(True)

        self._image = QImage()
        self._scale = 1.0              # physical pixels per logical pixel of the capture
        self._shapes: list[Shape] = []
        self._undo: list[tuple[QImage, list[Shape]]] = []
        self._redo: list[tuple[QImage, list[Shape]]] = []
        self._pending: tuple[QImage, list[Shape]] | None = None

        self._tool = "arrow"
        self._color = "#F43F5E"
        self._size = 1
        self._fill = False

        self._selected: int | None = None
        # Picked on purpose (select tool, or the text being typed), as opposed
        # to just drawn: only then does a new colour or size change it.
        self._picked = False
        self._editing: int | None = None     # text shape receiving keystrokes
        self._drag: str | None = None        # "draw" | "move" | "handle" | "crop"
        self._handle = -1
        self._origin = QPointF()
        self._last = QPointF()
        self._crop: QRectF | None = None
        self._backdrop: QImage | None = None   # the screenshot scaled to the view

    # --- set up from Python ---------------------------------------------------------

    def set_image(self, image: QImage, scale: float) -> None:
        self._image = image
        self._scale = scale
        self._shapes, self._undo, self._redo = [], [], []
        self._selected = self._editing = None
        self._backdrop = None
        self.imageChanged.emit()
        self.historyChanged.emit()
        self.selectionChanged.emit()
        self.update()

    def rendered(self) -> QImage:
        self._finish_text()
        return S.render(self._image, self._shapes)

    # --- properties for QML ---------------------------------------------------------

    def _get_tool(self) -> str:
        return self._tool

    def _set_tool(self, tool: str) -> None:
        if tool == self._tool:
            return
        self._finish_text()
        self._tool = tool
        if tool == "crop":
            self._select(None)
        self._update_cursor(None)
        self.toolChanged.emit()

    def _get_color(self) -> str:
        return self._color

    def _set_color(self, color: str) -> None:
        self._color = color
        self._restyle(color=color)
        self.styleChanged.emit()

    def _get_size(self) -> int:
        return self._size

    def _set_size(self, size: int) -> None:
        self._size = max(0, min(size, len(S.SIZES) - 1))
        self._restyle(width=self._width())
        self.styleChanged.emit()

    def _get_fill(self) -> bool:
        return self._fill

    def _set_fill(self, fill: bool) -> None:
        self._fill = fill
        self._restyle(fill=fill)
        self.styleChanged.emit()

    tool = Property(str, _get_tool, _set_tool, notify=toolChanged)
    color = Property(str, _get_color, _set_color, notify=styleChanged)
    size = Property(int, _get_size, _set_size, notify=styleChanged)
    fill = Property(bool, _get_fill, _set_fill, notify=styleChanged)
    canUndo = Property(bool, lambda self: bool(self._undo), notify=historyChanged)
    canRedo = Property(bool, lambda self: bool(self._redo), notify=historyChanged)
    hasSelection = Property(bool, lambda self: self._selected is not None,
                            notify=selectionChanged)
    editing = Property(bool, lambda self: self._editing is not None, notify=editingChanged)
    # The capture's size in logical pixels: what "100 %" means on screen.
    naturalWidth = Property(float, lambda self: self._image.width() / self._scale,
                            notify=imageChanged)
    naturalHeight = Property(float, lambda self: self._image.height() / self._scale,
                             notify=imageChanged)
    pixelWidth = Property(int, lambda self: self._image.width(), notify=imageChanged)
    pixelHeight = Property(int, lambda self: self._image.height(), notify=imageChanged)

    # --- history --------------------------------------------------------------------

    def _state(self) -> tuple[QImage, list[Shape]]:
        return self._image, [s.copy() for s in self._shapes]

    def _begin(self) -> None:
        """Remember the state before a change; it reaches the history only if
        something actually changed by the time `_commit` runs."""
        if self._pending is None:
            self._pending = self._state()

    def _commit(self) -> None:
        if self._pending is None:
            return
        image, before = self._pending
        self._pending = None
        if image is self._image and before == self._shapes:
            return
        self._undo.append((image, before))
        del self._undo[:-UNDO_LIMIT]
        self._redo.clear()
        self.historyChanged.emit()

    def _restore(self, state: tuple[QImage, list[Shape]]) -> None:
        image, shapes = state
        if image is not self._image:
            self._image = image
            self._backdrop = None
            self.imageChanged.emit()
        self._shapes = shapes
        self._selected = self._editing = None
        self.selectionChanged.emit()
        self.editingChanged.emit()
        self.historyChanged.emit()
        self.update()

    @Slot()
    def undo(self) -> None:
        self._finish_text()
        if self._undo:
            self._redo.append(self._state())
            self._restore(self._undo.pop())

    @Slot()
    def redo(self) -> None:
        self._finish_text()
        if self._redo:
            self._undo.append(self._state())
            self._restore(self._redo.pop())

    @Slot()
    def deleteSelection(self) -> None:
        if self._selected is None:
            return
        self._begin()
        del self._shapes[self._selected]
        self._selected = self._editing = None
        self._commit()
        self.selectionChanged.emit()
        self.editingChanged.emit()
        self.update()

    # --- helpers --------------------------------------------------------------------

    def _width(self) -> float:
        return S.SIZES[self._size] * self._scale

    def _view_scale(self) -> float:
        return self.width() / self._image.width() if self._image.width() else 1.0

    def _to_image(self, pos: QPointF) -> QPointF:
        k = self._view_scale()
        return QPointF(pos.x() / k, pos.y() / k)

    def _tolerance(self) -> float:
        return 5 / self._view_scale()

    def _select(self, index: int | None, picked: bool = False) -> None:
        """Select a shape. A shape just drawn is selected too, for its handles,
        but not `picked`: choosing a colour right after drawing is for the next
        shape, and recolouring the last one would come as a surprise."""
        was_picked, self._picked = self._picked, picked and index is not None
        if index == self._selected and self._picked == was_picked:
            return
        self._selected = index
        if index is not None and self._picked:
            # The toolbar follows the picked shape, so it shows what a change
            # of colour or size would apply to.
            s = self._shapes[index]
            self._color, self._fill = s.color, s.fill
            self._size = min(range(len(S.SIZES)),
                             key=lambda i: abs(S.SIZES[i] * self._scale - s.width))
            self.styleChanged.emit()
        self.selectionChanged.emit()
        self.update()

    def _restyle(self, **changes) -> None:
        if self._selected is None or not self._picked:
            return
        s = self._shapes[self._selected]
        if all(getattr(s, k) == v for k, v in changes.items()):
            return
        self._begin()
        for k, v in changes.items():
            setattr(s, k, v)
        self._commit()
        self.update()

    def _handle_at(self, pos: QPointF) -> int:
        if self._selected is None:
            return -1
        reach = HANDLE_PX / self._view_scale()
        for i, h in enumerate(S.handles(self._shapes[self._selected])):
            if abs(h.x() - pos.x()) <= reach and abs(h.y() - pos.y()) <= reach:
                return i
        return -1

    def _new_shape(self, pos: QPointF) -> Shape:
        kind = self._tool
        pts = [(pos.x(), pos.y())]
        if kind in S.TWO_POINT:
            pts.append((pos.x(), pos.y()))
        return Shape(kind, pts, self._color, self._width(), self._fill,
                     number=S.next_step(self._shapes) if kind == "step" else 0)

    def _finish_text(self) -> None:
        """Stop typing: an empty text box is dropped rather than kept invisible."""
        if self._editing is None:
            return
        index = self._editing
        self._editing = None
        self._picked = False
        if not self._shapes[index].text.strip():
            del self._shapes[index]
            if self._selected == index:
                self._selected = None
            elif self._selected is not None and self._selected > index:
                self._selected -= 1
            self.selectionChanged.emit()
        self._commit()
        self.editingChanged.emit()
        self.update()

    def _edit_text(self, index: int) -> None:
        self._begin()
        self._editing = index
        self._select(index, picked=True)
        self.editingChanged.emit()
        self.update()

    def _apply_crop(self, rect: QRectF) -> None:
        area = rect.toAlignedRect().intersected(self._image.rect())
        if area.width() < 4 or area.height() < 4:
            return
        self._begin()
        self._image = self._image.copy(area)
        for s in self._shapes:
            S.move(s, -area.x(), -area.y())
        self._backdrop = None
        self._commit()
        self.imageChanged.emit()

    def _update_cursor(self, pos: QPointF | None) -> None:
        shape = Qt.CrossCursor
        if self._tool == "text":
            shape = Qt.IBeamCursor
        if pos is not None:
            if self._handle_at(pos) >= 0:
                shape = Qt.SizeAllCursor
            elif self._tool == "select":
                hit = S.topmost_at(self._shapes, pos, self._tolerance())
                shape = Qt.SizeAllCursor if hit is not None else Qt.ArrowCursor
        self.setCursor(QCursor(shape))

    # --- mouse ----------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        self.forceActiveFocus()
        pos = self._to_image(event.position())
        self._origin = self._last = pos

        if self._editing is not None:
            editing = self._editing
            if S.hit(self._shapes[editing], pos, self._tolerance()):
                event.accept()
                return                      # clicking inside the text keeps typing
            self._finish_text()

        handle = self._handle_at(pos)
        if handle >= 0:
            self._begin()
            self._drag, self._handle = "handle", handle
        elif self._tool == "select":
            hit = S.topmost_at(self._shapes, pos, self._tolerance())
            self._select(hit, picked=True)
            if hit is not None:
                self._begin()
                self._drag = "move"
        elif self._tool == "crop":
            self._drag = "crop"
            self._crop = QRectF(pos, pos)
        elif self._tool == "text":
            hit = S.topmost_at(self._shapes, pos, self._tolerance())
            if hit is not None and self._shapes[hit].kind == "text":
                self._edit_text(hit)
            else:
                self._begin()
                font = S.font_px(Shape("text", [], width=self._width()))
                # The click marks the middle of the first line, not its top.
                self._shapes.append(Shape("text", [(pos.x(), pos.y() - font * 0.65)],
                                          self._color, self._width()))
                self._edit_text(len(self._shapes) - 1)
        else:
            self._begin()
            self._shapes.append(self._new_shape(pos))
            self._select(len(self._shapes) - 1)
            self._drag = "draw" if self._tool != "step" else None
            if self._tool == "step":
                self._commit()
        event.accept()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        pos = self._to_image(event.position())
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        if self._drag == "draw" and self._selected is not None:
            s = self._shapes[self._selected]
            if s.kind in S.TWO_POINT:
                end = S.constrain(self._origin, pos, s.kind) if shift else pos
                s.pts[1] = (end.x(), end.y())
            elif shift and s.kind in S.FREEHAND:
                # A straight stroke, as with a ruler: handy for underlining.
                end = S.constrain(self._origin, pos, "line")
                s.pts[1:] = [(end.x(), end.y())]
            else:
                last = s.pts[-1]
                if abs(pos.x() - last[0]) + abs(pos.y() - last[1]) >= 1.5 / self._view_scale():
                    s.pts.append((pos.x(), pos.y()))
        elif self._drag == "move" and self._selected is not None:
            S.move(self._shapes[self._selected], pos.x() - self._last.x(),
                   pos.y() - self._last.y())
        elif self._drag == "handle" and self._selected is not None:
            s = self._shapes[self._selected]
            if shift and s.kind in S.TWO_POINT:
                anchor = S.handles(s)[(self._handle + 2) % 4 if s.kind in S.BOXES
                                      else 1 - self._handle]
                pos = S.constrain(anchor, pos, s.kind)
            S.drag_handle(s, self._handle, pos)
        elif self._drag == "crop":
            self._crop = QRectF(self._origin, pos).normalized()
        self._last = pos
        event.accept()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        drag, self._drag = self._drag, None
        if drag == "draw" and self._selected is not None:
            s = self._shapes[self._selected]
            span = S.bounds(s).adjusted(s.width / 2, s.width / 2, -s.width / 2, -s.width / 2)
            too_small = max(span.width(), span.height()) * self._view_scale() < MIN_DRAG_PX
            if s.kind in S.TWO_POINT and too_small:
                del self._shapes[self._selected]
                self._select(None)
            else:
                S.normalise(s)
        elif drag == "handle" and self._selected is not None:
            S.normalise(self._shapes[self._selected])
        elif drag == "crop" and self._crop is not None:
            self._apply_crop(self._crop)
            self._crop = None
            self._set_tool("select")
        if self._editing is None:
            self._commit()
        event.accept()
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        pos = self._to_image(event.position())
        hit = S.topmost_at(self._shapes, pos, self._tolerance())
        if hit is not None and self._shapes[hit].kind == "text":
            self._edit_text(hit)
        event.accept()

    def hoverMoveEvent(self, event) -> None:
        self._update_cursor(self._to_image(event.position()))

    # --- keyboard -------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        key, mods = event.key(), event.modifiers()
        if event.matches(QKeySequence.Undo):
            self.undo()
        elif event.matches(QKeySequence.Redo):
            self.redo()
        elif self._editing is not None:
            self._type(event)
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.deleteSelection()
        elif key == Qt.Key_Escape and self._crop is not None:
            self._crop, self._drag = None, None
        elif key == Qt.Key_Escape:
            self._select(None)
        elif key in TOOL_KEYS and not mods & (Qt.ControlModifier | Qt.AltModifier):
            self._set_tool(TOOL_KEYS[key])
        elif Qt.Key_1 <= key <= Qt.Key_3 and not mods & Qt.ControlModifier:
            self._set_size(key - Qt.Key_1)
        else:
            event.ignore()
            return
        event.accept()
        self.update()

    def _type(self, event) -> None:
        s = self._shapes[self._editing]
        key = event.key()
        if key == Qt.Key_Escape or (key in (Qt.Key_Return, Qt.Key_Enter)
                                    and event.modifiers() & Qt.ControlModifier):
            self._finish_text()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            s.text += "\n"
        elif key == Qt.Key_Backspace:
            s.text = s.text[:-1]
        elif event.text() and event.text().isprintable():
            s.text += event.text()
        else:
            event.ignore()

    # --- painting -------------------------------------------------------------------

    def paint(self, painter: QPainter) -> None:
        if self._image.isNull():
            return
        k = self._view_scale()
        target = QRectF(0, 0, self.width(), self.height())

        # The screenshot is scaled once per view size, not on every repaint:
        # drawing a 1440p image smoothly on each mouse move would stutter.
        dpr = self.window().effectiveDevicePixelRatio() if self.window() else 1.0
        wanted = QSizeF(self.width() * dpr, self.height() * dpr).toSize()
        if self._backdrop is None or self._backdrop.size() != wanted:
            self._backdrop = self._image.scaled(wanted, Qt.IgnoreAspectRatio,
                                                Qt.SmoothTransformation)
        painter.drawImage(target, self._backdrop)

        painter.save()
        painter.scale(k, k)
        S.paint(painter, self._shapes, self._image)
        painter.restore()

        if self._editing is not None:
            self._paint_caret(painter, k)
        if self._selected is not None and self._editing is None:
            self._paint_selection(painter, k)
        if self._crop is not None:
            self._paint_crop(painter, k)

    def _paint_caret(self, painter: QPainter, k: float) -> None:
        s = self._shapes[self._editing]
        r = S.text_rect(s)
        line_h = r.height() / len(S.text_lines(s))
        last = S.text_lines(s)[-1]
        x = r.left() + QFontMetricsF(S.font(s)).horizontalAdvance(last) + 2
        top = r.bottom() - line_h
        painter.setPen(QPen(QColor(s.color), 2))
        painter.drawLine(QPointF(x * k, top * k), QPointF(x * k, (top + line_h) * k))
        frame = r.adjusted(-6, -4, 10, 4)
        pen = QPen(ACCENT, 1, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(frame.x() * k, frame.y() * k, frame.width() * k,
                                frame.height() * k))

    def _paint_selection(self, painter: QPainter, k: float) -> None:
        s = self._shapes[self._selected]
        painter.setRenderHint(QPainter.Antialiasing, True)
        points = S.handles(s)
        if not points:
            # Nothing to reshape (text, steps, freehand): the frame shows the selection.
            r = S.bounds(s)
            painter.setPen(QPen(ACCENT, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(r.x() * k, r.y() * k, r.width() * k, r.height() * k))
        half = HANDLE_PX / 2
        painter.setPen(QPen(QColor("#0B0D12"), 1))
        painter.setBrush(QColor("#FFFFFF"))
        for h in points:
            painter.drawRect(QRectF(h.x() * k - half, h.y() * k - half, HANDLE_PX, HANDLE_PX))

    def _paint_crop(self, painter: QPainter, k: float) -> None:
        r = QRectF(self._crop.x() * k, self._crop.y() * k,
                   self._crop.width() * k, self._crop.height() * k)
        shade = QColor(0, 0, 0, 140)
        w, h = self.width(), self.height()
        painter.fillRect(QRectF(0, 0, w, r.top()), shade)
        painter.fillRect(QRectF(0, r.bottom(), w, h - r.bottom()), shade)
        painter.fillRect(QRectF(0, r.top(), r.left(), r.height()), shade)
        painter.fillRect(QRectF(r.right(), r.top(), w - r.right(), r.height()), shade)
        painter.setPen(QPen(ACCENT, 1.5, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(r)
