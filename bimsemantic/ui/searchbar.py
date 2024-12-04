from typing import Any
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

    def __init__(self, parent=None, filtermode=False):
        super().__init__(parent)
        self._parent = parent
        self.mainwindow = parent.mainwindow
        self.filtermode = filtermode

        self.is_som = hasattr(self._parent, "autosearch")

        if self.filtermode:
            if self.is_som:
                self.indicator_act = QAction(self.tr("Clear SOM filter"), self)
            else:
                self.indicator_act = QAction(self.tr("Clear IFC filter"), self)
            self.indicator_act.setEnabled(False)
            self.mainwindow.filterindicator.menu.addAction(self.indicator_act)
            self.indicator_act.triggered.connect(self.remove_filter)

        self.searchresults = []
        self.current = 0

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(1)

        self.search_text = QLineEdit()
        if filtermode:
            txt = self.tr("Filter...")
        else:
            txt = self.tr("Search...")
        self.search_text.setPlaceholderText(txt)
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
        if filtermode:
            self.column_combo.setToolTip(self.tr("Filter on column"))
        else:
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

        
        self.how_button = HowButton(self, is_som=self.is_som, is_filter=filtermode)


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
        

        if filtermode:
            self.reset_filter_button = QPushButton("Reset Filter")
            self.layout.addWidget(self.reset_filter_button)
            self.reset_filter_button.clicked.connect(self.remove_filter)
        else:
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
            if self.filtermode:
                self.remove_filter()
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
            # Regex or List Contains    
            pass
        

        if self.how_button.is_case_sensitive():
            options = QRegularExpression.NoPatternOption
        else:
            options = QRegularExpression.CaseInsensitiveOption

        if how == "List Contains":
            regular_expression = "" # TODO implement List Contains
        else:    
            regular_expression = QRegularExpression(pattern, options)

        if not regular_expression.isValid():
            self.search_text.setStyleSheet("color: red; background-color: yellow")
            self.search_text.setToolTip(regular_expression.errorString())
            self.mainwindow.statusbar.showMessage(f"Regex: {regular_expression.errorString()}", 5000)
            self.counterlabel.setText("-/-")
            return

        self.search_text.setToolTip("")
        self.search_text.setStyleSheet("")

        if self.filtermode:
            self._parent.proxymodel.setFilterKeyColumn(column)
            self._parent.proxymodel.setFilterRegularExpression(regular_expression)
            self.mainwindow.filterindicator.show()
            self.indicator_act.setEnabled(True)
            return

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

    def remove_filter(self):
        """Remove the filter from the proxy model"""
        self.search_text.setText("")
        self._parent.proxymodel.setFilterRegularExpression(QRegularExpression())
        self.indicator_act.setEnabled(False)
        self.mainwindow.filterindicator.check()


class HowButton(QPushButton):
    def __init__(self, parent, is_som=False, is_filter=False):
        super().__init__()
        if is_filter:
            self.setIcon(QIcon(":/icons/funnel.png"))
        else:
            self.setIcon(QIcon(":/icons/binocular.png"))
        self.setFlat(True)
        self.setMinimumWidth(30)
        self.setToolTip("Search mode")
        self._parent = parent
        self.is_som = is_som

        self.how_menu = QMenu()
        self.setMenu(self.how_menu)

        self.action_text = QAction(self.tr("Text"), self)
        self.action_exact = QAction(self.tr("Exact"), self)
        self.action_wildcard = QAction(self.tr("Wildcard"), self)
        self.action_regex = QAction(self.tr("Regex"), self)
        self.action_listcontains = QAction(self.tr("List Contains"), self)

        self.how_menu.addAction(self.action_text)
        self.how_menu.addAction(self.action_exact)
        self.how_menu.addAction(self.action_wildcard)
        self.how_menu.addAction(self.action_regex)

        if is_som:
            self.how_menu.addAction(self.action_listcontains)

        self.how_menu.addSeparator()

        self.case_sensitive_action = QAction(self.tr("Case Sensitive"), self)
        self.case_sensitive_action.setCheckable(True)
        self.how_menu.addAction(self.case_sensitive_action)

        self.action_text.triggered.connect(lambda: self.set_search_mode("Text"))
        self.action_exact.triggered.connect(lambda: self.set_search_mode("Exact"))
        self.action_wildcard.triggered.connect(lambda: self.set_search_mode("Wildcard"))
        self.action_regex.triggered.connect(lambda: self.set_search_mode("Regex"))
        self.action_listcontains.triggered.connect(lambda: self.set_search_mode("List Contains"))
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


class FilterIndicator(QPushButton):
    """Indicator for the status bar"""
    def __init__(self, mainwindow):
        super().__init__()
        self.mainwindow = mainwindow
        self.setFlat(True)
        self.setIcon(QIcon(":/icons/funnel.png"))
        self.setToolTip(self.tr("Filter active"))
        self.menu = QMenu()
        self.setMenu(self.menu)
        self.hide()


    def check(self):
        """Hide if no filter is active"""
        about_to_hide = True
        for action in self.menu.actions():
            if action.isEnabled():
                about_to_hide = False
                break
        if about_to_hide:
            self.hide()



class SearchInList():
    def __init__(self, pattern, options):
        self.options = options
        self._isvalid = True
        patterns = pattern.split(",")
        patterns = [pattern.strip() for pattern in patterns]
        self.patterns = []
        for pattern in patterns:
            if "-" in pattern:
                start, end = pattern.split("-")
                try:
                    start = int(start)
                    end = int(end)
                except ValueError:
                    self._isvalid = False
                range_str = [str(i) for i in range(start, end+1)]
                self.patterns.extend(range_str)
            else:
                if self.options == QRegularExpression.CaseInsensitiveOption:
                    pattern = str(pattern).lower()
                else:
                    pattern = str(pattern)
                self.patterns.append(str(pattern))

        if not patterns:
            self._isvalid = False

    def isValid(self):
        return self._isvalid
    
    def match(self, item_list):
        if not isinstance(item_list, list):
            return self.Match(False)

        item_list = [str(item) for item in item_list]
        if self.options == QRegularExpression.CaseInsensitiveOption:
            item_list = [item.lower() for item in item_list]

        for pattern in self.patterns:
            if pattern in item_list:
                return self.Match(True)
        return self.Match(False)

    class Match:
        def __init__(self, hasmatch):
            self._hasmatch = hasmatch
    
        def hasMatch(self):
            return self._hasmatch
    
        def __repr__(self):
            return f"Match {self._hasmatch}"