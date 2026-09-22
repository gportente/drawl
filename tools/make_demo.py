r"""Generates the demo images used in the README.

    .venv\Scripts\python.exe tools\make_demo.py

It shows the REAL interface (drawl/ui/Main.qml) on top of a backdrop scene,
driven by real data: the halo levels are the RMS energy measured on the audio,
and the text is what the model actually produced for that audio. The microphone
is not involved — the audio goes straight to the engine, because capturing
through the air depends on speakers and background noise.

The source audio is tools/demo/phrase.wav, produced with the Italian voice of
the Windows speech synthesiser saying the sentence that appears in the document.

Produces, in docs/:
    demo.png      the full sequence, as an APNG
    hero.png      a single frame, for previews and links
    states.png    the three states of the pill side by side
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import Property, QObject, QPointF, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "drawl" / "ui"
SCENE = Path(__file__).resolve().parent / "demo" / "Scene.qml"
DOCS = ROOT / "docs"

SCENE_X, SCENE_Y = 400, 300
SCENE_W, SCENE_H = 900, 520
PILL_X, PILL_Y = SCENE_X + 648, SCENE_Y + 326

FPS = 10
TRIM = 4                    # pixels cut from each side, to remove the marker
MARKER = (255, 0, 255)


# ---------------------------------------------------------------------- data
def analyse_audio(wav: Path) -> tuple[str, list[float]]:
    """Actually transcribes the audio and derives the levels for the animation."""
    sys.path.insert(0, str(ROOT))
    from drawl.engine.parakeet import ParakeetEngine

    with wave.open(str(wav)) as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    samples = int(len(pcm) * 16000 / sr)
    pcm16 = np.interp(np.linspace(0, len(pcm) - 1, samples),
                      np.arange(len(pcm)), pcm).astype(np.float32)

    engine = ParakeetEngine(10)
    engine.load()
    text = engine.transcribe(pcm16, 16000)

    step = 16000 // FPS
    levels = [float(min(1.0, np.sqrt(np.mean(pcm16[i:i + step] ** 2)) * 7))
              for i in range(0, len(pcm16) - step, step)]
    return text, levels


# ------------------------------------------------------------ stand-in controller
class DemoController(QObject):
    """Offers Main.qml the same interface as the real controller."""

    stateChanged = Signal()
    levelChanged = Signal()
    statusChanged = Signal()
    lastTextChanged = Signal()

    def __init__(self):
        super().__init__()
        self._state = "idle"
        self._level = 0.0
        self._status = "Ready"
        self._last = ""

    state = Property(str, lambda s: s._state, notify=stateChanged)
    level = Property(float, lambda s: s._level, notify=levelChanged)
    status = Property(str, lambda s: s._status, notify=statusChanged)
    lastText = Property(str, lambda s: s._last, notify=lastTextChanged)

    def apply(self, state=None, level=None, status=None, last=None):
        if state is not None and state != self._state:
            self._state = state
            self.stateChanged.emit()
        if level is not None:
            self._level = level
            self.levelChanged.emit()
        if status is not None and status != self._status:
            self._status = status
            self.statusChanged.emit()
        if last is not None:
            self._last = last
            self.lastTextChanged.emit()

    @Slot()
    def toggleRecord(self): pass
    @Slot()
    def copyLast(self): pass
    @Slot(result=bool)
    def toggleAutoPaste(self): return True
    @Slot(result=bool)
    def autoPasteEnabled(self): return True
    @Slot(result=QPointF)
    def cursorPos(self): return QPointF(QCursor.pos())
    @Slot(int, int)
    def saveOrbPosition(self, x, y): pass
    @Slot()
    def quit(self): pass


class DemoStrings(QObject):
    """The `i18n` context property Main.qml expects."""

    TIPS = {
        "tip.copy": "Copy the last transcription",
        "tip.autoPasteOn": "Auto-paste: on",
        "tip.autoPasteOff": "Auto-paste: off",
    }

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        return self.TIPS.get(key, key)


# ------------------------------------------------------------------- capture
def safe_grab(app, screen, x, y, w, h, attempts: int = 40):
    """Grabs the region only once the scene is genuinely drawn on top.

    Without this check the first frame can portray whatever window sits
    underneath, and end up published: it has happened. The scene paints three
    magenta pixels in its corner; if they are not there, the grab is not valid.
    """
    for _ in range(attempts):
        img = screen.grabWindow(0, x, y, w, h)
        colour = img.toImage().pixelColor(1, 1)
        if (colour.red(), colour.green(), colour.blue()) == MARKER:
            return img
        app.processEvents()
    raise RuntimeError(
        "the scene does not appear to be drawn over the capture region: "
        "stopping rather than publishing whatever lies underneath"
    )


def grab_pill(app, screen, folder: Path, index: int) -> Path:
    """Crops the pill out of a full-scene frame.

    Starting from the verified capture rather than grabbing the pill's region
    directly means these crops inherit the same guarantee.
    """
    img = safe_grab(app, screen, SCENE_X, SCENE_Y, SCENE_W, SCENE_H)
    margin = 22
    inner_x = PILL_X - SCENE_X - margin
    inner_y = PILL_Y - SCENE_Y - margin
    p = folder / f"pose_{index:d}.png"
    img.copy(inner_x, inner_y, 172 + margin * 2, 106 + margin * 2).save(str(p))
    return p


# ------------------------------------------------------------------ sequence
def build_sequence(levels: list[float], text: str) -> list[dict]:
    """The shot list: each entry is what is on screen at that moment."""
    seq: list[dict] = []

    def add(n, **kw):
        seq.extend(dict(kw) for _ in range(n))

    # 1. empty document, pill closed
    add(8, state="idle", level=0.0, status="Ready", text="", open=False)
    # 2. the pill opens as the pointer arrives
    add(6, state="idle", level=0.0, status="Ready", text="", open=True)
    # 3. listening: the halo follows the real energy of the voice
    for lv in levels:
        add(1, state="recording", level=lv, status="Listening…", text="", open=True)
    # 4. transcribing
    add(6, state="transcribing", level=0.0, status="Transcribing…", text="", open=True)
    # 5. the text appears all at once, the way the real paste works
    add(3, state="idle", level=0.0, status="0.5s for 6s (12×)",
        text=text, open=True, flash=True)
    add(10, state="idle", level=0.0, status="0.5s for 6s (12×)", text=text, open=True)

    # 6. the pill is dragged wherever it is wanted, and remembers where
    destination = (SCENE_X + 96, SCENE_Y + 330)
    steps = 16
    for k in range(1, steps + 1):
        progress = 1 - (1 - k / steps) ** 3          # eases towards the end
        seq.append(dict(
            state="idle", level=0.0, status="Drag to move it",
            text=text, open=True,
            pos=(round(PILL_X + (destination[0] - PILL_X) * progress),
                 round(PILL_Y + (destination[1] - PILL_Y) * progress)),
        ))
    add(8, state="idle", level=0.0, status="Position remembered",
        text=text, open=True, pos=destination)

    # 7. closing
    add(10, state="idle", level=0.0, status="Ready",
        text=text, open=False, pos=destination)

    # 8. Poses for the three-states image. They live at the end of the same
    # timeline, rather than in a function of their own, because the pill's
    # animations run for up to 260 ms: changing state and grabbing immediately
    # would capture the previous frame. These frames stay out of the animation.
    for label, st, lv, status in (
        ("Idle", "idle", 0.0, "Ready"),
        ("Listening", "recording", 0.85, "Listening…"),
        ("Transcribing", "transcribing", 0.0, "Transcribing…"),
    ):
        add(7, state=st, level=lv, status=status,
            text="", open=True, pose=True, pos=(PILL_X, PILL_Y))
        add(1, state=st, level=lv, status=status,
            text="", open=True, pose=True, grab=label, pos=(PILL_X, PILL_Y))
    return seq


def main() -> int:
    wav = Path(sys.argv[1]) if len(sys.argv) > 1 else SCENE.parent / "phrase.wav"
    if not wav.exists():
        print(f"missing demo audio: {wav}", file=sys.stderr)
        return 2

    print("transcribing the demo audio with the real engine…")
    text, levels = analyse_audio(wav)
    print(f"  text   : {text}")
    print(f"  levels : {len(levels)} samples at {FPS} fps")

    app = QGuiApplication(sys.argv[:1])
    ctl = DemoController()
    strings = DemoStrings()

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(UI))
    engine.rootContext().setContextProperty("ctl", ctl)
    engine.rootContext().setContextProperty("i18n", strings)
    engine.load(QUrl.fromLocalFile(str(SCENE)))
    engine.load(QUrl.fromLocalFile(str(UI / "Main.qml")))
    roots = engine.rootObjects()
    if len(roots) != 2:
        print("could not load both the scene and the pill", file=sys.stderr)
        return 1
    scene, pill = roots
    scene.setX(SCENE_X); scene.setY(SCENE_Y)
    pill.setX(PILL_X); pill.setY(PILL_Y)

    DOCS.mkdir(exist_ok=True)
    original_cursor = QCursor.pos()
    sequence = build_sequence(levels, text)
    frames: list[Path] = []
    crops: list[tuple[str, Path]] = []
    folder = Path(tempfile.mkdtemp(prefix="drawl-demo-"))
    screen = app.primaryScreen()
    position = {"i": 0}

    def step():
        if position["i"] >= len(sequence):
            app.quit()
            return
        f = sequence[position["i"]]
        ctl.apply(state=f["state"], level=f["level"], status=f["status"])
        scene.setProperty("text", f["text"])
        scene.setProperty("flash", bool(f.get("flash")))

        px, py = f.get("pos", (PILL_X, PILL_Y))
        pill.setX(px)
        pill.setY(py)
        # Scene and pill are both "always on top", and among peers the order is
        # not guaranteed: without this the pill ends up behind the scene.
        pill.raise_()
        # Real hover: the pointer is moved onto the pill rather than adding
        # convenience properties to the QML. grabWindow does not capture the
        # cursor, so it stays out of the recording.
        if f["open"]:
            QCursor.setPos(px + 38, py + 38)
        else:
            QCursor.setPos(SCENE_X + 30, SCENE_Y + 30)
        app.processEvents()

        if f.get("pose"):
            if f.get("grab"):
                crops.append((f["grab"], grab_pill(app, screen, folder, len(crops))))
        else:
            img = safe_grab(app, screen, SCENE_X, SCENE_Y, SCENE_W, SCENE_H)
            p = folder / f"f{position['i']:04d}.png"
            img.copy(TRIM, TRIM, SCENE_W - TRIM * 2, SCENE_H - TRIM * 2).save(str(p))
            frames.append(p)
        position["i"] += 1

    timer = QTimer()
    timer.timeout.connect(step)
    timer.start(1000 // FPS)
    app.exec()

    QCursor.setPos(original_cursor)
    print(f"captured {len(frames)} frames")
    write_apng(frames, DOCS / "demo.png")
    shutil.copy(frames[len(frames) - 20], DOCS / "hero.png")
    compose_states(crops, DOCS / "states.png")
    shutil.rmtree(folder, ignore_errors=True)
    return 0


def compose_states(crops, destination: Path) -> None:
    """Places the three captured states side by side, with their labels."""
    from PIL import ImageDraw, ImageFont

    if not crops:
        return
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15)
    except OSError:
        font = ImageFont.load_default()

    images = [(name, Image.open(p).convert("RGB")) for name, p in crops]
    width, height = images[0][1].size
    gap, strip = 18, 34
    canvas = Image.new("RGB", (width * len(images) + gap * (len(images) - 1),
                               height + strip), "#07080B")
    draw = ImageDraw.Draw(canvas)
    for i, (label, img) in enumerate(images):
        x = i * (width + gap)
        canvas.paste(img, (x, 0))
        w = draw.textlength(label, font=font)
        draw.text((x + (width - w) / 2, height + 9), label, font=font, fill="#8A8F98")
    canvas.save(destination)
    print(f"  {destination.name}: {canvas.size[0]}x{canvas.size[1]}")


def resize(frames: list[Path], width: int = 820) -> list:
    images = [Image.open(p).convert("RGB") for p in frames]
    scale = width / images[0].width
    return [im.resize((width, int(im.height * scale)), Image.LANCZOS) for im in images]


def write_apng(frames: list[Path], destination: Path) -> None:
    """APNG: full colour, so no banding where the backdrop fades.

    GIF is limited to 256 colours per frame, and over a gradient backdrop the
    result is either banded (without dithering) or heavy and noisy (with it).
    GitHub renders APNGs like any other image.
    """
    images = resize(frames)
    images[0].save(
        destination, save_all=True, append_images=images[1:],
        duration=1000 // FPS, loop=0,
    )
    mb = destination.stat().st_size / 1048576
    print(f"  {destination.name}: {mb:.1f} MB, {len(images)} frames (APNG)")


if __name__ == "__main__":
    sys.exit(main())
