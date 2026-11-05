"""Markdown 转换器入口。"""

import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Markdown 转换器')

    app.setStyleSheet("""
        QMainWindow { background: #fff; }
        QPushButton {
            padding: 6px 16px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background: #fff;
        }
        QPushButton:hover { background: #f0f0f0; }
        QPushButton:disabled { color: #bbb; }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
