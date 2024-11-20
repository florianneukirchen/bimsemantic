from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
)




class CustomTreeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        name = "Bla"

        self.setWindowTitle(self.tr("Create Custom Treeview"))

        layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(self.tr("Name")))
        self.name = QLineEdit(name)
        name_layout.addWidget(self.name)
        layout.addLayout(name_layout)

        self.left_list = QListWidget()
        self.right_list = QListWidget()

        self.left_list.setMinimumWidth(200)
        self.left_list.setMinimumHeight(300)
        self.right_list.setMinimumWidth(200)
        self.left_list.setMinimumHeight(300)

        for i in range(10):
            item = QListWidgetItem(f"Element {i}")
            self.left_list.addItem(item)


        list_layout = QHBoxLayout()
        left_button_layout = QVBoxLayout()
        right_button_layout = QVBoxLayout()

        list_layout.addWidget(self.left_list)
        list_layout.addLayout(left_button_layout)
        list_layout.addWidget(self.right_list)
        list_layout.addLayout(right_button_layout)


        add_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        add_button.setIcon(icon)
        remove_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        remove_button.setIcon(icon)

        up_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp)
        up_button.setIcon(icon)
        down_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
        down_button.setIcon(icon)

        left_button_layout.addStretch()
        left_button_layout.addWidget(add_button)
        left_button_layout.addWidget(remove_button)
        left_button_layout.addStretch()
        right_button_layout.addStretch()
        right_button_layout.addWidget(up_button)
        right_button_layout.addWidget(down_button)
        right_button_layout.addStretch()

        add_button.clicked.connect(self.add_item)
        remove_button.clicked.connect(self.remove_item)
        up_button.clicked.connect(self.move_item_up)
        down_button.clicked.connect(self.move_item_down)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout.addSpacing(10)
        layout.addLayout(list_layout)
        layout.addSpacing(20)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def add_item(self):
        selected_items = self.left_list.selectedItems()
        for item in selected_items:
            self.left_list.takeItem(self.left_list.row(item))
            self.right_list.addItem(item)

    def remove_item(self):
        selected_items = self.right_list.selectedItems()
        for item in selected_items:
            self.right_list.takeItem(self.right_list.row(item))
            self.left_list.addItem(item)

    def move_item_up(self):
        current_row = self.right_list.currentRow()
        if current_row > 0:
            item = self.right_list.takeItem(current_row)
            self.right_list.insertItem(current_row - 1, item)
            self.right_list.setCurrentItem(item)

    def move_item_down(self):
        current_row = self.right_list.currentRow()
        if current_row < self.right_list.count() - 1:
            item = self.right_list.takeItem(current_row)
            self.right_list.insertItem(current_row + 1, item)
            self.right_list.setCurrentItem(item)

    def get_name(self):
        """Get the text from the input field"""
        return self.name.text().strip()

    def get_items(self):
        items = []
        for i in range(self.right_list.count()):
            items.append(self.right_list.item(i).text())
        return items

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            button = QPushButton("Press me")
            button.clicked.connect(self.button_clicked)
            self.setCentralWidget(button)

        def button_clicked(self, s):
            dlg = CustomTreeDialog(self)
            if dlg.exec() == QDialog.Accepted:
                print(dlg.get_name())
                items = dlg.get_items()
                for item in items:
                    print(item)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()




