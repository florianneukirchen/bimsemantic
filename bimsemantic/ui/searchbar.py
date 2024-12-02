from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QComboBox,
    QStyle,
    QLabel,
    QMenu,
)


class SearchBar(QWidget):
    """Search bar widget

    For searching in a IFC tree view or SOM tree view

    :param parent: The parent widget (IfcTabs or SomDockWidget)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.mainwindow = parent.mainwindow

        self.searchresults = []
        self.current = 0

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(1)

        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText(self.tr("Search..."))
        self.search_text.setMaximumWidth(200)
        self.column_combo = QComboBox()
        self.column_combo.addItems(
            [
                self._parent.treemodel.headerData(i)
                for i in range(self._parent.treemodel.columnCount())
                if not self._parent.tree.isColumnHidden(i)
            ]
        )

        self.column_combo.setMinimumWidth(50)
        self.column_combo.setToolTip(self.tr("Search in column"))
        self.stop_auto_button = QPushButton("")
        self.stop_auto_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserStop)
        )
        self.stop_auto_button.setVisible(False)
        self.search_next_button = QPushButton("")
        self.search_next_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        )
        self.search_prev_button = QPushButton("")
        self.search_prev_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        )
        self.counterlabel = QLabel("-/-")
        self.how_button = HowButton(self)

        self.close_button = QPushButton("")
        self.close_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)
        )
        self.close_button.setFlat(True)


        self.layout.addWidget(self.how_button)
        self.layout.addWidget(self.search_text)
        self.layout.addWidget(self.column_combo)
        self.layout.addWidget(self.stop_auto_button)
        self.layout.addWidget(self.search_prev_button)
        self.layout.addWidget(self.search_next_button)
        self.layout.addWidget(self.counterlabel)
        self.layout.addStretch()
        self.layout.addWidget(self.close_button)
        

        self.search_text.returnPressed.connect(self.search)
        self.column_combo.currentIndexChanged.connect(self.search)
        self.search_next_button.clicked.connect(self.search_next)
        self.search_prev_button.clicked.connect(self.search_prev)
        self.close_button.clicked.connect(self.hide)

        self.hide()

    def search(self):
        """Search the text in the tree view"""
        self.searchresults = []
        pattern = self.search_text.text()
        pattern = pattern.strip()
        if not pattern:
            self.search_text.setStyleSheet("")
            self.counterlabel.setText("-/-")
            return

        column_name = self.column_combo.currentText()
        if not column_name:
            # If the selected column gets hidden
            self.counterlabel.setText("-/-")
            return
        columns = [
            self._parent.treemodel.headerData(i)
            for i in range(self._parent.treemodel.columnCount())
        ]
        column = columns.index(column_name)

        how = self.how_button.get_search_mode()

        if how == "Text":
            pattern = QRegularExpression.escape(pattern)
        elif how == "Exact":
            pattern = QRegularExpression.anchoredPattern(pattern) 
        elif how == "Wildcard":
            pattern = QRegularExpression.wildcardToRegularExpression(pattern)

        else:
            # Regex    
            pass
        
        if self.how_button.is_case_sensitive():
            options = QRegularExpression.NoPatternOption
        else:
            options = QRegularExpression.CaseInsensitiveOption
        regular_expression = QRegularExpression(pattern, options)

        if not regular_expression.isValid():
            self.search_text.setStyleSheet("color: red; background-color: yellow")
            self.search_text.setToolTip(regular_expression.errorString())
            self.mainwindow.statusbar.showMessage(f"Regex: {regular_expression.errorString()}", 5000)
            self.counterlabel.setText("-/-")
            return

        self.search_text.setToolTip("")
        self.search_text.setStyleSheet("")

        items = self._parent.treemodel.root_item.search(
            regular_expression, column
        )

        for item in items:
            source_index = self._parent.treemodel.createIndex(item.row(), 0, item)
            index = self._parent.proxymodel.mapFromSource(source_index)
            if index.isValid():
                self.searchresults.append(index)

        if len(self.searchresults) == 0:
            self.counterlabel.setText("0/0")
            self._parent.tree.clearSelection()
            return

        # Sort the search results
        self.searchresults.sort(
            key=lambda index: self._parent.tree.visualRect(index).top()
        )
        self.current = 0
        self.counterlabel.setText(f"1/{len(self.searchresults)}")
        self._parent.tree.setCurrentIndex(self.searchresults[0])
        self._parent.tree.scrollTo(self.searchresults[0])

    def search_next(self):
        """Select and scroll to the next search result"""
        if len(self.searchresults) == 0:
            return
        self.current += 1
        if self.current >= len(self.searchresults):
            self.current = 0
        self.counterlabel.setText(f"{self.current+1}/{len(self.searchresults)}")
        self._parent.tree.setCurrentIndex(self.searchresults[self.current])
        self._parent.tree.scrollTo(self.searchresults[self.current])

    def search_prev(self):
        """Select and scroll to the previous search result"""
        if len(self.searchresults) == 0:
            return
        self.current -= 1
        if self.current < 0:
            self.current = len(self.searchresults) - 1
        self.counterlabel.setText(f"{self.current+1}/{len(self.searchresults)}")
        self._parent.tree.setCurrentIndex(self.searchresults[self.current])
        self._parent.tree.scrollTo(self.searchresults[self.current])

    def columns_changed(self):
        """Update the column combo box"""
        current = self.column_combo.currentText()
        self.column_combo.clear()
        columns = [
                self._parent.treemodel.headerData(i)
                for i in range(self._parent.treemodel.columnCount())
                if not self._parent.tree.isColumnHidden(i)
            ]
        self.column_combo.addItems(
            columns
        )
        if current in columns:
            self.column_combo.setCurrentIndex(columns.index(current))
        else:
            self.column_combo.setCurrentIndex(0)

class HowButton(QPushButton):
    def __init__(self, parent):
        super().__init__()
        self.setIcon(QIcon(":/icons/binocular.png"))
        self.setFlat(True)
        self.setMinimumWidth(30)
        self.setToolTip("Search mode")
        self._parent = parent

        self.how_menu = QMenu()
        self.setMenu(self.how_menu)

        self.action_text = QAction(self.tr("Text"), self)
        self.action_exact = QAction(self.tr("Exact"), self)
        self.action_wildcard = QAction(self.tr("Wildcard"), self)
        self.action_regex = QAction(self.tr("Regex"), self)

        self.how_menu.addAction(self.action_text)
        self.how_menu.addAction(self.action_exact)
        self.how_menu.addAction(self.action_wildcard)
        self.how_menu.addAction(self.action_regex)

        self.how_menu.addSeparator()

        self.case_sensitive_action = QAction(self.tr("Case Sensitive"), self)
        self.case_sensitive_action.setCheckable(True)
        self.how_menu.addAction(self.case_sensitive_action)

        self.action_text.triggered.connect(lambda: self.set_search_mode("Text"))
        self.action_exact.triggered.connect(lambda: self.set_search_mode("Exact"))
        self.action_wildcard.triggered.connect(lambda: self.set_search_mode("Wildcard"))
        self.action_regex.triggered.connect(lambda: self.set_search_mode("Regex"))
        self.case_sensitive_action.toggled.connect(self._parent.search)

        self.set_search_mode("Text")

    def set_search_mode(self, mode):
        self.setText(mode)
        self.search_mode = mode
        self._parent.search()

    def get_search_mode(self):
        return self.search_mode

    def is_case_sensitive(self):
        return self.case_sensitive_action.isChecked()