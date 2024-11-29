from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QStyle, QLabel


class SearchBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        self.searchresults = []
        self.current = 0

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText(self.tr("Search..."))
        self.search_text.setMaximumWidth(200)
        self.column_combo = QComboBox()
        self.column_combo.addItems([self._parent.treemodel.headerData(i) for i in range(self._parent.treemodel.columnCount()) if not self._parent.tree.isColumnHidden(i)])
        self.column_combo.setMinimumWidth(50)
        self.case_button = QPushButton("Aa")
        self.case_button.setToolTip(self.tr("Case sensitive"))
        self.case_button.setMaximumWidth(30)
        self.case_button.setCheckable(True)
        self.counterlabel = QLabel("_/_")
        self.search_next_button = QPushButton("")
        self.search_next_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.search_prev_button = QPushButton("")
        self.search_prev_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.layout.addWidget(self.search_text)
        self.layout.addWidget(self.column_combo)
        self.layout.addWidget(self.case_button)
        self.layout.addWidget(self.counterlabel)
        self.layout.addWidget(self.search_prev_button)
        self.layout.addWidget(self.search_next_button)
        self.layout.addStretch()

        self.search_text.returnPressed.connect(self.search)
        self.search_next_button.clicked.connect(self.search_next)
        self.search_prev_button.clicked.connect(self.search_prev)

    def search(self):

        self.searchresults = []
        self.current = 0
        case_sensitive = self.case_button.isChecked()
        column_name = self.column_combo.currentText()
        columns = [self._parent.treemodel.headerData(i) for i in range(self._parent.treemodel.columnCount())]
        column = columns.index(column_name)
        items = self._parent.treemodel.root_item.search(self.search_text.text(), column=column, case_sensitive=case_sensitive)

        for item in items:
            source_index = self._parent.treemodel.createIndex(item.row(), 0, item)
            index = self._parent.proxymodel.mapFromSource(source_index)
            if index.isValid():
                self.searchresults.append(index)

        if len(self.searchresults) == 0:
            self.counterlabel.setText("0/0")
            self._parent.tree.clearSelection()
            return
         
        self.counterlabel.setText(f"1/{len(self.searchresults)}")
        self._parent.tree.setCurrentIndex(self.searchresults[0])
        self._parent.tree.scrollTo(self.searchresults[0])

    def search_next(self):
        if len(self.searchresults) == 0:
            return
        self.current += 1
        if self.current >= len(self.searchresults):
            self.current = 0
        self.counterlabel.setText(f"{self.current+1}/{len(self.searchresults)}")
        self._parent.tree.setCurrentIndex(self.searchresults[self.current])
        self._parent.tree.scrollTo(self.searchresults[self.current])

    def search_prev(self):
        if len(self.searchresults) == 0:
            return
        self.current -= 1
        if self.current < 0:
            self.current = len(self.searchresults) - 1
        self.counterlabel.setText(f"{self.current+1}/{len(self.searchresults)}")
        self._parent.tree.setCurrentIndex(self.searchresults[self.current])
        self._parent.tree.scrollTo(self.searchresults[self.current])