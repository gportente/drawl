"""Screenshots and screen recordings: selection, editor, saving.

The flow is the same for both: the screens are frozen, a selector covers each
one, and the chosen area either opens in the editor or starts a recording.
"""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (Property, QEventLoop, QObject, QRect, QRectF, QStandardPaths,
                            QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QCursor, QGuiApplication, QImage
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtWidgets import QFileDialog

from ..capture import win
from ..capture.grab import Shot, grab_screens, window_rects_on
from ..capture.recorder import ScreenRecorder
from ..config import Config
from ..i18n import number, t
from .canvas import AnnotationCanvas

UI_DIR = Path(__file__).resolve().parent


class ShotProvider(QQuickImageProvider):
    """Hands the frozen screens to the selector as `image://shot/<key>`."""

    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.images: dict[str, QImage] = {}

    def requestImage(self, key, size, requested_size):
        image = self.images.get(key, QImage())
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image


def _folder(setting: str | None, standard: QStandardPaths.StandardLocation) -> Path:
    base = Path(setting) if setting else (
        Path(QStandardPaths.writableLocation(standard)) / "drawl")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _stamp() -> str:
    return datetime.now().strftime("drawl-%Y-%m-%d_%H-%M-%S")


def _rect_dict(r: QRectF) -> dict:
    return {"x": r.x(), "y": r.y(), "width": r.width(), "height": r.height()}


def show_in_explorer(path: str) -> None:
    subprocess.Popen(["explorer", f"/select,{Path(path)}"])


class CaptureController(QObject):
    screenshotHotkey = Signal()    # emitted from the hotkey threads
    recordHotkey = Signal()
    recordingChanged = Signal()
    elapsedChanged = Signal()
    recordingSaved = Signal(str, str)      # path, message
    message = Signal(str)                  # for the pill's status bar

    def __init__(self, config: Config, engine, provider: ShotProvider):
        super().__init__()
        self._config = config
        self._engine = engine
        self._provider = provider
        self._selectors: list = []
        self._shots: list[Shot] = []
        self._mode = ""
        self._serial = 0
        self._editors: list = []
        self._frame = None

        self._recorder = ScreenRecorder(self)
        self._recorder.finished.connect(self._recording_finished)
        self._recorder.failed.connect(self._recording_failed)
        self._tick = QTimer(self)
        self._tick.setInterval(250)
        self._tick.timeout.connect(self.elapsedChanged)

        self._selector_component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(UI_DIR / "Selector.qml")))
        self._editor_component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(UI_DIR / "Editor.qml")))
        self._frame_component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(UI_DIR / "RecordFrame.qml")))

        # Queued: the hotkeys fire on threads of their own.
        self.screenshotHotkey.connect(self.screenshot)
        self.recordHotkey.connect(self.toggleRecording)

    # --- state for QML --------------------------------------------------------------

    recording = Property(bool, lambda self: self._recorder.active, notify=recordingChanged)

    def _get_elapsed(self) -> str:
        seconds = int(self._recorder.elapsed())
        return f"{seconds // 60}:{seconds % 60:02d}"

    elapsed = Property(str, _get_elapsed, notify=elapsedChanged)

    # --- selection ------------------------------------------------------------------

    @Slot()
    def screenshot(self) -> None:
        self._select("shot")

    @Slot()
    def toggleRecording(self) -> None:
        if self._recorder.active:
            self._recorder.stop()
        else:
            self._select("record")

    def _select(self, mode: str) -> None:
        if self._selectors:
            return                      # already choosing
        self._mode = mode
        self._shots = grab_screens()
        self._serial += 1
        self._provider.images = {f"{self._serial}-{i}": s.image
                                 for i, s in enumerate(self._shots)}
        cursor = QCursor.pos()
        for i, shot in enumerate(self._shots):
            geo = shot.screen.geometry()
            windows = [_rect_dict(QRectF(r.x() / shot.scale, r.y() / shot.scale,
                                         r.width() / shot.scale, r.height() / shot.scale))
                       for r in window_rects_on(shot)]
            selector = self._selector_component.createWithInitialProperties({
                "source": f"image://shot/{self._serial}-{i}",
                "windows": windows,
                "mode": mode,
                "pixelScale": shot.scale,
                "hint": t("capture.hintRecord" if mode == "record" else "capture.hintShot"),
                "startCursor": cursor - geo.topLeft(),
            })
            if selector is None:
                self.message.emit(t("error.qmlLoad"))
                print(self._selector_component.errorString())
                self._close_selectors()
                return
            selector.setScreen(shot.screen)
            selector.setGeometry(geo)
            selector.chosen.connect(lambda x, y, w, h, i=i: self._chosen(i, QRectF(x, y, w, h)))
            selector.cancelled.connect(self._close_selectors)
            selector.show()
            self._selectors.append(selector)
        # The keyboard goes to the screen the pointer is on, for Esc and Enter.
        for selector, shot in zip(self._selectors, self._shots):
            if shot.screen.geometry().contains(cursor):
                selector.raise_()
                selector.requestActivate()

    def _close_selectors(self) -> None:
        for selector in self._selectors:
            selector.close()
            selector.deleteLater()
        self._selectors = []
        self._provider.images = {}

    def _chosen(self, index: int, logical: QRectF) -> None:
        shot = self._shots[index]
        k = shot.scale
        area = QRect(round(logical.x() * k), round(logical.y() * k),
                     round(logical.width() * k), round(logical.height() * k))
        area = area.intersected(shot.image.rect())
        self._close_selectors()
        self._shots = []
        if area.width() < 2 or area.height() < 2:
            return
        if self._mode == "record":
            self._start_recording(shot, area, logical)
        else:
            image = shot.image.copy(area)
            QGuiApplication.clipboard().setImage(image)
            self._open_editor(image, shot)

    # --- editor ---------------------------------------------------------------------

    def _open_editor(self, image: QImage, shot: Shot) -> None:
        area = shot.screen.availableGeometry()
        # Room for the toolbar and the status line around the picture.
        chrome_w, chrome_h = 48, 120
        width = min(max(image.width() / shot.scale + chrome_w, 980), area.width() * 0.92)
        height = min(max(image.height() / shot.scale + chrome_h, 520), area.height() * 0.9)
        editor = self._editor_component.createWithInitialProperties({
            "title": f"drawl — {t('editor.title')}",
        })
        if editor is None:
            print(self._editor_component.errorString())
            self.message.emit(t("error.qmlLoad"))
            return
        canvas = editor.findChild(AnnotationCanvas, "canvas")
        canvas.set_image(image, shot.scale)
        editor.setScreen(shot.screen)
        editor.setGeometry(int(area.x() + (area.width() - width) / 2),
                           int(area.y() + (area.height() - height) / 2),
                           int(width), int(height))
        editor.closing.connect(lambda _event, e=editor: self._editor_closed(e))
        editor.show()
        editor.raise_()
        editor.requestActivate()
        self._editors.append(editor)

    def _editor_closed(self, editor) -> None:
        if editor in self._editors:
            self._editors.remove(editor)
            editor.deleteLater()

    # The editor's actions answer with {message, path}: the message goes in its
    # status line, and a path makes that line open the folder when clicked.

    @Slot(QObject, result="QVariantMap")
    def copy(self, canvas: AnnotationCanvas) -> dict:
        QGuiApplication.clipboard().setImage(canvas.rendered())
        return {"message": t("editor.copied"), "path": ""}

    @Slot(QObject, result="QVariantMap")
    def save(self, canvas: AnnotationCanvas) -> dict:
        folder = _folder(self._config["screenshot_dir"], QStandardPaths.PicturesLocation)
        return self._write(canvas, folder / f"{_stamp()}.png")

    @Slot(QObject, result="QVariantMap")
    def saveAs(self, canvas: AnnotationCanvas) -> dict:
        folder = _folder(self._config["screenshot_dir"], QStandardPaths.PicturesLocation)
        path, _ = QFileDialog.getSaveFileName(
            None, t("editor.saveAs"), str(folder / f"{_stamp()}.png"),
            "PNG (*.png);;JPEG (*.jpg *.jpeg)")
        return self._write(canvas, Path(path)) if path else {}

    def _write(self, canvas: AnnotationCanvas, path: Path) -> dict:
        quality = 92 if path.suffix.lower() in (".jpg", ".jpeg") else -1
        if not canvas.rendered().save(str(path), None, quality):
            return {"message": t("editor.saveFailed", path=path), "path": ""}
        return {"message": t("editor.saved", path=path), "path": str(path)}

    @Slot(str)
    def reveal(self, path: str) -> None:
        show_in_explorer(path)

    # --- recording ------------------------------------------------------------------

    def _start_recording(self, shot: Shot, area: QRect, logical: QRectF) -> None:
        folder = _folder(self._config["recording_dir"], QStandardPaths.MoviesLocation)
        path = str(folder / f"{_stamp()}.mp4")
        whole = area.size() == shot.image.size()
        self._recorder.start(shot.screen, None if whole else area, path,
                             int(self._config["record_fps"]))
        if not whole:
            self._show_frame(shot, logical)
        self._tick.start()
        self.recordingChanged.emit()
        self.elapsedChanged.emit()
        self.message.emit(t("capture.recording"))

    def _show_frame(self, shot: Shot, logical: QRectF) -> None:
        """A border just outside the recorded area, so it is clear what is being
        filmed. It is outside the area and excluded from capture besides."""
        margin = 3
        geo = shot.screen.geometry()
        frame = self._frame_component.createWithInitialProperties({"margin": margin})
        if frame is None:
            return
        frame.setScreen(shot.screen)
        frame.setGeometry(int(geo.x() + logical.x() - margin), int(geo.y() + logical.y() - margin),
                          int(logical.width() + 2 * margin), int(logical.height() + 2 * margin))
        frame.show()
        win.exclude_from_capture(int(frame.winId()))
        self._frame = frame

    def shutdown(self) -> None:
        """On quit, let a running recording finish writing its file: stopped
        halfway the MP4 has no index and no player will open it."""
        for editor in list(self._editors):
            editor.close()
        if not self._recorder.active:
            return
        loop = QEventLoop()
        self._recorder.finished.connect(loop.quit)
        self._recorder.failed.connect(loop.quit)
        QTimer.singleShot(5000, loop.quit)
        self._recorder.stop()
        loop.exec()

    def _stopped(self) -> None:
        self._tick.stop()
        if self._frame is not None:
            self._frame.close()
            self._frame.deleteLater()
            self._frame = None
        self.recordingChanged.emit()
        self.elapsedChanged.emit()

    def _recording_finished(self, path: str, seconds: float) -> None:
        self._stopped()
        try:
            size = Path(path).stat().st_size / 1e6
        except OSError:
            self.message.emit(t("capture.recordFailed", detail=path))
            return
        figures = {"seconds": number(seconds, 0), "size": number(size)}
        self.message.emit(t("capture.recordSaved", **figures))
        self.recordingSaved.emit(path, t("capture.recordSavedAs", name=Path(path).name,
                                          **figures))

    def _recording_failed(self, detail: str) -> None:
        self._stopped()
        self.message.emit(t("capture.recordFailed", detail=detail))
