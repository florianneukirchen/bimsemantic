from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView
from .treebase import TreeItem, TreeModelBaseclass


class LocationTreeModel(TreeModelBaseclass):
    def setupRootItem(self):
        self._rootItem = TreeItem(["Name", "Type", "Foo"])
        self.column_count = 3

    def setupModelData(self, data, parent):
        self.ifc = data  # ifcopenshell ifc model

        project = self.ifc.by_type("IfcProject")[0]
        project_item = TreeItem(
            [f"Project: {project.Name}", project.is_a()], project.id(), parent
        )
        parent.appendChild(project_item)

        for site in self.ifc.by_type("IfcSite"):
            site_item = TreeItem(
                [f"Site: {site.Name}", site.is_a()], site.id(), project_item
            )
            project_item.appendChild(site_item)
            for building in site.IsDecomposedBy[0].RelatedObjects:
                building_item = TreeItem(
                    [f"Building: {building.Name}", building.is_a()],
                    building.id(),
                    site_item,
                )
                site_item.appendChild(building_item)
                for storey in building.IsDecomposedBy[0].RelatedObjects:
                    storey_item = TreeItem(
                        [f"Storey: {storey.Name}", storey.is_a()],
                        storey.id(),
                        building_item,
                    )
                    building_item.appendChild(storey_item)
                    for element in storey.ContainsElements[0].RelatedElements:
                        element_item = TreeItem(
                            [f"{element.Name}", element.is_a()],
                            element.id(),
                            storey_item,
                        )
                        storey_item.appendChild(element_item)
