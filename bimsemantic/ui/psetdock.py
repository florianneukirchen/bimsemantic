from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass, CustomTreeMaker, CustomFieldType
import ifcopenshell.util.element
from PySide6.QtWidgets import QDockWidget, QTreeView

class PsetDockWidget(QDockWidget):
    def __init__(self, parent):
        super(PsetDockWidget, self).__init__(self.tr("&Psets"), parent)
        self.mainwindow = parent
        self.reset()


    def reset(self):
        self.treemodel = PsetTreeModel(data=self.mainwindow.ifcfiles, parent=self)
        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.treemodel)

        self.treeview = QTreeView()
        self.treeview.setSortingEnabled(True)
        self.treeview.setModel(self.proxymodel)
        self.treeview.setAlternatingRowColors(True)
        self.treeview.setColumnWidth(0, 200)
        self.setWidget(self.treeview)


class PsetTreeModel(TreeModelBaseclass):

    def __init__(self, data, parent):
        super(PsetTreeModel, self).__init__(data, parent)
        self.psetdock = parent
        self.column_count = 3

    def setup_root_item(self):
        self._rootItem = TreeItem(["Property Set", "Elements", "Types"], showchildcount=False)

    def setup_model_data(self, data, parent):
        self.ifc_files = data
        
        for file in self.ifc_files:
            self.add_file(file)

    def add_file(self, ifc_file):

        self.beginResetModel()
        elements = ifc_file.model.by_type("IfcElement")
        self.add_elements(elements)
        elementtypes = ifc_file.model.by_type("IfcElementType")
        self.add_elements(elementtypes, count_col=2)
        self.endResetModel()
        self.psetdock.proxymodel.sort(0, Qt.SortOrder.AscendingOrder)
        self.psetdock.treeview.expandAll()

    def add_elements(self, elements, count_col=1):
        for element in elements:
            psets = ifcopenshell.util.element.get_psets(element, psets_only=True)
            if not psets:
                continue
            for pset_name, pset in psets.items():
                pset_item = self.get_child_by_label(self._rootItem, pset_name)
                if not pset_item:
                    pset_item = TreeItem([pset_name, ""], self._rootItem)
                    self._rootItem.appendChild(pset_item)
                for prop_name, prop_value in pset.items():
                    if not prop_value:
                        prop_value = self.nan
                    if prop_name == "id":
                        continue
                    prop_item = self.get_child_by_label(pset_item, prop_name)
                    if not prop_item:
                        prop_item = TreeItem([prop_name, ""], pset_item)
                        pset_item.appendChild(prop_item)
                    value_item = self.get_child_by_label(prop_item, prop_value)
                    if not value_item:
                        value_item = TreeItem([prop_value, 0, 0], prop_item)
                        value_item.set_data(count_col, 1)
                        prop_item.appendChild(value_item)
                    else:
                        value_item.set_data(count_col, value_item.data(count_col) + 1)

