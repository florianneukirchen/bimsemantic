from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt,  Qt, Signal, QTimer


class ColumnsTreeModel(QTreeWidget):
    """Model for the columns tree view
    
    Based on QTreeWidget, giving functionality such as checkboxes.
    The model is used to manage the columns of the IFC tree views.
    It is initalized in the main window. Can be initalized without data,
    but entries can be added later with addFile().

    :param data: The data, optional
    :type data: IfcFile instance
    :param parent: The parent widget (main window)
    """

    columnsChanged = Signal()
    hideInfoColumn = Signal(int, bool)

    def __init__(self, data=None, parent=None):
        super(ColumnsTreeModel, self).__init__(parent)
        self.first_cols = [
            self.tr("Type"), 
            "ID", 
            self.tr("Name"), 
            "GUID", 
            "Tag",
            self.tr("Object Type"),
            self.tr("Description"),
            self.tr("Filename"), 
            self.tr("Contained In"),
            self.tr("Validation"),
            ]
        self._hidden = [
            "ID", 
            "GUID", 
            "Tag", 
            self.tr("Object Type"), 
            self.tr("Description"), 
            self.tr("Filename"), 
            self.tr("Contained In"),
            self.tr("Validation")] 
        self._count_first_cols = len(self.first_cols)
        self._psetcolumns = []
        self.mainwindow = parent
        self.timer = QTimer()
        self.timer.setSingleShot(True) 
        self.setHeaderHidden(True)
        self.setupModelData(data)
        self.expandAll()
        self.itemChanged.connect(self.item_changed)
        self.timer.timeout.connect(self.emit_columns_changed)


    def setupModelData(self, data):
        """Setup the model data, at least the Info Columns and all top level items"""
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
        self.psets_item.setFlags(self.psets_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

        self.qsets_item = QTreeWidgetItem(self)
        self.qsets_item.setText(0, self.tr("Quantity Sets"))
        self.qsets_item.setFlags(self.psets_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

        if data:
            self.addFile(data)

    def addFile(self, ifc_file):
        """Add an IFC file to the model
        
        Adds the property sets of the IFC file to the tree model.
        :param ifc_file: The IFC file
        :type ifc_file: IfcFile instance
        """
        self.blockSignals(True) # Prevent itemChanged signal from being emitted when the checkboxes are set

        pset_info = ifc_file.pset_info

        for pset_name in pset_info.keys():
            pset_item = self.get_child_by_name(self.psets_item, pset_name)
            if pset_item is None:
                pset_item = QTreeWidgetItem(self.psets_item)
                pset_item.setText(0, pset_name)
                pset_item.setFlags(pset_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

            for prop in pset_info[pset_name]:
                prop_item = self.get_child_by_name(pset_item, prop)
                if prop_item is None:
                    prop_item = QTreeWidgetItem(pset_item)
                    prop_item.setText(0, prop)
                    prop_item.setFlags(prop_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    prop_item.setCheckState(0, Qt.CheckState.Unchecked)

        qset_info = ifc_file.qset_info
        print(qset_info)

        for qset_name in qset_info.keys():
            qset_item = self.get_child_by_name(self.qsets_item, qset_name)
            if qset_item is None:
                qset_item = QTreeWidgetItem(self.qsets_item)
                qset_item.setText(0, qset_name)
                qset_item.setFlags(qset_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)

            for qset in qset_info[qset_name]:
                qto_item = self.get_child_by_name(qset_item, qset)
                if qto_item is None:
                    qto_item = QTreeWidgetItem(qset_item)
                    qto_item.setText(0, qset)
                    qto_item.setFlags(qset_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    qto_item.setCheckState(0, Qt.CheckState.Unchecked)


        self.sort_psetcolumns()
        self.expandAll()
        self.blockSignals(False)
    
    def get_child_by_name(self, parent, name):
        """Get a child item by its name, if it exists"""
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.text(0) == name:
                return child
        return None

    def sort_psetcolumns(self):
        """Sort the properties/quantities of the property/quantity sets"""
        self.psets_item.sortChildren(0, Qt.SortOrder.AscendingOrder)
        for i in range(self.psets_item.childCount()):
            self.psets_item.child(i).sortChildren(0, Qt.SortOrder.AscendingOrder)

        self.qsets_item.sortChildren(0, Qt.SortOrder.AscendingOrder)
        for i in range(self.qsets_item.childCount()):
            self.qsets_item.child(i).sortChildren(0, Qt.SortOrder.AscendingOrder)

    def col(self, column):
        """Return a tuple pset and property for a column
        
        These can be used as keys in the pset dictionary of an ifc item.

        :param column: The column index of a property set column
        :type column: int
        :return: Tuple (pset, property) 
        :rtype: tuple of str
        """
        column = column - self._count_first_cols
        return self._psetcolumns[column]
    
    def column_name(self, column):
        """Return the name of a column
        
        :param column: The column index
        :type column: int
        :return: The name of the column
        :rtype: str
        """
        if column < self._count_first_cols:
            return self.first_cols[column]
        column = column - self._count_first_cols
        return self._psetcolumns[column][1]

    def item_changed(self, item, column):
        """Slot for the itemChanged signal
        
        For the Info Columns, the signal hideInfoColumn is emitted
        to toggle the visibility of these colums.

        For the Property Sets, the signal update_psetcolumns is emitted
        telling the IFC treeviews to update their layout. If the checkbox
        of a root item with several children is toggled, itemChanged is
        fired for each checkbox. A timer is used to collect these signals
        into one.
        :param item: The item containg the checkbox that was toggled
        :type item: QTreeWidgetItem
        :param column: The column of the checkbox
        """
        if item.checkState(column) in (Qt.CheckState.Checked, Qt.CheckState.Unchecked) and item.parent() is not None:
            if item.parent().text(column) == self.tr("Info Columns"):
                ishidden = item.checkState(column) == Qt.CheckState.Unchecked
                col_index = self.first_cols.index(item.text(column))
                self.hideInfoColumn.emit(col_index, ishidden)
            else:
                self.blockSignals(True)
                self.update_psetcolumns()
                self.blockSignals(False)
                self.timer.start(20)

    def emit_columns_changed(self):
        """Callback of the timer that is used in item_changed"""
        self.columnsChanged.emit()

    def update_psetcolumns(self):
        """For checked items, create a list of tuples with the psets and their properties"""
        self.mainwindow.statusbar.showMessage(self.tr("Update columns..."))
        self.mainwindow.progressbar.setRange(0, 0)

        self._psetcolumns = []

        for i in range(self.psets_item.childCount()):
            pset_item = self.psets_item.child(i)
            pset_name = pset_item.text(0)
            for j in range(pset_item.childCount()):
                prop_item = pset_item.child(j)
                if prop_item.checkState(0) == Qt.CheckState.Checked:
                    self._psetcolumns.append((pset_name, prop_item.text(0)))

        for i in range(self.qsets_item.childCount()):
            qset_item = self.qsets_item.child(i)
            qset_name = qset_item.text(0)
            for j in range(qset_item.childCount()):
                qto_item = qset_item.child(j)
                if qto_item.checkState(0) == Qt.CheckState.Checked:
                    self._psetcolumns.append((qset_name, qto_item.text(0)))

    def hidden_info_columns(self):
        """Returns a list of column indexes that are hidden"""
        hidden = []
        for i in range(self.infocols_item.childCount()):
            child = self.infocols_item.child(i)
            if child.checkState(0) == Qt.CheckState.Unchecked:
                hidden.append(self.first_cols.index(child.text(0)))
        return hidden


    def count(self):
        """Return the total number of columns, including info and pset columns"""
        return self._count_first_cols + len(self._psetcolumns)
    
    
    def count_psets(self):
        """Return the number of property sets of all open files"""
        return self.psets_item.childCount()

