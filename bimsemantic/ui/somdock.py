from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QTreeView,
    QMenu,
    QWidget,
    QVBoxLayout,
)
import ifcopenshell.util.element
import json
from bimsemantic.ui import TreeItem, TreeModelBaseclass, CopyMixin, SearchBar


class SomTreeItem(TreeItem):
    """Item for the SOM tree model

    On init, it creates child items for the children of the item.
    Takes a JSON-like nested dictionary as data, with children
    grouped in a dictionary under the key "childs".

    The columns are used to get the data for the columns from the data dictionary.

    :param data: The data for the item as a nested dictionary
    :type data: dict
    :param name: The name of the item (or the key of the parent dictionary)
    :type name: str
    :param parent: The parent item
    :type parent: TreeItem or derived class
    :param columns: The columns to use for the item
    :type columns: list
    """

    def __init__(self, data, name, parent, columns=["Name"]):
        childs = data.pop("childs", {})
        data.pop("columns", None)  # Remove columns if they are present
        super(SomTreeItem, self).__init__(data, parent=parent)
        self.name = name
        self.columns = columns

        for key, value in childs.items():
            item = SomTreeItem(value, key, self, columns)
            self.appendChild(item)

    def data(self, column, to_string=True):
        """Get the data for a column"""
        if column < 0 or column >= len(self.columns):
            return None
        if column == 0:
            return self.name
        else:
            key = self.columns[column]
            data = self._data.get(key, None)
            if isinstance(data, list) and to_string:
                data = [str(item) for item in data]
                return ", ".join(data)
            return data

    @property
    def label(self):
        """First column without counter"""
        return self.name

    def __repr__(self):
        return f"SomTreeItem {self.name}"


class SomTreeModel(TreeModelBaseclass):
    """Model for the SOM tree view

    The model is created from a JSON-like nested dictionary.

    :param data: The data for the model as a nested dictionary
    :type data: dict
    :param parent: The parent widget (the SOM dockwidget)
    """

    def __init__(self, data, parent):
        self.somdock = parent
        # Get a list of colums from the first Fachmodell
        firstkey = list(data.keys())[0]
        self.columns = ["Name"] + data[firstkey].get("columns", [])
        super(SomTreeModel, self).__init__(data, parent)

    def setup_root_item(self):
        """Set up the root item for the model"""
        self._rootItem = TreeItem(self.columns, showchildcount=False)
        self.column_count = len(self.columns)

    def setup_model_data(self, data, parent):
        """Set up the model data from a nested dictionary

        SomTreeItem automatically creates child items for anything
        found under the key 'childs'.

        :param data: The data for the model as a nested dictionary
        :type data: dict
        :param parent: The parent item
        :type parent: TreeItem or derived class
        """
        for key, value in data.items():
            # key ist Fachmodell in DB SOM
            item = SomTreeItem(value, key, parent, self.columns)
            parent.appendChild(item)


