from ui.mainwindow import MainWindow
from PySide6.QtWidgets import QApplication
import sys


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    print("show")
    main_win.show()
    print("starting main loop")
    sys.exit(app.exec())
