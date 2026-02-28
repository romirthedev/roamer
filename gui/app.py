"""Vercept desktop app entry point."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def run_app() -> int:
    # Enable high-DPI scaling (important for Retina Macs)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Vercept")
    app.setApplicationDisplayName("Vercept")

    window = MainWindow()
    window.show()

    return app.exec()
