"""
EEG Viewer - Windows Desktop Application
主程式入口
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow

def main():
    # 啟用高 DPI 支援
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("EEG Viewer")
    app.setOrganizationName("EEG Research")

    # 建立主視窗
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
