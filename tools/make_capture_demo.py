r"""Generates the README images for screenshots and screen recording.

    .venv\Scripts\python.exe tools\make_capture_demo.py

The real selector, editor and pill (drawl/ui/*.qml, drawl/ui/canvas.py) are
driven with real mouse and keyboard events over a made-up desktop, painted here.
Every frame comes from QQuickWindow.grabWindow(), which renders the window's own
scene: nothing is read back from the screen, so nothing that happens to be on it
can end up in a picture. It runs on the offscreen platform, so nothing shows up
on screen either. The pointer is not part of a window: it is drawn onto the
frames afterwards, where the events were sent.

Produces, in docs/:
    screenshot.png   select an area, annotate it, copy it (APNG)
    recording.png    select an area, record it, stop (APNG)
    editor.png       the editor with the finished annotations, full size
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Before Qt loads. Offscreen: no window ever appears on screen. Basic render
# loop: grabWindow() and the Python paint() of the canvas share one thread (see
# the note on the GIL in tests/test_annotate.py). The offscreen platform finds
# no fonts by itself.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RENDER_LOOP"] = "basic"
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))

from PIL import Image, ImageDraw  # noqa: E402
from PySide6.QtCore import (Property, QCoreApplication, QEvent, QObject, QPoint,  # noqa: E402
                            QPointF, QRect, QRectF, Qt, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage, QKeyEvent,  # noqa: E402
                           QLinearGradient, QMouseEvent, QPainter, QPainterPath,
                           QRadialGradient)
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, qmlRegisterType  # noqa: E402
from PySide6.QtQuick import QQuickImageProvider  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from drawl import i18n  # noqa: E402
from drawl.i18n import t  # noqa: E402
from drawl.ui.app import Strings  # noqa: E402
from drawl.ui.canvas import AnnotationCanvas  # noqa: E402

UI = ROOT / "drawl" / "ui"
DOCS = ROOT / "docs"
W, H = 1180, 740                 # the made-up screen, and every frame
FPS = 10

# The made-up desktop: where its windows are.
BILLING = QRect(90, 110, 640, 480)
NOTES = QRect(600, 56, 520, 400)
TASKBAR = 44


# --------------------------------------------------------------------- desktop
def paint_desktop() -> QImage:
    img = QImage(W, H, QImage.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    bg = QLinearGradient(0, 0, W, H)
    bg.setColorAt(0, QColor("#0F172A"))
    bg.setColorAt(1, QColor("#2E1065"))
    p.fillRect(img.rect(), bg)
    glow = QRadialGradient(QPointF(180, 90), 620)
    glow.setColorAt(0, QColor(110, 231, 249, 60))
    glow.setColorAt(1, QColor(110, 231, 249, 0))
    p.fillRect(img.rect(), glow)

    def window(r: QRect, title: str, dark: bool) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(QRectF(r).translated(0, 8).adjusted(-4, 0, 4, 4), 12, 12)
        p.setBrush(QColor("#1B1D27" if dark else "#F8FAFC"))
        p.drawRoundedRect(QRectF(r), 10, 10)
        bar = QPainterPath()
        bar.setFillRule(Qt.WindingFill)       # the two pieces overlap: keep both
        bar.addRoundedRect(QRectF(r.x(), r.y(), r.width(), 40), 10, 10)
        bar.addRect(QRectF(r.x(), r.y() + 20, r.width(), 20))
        p.fillPath(bar.simplified(), QColor("#232634" if dark else "#E2E8F0"))
        for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
            p.setBrush(QColor(c))
            p.drawEllipse(QPointF(r.x() + 20 + i * 18, r.y() + 20), 5.5, 5.5)
        p.setPen(QColor("#A6ADC8" if dark else "#334155"))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(QRect(r.x(), r.y(), r.width(), 40), Qt.AlignCenter, title)

    window(NOTES, "release-notes.md", dark=True)
    p.setFont(QFont("Cascadia Mono", 10))
    lines = [("#89B4FA", "## 2.4.0"), ("#A6ADC8", ""), ("#A6ADC8", "- Faster sync on large folders"),
             ("#A6ADC8", "- New billing page"), ("#A6ADC8", "- Fixed: invoices in the wrong"),
             ("#A6ADC8", "  currency after a plan change"), ("#A6ADC8", ""),
             ("#89B4FA", "## 2.3.2"), ("#A6ADC8", ""), ("#A6ADC8", "- Retry failed payments")]
    for i, (colour, text) in enumerate(lines):
        p.setPen(QColor("#585B70"))
        p.drawText(NOTES.x() + 18, NOTES.y() + 72 + i * 26, f"{i + 1:>2}")
        p.setPen(QColor(colour))
        p.drawText(NOTES.x() + 54, NOTES.y() + 72 + i * 26, text)

    window(BILLING, "Billing — Acme Cloud", dark=False)
    x, y = BILLING.x() + 36, BILLING.y() + 64
    p.setPen(QColor("#0F172A"))
    p.setFont(QFont("Segoe UI Semibold", 17))
    p.drawText(x, y + 26, "Payment details")
    rows = [("Plan", "Business, yearly", "#0F172A"),
            ("Account email", "jane.doe@example.com", "#0F172A"),
            ("IBAN", "DE89 3704 0044 0532 0130 00", "#0F172A"),
            ("Next invoice", "1 Oct 2026  ·  €490.00", "#0F172A"),
            ("Status", "Payment failed", "#DC2626")]
    for i, (label, value, colour) in enumerate(rows):
        ry = y + 76 + i * 52
        p.setPen(QColor("#E2E8F0"))
        p.drawLine(x, ry + 18, BILLING.right() - 36, ry + 18)
        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QColor("#64748B"))
        p.drawText(x, ry, label)
        p.setPen(QColor(colour))
        p.setFont(QFont("Segoe UI Semibold" if colour != "#0F172A" else "Segoe UI", 11))
        p.drawText(x + 180, ry, value)
    for text, left, fill, ink in (("Cancel", 334, "#FFFFFF", "#334155"),
                                   ("Update payment", 450, "#2563EB", "#FFFFFF")):
        b = QRectF(BILLING.x() + left, BILLING.bottom() - 70, 140 if left > 400 else 100, 40)
        p.setPen(QColor("#CBD5E1") if fill == "#FFFFFF" else Qt.NoPen)
        p.setBrush(QColor(fill))
        p.drawRoundedRect(b, 8, 8)
        p.setPen(QColor(ink))
        p.setFont(QFont("Segoe UI Semibold", 10))
        p.drawText(b, Qt.AlignCenter, text)

    p.fillRect(0, H - TASKBAR, W, TASKBAR, QColor(8, 9, 12, 225))
    for i in range(5):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 40 if i != 2 else 90))
        p.drawRoundedRect(QRectF(W / 2 - 110 + i * 46, H - TASKBAR + 8, 28, 28), 6, 6)
    p.end()
    return img


# ------------------------------------------------------------- stand-ins
class DemoController(QObject):
    """What Main.qml reads from `ctl`: the pill is idle, dictation-wise."""

    changed = Signal()

    def __init__(self):
        super().__init__()
        self._status = t("status.ready")

    state = Property(str, lambda s: "idle", notify=changed)
    level = Property(float, lambda s: 0.0, notify=changed)
    status = Property(str, lambda s: s._status, notify=changed)
    lastText = Property(str, lambda s: "", notify=changed)

    def set_status(self, text: str) -> None:
        self._status = text
        self.changed.emit()

    @Slot(result=bool)
    def autoPasteEnabled(self): return True
    @Slot()
    def toggleRecord(self): pass
    @Slot(result=QPointF)
    def cursorPos(self): return QPointF()


class DemoCapture(QObject):
    """What the QML reads from `cap`, without touching the clipboard or disk."""

    changed = Signal()

    def __init__(self, ctl: DemoController):
        super().__init__()
        self._ctl = ctl
        self._recording = False
        self._elapsed = "0:00"

    recording = Property(bool, lambda s: s._recording, notify=changed)
    elapsed = Property(str, lambda s: s._elapsed, notify=changed)

    def set(self, recording: bool, elapsed: str = "0:00") -> None:
        self._recording, self._elapsed = recording, elapsed
        self.changed.emit()

    @Slot()
    def toggleRecording(self) -> None:
        # The figures are those a real 8-second recording of an area this size
        # produces (see the table in the README).
        self.set(False)
        self._ctl.set_status(t("capture.recordSaved", seconds="8", size="0.8"))

    @Slot()
    def screenshot(self): pass

    @Slot(QObject, result="QVariantMap")
    def copy(self, _canvas): return {"message": t("editor.copied"), "path": ""}

    @Slot(QObject, result="QVariantMap")
    def save(self, _canvas): return {}

    @Slot(QObject, result="QVariantMap")
    def saveAs(self, _canvas): return {}

    @Slot(str)
    def reveal(self, _path): pass


class Provider(QQuickImageProvider):
    def __init__(self, image: QImage):
        super().__init__(QQuickImageProvider.Image)
        self.image = image

    def requestImage(self, _key, size, _requested):
        size.setWidth(self.image.width())
        size.setHeight(self.image.height())
        return self.image


# ------------------------------------------------------------------ input
def move(win, x: float, y: float, buttons=Qt.NoButton) -> None:
    p = QPointF(x, y)
    QCoreApplication.sendEvent(win, QMouseEvent(QEvent.MouseMove, p, p, Qt.NoButton,
                                                buttons, Qt.NoModifier))


def press(win, x, y) -> None:
    QTest.mousePress(win, Qt.LeftButton, Qt.NoModifier, QPoint(round(x), round(y)))


def release(win, x, y) -> None:
    QTest.mouseRelease(win, Qt.LeftButton, Qt.NoModifier, QPoint(round(x), round(y)))


def type_text(win, text: str) -> None:
    for ch in text:
        for kind in (QEvent.KeyPress, QEvent.KeyRelease):
            QCoreApplication.sendEvent(win, QKeyEvent(kind, 0, Qt.NoModifier, ch))


def eased(a, b, n):
    """n points from a to b, slowing down on arrival like a hand does."""
    for k in range(1, n + 1):
        f = 1 - (1 - k / n) ** 3
        yield a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f


# --------------------------------------------------------------- pointer
def draw_pointer(img: Image.Image, x: float, y: float, kind: str) -> None:
    d = ImageDraw.Draw(img)
    if kind == "cross":
        for dx, dy in ((1, 0), (0, 1)):
            d.line([(x - 10 * dx, y - 10 * dy), (x + 10 * dx, y + 10 * dy)], fill="#0B0D12", width=4)
        for dx, dy in ((1, 0), (0, 1)):
            d.line([(x - 9 * dx, y - 9 * dy), (x + 9 * dx, y + 9 * dy)], fill="#FFFFFF", width=2)
        return
    shape = [(0, 0), (0, 18), (4.5, 14), (7.5, 21), (10.5, 19.8), (7.5, 13), (13, 13)]
    d.polygon([(x + px, y + py) for px, py in shape], fill="#FFFFFF", outline="#0B0D12", width=1)


# --------------------------------------------------------------- the film
class Film:
    """Collects frames: a grabbed window, or a composition, plus the pointer."""

    def __init__(self):
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []

    def add(self, image: Image.Image, pointer=None, hold: int = 1) -> None:
        if image.size != (W, H):
            raise RuntimeError(f"unexpected frame size {image.size}")
        frame = image.convert("RGB")
        if pointer:
            draw_pointer(frame, *pointer)
        if self.frames and hold == 1 and frame.tobytes() == self.frames[-1].tobytes():
            self.durations[-1] += 1000 // FPS
            return
        self.frames.append(frame)
        self.durations.append(hold * 1000 // FPS)

    def save(self, path: Path) -> None:
        # Full size: scaled down, the pill's status line stops being legible.
        self.frames[0].save(path, save_all=True, append_images=self.frames[1:],
                            duration=self.durations, loop=0)
        print(f"  {path.name}: {path.stat().st_size / 1048576:.1f} MB, "
              f"{len(self.frames)} frames")


def to_pil(img: QImage) -> Image.Image:
    img = img.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombuffer("RGBA", (img.width(), img.height()), bytes(img.constBits()),
                            "raw", "RGBA", img.bytesPerLine(), 1).copy()


def settle(app, ms: int = 1000 // FPS) -> None:
    """Let animations run for one frame of real time."""
    QTest.qWait(ms)
    app.processEvents()


# ------------------------------------------------------------------ scenes
def selector_scene(app, engine, film: Film, mode: str, area: QRect) -> None:
    comp = QQmlComponent(engine, QUrl.fromLocalFile(str(UI / "Selector.qml")))
    sel = comp.createWithInitialProperties({
        "source": "image://desk/0",
        "windows": [{"x": r.x(), "y": r.y(), "width": r.width(), "height": r.height()}
                    for r in (BILLING, NOTES)],
        "mode": mode, "pixelScale": 1.0,
        "hint": t("capture.hintRecord" if mode == "record" else "capture.hintShot"),
        "startCursor": QPoint(1000, 620),
    })
    if sel is None:
        raise RuntimeError(comp.errorString())
    sel.setGeometry(0, 0, W, H)
    sel.show()
    settle(app)

    def shot(x, y, hold=1):
        settle(app)
        film.add(to_pil(sel.grabWindow()), (x, y, "cross"), hold)

    pos = (1000, 620)
    shot(*pos, hold=8)
    for target in ((880, 300), (400, 420)):            # the notes, then billing
        for x, y in eased(pos, target, 7):
            move(sel, x, y)
            shot(x, y)
        pos = target
        shot(*pos, hold=6)
    start, end = (area.x(), area.y()), (area.right() + 1, area.bottom() + 1)
    for x, y in eased(pos, start, 6):
        move(sel, x, y)
        shot(x, y)
    press(sel, *start)
    for x, y in eased(start, end, 12):
        move(sel, x, y, Qt.LeftButton)
        shot(x, y)
    shot(*end, hold=8)
    release(sel, *end)
    sel.close()
    del comp


def screenshot_scene(app, engine, desk: QImage, film: Film) -> Image.Image:
    # Both windows: the editor then shows the picture at 100 % and fills up.
    area = QRect(50, 30, 1080, 600)
    selector_scene(app, engine, film, "shot", area)

    comp = QQmlComponent(engine, QUrl.fromLocalFile(str(UI / "Editor.qml")))
    ed = comp.createWithInitialProperties({"title": "drawl"})
    if ed is None:
        raise RuntimeError(comp.errorString())
    canvas = ed.findChild(AnnotationCanvas, "canvas")
    canvas.set_image(desk.copy(area), 1.0)
    ed.setGeometry(0, 0, W, H)
    ed.show()
    ed.requestActivate()
    settle(app)
    canvas.forceActiveFocus()
    origin = canvas.mapToScene(QPointF(0, 0))

    def at(x, y):
        """Desktop coordinates to editor-window coordinates."""
        return origin.x() + x - area.x(), origin.y() + y - area.y()

    pointer = {"pos": at(700, 560), "kind": "arrow"}

    def shot(hold=1):
        settle(app)
        film.add(to_pil(ed.grabWindow()), (*pointer["pos"], pointer["kind"]), hold)

    def glide(to, n=6):
        for p in eased(pointer["pos"], to, n):
            pointer["pos"] = p
            move(ed, *p)
            shot()

    def drag(a, b, n=9):
        glide(a)
        press(ed, *a)
        for p in eased(a, b, n):
            pointer["pos"] = p
            move(ed, *p, Qt.LeftButton)
            shot()
        release(ed, *b)
        shot(hold=3)

    def key(k):
        QTest.keyClick(ed, k)
        shot(hold=3)

    def swatch(colour: str):
        """Click the colour in the toolbar, where the layout puts it.

        Repeater delegates are not QObject children of the window, so the
        visual tree is walked instead; a swatch is known by its inner disc.
        """
        def items(node):
            for child in node.childItems():
                yield child
                yield from items(child)

        for item in items(ed.contentItem()):
            discs = item.childItems()
            if (item.property("tip") == t("editor.color") and len(discs) > 1
                    and discs[1].property("color").name().upper() == colour.upper()):
                centre = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
                pointer["kind"] = "arrow"
                glide((centre.x(), centre.y()), 5)
                QTest.mouseClick(ed, Qt.LeftButton, Qt.NoModifier,
                                 QPoint(round(centre.x()), round(centre.y())))
                if canvas.color.upper() != colour.upper():
                    raise RuntimeError(f"clicking the {colour} swatch did not pick it")
                shot(hold=3)
                return
        raise RuntimeError(f"no swatch for {colour}")

    shot(hold=10)
    y0 = BILLING.y() + 64 + 76                  # baseline of the first row
    row = lambda i: y0 + i * 52                  # noqa: E731

    # Hide the personal data.
    key(Qt.Key_B)
    pointer["kind"] = "cross"
    drag(at(BILLING.x() + 206, row(1) - 20), at(BILLING.x() + 420, row(1) + 8))
    drag(at(BILLING.x() + 206, row(2) - 20), at(BILLING.x() + 470, row(2) + 8))

    # Highlight the problem.
    swatch("#FACC15")
    key(Qt.Key_H)
    pointer["kind"] = "cross"
    drag(at(BILLING.x() + 210, row(4) - 5), at(BILLING.x() + 330, row(4) - 5), 8)

    # Point at the way out.
    swatch("#F43F5E")
    key(Qt.Key_R)
    pointer["kind"] = "cross"
    button = QRect(BILLING.x() + 450, BILLING.bottom() - 70, 140, 40)
    drag(at(button.x() - 8, button.y() - 8), at(button.right() + 9, button.bottom() + 9), 8)
    key(Qt.Key_A)
    pointer["kind"] = "cross"
    drag(at(BILLING.x() + 460, row(5) - 60), at(button.x() + 40, button.y() - 14), 9)

    key(Qt.Key_T)
    pointer["kind"] = "arrow"
    glide(at(BILLING.x() + 440, row(5) - 90))
    QTest.mouseClick(ed, Qt.LeftButton, Qt.NoModifier, QPoint(*map(round, pointer["pos"])))
    for word in ("Retry ", "here"):
        type_text(ed, word)
        shot(hold=2)
    QTest.keyClick(ed, Qt.Key_Escape)
    shot(hold=3)

    # Number the steps.
    swatch("#3B82F6")
    key(Qt.Key_N)
    for x, y in ((BILLING.x() + 16, row(4) - 6), (button.right() + 30, button.y() + 20)):
        glide(at(x, y), 5)
        QTest.mouseClick(ed, Qt.LeftButton, Qt.NoModifier, QPoint(*map(round, pointer["pos"])))
        shot(hold=3)
    QTest.keyClick(ed, Qt.Key_Escape)
    pointer["kind"] = "arrow"
    glide(at(700, 600), 5)
    still = to_pil(ed.grabWindow())

    QTest.keyClick(ed, Qt.Key_C, Qt.ControlModifier)
    shot(hold=30)
    ed.close()
    del comp
    return still


def recording_scene(app, engine, desk: QImage, ctl, cap, film: Film) -> None:
    area = QRect(70, 92, 680, 520)
    selector_scene(app, engine, film, "record", area)

    frame_comp = QQmlComponent(engine, QUrl.fromLocalFile(str(UI / "RecordFrame.qml")))
    frame = frame_comp.create()
    margin = 3
    frame.setGeometry(area.x() - margin, area.y() - margin,
                      area.width() + 2 * margin, area.height() + 2 * margin)
    frame.show()

    engine.load(QUrl.fromLocalFile(str(UI / "Main.qml")))
    pill = engine.rootObjects()[-1]
    pill_at = (W - 268 - 20, H - TASKBAR - 106 - 14)
    cap.set(True, "0:00")
    base = to_pil(desk)
    pointer = {"pos": (area.right() - 40, area.bottom() - 40)}

    def shot(with_frame=True, hold=1):
        settle(app)
        img = base.copy()
        if with_frame:
            img.alpha_composite(to_pil(frame.grabWindow()),
                                (area.x() - margin, area.y() - margin))
        img.alpha_composite(to_pil(pill.grabWindow()), pill_at)
        film.add(img, (*pointer["pos"], "arrow"), hold)

    # Recording: the clock runs (sped up, a second every 0.4 s), the user works.
    route = [(BILLING.x() + 520, BILLING.y() + 330), (BILLING.x() + 520, BILLING.bottom() - 50),
             (BILLING.x() + 300, BILLING.y() + 200)]
    second = 0
    for target in route:
        for p in eased(pointer["pos"], target, 8):
            pointer["pos"] = p
            second += 1
            cap.set(True, f"0:{second // 4:02d}")
            shot()
    for _ in range(4):
        second += 4
        cap.set(True, f"0:{second // 4:02d}")
        shot(hold=4)

    # Stop, from the pill's red button.
    stop = (pill_at[0] + 240, pill_at[1] + 38)
    for p in eased(pointer["pos"], stop, 10):
        pointer["pos"] = p
        move(pill, p[0] - pill_at[0], p[1] - pill_at[1])
        shot()
    shot(hold=6)
    QTest.mouseClick(pill, Qt.LeftButton, Qt.NoModifier, QPoint(240, 38))
    frame.close()
    # Onto the orb, where the status line shows the outcome rather than a tip.
    orb = (pill_at[0] + 30, pill_at[1] + 30)
    for p in eased(pointer["pos"], orb, 6):
        pointer["pos"] = p
        move(pill, p[0] - pill_at[0], p[1] - pill_at[1])
        shot(with_frame=False)
    shot(with_frame=False, hold=35)


def main() -> int:
    i18n.set_language("en")
    app = QGuiApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    desk = paint_desktop()

    ctl = DemoController()
    cap = DemoCapture(ctl)
    strings = Strings()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(UI))
    qmlRegisterType(AnnotationCanvas, "Drawl", 1, 0, "AnnotationCanvas")
    engine.addImageProvider("desk", Provider(desk))
    for name, obj in (("ctl", ctl), ("cap", cap), ("i18n", strings)):
        engine.rootContext().setContextProperty(name, obj)

    DOCS.mkdir(exist_ok=True)
    print("screenshot…")
    film = Film()
    still = screenshot_scene(app, engine, desk, film)
    film.save(DOCS / "screenshot.png")
    still.convert("RGB").save(DOCS / "editor.png", optimize=True)
    print(f"  editor.png: {still.size[0]}x{still.size[1]}")

    print("recording…")
    film = Film()
    recording_scene(app, engine, desk, ctl, cap, film)
    film.save(DOCS / "recording.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
