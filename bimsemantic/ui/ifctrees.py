from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView
from .treebase import TreeItem, TreeModelBaseclass


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

