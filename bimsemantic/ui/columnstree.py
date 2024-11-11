from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon


class ColumnsTreeModel(QTreeWidget):
    def __init__(self, data, parent=None):
        super(ColumnsTreeModel, self).__init__(parent)
        self.first_cols = ["Type", "ID", "Name", "GUID"]
        self.setHeaderHidden(True)
        self.setupModelData(data)
        self.expandAll()

    def setupModelData(self, data):
        infocols_item = QTreeWidgetItem(self)
        infocols_item.setText(0, "Info Columns")
        infocols_item.setFlags(infocols_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
        
        for col in self.first_cols[1:]:
            col_item = QTreeWidgetItem(infocols_item)
            col_item.setText(0, col)
            col_item.setFlags(col_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            col_item.setCheckState(0, Qt.CheckState.Checked)
        
        psets_item = QTreeWidgetItem(self)
        psets_item.setText(0, "Property Sets")
        psets_item.setFlags(psets_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

        pset_info = data.pset_info

        for pset_name, pset_props in pset_info.items():
            pset_item = QTreeWidgetItem(psets_item)
            pset_item.setText(0, pset_name)
            pset_item.setFlags(pset_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

            for prop in pset_props:
                prop_item = QTreeWidgetItem(pset_item)
                prop_item.setText(0, prop)
                prop_item.setFlags(prop_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                prop_item.setCheckState(0, Qt.CheckState.Unchecked)

    def _get_pset_info(self):
        pset_info = {}
        psets = self._model.by_type("IfcPropertySet")
        for pset in psets:
            if not pset.Name in pset_info:
                pset_info[pset.Name] = []
            for prop in pset.HasProperties:
                if not prop.Name in pset_info[pset.Name]:
                    pset_info[pset.Name].append(prop.Name)
        return pset_info
