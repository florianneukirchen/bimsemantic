from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon


class ColumnsTreeModel(QTreeWidget):

    columnsChanged = Signal()
    hideInfoColumn = Signal(int, bool)

    def __init__(self, data=None, parent=None):
        super(ColumnsTreeModel, self).__init__(parent)
        self.first_cols = [
            self.tr("Type"), 
            "ID", self.tr("Name"), 
            "GUID", 
            self.tr("Filename")
            ]
        self._hidden = ["ID", "GUID", self.tr("Filename")] 
        self._count_first_cols = len(self.first_cols)
        self._psetcolumns = []
        self.setHeaderHidden(True)
        self.setupModelData(data)
        self.expandAll()
        self.itemChanged.connect(self.item_changed)


    def setupModelData(self, data):
        self.infocols_item = QTreeWidgetItem(self)

        # Info Columns
        self.infocols_item.setText(0, self.tr("Info Columns"))
        self.infocols_item.setFlags(self.infocols_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
        
        for col in self.first_cols[1:]:
            col_item = QTreeWidgetItem(self.infocols_item)
            col_item.setText(0, col)
            col_item.setFlags(col_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if col in self._hidden:
                col_item.setCheckState(0, Qt.CheckState.Unchecked)
            else:
                col_item.setCheckState(0, Qt.CheckState.Checked)
        
        # Pset Columns
        self.psets_item = QTreeWidgetItem(self)
        self.psets_item.setText(0, self.tr("Property Sets"))
        if data:
            self.addFile(data)

    def addFile(self, ifc_file):


        pset_info = ifc_file.pset_info
        pset_keys = list(pset_info.keys())
        pset_keys.sort()

        for pset_name in pset_keys:
            pset_props = pset_info[pset_name]
            pset_props.sort()
            pset_item = QTreeWidgetItem(self.psets_item)
            pset_item.setText(0, pset_name)
            pset_item.setFlags(pset_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

            for prop in pset_props:
                prop_item = QTreeWidgetItem(pset_item)
                prop_item.setText(0, prop)
                prop_item.setFlags(prop_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                prop_item.setCheckState(0, Qt.CheckState.Unchecked)

    def col(self, column):
        column = column - self._count_first_cols
        return self._psetcolumns[column]
    
    def column_name(self, column):
        if column < self._count_first_cols:
            return self.first_cols[column]
        column = column - self._count_first_cols
        return self._psetcolumns[column][1]

    def item_changed(self, item, column):
        if item.checkState(column) in (Qt.CheckState.Checked, Qt.CheckState.Unchecked) and item.parent() is not None:
            if item.parent().text(column) == self.tr("Info Columns"):
                ishidden = item.checkState(column) == Qt.CheckState.Unchecked
                col_index = self.first_cols.index(item.text(column))
                self.hideInfoColumn.emit(col_index, ishidden)
            else:
                self.update_psetcolumns()
                self.columnsChanged.emit()

    def update_psetcolumns(self):
        self._psetcolumns = []
        for i in range(self.psets_item.childCount()):
            pset_item = self.psets_item.child(i)
            pset_name = pset_item.text(0)
            for j in range(pset_item.childCount()):
                prop_item = pset_item.child(j)
                if prop_item.checkState(0) == Qt.CheckState.Checked:
                    self._psetcolumns.append((pset_name, prop_item.text(0)))


    def hidden_info_columns(self):
        """Returns a list of column indexes that are hidden"""
        hidden = []
        for i in range(self.infocols_item.childCount()):
            child = self.infocols_item.child(i)
            if child.checkState(0) == Qt.CheckState.Unchecked:
                hidden.append(self.first_cols.index(child.text(0)))
        return hidden


    def count(self):
        return self._count_first_cols + len(self._psetcolumns)
    
    


