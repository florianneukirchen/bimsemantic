from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass, CustomTreeMaker, CustomFieldType
import ifcopenshell.util.element
from PySide6.QtWidgets import QDockWidget, QTreeView
from bimsemantic.ui import CopyMixin, ContextMixin
import statistics

class PsetDockWidget(CopyMixin, ContextMixin, QDockWidget):
    """Dock widget for property sets or quantity sets

    Also holds the tree model and the tree view, and adds methods
    to reset and to add files.

    :param parent: The parent widget
    :type parent: QMainWindow
    :param qset: If True, the widget will show quantity sets, otherwise property sets
    :type qset: bool
    """
    def __init__(self, parent, qset=False):
        self.is_qset = qset
        if self.is_qset:
            label = self.tr("&Qsets")
        else:
            label = self.tr("&Psets")
        super(PsetDockWidget, self).__init__(label, parent)
        self.mainwindow = parent
        self.reset()

        # Setup Context Menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)


    def reset(self):
        """Reset the tree model and the tree view"""
        if self.is_qset:
            self.treemodel = QsetTreeModel(data=self.mainwindow.ifcfiles, parent=self)
            self.treemodel.calculate_statistics()
        else:
            self.treemodel = PsetTreeModel(data=self.mainwindow.ifcfiles, parent=self)
        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.treemodel)

        self.tree = QTreeView()
        self.tree.setSortingEnabled(True)
        self.tree.setModel(self.proxymodel)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 200)
        self.setWidget(self.tree)

        self.proxymodel.sort(0, Qt.SortOrder.AscendingOrder)
        self.tree.expandAll()

    def add_files(self, ifc_files):
        """Add files to the tree model
        
        :param ifc_files: A list of IfcFile objects
        """
        for file in ifc_files:
            self.treemodel.add_file(file)
        if self.is_qset:
            self.treemodel.calculate_statistics()
        self.proxymodel.sort(0, Qt.SortOrder.AscendingOrder)
        self.tree.expandAll()

    def get_pset_tuple(self, index):
        """Get the property set tuple from the index
        
        Used in the context menu actions
        :param index: The index of the item
        :type index: QModelIndex
        :return: The property set tuple (pset_name, prop_name)
        :rtype: tuple
        """
        if not index.isValid():
            return None
        if self.is_qset:
            return None
        source_index = self.proxymodel.mapToSource(index)
        item = source_index.internalPointer()
        if not item:
            return None
        if item.parent() == self.treemodel.root_item:
            return None

        if item.parent().parent() != self.treemodel.root_item:
            # item is a property value
            item = item.parent()
        pset_name = item.parent().label
        prop_name = item.label
        return pset_name, prop_name

class PsetTreeModel(TreeModelBaseclass):
    """Model for property sets dockwidget
    
    :param data: The IfcFiles object of the main window
    :type data: IfcFiles
    :param parent: The parent widget (PsetDockWidget)
    """

    def __init__(self, data, parent):
        self.psetdock = parent
        super(PsetTreeModel, self).__init__(data, parent)  
        self.column_count = 3

    def setup_root_item(self):
        self._rootItem = TreeItem(["Property Set", self.tr("Elements"), self.tr("Types")], showchildcount=False)

    def setup_model_data(self, data, parent):
        """Set up the model data on init"""
        self.ifc_files = data
        
        for file in self.ifc_files:
            self.add_file(file)

    def add_file(self, ifc_file):
        """Add a file to the model
        
        :param ifc_file: The IfcFile object
        :type ifc_file: IfcFile
        """

        self.beginResetModel()
        elements = ifc_file.model.by_type("IfcElement")
        self.add_elements(elements)
        elementtypes = ifc_file.model.by_type("IfcElementType")
        self.add_elements(elementtypes, count_col=2)
        self.endResetModel()

    def add_elements(self, elements, count_col=1):
        """Add elements or element types to the model"""
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





class QsetTreeModel(TreeModelBaseclass):
    """Model for quantity sets dockwidget with basic statistics
    
    Complex quantity types are ignored

    Note: No quantity sets in IFC2x3

    :param data: The IfcFiles object of the main window
    :type data: IfcFiles
    :param parent: The parent widget (PsetDockWidget)
    """

    def __init__(self, data, parent):
        self.qsetdock = parent
        super(QsetTreeModel, self).__init__(data, parent)
        self.column_count = 7

    def setup_root_item(self):
        """Set up the root item"""
        self._rootItem = TreeItem(["Quantity Set", self.tr("Elements"), self.tr("Std"), self.tr("Min"), self.tr("Mean"), self.tr("Median"), self.tr("Max")], showchildcount=False)

    def setup_model_data(self, data, parent):
        """Set up the model data on init"""
        self.ifc_files = data
        
        for file in self.ifc_files:
            self.add_file(file)

    def add_file(self, ifc_file):
        """Add a file to the model

        :param ifc_file: The IfcFile object
        :type ifc_file: IfcFile
        """
        if ifc_file.model.schema_version[0] < 4:
            # No quantity sets in IFC2x3
            return 
        self.beginResetModel()
        elements = ifc_file.model.by_type("IfcElement")
        self.add_elements(elements)
        self.endResetModel()


    def add_elements(self, elements, count_col=1):
        """Add elements to the model"""
        for element in elements:
            qsets = ifcopenshell.util.element.get_psets(element, qtos_only=True)
            if not qsets:
                continue
            for qset_name, qset in qsets.items():
                qset_item = self.get_child_by_label(self._rootItem, qset_name)
                if not qset_item:
                    qset_item = TreeItem([qset_name], self._rootItem)
                    self._rootItem.appendChild(qset_item)
                for qto_name, qto_value in qset.items():
                    if qto_value is None:
                        continue
                    if qto_name == "id":
                        continue
                    # Ignore complex quantity types for now:
                    # The value could be a dict like
                    # {'value': 4.05, 'unit': 'm3'} or 
                    # {'GrossArea': 13.5, 'NetArea': 12.7} or
                    # {'id': 14643, 'type': 'IfcPhysicalComplexQuantity', 'Discrimination': 'Layer', 'properties': {'Width': 0.08}}
                    # or a list with several values or even a table
                    if not isinstance(qto_value, (int, float)):
                        continue
                    qto_item = self.get_child_by_label(qset_item, qto_name)
                    if not qto_item:
                        # [name, count, min, mean, median, max, values]
                        # values will be invisible in the tree, but is needed to 
                        # calculate mean, median, etc.
                        qto_item = TreeItem([qto_name, 1, 0,0,0,0,0, [qto_value]], qset_item)
                        qset_item.appendChild(qto_item)
                    else:
                        qto_item.set_data(1, qto_item.data(1) + 1)
                        values = qto_item.data(7)
                        values.append(qto_value)
                        qto_item.set_data(7, values)


    def calculate_statistics(self):
        """Calculate basic statistics and add them to the TreeItems"""
        for qset_item in self._rootItem.children:
            for qto_item in qset_item.children:
                values = qto_item.data(7)
                if not values:
                    continue
                min_val = min(values)
                max_val = max(values)
                mean_val = sum(values) / len(values)
                median_val = statistics.median(values)
                if len(values) > 1:
                    std_val = statistics.stdev(values)
                else:
                    std_val = None
                qto_item.set_data(2, std_val)
                qto_item.set_data(3, min_val)
                qto_item.set_data(4, mean_val)
                qto_item.set_data(5, median_val)
                qto_item.set_data(6, max_val)