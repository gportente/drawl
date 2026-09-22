"""Application startup: QML engine, tray icon, global hotkey."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Qt, Slot
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .. import i18n
from ..config import Config
from ..i18n import t
from ..output import single_instance
from ..output.hotkey import GlobalHotkey
from .controller import Controller

UI_DIR = Path(__file__).resolve().parent
MARGIN = 28


class Strings(QObject):
    """Gives QML access to the translations, as the `i18n` context property."""

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        return t(key)


def _app_icon() -> QIcon:
    """Drawn at runtime, so no binary asset is needed in the repository."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, 64)
    grad.setColorAt(0.0, QColor("#6EE7F9"))
    grad.setColorAt(1.0, QColor("#A78BFA"))
    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, 56, 56)
    painter.setPen(QColor("#0B0D12"))
    painter.setBrush(QColor("#0B0D12"))
    painter.drawRoundedRect(26, 16, 12, 22, 6, 6)
    painter.end()
    return QIcon(pm)


def _place(window, config: Config) -> None:
    """Where it was left, or bottom right of the primary screen."""
    x, y = config["orb_x"], config["orb_y"]
    screen = window.screen() or QApplication.primaryScreen()
    area = screen.availableGeometry()
    if x < 0 or y < 0 or not area.contains(x + 40, y + 40):
        x = area.right() - window.width() - MARGIN
        y = area.bottom() - window.height() - MARGIN
    window.setX(int(x))
    window.setY(int(y))


def main() -> int:
    # One copy at a time: the global hotkey can belong to a single process, and
    # a second instance would sit there without one, silently.
    if not single_instance.acquire():
        single_instance.ask_running_instance_to_show()
        print(t("error.alreadyRunning"), file=sys.stderr)
        return 0

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName("drawl")
    app.setWindowIcon(_app_icon())
    # It lives in the tray: closing the pill must not end the process.
    app.setQuitOnLastWindowClosed(False)

    config = Config.load()
    i18n.set_language(config["ui_language"])
    controller = Controller(config)
    strings = Strings()

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(UI_DIR))
    engine.rootContext().setContextProperty("ctl", controller)
    engine.rootContext().setContextProperty("i18n", strings)
    engine.load(QUrl.fromLocalFile(str(UI_DIR / "Main.qml")))
    if not engine.rootObjects():
        print(t("error.qmlLoad"), file=sys.stderr)
        return 1

    window = engine.rootObjects()[0]
    _place(window, config)

    hotkey = GlobalHotkey(config["hotkey"], controller.hotkeyPressed.emit)
    if not hotkey.start():
        # Reported in a way that sticks: the engine's status message comes
        # later and would otherwise overwrite it.
        controller.set_hotkey_error(hotkey.error)

    tray = QSystemTrayIcon(_app_icon(), app)
    tray.setToolTip(t("tray.tooltip", hotkey=config["hotkey"]))
    menu = QMenu()
    act_record = QAction(t("tray.dictate", hotkey=config["hotkey"]), menu)
    act_record.triggered.connect(controller.toggleRecord)
    act_toggle = QAction(t("tray.toggle"), menu)
    act_toggle.triggered.connect(lambda: window.setVisible(not window.isVisible()))
    act_quit = QAction(t("tray.quit"), menu)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_record)
    menu.addAction(act_toggle)
    menu.addSeparator()
    menu.addAction(act_quit)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: window.setVisible(True)
        if reason == QSystemTrayIcon.Trigger else None
    )
    tray.show()

    app.aboutToQuit.connect(hotkey.stop)
    controller.start_engine()
    return app.exec()
