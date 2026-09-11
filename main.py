"""
EEG Visualizer — entry point.

Sets the matplotlib Qt backend *before* any matplotlib import, then
launches the PyQt6 application using the new ui/core architecture.
"""

import sys
import os

# Must be set before any matplotlib import
os.environ.setdefault("MPLBACKEND", "QtAgg")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("EEG Visualizer")
    app.setOrganizationName("EEG Research")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
