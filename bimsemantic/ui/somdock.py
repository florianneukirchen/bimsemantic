from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass, CustomTreeMaker, CustomFieldType
import ifcopenshell.util.element
from PySide6.QtWidgets import QDockWidget, QTreeView
import json

class SomTreeItem(TreeItem):
    """Item for the SOM tree model

    On init, it creates child items for the children of the item.
    Takes a JSON-like nested dictionary as data, with children 
    grouped in a dictionary under the key "childs".

    :param data: The data for the item as a nested dictionary
    :type data: dict
    :param name: The name of the item
    :type name: str
    :param parent: The parent item
    :type parent: TreeItem or derived class
    """
    def __init__(self, data, name, parent):
        childs = data.pop("childs", {})
        super(SomTreeItem, self).__init__(data, parent=parent)
        self.name = name

        for key, value in childs.items():
            item = SomTreeItem(value, key, self)
            self.appendChild(item)

    def data(self, column):
        if column == 0:
            return self.name
        elif column == 1:
            return self._data.get("type", "")
        else:
            return None

    def __repr__(self):
        return f"SomTreeItem {self.name}"

    
class SomTreeModel(TreeModelBaseclass):
    def __init__(self, data, parent):
        self.somdock = parent
        super(SomTreeModel, self).__init__(data, parent)
        self.column_count = 3
    
    def setup_model_data(self, data, parent):
        for key, value in data.items():
            # key ist Fachmodell in DB SOM
            item = SomTreeItem(value, key, parent)
            parent.appendChild(item)

       


class SomDockWidget(QDockWidget):
    def __init__(self, parent, filename):
        super(SomDockWidget, self).__init__(self.tr("SOM"), parent)
        self.mainwindow = parent
        self.filename = filename
        self._isvalid = True

        try:
            with open(self.filename, "r") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self._isvalid = False
            return

        self.treemodel = SomTreeModel(data, self)
        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.treemodel)

        self.treeview = QTreeView(self)
        self.treeview.setModel(self.proxymodel)
        self.treeview.setSortingEnabled(True)
        self.treeview.setColumnWidth(0, 200)
        self.setWidget(self.treeview)

        self.treeview.expandAll()
        self.proxymodel.sort(0, Qt.SortOrder.AscendingOrder)
        

    def is_valid(self):
        return self._isvalid