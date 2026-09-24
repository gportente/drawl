"""Records the primary screen for real and checks the files are playable video.

    .venv\\Scripts\\python.exe tests\\test_record.py

Nothing is kept: the videos go to a temporary folder that is deleted at the end.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QEventLoop, QRect, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from drawl.capture.recorder import ScreenRecorder  # noqa: E402

SECONDS = 3


def wait(ms: int, until=None) -> None:
    loop = QEventLoop()
    if until is not None:
        until.connect(loop.quit)
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def record(screen, area, path: str) -> tuple[str, float, float]:
    rec = ScreenRecorder()
    result = {}
    rec.finished.connect(lambda p, s: result.update(path=p, seconds=s))
    rec.failed.connect(lambda msg: result.update(error=msg))
    cpu = time.process_time()
    rec.start(screen, area, path)
    wait(SECONDS * 1000)
    load = (time.process_time() - cpu) / SECONDS
    rec.stop()
    wait(5000, rec.finished)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result.get("path", ""), result.get("seconds", 0.0), load


def probe(path: str) -> tuple[int, tuple[int, int]]:
    """Duration in ms and frame size, as a player sees them."""
    player, sink = QMediaPlayer(), QVideoSink()
    player.setVideoOutput(sink)
    size = {}
    sink.videoFrameChanged.connect(lambda f: size.setdefault("s", (f.width(), f.height())))
    player.setSource(QUrl.fromLocalFile(path))
    player.play()
    wait(1500)
    duration = player.duration()
    player.stop()
    return duration, size.get("s", (0, 0))


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841
    screen = QGuiApplication.primaryScreen()
    full = screen.size() * screen.devicePixelRatio()
    failures = 0
    with tempfile.TemporaryDirectory() as folder:
        cases = [("whole screen", None, (full.width(), full.height())),
                 # An odd size on purpose: H.264 needs it rounded down to even.
                 ("area", QRect(101, 77, 641, 361), (640, 360))]
        for name, area, expected in cases:
            path = str(Path(folder) / f"{name.replace(' ', '_')}.mp4")
            try:
                saved, seconds, load = record(screen, area, path)
            except RuntimeError as exc:
                print(f"  FAIL {name}: {exc}")
                failures += 1
                continue
            megabytes = Path(saved).stat().st_size / 1e6 if saved else 0
            duration, size = probe(saved)
            ok = (abs(duration / 1000 - SECONDS) < 1.0 and size == expected
                  and megabytes > 0.01)
            failures += not ok
            print(f"  {'ok  ' if ok else 'FAIL'} {name}: {size[0]}x{size[1]}, "
                  f"{duration / 1000:.1f}s of video for {seconds:.1f}s, "
                  f"{megabytes:.2f} MB, {load * 100:.0f}% of a core")
    print("all passed" if not failures else f"{failures} FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