class SomDockWidget(CopyMixin, QDockWidget):
    """Dock widget for the SOM-list tree view

    Opens a JSON file with the SOM data and displays it in a tree view.
    Also adds actions to the main window.

    :param parent: The parent widget (the main window)
    :param filename: The filename of the JSON file with the SOM data
    """

    def __init__(self, parent, filename):
        super(SomDockWidget, self).__init__(self.tr("SOM"), parent)
        self.mainwindow = parent
        self.filename = filename
        self._autosearch_attribute = None

        try:
            with open(self.filename, "r") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            raise ValueError(f"File {self.filename} is not a valid JSON file.")

        self.main_widget = QWidget()
        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(4, 2, 4, 2)
        self.setWidget(self.main_widget)

        # Tree widget
        self.treemodel = SomTreeModel(data, self)
        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.treemodel)

        self.tree = QTreeView(self)
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.proxymodel.sort(0, Qt.SortOrder.AscendingOrder)
        self.tree.setColumnWidth(0, 200)

        # Search widget
        self.searchbar = SearchBar(self)
        self.searchbar.stop_auto_button.clicked.connect(
            lambda: self.set_autosearch_attribute(None)
        )
        self.filterbar = SearchBar(self, filtermode=True)


        self.layout.addWidget(self.searchbar)
        self.layout.addWidget(self.filterbar)
        self.layout.addWidget(self.tree)

        # Add menu actions

        self._collapse_act = QAction(
            self.tr("&Collapse"),
            self,
            # Using lambda makes it possible to pass an argument to the function
            triggered=(lambda: self.expand_view(-1)),
        )
        self.mainwindow.expand_som_menu.addAction(self._collapse_act)

        self._expand_level1_act = QAction(
            self.tr("Expand to level &1"),
            self,
            triggered=(lambda: self.expand_view(1)),
        )
        self.mainwindow.expand_som_menu.addAction(self._expand_level1_act)

        self._expand_level2_act = QAction(
            self.tr("Expand to level &2"),
            self,
            triggered=(lambda: self.expand_view(2)),
        )
        self.mainwindow.expand_som_menu.addAction(self._expand_level2_act)

        self._expand_level3_act = QAction(
            self.tr("Expand to level &3"),
            self,
            triggered=(lambda: self.expand_view(3)),
        )
        self.mainwindow.expand_som_menu.addAction(self._expand_level3_act)

        self._expand_level4_act = QAction(
            self.tr("Expand to level &4"),
            self,
            triggered=(lambda: self.expand_view(4)),
        )
        self.mainwindow.expand_som_menu.addAction(self._expand_level4_act)

        self._expand_all_act = QAction(
            self.tr("Expand &all"),
            self,
            triggered=(lambda: self.expand_view("all")),
        )
        self.mainwindow.expand_som_menu.addAction(self._expand_all_act)

        # Setup Context Menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        """Show the context menu in the som dock"""
        index = self.tree.indexAt(position)
        context_menu = QMenu(self)
        context_menu.addAction(self.mainwindow.copy_rows_act)
        context_menu.addAction(self.mainwindow.copy_cell_act)
        expand_menu = QMenu(self.tr("Expand/Collapse"), self)
        for action in self.mainwindow.expand_som_menu.actions():
            expand_menu.addAction(action)
        context_menu.addMenu(expand_menu)
        context_menu.addSeparator()
        if index.isValid() and index.column() > 0:
            context_menu.addAction(
                QAction(
                    self.tr("Hide column"),
                    self,
                    triggered=lambda: self.hide_column(index.column()),
                )
            )
        context_menu.addAction(
            QAction(
                self.tr("Show hidden columns"), self, triggered=self.show_hidden_columns
            )
        )
        context_menu.exec(self.tree.viewport().mapToGlobal(position))

    def expand_view(self, level):
        """Expand the treeview to a certain level"""
        if level == -1:
            self.tree.collapseAll()
        elif level == "all":
            self.tree.expandAll()
        else:
            self.tree.expandToDepth(level - 1)

    def show_hidden_columns(self):
        """Unhide all columns in the tree view"""
        for i in range(self.treemodel.columnCount()):
            self.tree.setColumnHidden(i, False)
        self.searchbar.columns_changed()

    def hide_column(self, column):
        """Hide a column in the tree view

        :param column: The column to hide
        :type column: int
        """
        self.tree.setColumnHidden(column, True)
        self.searchbar.columns_changed()

    def autosearch(self, ifc_object):
        """Select an element in the tree view by an IfcElement

        :param ifc_object: The IfcElement to select
        :type ifc_object: IfcElement
        """
        if not self._autosearch_attribute:
            return

        psets = ifcopenshell.util.element.get_psets(ifc_object, psets_only=True)
        if not psets:
            return

        try:
            name = psets[self._autosearch_attribute[0]][self._autosearch_attribute[1]]
        except KeyError:
            return
        self.searchbar.search_text.setText(name)
        self.searchbar.column_combo.setCurrentIndex(0)
        self.searchbar.search()

    def set_autosearch_attribute(self, attribute):
        """Set the attribute to use for autosearch

        Pass a tuple (pset_name, attribute_name) to enable autosearch,
        or None to disable autosearch.

        :param attribute: The attribute to use for autosearch as a tuple
        :type attribute: tuple or None
        """
        self._autosearch_attribute = attribute
        self.searchbar.stop_auto_button.setVisible(attribute is not None)
        self.mainwindow.stop_auto_act.setEnabled(attribute is not None)
        if attribute:
            self.searchbar.show()
            tooltip=self.tr("Stop autosearch on %s" % f"{attribute[0]} | {attribute[1]}")
            self.searchbar.stop_auto_button.setToolTip(tooltip)
            self.mainwindow.stop_auto_act.setToolTip(tooltip)
            self.mainwindow.stop_auto_act.setEnabled(True)

            self.mainwindow.statusbar.showMessage(
                self.tr(
                    "Autosearch attribute set to: %s"
                    % f"{attribute[0]} | {attribute[1]}"
                )
            )
            # Autosearch the current item
            index = self.mainwindow.tabs.tree.currentIndex()
            source_index = self.mainwindow.tabs.proxymodel.mapToSource(index)
            if source_index.isValid():
                item = source_index.internalPointer()
                self.autosearch(item.ifc)
        else:
            self.mainwindow.stop_auto_act.setToolTip(self.tr("Stop the auto search in the SOM"))


    def __repr__(self):
        return f"SomDockWidget {self.filename}"
