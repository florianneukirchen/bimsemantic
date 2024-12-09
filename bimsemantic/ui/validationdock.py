from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass
import ifcopenshell.util.element
from PySide6.QtWidgets import QDockWidget, QTreeView
from bimsemantic.ui import CopyMixin, ContextMixin
from bimsemantic.util import IfsValidator
import statistics


class ValidationDockWidget(CopyMixin, ContextMixin, QDockWidget):
    def __init__(self, parent):
        super().__init__(self.tr("&Validation"), parent)
        self.mainwindow = parent
        self.validators = []
        
        self.treemodel = ValidationTreeModel(None, self)
        self.proxymodel = QSortFilterProxyModel()
        self.proxymodel.setSourceModel(self.treemodel)
        self.tree = QTreeView()
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.setWidget(self.tree)


    def add_file(self, filename):
        validator = IfsValidator(filename)
        self.validators.append(validator)
        self.treemodel.add_file(validator)
        self.tree.expandAll()


class ValidationTreeModel(TreeModelBaseclass):
    def __init__(self, data, parent):
        super(ValidationTreeModel, self).__init__(data, parent)
        self.column_count = 2

    def setup_root_item(self):
        self._rootItem = TreeItem(
            ["Foo", "Bar"],
            showchildcount=False,
        )

    def add_file(self, validator):
        self.beginResetModel()
        file_item = TreeItem(
            [validator.filename, ""],
            parent=self._rootItem,
        )
        self._rootItem.appendChild(file_item)
        self.endResetModel()
