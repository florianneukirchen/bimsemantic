from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
)




class CustomTreeDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setWindowTitle(self.tr("Create Custom Treeview"))

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )


        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(self.tr("Name")))
        self.name = QLineEdit()
        name_layout.addWidget(self.name)
        layout.addLayout(name_layout)
        


        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def get_name(self):
        """Get the text from the input field"""
        return self.name.text().strip()
    



if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QPushButton
    import sys

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            button = QPushButton("Press me")
            button.clicked.connect(self.button_clicked)
            self.setCentralWidget(button)

        def button_clicked(self, s):
            dlg = CustomTreeDialog(self)
            if dlg.exec_() == QDialog.Accepted:
                print(dlg.get_name())

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()




