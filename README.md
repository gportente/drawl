# drawl

Offline voice dictation for Windows. A floating pill that stays on top: press
the hotkey (or click the orb), speak, and the text lands in whichever window you
were typing in. No audio ever leaves your computer.

<p align="center">
  <img src="docs/demo.png" width="820"
       alt="drawl's pill: the hotkey is pressed, the orb turns red and pulses with the voice, the dictated text appears in the document, and the pill is dragged elsewhere.">
</p>

<p align="center">
  <sub>The real interface. The halo follows the actual energy of the voice and
  the text is what the model genuinely produced for that audio; the microphone is
  replaced by a file, so the recording does not depend on background noise.
  The spoken sentence is Italian, to show a language other than English.</sub>
</p>

## Download

[**Latest release**](https://github.com/gportente/drawl/releases/latest) —
installer (49 MB) or portable archive (75 MB). On first launch it downloads the
recognition model, ~490 MB: an internet connection is needed only for that step.

To work on drawl instead of just using it, see *Running from source*.

## If Windows blocks it

The executables are **not code-signed**, which has two consequences.

**SmartScreen** shows a warning on first launch: *More info* → *Run anyway*.

**Smart App Control**, on the other hand, blocks the app outright, with no way
past it — the dialog only offers *OK* and *Get app from Store*. It is on by
default on clean Windows 11 installations, and it refuses unsigned executables
regardless of where they came from. Until drawl is signed, there are two ways
around it:

- Turn Smart App Control off, under *Windows Security → App & browser control*.
  Since the April 2026 cumulative update it can be turned back on afterwards;
  on earlier builds that took reinstalling Windows.
- Run it from source instead. `pythonw.exe` is signed by the Python Software
  Foundation, so Smart App Control lets it through: see *Running from source*.

Signing is the real fix and is on the list. It is not a switch that can be
flipped for free: it needs a certificate from a recognised authority, and even
then SmartScreen reputation accrues over successive releases rather than
arriving with the first one.

## Using it

However you installed it, drawl behaves the same.

<p align="center">
  <img src="docs/states.png" width="684"
       alt="The pill's three states: idle with a blue orb, listening with a red orb and a pulsing halo, and transcribing with a spinning indicator.">
</p>

- **Ctrl+Shift+Space** — start and stop dictation, from any application
- **Click the orb** — the same thing
- **Drag the orb** — move the pill; the position is remembered
- **Hover** — reveals the secondary buttons and the status bar
- **Ctrl+PrtScn** — screenshot, then annotate it (see below)
- **Shift+PrtScn** — record the screen; the same keys again stop it
- **Tray icon** — show/hide, dictate, screenshot, record, quit

The secondary buttons are *copy the last transcription*, *toggle auto-paste*
(with paste off the text only goes to the clipboard), *screenshot* and *record
the screen*.

On first launch the Parakeet model (~490 MB compressed) downloads itself into
`%LOCALAPPDATA%\drawl\models`, with progress shown under the pill. After that
drawl never needs the network again.

The installer offers to create the desktop shortcut and to start drawl when you
sign in to Windows; both are optional, and the second can be turned off later
from *Task Manager → Startup apps*. Idle, drawl takes ~125 MB, because the model
does not stay in memory: see *Resource use*. A second copy started by mistake
notices the first and exits, rather than sitting there without a hotkey.

## Screenshots and screen recording

Both start the same way: the screens freeze, and a click takes the window under
the pointer (the whole screen when over the desktop), a drag takes an area,
Enter takes the whole screen, Esc or a right click cancels. The size shown next
to the selection is in real pixels, the ones the file will have. The pill never
appears in either: it is excluded from capture.

<p align="center">
  <img src="docs/screenshot.png" width="820"
       alt="A screenshot: hovering highlights one window, then another; an area is dragged out and opens in the editor, where the email and IBAN are pixelated, the failed payment is highlighted, and a rectangle, an arrow, a note and two numbered steps point to the Update payment button.">
</p>

**A screenshot** lands on the clipboard straight away and opens in the editor:

| Tool | Key | |
|---|---|---|
| Select and move | V | drag a shape to move it, its handles to reshape it; Del removes it |
| Arrow, line | A, L | Shift snaps to 45° |
| Rectangle, ellipse | R, E | Shift draws squares and circles; *Filled shapes* fills them |
| Pen, highlighter | P, H | the highlighter is translucent; Shift draws it straight |
| Text | T | Enter starts a new line, Esc finishes; double click edits it again |
| Numbered steps | N | 1, 2, 3… each click, carrying on from the highest |
| Pixelate | B | hides passwords and personal data |
| Crop | C | Ctrl+Z brings the rest back |

Eight colours and three sizes, with keys 1–3, apply to the next shape and to the
selected one. Ctrl+Z / Ctrl+Y undo and redo, Ctrl+C copies the annotated image,
Ctrl+S saves a PNG to `Pictures\drawl`, Ctrl+Shift+S asks where (PNG or JPEG).
Pixelation is used instead of blur on purpose: a blur can be partly reversed,
blocks of a single colour cannot.

**A recording** is an H.264 MP4 in `Videos\drawl`. While it runs, a red border
marks the area (it stays out of the video), the pill shows the elapsed time and
its red button stops it; when the file is ready a notification offers to show
it in Explorer. There is no audio for now.

<p align="center">
  <img src="docs/recording.png" width="820"
       alt="A recording: an area is chosen the same way, a red border marks it while the pill counts the seconds, and the pill's red button stops it and reports the saved file.">
</p>

<p align="center">
  <sub>The real selector, editor and pill, driven by real mouse and keyboard
  events over a made-up desktop; the pointer is drawn in afterwards. In the
  recording the clock runs faster than real time.</sub>
</p>

Recording uses Qt Multimedia and the Media Foundation encoder that comes with
Windows, so it needs no FFmpeg installed: the libraries ship with PySide6. On a
2560×1440 screen at 30 fps:

| What | CPU | Size |
|---|---|---|
| whole screen | 103 % of one core | 6.6 MB for 8 s |
| 1280×720 area | 59 % of one core | 1.0 MB for 8 s |

It costs the package ~15 MB: the portable archive goes from 78 to 93 MB.

## Settings

`%LOCALAPPDATA%\drawl\config.json`, created on first launch:

| Key | Default | Notes |
|---|---|---|
| `engine` | `parakeet` | or `whisper` |
| `ui_language` | `en` | `en`, `it`, or `auto` to follow the system |
| `hotkey` | `ctrl+shift+space` | `ctrl+alt+space` is often already taken on Windows |
| `auto_paste` | `true` | if `false`, the text only reaches the clipboard |
| `input_device` | `null` | microphone index or name; `null` is the system default |
| `screenshot_hotkey` | `ctrl+printscreen` | `printscreen` rather than letters, so no application loses a shortcut |
| `record_hotkey` | `shift+printscreen` | starts and stops recording |
| `screenshot_dir` | `null` | `null` is `Pictures\drawl` |
| `recording_dir` | `null` | `null` is `Videos\drawl` |
| `record_fps` | `30` | frame rate of recordings |
| `num_threads` | `10` | inference threads |
| `unload_after_s` | `180` | seconds idle before freeing the RAM; `0` never does |
| `whisper_model` | `large-v3-turbo` | only used with `engine: whisper` |
| `language` | `it` | Whisper only; Parakeet detects the language itself |

### Interface language

English by default, Italian available. Set `ui_language` to `it`, or to `auto`
to follow the system locale, and restart. Adding a third language means adding a
column to `drawl/i18n.py`: no build step, no compiled catalogues.

Recognition is a separate matter and needs no setting — Parakeet detects the
spoken language on its own, across 25 European languages.

## How it is built

| Piece | Choice | Why |
|---|---|---|
| Recognition | [Parakeet TDT 0.6B v3](https://github.com/k2-fsa/sherpa-onnx) via sherpa-onnx | ~13× realtime on CPU, 25 European languages including English and Italian |
| Fallback | faster-whisper (`large-v3-turbo`) | covers languages outside Parakeet's 25 |
| Interface | PySide6 + QML (Qt Quick) | GPU-accelerated animation, frameless translucent window |
| Output | Clipboard + synthetic Ctrl+V | works in any application, with no integration |

Inference runs entirely in native code (ONNX Runtime / CTranslate2): Python only
orchestrates, and does not show up in the timings.

## Measured performance

On an AMD Ryzen AI 9 365 (10 cores / 20 threads), CPU only, on a 17.8 s
Italian sentence:

| Model | Load | Transcribe | Speed |
|---|---|---|---|
| **Parakeet v3 int8** | **2.1 s** | **1.4 s** | **13×** realtime |
| whisper large-v3-turbo int8 | 23.2 s | 5.4–6.5 s | 2.7× |
| whisper small int8 | 9.4 s | 2.4 s | 7.4× |
| whisper base int8 | 3.3 s | 0.9 s | 20× |

While loaded, Parakeet takes ~730 MB, nearly all of it model weights (the int8
encoder alone is 652 MB). On a machine short of memory, `engine: whisper` with
`whisper_model: base` stays under 250 MB, at the cost of a few more errors.

### Resource use

| Phase | RAM | CPU |
|---|---|---|
| idle, model unloaded | **125 MB** | 0.02 % |
| recording, microphone open | 802 MB | 4 % of one core |
| short dictation (8 s) | 854 MB | 9.5 cores for 0.5 s |
| long dictation (60 s) | 1.23 GB | 9.9 cores for 3.2 s |
| after `unload_after_s` idle | **157 MB** | 0.02 % |

Startup: 2 s from launch to "Ready". On disk: 640 MB the model, 963 MB the
Python environment, 89 KB the code.

**The model does not stay in memory.** It takes ~730 MB, so after
`unload_after_s` seconds idle it is dropped, and reloaded when the next
recording starts — in parallel, while you are already speaking. Loading costs
~2.8 s, less than an ordinary dictation takes, so the extra wait at the end of a
sentence is:

| Sentence length | Extra wait |
|---|---|
| 8 s | 0.00 s |
| 3 s | 0.33 s |
| 1.5 s | 1.30 s |

Only very short dictations pay part of it, and only the first one after a break.
With `unload_after_s: 0` the model stays loaded for good (825 MB, constantly).

### Long audio

Parakeet processes the whole clip at once, so time and memory grow faster than
linearly with duration, and past **400 seconds** (5000 encoder frames) it fails
with a broadcast error in the self-attention. Audio is therefore split into
~45 s chunks cut on silences (`drawl/audio/segment.py`).

| Duration | Without chunking | With chunking |
|---|---|---|
| 15 s | 0.91 s · 875 MB | 0.76 s · 874 MB |
| 60 s | 4.31 s · 1.4 GB | 3.15 s · 1.3 GB |
| 120 s | 9.24 s · 2.0 GB | 6.84 s · 1.4 GB |
| 300 s | 35.66 s · 3.6 GB | 20.50 s · 1.6 GB |
| 440 s | error | 30.05 s · 1.7 GB |
| 637 s | error | 42.74 s · 1.7 GB |

Chunked, the realtime factor stays flat at around **15×** at any duration,
memory settles below 1.7 GB, and the six-minute-forty ceiling disappears.

## Running from source

Needed only to work on drawl, or to sidestep Smart App Control: the Python
interpreter is signed, so it runs where the packaged executable is refused.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe -m drawl     # no console window
```

The launcher is `pythonw.exe` rather than `python.exe`: being the GUI-subsystem
build of Python, it opens no console window.

There is no installer this way, so the shortcuts have to be made by hand:

```powershell
.venv\Scripts\python.exe tools\make_icon.py   # generates drawl\ui\drawl.ico

$root = (Get-Location).Path
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "drawl.lnk"))
$s.TargetPath = "$root\.venv\Scripts\pythonw.exe"
$s.Arguments = "-m drawl"
$s.WorkingDirectory = $root
$s.IconLocation = "$root\drawl\ui\drawl.ico,0"
$s.Save()

