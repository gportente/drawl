# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller build recipe.

    .venv\Scripts\python.exe -m PyInstaller drawl.spec --noconfirm

Produces dist/drawl/, a self-contained folder: no Python needed on the target
machine. The ASR model is not included — it is 640 MB and downloads itself on
first launch.
"""
from PyInstaller.utils.hooks import collect_data_files

# QML files are data, not modules: they have to be copied next to the code, at
# the same relative path app.py loads them from.
qml_files = [
    ("drawl/ui/Main.qml", "drawl/ui"),
    ("drawl/ui/Icon.qml", "drawl/ui"),
    ("drawl/ui/SatelliteButton.qml", "drawl/ui"),
    ("drawl/ui/Selector.qml", "drawl/ui"),
    ("drawl/ui/Editor.qml", "drawl/ui"),
    ("drawl/ui/EditorButton.qml", "drawl/ui"),
    ("drawl/ui/RecordFrame.qml", "drawl/ui"),
    ("drawl/ui/drawl.ico", "drawl/ui"),
]

# sherpa-onnx brings the ONNX Runtime native libraries with it.
sherpa_data = collect_data_files("sherpa_onnx", include_py_files=False)

a = Analysis(
    ["run_drawl.py"],
    pathex=[],
    binaries=[],
    datas=qml_files + sherpa_data,
    hiddenimports=["sherpa_onnx"],
    hookspath=[],
    runtime_hooks=[],
    # The distributed package only uses Parakeet: faster-whisper would drag in
    # CTranslate2 and PyTorch for a spare engine nobody runs. Anyone who wants
    # `engine: whisper` works from source.
    excludes=[
        "faster_whisper", "ctranslate2", "torch", "torchaudio", "transformers",
        "tkinter", "matplotlib", "scipy", "pandas", "PIL", "pytest",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtPdf", "PySide6.QtSql", "PySide6.QtTest",
    ],
    noarchive=False,
)

# The PySide6 hook copies Qt's DLLs regardless of `excludes`, which only act on
# Python modules: Qt6WebEngineCore alone weighs 194 MB. They have to be dropped
# here, after the analysis. drawl uses QtCore, QtGui, QtWidgets, QtQml, QtQuick
# QtQuickShapes and QtMultimedia (screen recording, with the FFmpeg libraries
# PySide6 ships); everything else is ballast.
UNUSED_QT = (
    "Qt6WebEngine", "QtWebEngine", "Qt6Pdf", "Qt6Quick3D", "Qt6Charts",
    "Qt6DataVisualization", "Qt6Sql", "Qt6Test",
    "Qt6Designer", "Qt6Help", "Qt6Bluetooth", "Qt6Nfc", "Qt6SerialPort",
    "Qt6Sensors", "Qt6WebSockets", "Qt6WebChannel", "Qt6RemoteObjects",
    "Qt6Scxml", "Qt6TextToSpeech", "Qt63D", "Qt6Spatial",
    "qml/QtQuick3D", "qml/QtCharts", "qml/QtDataVisualization",
    "qml/QtWebEngine", "qml/QtWebSockets",
    "qml/Qt3D", "qml/QtSensors", "qml/QtTextToSpeech",
    "translations/qtwebengine",
    # Qt Quick's ready-made controls are not needed: the pill is made of
    # Rectangle, Shape and MouseArea. The FluentWinUI3 theme also ships
    # thousands of PNGs with very long names, which on a deep install path
    # exceed the 260-character MAX_PATH and make the installer fail.
    "Qt6QuickControls2", "Qt6QuickTemplates2", "Qt6QuickDialogs",
    "qml/QtQuick/Controls", "qml/QtQuick/Templates", "qml/QtQuick/Dialogs",
    "qml/QtQuick/VirtualKeyboard",
)


def _drop(entry) -> bool:
    path = str(entry[0]).replace("\\", "/").lower()
    return any(p.lower() in path for p in UNUSED_QT)


a.binaries = [v for v in a.binaries if not _drop(v)]
a.datas = [v for v in a.datas if not _drop(v)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="drawl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # no console window
    icon="drawl/ui/drawl.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="drawl",
)
