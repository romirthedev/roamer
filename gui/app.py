"""Vercept desktop app entry point."""

import sys

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def run_app() -> int:
    # Qt 6 enables high-DPI / Retina support automatically — no flag needed.
    app = QApplication(sys.argv)
    app.setApplicationName("Vercept")
    app.setApplicationDisplayName("Vercept")

    window = MainWindow()
    window.show()

    return app.exec()
