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
    def __init__(self, data, name, parent, columns=["Name"]):
        childs = data.pop("childs", {})
        data.pop("columns", None) # Remove columns if they are present
        super(SomTreeItem, self).__init__(data, parent=parent)
        self.name = name
        self.columns = columns

        for key, value in childs.items():
            item = SomTreeItem(value, key, self, columns)
            self.appendChild(item)

    def data(self, column):
        if column < 0 or column >= len(self.columns):
            return None
        if column == 0:
            return self.name
        else:
            key = self.columns[column]
            data = self._data.get(key, None)
            if isinstance(data, list):
                data = [str(item) for item in data]
                return ", ".join(data)
            return data

    @property
    def label(self):
        return self.name

    def __repr__(self):
        return f"SomTreeItem {self.name}"

    
class SomTreeModel(TreeModelBaseclass):
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
        for key, value in data.items():
            # key ist Fachmodell in DB SOM
            item = SomTreeItem(value, key, parent, self.columns)
            parent.appendChild(item)

       


class SomDockWidget(QDockWidget):
    def __init__(self, parent, filename):
        super(SomDockWidget, self).__init__(self.tr("SOM"), parent)
        self.mainwindow = parent
        self.filename = filename

        try:
            with open(self.filename, "r") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            raise ValueError(f"File {self.filename} is not a valid JSON file.")
        

        self.treemodel = SomTreeModel(data, self)
        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.treemodel)

        self.treeview = QTreeView(self)
        self.treeview.setModel(self.proxymodel)
        self.treeview.setSortingEnabled(True)
        self.treeview.setColumnWidth(0, 200)
        self.setWidget(self.treeview)