# and, to start it with Windows:
Copy-Item (Join-Path ([Environment]::GetFolderPath("Desktop")) "drawl.lnk") `
          ([Environment]::GetFolderPath("Startup"))
```

## Building the packages

```powershell
.\tools\build.ps1
```

Produces both `dist/drawl-<version>-setup.exe` and
`dist/drawl-<version>-portable.zip`. The installer needs
[Inno Setup](https://jrsoftware.org/isinfo.php)
(`winget install --id JRSoftware.InnoSetup`); without it the portable archive is
still produced. The ASR model is in neither: it downloads on first launch.

## Layout

```
drawl/
  i18n.py              user-facing strings, English and Italian
  audio/recorder.py    microphone capture at 16 kHz + RMS level
  audio/segment.py     splitting long audio on silences
  engine/base.py       engine lifecycle: prepare / load / unload
  engine/parakeet.py   sherpa-onnx engine (the default)
  engine/whisper.py    faster-whisper engine (fallback)
  engine/models.py     downloading and unpacking the models
  output/inject.py     synthetic Ctrl+V into the active window
  output/hotkey.py     global hotkey (RegisterHotKey on its own thread)
  output/single_instance.py  stops a second copy running without a hotkey
  capture/grab.py      freezing the screens for the selection
  capture/win.py       excluding windows from capture, listing windows to snap to
  capture/recorder.py  screen recording to MP4
  capture/shapes.py    the annotations: model, hit testing, painting
  ui/Selector.qml      choosing a window or an area
  ui/Editor.qml        the screenshot editor
  ui/canvas.py         the editor's drawing surface: tools, selection, undo
  ui/capture.py        screenshots and recordings from hotkey to saved file
  ui/Main.qml          the pill: orb, buttons, status bar
  ui/controller.py     QML <-> engines bridge, states and model memory
tests/test_pipeline.py end-to-end WAV -> text
tests/test_segment.py  long-audio chunking
tests/test_paste.py    the synthetic Ctrl+V
tests/test_annotate.py annotations, and the editor driven by mouse and keyboard
tests/test_record.py   a real recording of the screen, checked with a player
tools/make_icon.py     generates drawl.ico for the shortcuts
tools/make_demo.py     generates the README images in docs/
tools/make_capture_demo.py  the same, for screenshots and recording
tools/build.ps1        produces the installer and the portable archive
```

## Checking it works

```powershell
.venv\Scripts\python.exe tests\test_pipeline.py some_audio.wav
.venv\Scripts\python.exe tests\test_segment.py
.venv\Scripts\python.exe tests\test_paste.py
.venv\Scripts\python.exe tests\test_annotate.py
.venv\Scripts\python.exe tests\test_record.py
```

The first loads the application's real engine, transcribes the file and checks
that the microphone opens at the configured rate.

## Implementation notes

Behaviours worth remembering, all commented in the code:

- With the flags `Qt.Tool | Qt.WindowDoesNotAcceptFocus` a `HoverHandler` never
  receives hover events: a `MouseArea` is needed instead.
- `Repeater` cannot instantiate `ShapePath`, because it is not an `Item`.
- The `INPUT` struct for `SendInput` must include `MOUSEINPUT` too: without it,
  on x64 it is 32 bytes instead of 40 and the call fails with error 87.
- A `Slot`'s return type towards QML must be declared with the class
  (`result=QPointF`), not the string `"QPoint"`: otherwise the conversion fails
  silently and the handler that called it stops, with no visible error.
- Two windows that are both "always on top" have no guaranteed order between
  them: whichever must stay above needs an explicit `raise_()`.

- A `rect` read from a QML property is a live reference, not a copy: change
  what it is bound to and the variable changes with it. Copy the numbers out
  first.
- `QQuickPaintedItem.paint()` runs on the render thread while the GUI thread
  waits. That is fine under `app.exec()`, which releases the GIL, but QTest's
  waits do not, so the tests use `QSG_RENDER_LOOP=basic`.
- `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` hides a window from both
  GDI screenshots and Windows.Graphics.Capture: that is how the pill and the
  recording border stay out of every capture.
- The first frame from `QScreenCapture` is black: the recorder drops it.

**Dragging.** The pill does not use `startSystemMove()`; it moves itself, asking
the operating system where the pointer is on every event. Windows' own drag
honours the *"show window contents while dragging"* setting
(`HKCU\Control Panel\Desktop\DragFullWindows`), which is off whenever visual
effects are tuned for performance — and then all you would see is a dashed
rectangle moving. Moving the window directly keeps it smooth however the system
is configured.

The coordinates used are absolute rather than incremental: moving a window is
asynchronous, so summing relative deltas would leave the pill trailing behind
the pointer.

**Screenshots.** `tools/make_demo.py` keeps a frame only if it contains a marker
the scene paints in its own corner. Without that check the first frame can
portray whatever window sits underneath — which is exactly how a private
document once ended up in a published recording.

`tools/make_capture_demo.py` goes further and never reads the screen at all:
each frame is the window's own scene, rendered by `QQuickWindow.grabWindow()`
on Qt's offscreen platform, so there is nothing underneath to leak.

## To do

- Voice skills ("open Claude Code"): needs fuzzy matching, because English
  proper nouns get mangled ("Claude Code" → *load code*, *Clod Code*) while
  plain Italian is transcribed correctly
- A local wake word with openWakeWord — detected on the audio, not in the
  transcript: "hey drawl" comes out as *Hey Drawl*, *Hey Droll*, *Ey Droll*
- Push-to-talk: `RegisterHotKey` reports the press, never the release
- NPU acceleration on XDNA2 through the Ryzen AI software
- Code signing, so Smart App Control stops blocking the app outright and
  SmartScreen stops warning. Azure Artifact Signing (formerly Trusted Signing)
  is around $10 a month and is open to businesses and self-employed individuals
  in the EU, UK, US and Canada

## Licence

MIT — see [LICENSE](LICENSE).
