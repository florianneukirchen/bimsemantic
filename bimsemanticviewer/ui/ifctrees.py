from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView
from .treebase import TreeItem, TreeModelBaseclass


class LocationTreeModel(TreeModelBaseclass):
    def setupRootItem(self):
        self._rootItem = TreeItem(["Type", "Name", "Foo"])
        self.column_count = 3

    def setupModelData(self, data, parent):
        self.ifc = data  # ifcopenshell ifc model

        project = self.ifc.by_type("IfcProject")[0]
        project_item = TreeItem(
            [project.is_a(), project.Name], project.id(), parent
        )
        parent.appendChild(project_item)

        for site in self.ifc.by_type("IfcSite"):
            site_item = TreeItem(
                [site.is_a(), site.Name], site.id(), project_item
            )
            project_item.appendChild(site_item)
            for building in site.IsDecomposedBy[0].RelatedObjects:
                building_item = TreeItem(
                    [building.is_a(), building.Name],
                    building.id(),
                    site_item,
                )
                site_item.appendChild(building_item)
                for storey in building.IsDecomposedBy[0].RelatedObjects:
                    storey_item = TreeItem(
                        [storey.is_a(), storey.Name],
                        storey.id(),
                        building_item,
                    )
                    building_item.appendChild(storey_item)
                    for element in storey.ContainsElements[0].RelatedElements:
                        element_item = TreeItem(
                            [element.is_a(), element.Name],
                            element.id(),
                            storey_item,
                        )
                        storey_item.appendChild(element_item)
