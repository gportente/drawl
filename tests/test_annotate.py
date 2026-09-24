"""The screenshot annotations: painting, hit testing, and the editor's input.

    .venv\\Scripts\\python.exe tests\\test_annotate.py
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

# QQuickPaintedItem.paint() runs on the render thread while the GUI thread
# waits, and QTest's waits do not release the GIL, so under the threaded render
# loop the Python paint() can never start. The app is unaffected: app.exec()
# releases the GIL. Here everything simply renders on one thread.
os.environ["QSG_RENDER_LOOP"] = "basic"

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QKeyEvent, QMouseEvent  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drawl.capture import shapes as S  # noqa: E402
from drawl.capture.shapes import Shape  # noqa: E402
from drawl.ui.canvas import AnnotationCanvas  # noqa: E402

RED = "#F43F5E"
BG = QColor("#202830")
failures: list[str] = []


def check(what: str, ok: bool) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {what}")
    if not ok:
        failures.append(what)


def blank(w: int = 200, h: int = 120) -> QImage:
    image = QImage(w, h, QImage.Format_RGB32)
    image.fill(BG)
    return image


def near(a: QColor, b: QColor, tol: int = 40) -> bool:
    return all(abs(x - y) <= tol for x, y in
               zip(a.getRgb()[:3], b.getRgb()[:3]))


def at(image: QImage, x: int, y: int) -> QColor:
    return image.pixelColor(x, y)


def test_painting() -> None:
    print("painting")
    red = QColor(RED)

    out = S.render(blank(), [Shape("arrow", [(20, 60), (180, 60)], RED, 6)])
    check("arrow: shaft is drawn", near(at(out, 100, 60), red))
    check("arrow: head is wider than the shaft", near(at(out, 158, 68), red))
    check("arrow: nothing far from it", at(out, 100, 100) == BG)

    out = S.render(blank(), [Shape("rect", [(20, 20), (180, 100)], RED, 6)])
    check("rectangle: border drawn", near(at(out, 100, 20), red))
    check("rectangle: inside left alone", at(out, 100, 60) == BG)

    out = S.render(blank(), [Shape("rect", [(20, 20), (180, 100)], RED, 6, fill=True)])
    check("filled rectangle: inside painted", near(at(out, 100, 60), red))

    out = S.render(blank(), [Shape("ellipse", [(20, 20), (180, 100)], RED, 6)])
    check("ellipse: rim drawn", near(at(out, 100, 20), red))
    check("ellipse: corner of the box left alone", at(out, 22, 22) == BG)

    out = S.render(blank(), [Shape("marker", [(20, 60), (100, 60), (180, 60)], RED, 6)])
    c = at(out, 100, 60)
    check("highlighter: translucent, the background shows through",
          c != BG and not near(c, red, 10))

    out = S.render(blank(), [Shape("step", [(100, 60)], RED, 6, number=3)])
    check("step: disc filled with the colour", near(at(out, 100 - 12, 60), red, 60))
    check("step: number drawn in the middle",
          any(near(at(out, x, y), QColor("#FFFFFF"), 60)
              for x in range(94, 106) for y in range(52, 68)))

    out = S.render(blank(), [Shape("text", [(10, 10)], RED, 6, text="Ciao\nmondo")])
    painted = sum(near(at(out, x, y), red, 30) for x in range(10, 120) for y in range(10, 80))
    check(f"text: two lines drawn ({painted} px)", painted > 150)
    check("text: an empty box paints nothing",
          S.render(blank(), [Shape("text", [(10, 10)], RED, 6)]) == S.render(blank(), []))

    # Pixelation must destroy the detail, not just soften it.
    noise = blank()
    rng = random.Random(1)
    for x in range(200):
        for y in range(120):
            noise.setPixelColor(x, y, QColor(rng.randrange(256), rng.randrange(256),
                                             rng.randrange(256)))
    out = S.render(noise, [Shape("pixelate", [(0, 0), (200, 120)], RED, 6)])
    block = S.pixel_block(Shape("pixelate", [], width=6))
    uniform = all(at(out, x, y) == at(out, 0, 0) for x in range(block - 2) for y in range(block - 2))
    check(f"pixelate: {block}px blocks of a single colour", uniform)
    check("pixelate: outside the area untouched",
          S.render(noise, [Shape("pixelate", [(100, 0), (200, 120)], RED, 6)]).pixelColor(10, 10)
          == noise.pixelColor(10, 10))


def test_geometry() -> None:
    print("geometry")
    line = Shape("line", [(0, 0), (100, 0)], RED, 4)
    check("line: hit on the stroke", S.hit(line, QPointF(50, 3), 2))
    check("line: missed away from it", not S.hit(line, QPointF(50, 20), 2))

    outline = Shape("rect", [(0, 0), (100, 100)], RED, 4)
    check("outline rectangle: its middle is not a hit", not S.hit(outline, QPointF(50, 50), 2))
    check("filled rectangle: its middle is a hit",
          S.hit(Shape("rect", [(0, 0), (100, 100)], RED, 4, fill=True), QPointF(50, 50), 2))

    stack = [Shape("rect", [(0, 0), (100, 100)], RED, 4, fill=True),
             Shape("rect", [(40, 40), (60, 60)], RED, 4, fill=True)]
    check("the topmost shape wins", S.topmost_at(stack, QPointF(50, 50), 2) == 1)

    box = Shape("rect", [(80, 70), (10, 20)], RED, 4)
    S.normalise(box)
    check("a box drawn backwards is stored top-left first", box.pts == [(10, 20), (80, 70)])
    S.drag_handle(box, 2, QPointF(120, 90))        # bottom-right corner
    check("dragging a corner keeps the opposite one", box.pts == [(10, 20), (120, 90)])

    end = S.constrain(QPointF(0, 0), QPointF(100, 8), "line")
    check("Shift snaps a line to the horizontal", abs(end.y()) < 1e-6)
    end = S.constrain(QPointF(0, 0), QPointF(100, 60), "rect")
    check("Shift makes a box square", end == QPointF(100, 100))

    steps = [Shape("step", [(0, 0)], number=1), Shape("step", [(0, 0)], number=4)]
    check("steps continue from the highest number", S.next_step(steps) == 5)


def test_canvas() -> None:
    """Drives the real editor surface with mouse and keyboard events."""
    print("editor input")
    window = QQuickWindow()
    window.resize(400, 240)
    canvas = AnnotationCanvas(window.contentItem())
    canvas.setSize(window.size().toSizeF())
    canvas.set_image(blank(400, 240), 1.0)
    window.show()
    QTest.qWaitForWindowExposed(window)

    def drag(a, b, mods=Qt.NoModifier):
        # Sent by hand: QTest.mouseMove cannot carry a modifier such as Shift.
        QTest.mousePress(window, Qt.LeftButton, mods, QPoint(*a))
        for i in range(1, 6):
            p = QPointF(a[0] + (b[0] - a[0]) * i / 5, a[1] + (b[1] - a[1]) * i / 5)
            QCoreApplication.sendEvent(window, QMouseEvent(
                QEvent.MouseMove, p, window.mapToGlobal(p), Qt.NoButton,
                Qt.LeftButton, mods))
        QTest.mouseRelease(window, Qt.LeftButton, mods, QPoint(*b))

    def type_text(text):
        # QTest.keyClicks only takes widgets; the canvas reads event.text().
        for ch in text:
            for kind in (QEvent.KeyPress, QEvent.KeyRelease):
                QCoreApplication.sendEvent(window, QKeyEvent(kind, 0, Qt.NoModifier, ch))

    canvas.tool = "arrow"
    drag((20, 20), (200, 30))
    check("drawing an arrow adds it", len(canvas._shapes) == 1 and canvas._shapes[0].kind == "arrow")
    check("the new shape is selected", canvas.hasSelection)
    canvas.color = "#22C55E"
    check("a colour chosen after drawing is for the next shape",
          canvas._shapes[0].color == RED and canvas.color == "#22C55E")
    canvas.tool = "select"
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(110, 25))
    check("picking a shape brings its colour to the toolbar", canvas.color == RED)
    canvas.color = "#22C55E"
    check("a colour change applies to the picked shape", canvas._shapes[0].color == "#22C55E")
    canvas.tool = "arrow"

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(300, 200))
    check("a click without dragging draws nothing", len(canvas._shapes) == 1)

    canvas.tool = "rect"
    drag((50, 100), (150, 160), Qt.ShiftModifier)
    r = S.box(canvas._shapes[1])
    check("Shift draws a square", abs(r.width() - r.height()) < 1)

    canvas.tool = "select"
    drag((100, 25), (100, 85))
    moved = canvas._shapes[0].pts[0][1] - 20
    check(f"dragging a shape moves it ({moved:.0f}px)", 50 < moved < 70)

    canvas.undo()
    check("undo puts it back", abs(canvas._shapes[0].pts[0][1] - 20) < 1)
    canvas.redo()
    check("redo moves it again", canvas._shapes[0].pts[0][1] > 70)

    canvas.tool = "step"
    for x in (300, 340):
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(x, 40))
    numbers = [s.number for s in canvas._shapes if s.kind == "step"]
    check("steps number themselves", numbers == [1, 2])

    canvas.tool = "text"
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(250, 120))
    type_text("Però")
    QTest.keyClick(window, Qt.Key_Return)
    type_text("sì")
    QTest.keyClick(window, Qt.Key_Escape)
    texts = [s.text for s in canvas._shapes if s.kind == "text"]
    check(f"typing fills a text box, accents and newlines included {texts}", texts == ["Però\nsì"])

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(250, 220))
    QTest.keyClick(window, Qt.Key_Escape)
    check("an empty text box is dropped", len([s for s in canvas._shapes if s.kind == "text"]) == 1)

    count = len(canvas._shapes)
    canvas.tool = "select"
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(340, 40))
    QTest.keyClick(window, Qt.Key_Delete)
    check("Delete removes the selected shape", len(canvas._shapes) == count - 1)

    QTest.keyClick(window, Qt.Key_A)
    check("a letter picks a tool", canvas.tool == "arrow")

    canvas.tool = "crop"
    drag((100, 50), (300, 150))
    check(f"crop cuts the image ({canvas.pixelWidth}x{canvas.pixelHeight})",
          (canvas.pixelWidth, canvas.pixelHeight) == (200, 100))
    canvas.undo()
    check("and undo restores it", (canvas.pixelWidth, canvas.pixelHeight) == (400, 240))

    out = canvas.rendered()
    check("the export is at full resolution", out.size() == canvas._image.size())
    window.close()


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841 - fonts and painting need it
    test_painting()
    test_geometry()
    test_canvas()
    print(f"\n{'all passed' if not failures else f'{len(failures)} FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
