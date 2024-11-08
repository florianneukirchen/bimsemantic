from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView
import ifcopenshell
import ifcopenshell.util.element

class TreeItem:
    def __init__(self, data=None, parent=None, id=None):
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
            return self._parent.children.index(self)
        return 0

    @property
    def id(self):
        return self._id

    @property
    def children(self):
        return self._children


class PsetColumns:
    def __init__(self):
        self._columns = []

    def add_column(self, pset_name, attribute):
        self._columns.append((pset_name, attribute))
        return len(self._columns) - 1

    def remove_column(self, pset_column_index):
        self._columns.pop(pset_column_index)

    def col(self, column):
        return self._columns[column]
    
    def column_name(self, column):
        return self._columns[column][1]

    def count(self):
        return len(self._columns)
    
    @property
    def column_names(self):
        return [col[1] for col in self._columns]


class ColheaderTreeItem(TreeItem):
    def __init__(self, data, parent=None, first_cols=[]):
        self._pset_columns = data
        self._first_cols = first_cols
        self._count_first_cols = len(first_cols)
        self._parent = parent
        self._children = []

    def data(self, column):
        if column < 0 or column >= (self._pset_columns.count + self._count_first_cols):
            return None
        if column < self._count_first_cols:
            return self._first_cols[column]
        return self._pset_columns.column_name(column + self._count_first_cols)


class IfcTreeItem(TreeItem):
    def __init__(self, data, parent=None, pset_columns=None):
        self._ifc_item = data
        self._parent = parent
        self._id = self._ifc_item.id()
        self._children = []
        self._pset_columns = pset_columns

    def data(self, column):
        if column < 0 or column >= self._pset_columns.count + 4:
            return None
        if column == 0:
            return self._ifc_item.is_a()
        if column == 1:
            return self._ifc_item.id()
        if column == 2:
            return self._ifc_item.Name
        if column == 3:
            return self._ifc_item.GlobalId
        
        psets = ifcopenshell.util.element.get_psets(self._ifc_item)
        pset_name, attribute = self._pset_columns(column - 4)
        
        try:
            return psets[pset_name][attribute]
        except KeyError:
            return None




class TreeModelBaseclass(QAbstractItemModel):
    def __init__(self, data, parent=None):
        super(TreeModelBaseclass, self).__init__(parent)
        self.column_count = 2
        self._rootItem = TreeItem()
        self.setupModelData(data, self._rootItem)

       
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
