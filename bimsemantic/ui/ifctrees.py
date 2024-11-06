from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt, QSortFilterProxyModel
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView, QWidget, QTabWidget, QVBoxLayout
from bimsemantic.ui import TreeItem, TreeModelBaseclass


class IfcTabs(QWidget):
    def __init__(self, ifc, parent):
        super(IfcTabs, self).__init__(parent)
        self.ifc = ifc

        self.parent = parent
        self.layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.West)
        self.tabs.setMovable(True)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.locationtab = IfcTreeTab(LocationTreeModel(self.ifc), self)
        self.tabs.addTab(self.locationtab, "Location")

        self.typetab = QWidget()
        self.tabs.addTab(self.typetab, "Type")



class IfcTreeTab(QWidget):
    def __init__(self, treemodel, parent):
        super(IfcTreeTab, self).__init__(parent)
        self.parent = parent
        self.mainwindow = parent.parent
        self.model = treemodel
        self.ifc = treemodel.ifc
        print(self.ifc)
        self.layout = QVBoxLayout(self)

        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.model)
        self.tree = QTreeView()
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(2, 250)
        # self.tree.setColumnHidden(1, True)
        self.tree.expandAll()
        self.tree.clicked.connect(self.on_treeview_clicked)
        self.setLayout(self.layout)
        self.layout.addWidget(self.tree)
        

    def on_treeview_clicked(self, index):
        if not index.isValid():
            print("Invalid index")
            return
        source_index = self.proxymodel.mapToSource(index)
        item = source_index.internalPointer()
        if isinstance(item, TreeItem):
            element_id = item.id
            ifc_element = self.ifc.by_id(element_id)
            self.mainwindow.show_details(ifc_element)


class LocationTreeModel(TreeModelBaseclass):
    def setupRootItem(self):
        self.column_names = ["Type", "ID", "Name", "Guid"]
        self._rootItem = TreeItem(self.column_names)
        self.column_count = len(self.column_names)

    def newItem(self, ifc_item, parent):
        item = TreeItem(
            [ifc_item.is_a(), ifc_item.id(), ifc_item.Name, ifc_item.GlobalId],
            ifc_item.id(),
            parent,
        )
        return item

    def setupModelData(self, data, parent):
        self.ifc = data  # ifcopenshell ifc model

        project = self.ifc.by_type("IfcProject")[0]
        project_item = self.newItem(project, parent)
        parent.appendChild(project_item)

        for site in self.ifc.by_type("IfcSite"):
            self.addItems(site, project_item)

    def addItems(self, ifc_object, parent):
        item = self.newItem(ifc_object, parent)
        parent.appendChild(item)
        try:
            elements = ifc_object.ContainsElements[0].RelatedElements
        except IndexError:
            elements = []
        try:
            children = ifc_object.IsDecomposedBy[0].RelatedObjects
        except IndexError:
            children = []

        for element in elements:
            element_item = self.newItem(element, item)
            item.appendChild(element_item)

        for child in children:
            self.addItems(child, item)

