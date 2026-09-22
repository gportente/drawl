"""The bridge between the QML interface and the engines: state, recording, output."""
from __future__ import annotations

import gc
import threading
import time

import numpy as np
from PySide6.QtCore import Property, QObject, QPointF, QTimer, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication

from ..audio.recorder import Recorder
from ..config import Config
from ..i18n import number, t
from ..output.inject import paste_into_active_window

# Below this length we assume a stray keypress and skip transcription.
MIN_SECONDS = 0.35


class Controller(QObject):
    stateChanged = Signal()
    levelChanged = Signal()
    statusChanged = Signal()
    lastTextChanged = Signal()
    transcriptionReady = Signal(str)
    hotkeyPressed = Signal()       # emitted from the hotkey thread
    _unloadRequested = Signal()    # emitted from a worker thread

    def __init__(self, config: Config):
        super().__init__()
        self._config = config
        self._state = "loading"
        self._level = 0.0
        self._status = t("status.starting")
        self._last_text = ""
        self._hotkey_error: str | None = None

        self._engine = None
        self._engine_ready = threading.Event()
        self._engine_lock = threading.Lock()

        self._recorder = Recorder(
            sample_rate=config["sample_rate"], on_level=self._push_level,
            device=config["input_device"],
        )

        # The model takes ~740 MB, so after a while idle it is dropped and
        # reloaded when the next recording starts. Loading costs ~2 s, less than
        # a sentence takes to say, so it is ready in time.
        self._unload_timer = QTimer(self)
        self._unload_timer.setSingleShot(True)
        self._unload_timer.timeout.connect(self._unload_engine)

        self.transcriptionReady.connect(self._deliver)
        # Queued connections: these signals come from non-Qt threads.
        self.hotkeyPressed.connect(self.toggleRecord)
        self._unloadRequested.connect(self._arm_unload_timer)

    # --- properties exposed to QML ----------------------------------------------

    def _get_state(self) -> str:
        return self._state

    def _get_level(self) -> float:
        return self._level

    def _get_status(self) -> str:
        return self._status

    def _get_last_text(self) -> str:
        return self._last_text

    state = Property(str, _get_state, notify=stateChanged)
    level = Property(float, _get_level, notify=levelChanged)
    status = Property(str, _get_status, notify=statusChanged)
    lastText = Property(str, _get_last_text, notify=lastTextChanged)

    def set_hotkey_error(self, message: str | None) -> None:
        """An error that has to stay visible: the engine's message arrives later."""
        self._hotkey_error = message
        self._status = t("error.hotkey", detail=message)
        self.statusChanged.emit()

    def _set_state(self, value: str, status: str | None = None) -> None:
        if self._hotkey_error and status is not None:
            status = t("error.hotkeySuffix", status=status)
        if self._state != value:
            self._state = value
            self.stateChanged.emit()
        if status is not None and status != self._status:
            self._status = status
            self.statusChanged.emit()

    def _push_level(self, level: float) -> None:
        # Called on the audio thread: the signal is queued to the UI thread.
        self._level = level
        self.levelChanged.emit()

    # --- engine lifecycle -------------------------------------------------------

    def start_engine(self) -> None:
        """At startup fetch the model files, but do not load them into memory."""
        threading.Thread(target=self._prepare_engine, daemon=True,
                         name="prepare").start()

    def _new_engine(self):
        cfg = self._config
        if cfg["engine"] == "whisper":
            from ..engine.whisper import WhisperEngine

            return WhisperEngine(cfg["whisper_model"], cfg["language"],
                                 cfg["num_threads"])
        from ..engine.parakeet import ParakeetEngine

        return ParakeetEngine(cfg["num_threads"], progress=self._on_download)

    def _prepare_engine(self) -> None:
        try:
            with self._engine_lock:
                self._engine = self._new_engine()
                self._engine.prepare()
        except Exception as exc:  # the engine is optional: keep the UI alive
            self._set_state("error", t("error.engine", detail=exc))
            return

        if self._config["unload_after_s"] == 0:
            self._load_engine()      # unloading disabled: load it right away
        else:
            self._set_state("idle", t("status.ready"))

    def _load_engine(self) -> None:
        """Bring the model into RAM. Idempotent, safe from several threads."""
        with self._engine_lock:
            if self._engine is None:
                self._engine = self._new_engine()
            if not self._engine.loaded:
                try:
                    self._engine.load()
                except Exception as exc:
                    self._set_state("error", t("error.engine", detail=exc))
                    return
            self._engine_ready.set()
        if self._state == "loading":
            self._set_state("idle", t("status.ready"))

    def _unload_engine(self) -> None:
        if self._state != "idle":
            return                    # never mid-dictation
        with self._engine_lock:
            if self._engine is not None and self._engine.loaded:
                self._engine.unload()
                self._engine_ready.clear()
                gc.collect()

    @Slot()
    def _arm_unload_timer(self) -> None:
        # QTimers must be touched from the thread that owns them.
        seconds = self._config["unload_after_s"]
        if seconds:
            self._unload_timer.start(int(seconds * 1000))

    def _on_download(self, stage: str, frac: float) -> None:
        key = "status.downloading" if stage == "download" else "status.extracting"
        self._set_state("loading", t(key, percent=f"{frac * 100:.0f}"))

    # --- recording --------------------------------------------------------------

    @Slot()
    def toggleRecord(self) -> None:
        if self._state == "recording":
            self._stop_and_transcribe()
        elif self._state == "idle":
            self._start()

    def _start(self) -> None:
        try:
            self._recorder.start()
        except Exception as exc:
            self._set_state("error", t("error.microphone", detail=exc))
            return
        self._unload_timer.stop()
        # Loading starts now, in parallel: while the user speaks the model
        # reaches memory, and by the end of the sentence it is ready.
        if not self._engine_ready.is_set():
            threading.Thread(target=self._load_engine, daemon=True,
                             name="load").start()
        self._set_state("recording", t("status.listening"))

    def _stop_and_transcribe(self) -> None:
        pcm = self._recorder.stop()
        self._push_level(0.0)
        duration = len(pcm) / self._config["sample_rate"]
        if duration < MIN_SECONDS:
            self._set_state("idle", t("status.tooShort"))
            self._unloadRequested.emit()
            return
        self._set_state("transcribing", t("status.transcribing"))
        threading.Thread(target=self._transcribe, args=(pcm,), daemon=True,
                         name="transcribe").start()

    def _transcribe(self, pcm: np.ndarray) -> None:
        # If the dictation was shorter than the load, this is where we wait.
        if not self._engine_ready.wait(timeout=120):
            self._set_state("error", t("error.engineNotReady"))
            return
        try:
            t0 = time.perf_counter()
            text = self._engine.transcribe(pcm, self._config["sample_rate"])
            elapsed = time.perf_counter() - t0
        except Exception as exc:
            self._set_state("error", t("error.transcription", detail=exc))
            return
        finally:
            self._unloadRequested.emit()

        if not text:
            self._set_state("idle", t("status.noSpeech"))
            return
        secs = len(pcm) / self._config["sample_rate"]
        self._set_state("idle", t(
            "status.timing",
            elapsed=number(elapsed), audio=number(secs, 0),
            speed=number(secs / elapsed, 0),
        ))
        self.transcriptionReady.emit(text)

    def _deliver(self, text: str) -> None:
        # On the UI thread: Qt's clipboard prefers to be touched from here.
        self._last_text = text
        self.lastTextChanged.emit()
        QGuiApplication.clipboard().setText(text)
        if self._config["auto_paste"]:
            paste_into_active_window()

    # --- secondary actions ------------------------------------------------------

    @Slot()
    def copyLast(self) -> None:
        if self._last_text:
            QGuiApplication.clipboard().setText(self._last_text)
            self._set_state(self._state, t("status.copied"))

    @Slot(result=bool)
    def toggleAutoPaste(self) -> bool:
        value = not self._config["auto_paste"]
        self._config["auto_paste"] = value
        self._config.save()
        self._set_state(self._state,
                        t("status.autoPasteOn" if value else "status.autoPasteOff"))
        return value

    @Slot(result=bool)
    def autoPasteEnabled(self) -> bool:
        return bool(self._config["auto_paste"])

    @Slot(result=QPointF)
    def cursorPos(self) -> QPointF:
        """Where the operating system says the pointer is.

        Used for dragging the pill: the MouseArea's local coordinates are only
        valid once the window has actually moved, and moving it is asynchronous,
        so relative deltas leave the window trailing the pointer.

        The return type must be declared with the QPointF class: with the string
        "QPoint" the conversion to QML fails silently and whichever handler
        called it stops running, with no visible error.
        """
        return QPointF(QCursor.pos())

    @Slot(int, int)
    def saveOrbPosition(self, x: int, y: int) -> None:
        self._config["orb_x"], self._config["orb_y"] = x, y
        self._config.save()

    @Slot()
    def quit(self) -> None:
        QGuiApplication.quit()
