from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass
import ifcopenshell.util.element
from PySide6.QtWidgets import QDockWidget, QTreeView
from bimsemantic.ui import CopyMixin, ContextMixin
from bimsemantic.util import IfsValidator, Validators


class ValidationDockWidget(CopyMixin, ContextMixin, QDockWidget):
    def __init__(self, parent):
        super().__init__(self.tr("&Validation"), parent)
        self.mainwindow = parent
        self.validators = Validators(self.mainwindow.ifcfiles)
        
        self.treemodel = ValidationTreeModel(None, self)
        self.proxymodel = QSortFilterProxyModel()
        self.proxymodel.setSourceModel(self.treemodel)
        self.tree = QTreeView()
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 250)
        self.setWidget(self.tree)


    def add_file(self, filename):
        validator = IfsValidator(filename)
        self.validators.add_validator(validator)
        self.treemodel.add_file(validator)
        self.tree.expandAll()

    def run_all_validations(self):
        self.validators.validate()
        
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
            [f"{validator.title} | {validator.filename}", ""],
            parent=self._rootItem,
        )
        self._rootItem.appendChild(file_item)
        for spec in validator.rules.specifications:
            spec_item = TreeItem(
                [spec.name, ""],
                parent=file_item,
            )
            file_item.appendChild(spec_item)
            
        self.endResetModel()
