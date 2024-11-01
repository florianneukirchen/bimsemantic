from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView


class TreeItem:
    def __init__(self, data=None, id=None, parent=None):
        self._data = data
        if data is None:
            self._data = []
        self._parent = parent
        self._id = id
        self._children = []

    def appendChild(self, item):
        self._children.append(item)

    def child(self, row):
        if row < 0 or row >= len(self._children):
            return None
        return self._children[row]

    def childCount(self):
        return len(self._children)

    def data(self, column):
        if column < 0 or column >= len(self._data):
            return None
        return self._data[column]

    def parent(self):
        return self._parent

    def row(self):
        if self._parent:
            return self._parent._children.index(self)
        return 0

    @property
    def id(self):
        return self._id


class TreeModelBaseclass(QAbstractItemModel):
    def __init__(self, data, parent=None):
        super(TreeModelBaseclass, self).__init__(parent)
        self.column_count = 3
        self.setupRootItem()
        self.setupModelData(data, self._rootItem)

    def setupRootItem(self):
        self._rootItem = TreeItem()

    def setupModelData(self, data, parent):
        pass

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        parentItem = parent.internalPointer() if parent.isValid() else self._rootItem
        return parentItem.childCount()

    def columnCount(self, parent=QModelIndex()):
        return self.column_count

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        item = index.internalPointer()
        return item.data(index.column())

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._rootItem.data(section)
        return None

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parentItem = parent.internalPointer() if parent.isValid() else self._rootItem
        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        childItem = index.internalPointer()
        parentItem = childItem.parent()
        if parentItem == self._rootItem:
            return QModelIndex()
        return self.createIndex(parentItem.row(), 0, parentItem)


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
