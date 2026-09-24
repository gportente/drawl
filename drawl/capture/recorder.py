"""Screen recording to MP4, through Qt Multimedia's FFmpeg backend.

The encoding is H.264 by the Media Foundation encoder Windows ships with, so no
FFmpeg executable is needed: PySide6 carries the libraries. Measured on a
2560x1440 screen at 30 fps (8 s of recording):

    whole screen, capture straight into the recorder   103 % of a core   6.6 MB
    whole screen, through the cropping path             138 % of a core   6.5 MB
    1280x720 area, through the cropping path             59 % of a core   1.0 MB

So a full screen goes straight to the recorder, and only an area pays for the
round trip through a QImage.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, QRect, QUrl, Signal
from PySide6.QtGui import QScreen
from PySide6.QtMultimedia import (QMediaCaptureSession, QMediaFormat, QMediaRecorder,
                                  QScreenCapture, QVideoFrame, QVideoFrameInput,
                                  QVideoSink)


class ScreenRecorder(QObject):
    finished = Signal(str, float)    # path, seconds
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._capture: QScreenCapture | None = None
        self._recorder: QMediaRecorder | None = None
        self._sessions: list[QMediaCaptureSession] = []
        self._sink: QVideoSink | None = None
        self._input: QVideoFrameInput | None = None
        self._crop: QRect | None = None
        self._t0: int | None = None
        self._started = 0.0
        self._path = ""
        self._error = ""

    @property
    def active(self) -> bool:
        return self._recorder is not None

    def elapsed(self) -> float:
        return time.monotonic() - self._started if self.active else 0.0

    def start(self, screen: QScreen, area: QRect | None, path: str, fps: int = 30) -> None:
        """Record `screen`, or only `area` of it (physical pixels, screen-local)."""
        if self.active:
            return
        self._path, self._error = path, ""
        self._capture = QScreenCapture(screen)
        self._capture.errorOccurred.connect(lambda _e, msg: self._fail(msg))

        recorder = QMediaRecorder()
        fmt = QMediaFormat(QMediaFormat.MPEG4)
        fmt.setVideoCodec(QMediaFormat.VideoCodec.H264)
        recorder.setMediaFormat(fmt)
        recorder.setQuality(QMediaRecorder.HighQuality)
        recorder.setVideoFrameRate(fps)
        recorder.setOutputLocation(QUrl.fromLocalFile(path))
        recorder.errorOccurred.connect(lambda _e, msg: self._fail(msg))
        recorder.recorderStateChanged.connect(self._on_state)
        self._recorder = recorder

        output = QMediaCaptureSession()
        output.setRecorder(recorder)
        self._sessions = [output]

        full = area is None or area.size() == screen.size() * screen.devicePixelRatio()
        if full:
            output.setScreenCapture(self._capture)
        else:
            # H.264 works on 2x2 blocks of chroma: odd sizes are refused.
            self._crop = QRect(area.x(), area.y(), area.width() & ~1, area.height() & ~1)
            self._t0 = None
            source = QMediaCaptureSession()
            self._sink = QVideoSink()
            source.setScreenCapture(self._capture)
            source.setVideoSink(self._sink)
            self._input = QVideoFrameInput()
            output.setVideoFrameInput(self._input)
            self._sink.videoFrameChanged.connect(self._forward)
            self._sessions.append(source)

        self._capture.start()
        recorder.record()
        self._started = time.monotonic()

    def _forward(self, frame: QVideoFrame) -> None:
        if not frame.isValid():
            return
        if self._t0 is None:
            # The very first frame arrives before the capture is up, and it is
            # black: it would open every video with a flash.
            self._t0 = frame.startTime()
            return
        cropped = QVideoFrame(frame.toImage().copy(self._crop))
        cropped.setStartTime(frame.startTime() - self._t0)
        cropped.setEndTime(frame.endTime() - self._t0)
        # When the encoder falls behind the frame is refused: dropping it keeps
        # the timing right, which a queue that only grows would not.
        self._input.sendVideoFrame(cropped)

    def stop(self) -> None:
        if self._recorder is not None:
            self._capture.stop()
            self._recorder.stop()   # the file is complete once StoppedState arrives

    def _on_state(self, state) -> None:
        if state != QMediaRecorder.StoppedState or self._recorder is None:
            return
        seconds = self.elapsed()
        path = self._recorder.actualLocation().toLocalFile() or self._path
        error = self._error
        self._teardown()
        if error:
            self.failed.emit(error)
        else:
            self.finished.emit(path, seconds)

    def _fail(self, message: str) -> None:
        self._error = message or "unknown error"
        if self._recorder is not None and self._recorder.recorderState() == QMediaRecorder.StoppedState:
            self._teardown()
            self.failed.emit(self._error)
        else:
            self.stop()

    def _teardown(self) -> None:
        if self._sink is not None:
            self._sink.videoFrameChanged.disconnect(self._forward)
        self._capture = self._recorder = self._sink = self._input = None
        self._sessions = []
