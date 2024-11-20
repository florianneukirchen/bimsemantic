from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView

class TreeItem:
    """Basic item for a tree model.
    
    Can be used directly or subclassed to add more functionality.
    Data in this case is a list of strings, with one entry for each column.

    :param data: The data for the item
    :type data: list  (Optional only for the root item)
    :param parent: The parent tree item (None for the root item)
    :type parent: TreeItem or derived class
    :param id: An optional identifier for the item
    """
    def __init__(self, data=None, parent=None, id=None):
        self._data = data
        if data is None:
            self._data = []
        self._parent = parent
        self._id = id
        self._children = []

    def appendChild(self, item):
        """Add a child item to the item"""
        self._children.append(item)

    def child(self, row):
        """Get a child item by its row
        
        :param row: The row of the child item
        :type row: int
        :return: The child item
        :rtype: TreeItem or derived class
        """
        if row < 0 or row >= len(self._children):
            return None
        return self._children[row]

    def childCount(self):
        """Get the number of children"""
        return len(self._children)
    
    def leavesCount(self):
        """Recursively get the number of leave nodes connected to/as children of this item"""
        leaves = 0
        for child in self._children:
            leaves += child.leavesCount()
        if leaves == 0:
            return 1
        return leaves

    def data(self, column):
        """Get the data for a column
        
        For the first column, the number of children and leaves is added to the string.

        :param column: The column number
        :type column: int
        :return: The data for the column
        :rtype: str or None
        """
        if column < 0 or column >= len(self._data):
            return None
        if column == 0:
            count_children = self.childCount()
            if count_children > 0:
                count_leaves = self.leavesCount()
                if count_leaves != count_children:
                    return f"{self._data[0]} ({count_children}/{count_leaves})"
                else:
                    return f"{self._data[0]} ({count_children})"
        return self._data[column]

    @property
    def label(self):
        """Get the label of the item"""
        return self._data[0]

    def parent(self):
        """Get the parent item
        
        :return: The parent item
        :rtype: TreeItem or derived class
        """
        return self._parent

    def row(self):
        """Get the row of the item in the parent's children list"""
        if self._parent:
            return self._parent.children.index(self)
        return 0

    def find_item_by_guid(self, guid):
        """Find children of type IfcTreeItem by GUID
        
        TreeItem does not have a GUID, just pass on to the children, 
        for iteration in an IfcTreeModel.
        """
        for child in self._children:
            result = child.find_item_by_guid(guid)
            if result:
                return result
        return None
    
    def find_item_by_tag(self, tag):
        """Find children of type IfcTreeItem by tag
        
        TreeItem does not have a tag, just pass on to the children, 
        for iteration in an IfcTreeModel.
        """
        for child in self._children:
            result = child.find_item_by_tag(tag)
            if result:
                return result
        return None
    
    @property
    def id(self):
        """The optional ID of the item"""
        return self._id

    @property
    def children(self):
        """Children of the tree item"""
        return self._children

    def __repr__(self):
        return f"TreeItem ({self.data(0)})"

    

class TreeModelBaseclass(QAbstractItemModel):
    """Base class for a tree model, supposed to be subclassed.
    
    On init, the root item is created in setupRootItem() and the model data is 
    set up in setupModelData(). These functions are supposed to be overridden
    in derived classes.

    The other methods are required for the model to work with a QTreeView,
    some may be overwritten in derived classes, e.g. columnCount().

    :param data: The data for the model
    :type data: Any
    :param parent: The parent widget
    """
    def __init__(self, data, parent=None):
        super(TreeModelBaseclass, self).__init__(parent)
        self.column_count = 2

        self.setupRootItem()
        self.setupModelData(data, self._rootItem)

    def setupRootItem(self):
        """Set up the root item for the model, can be overridden in derived classes"""
        self._rootItem = TreeItem()
       
    def setupModelData(self, data, parent):
        """Set up the model data, must be overridden in derived classes"""
        pass

    def rowCount(self, parent=QModelIndex()):
        """Get the number of rows (children) for a parent item"""
        if parent.column() > 0:
            return 0
        parentItem = parent.internalPointer() if parent.isValid() else self._rootItem
        return parentItem.childCount()

    def columnCount(self, parent=QModelIndex()):
        """Get the number of columns of the model"""
        return self.column_count

    def data(self, index, role=Qt.DisplayRole):
        """Get the data for a given index
        
        :param index: The index of the item
        :type index: QModelIndex
        :param role: Flag for the role
        """
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        item = index.internalPointer()
        return item.data(index.column())

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Get the header data from the root item of the model"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._rootItem.data(section)
        return None

    def index(self, row, column, parent=QModelIndex()):
        """Crate a QModelIndex for a given row and column"""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parentItem = parent.internalPointer() if parent.isValid() else self._rootItem
        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        return QModelIndex()

    def parent(self, index):
        """Get the QModelIndex of the parent item"""
        if not index.isValid():
            return QModelIndex()
        childItem = index.internalPointer()
        parentItem = childItem.parent()
        if parentItem == self._rootItem:
            return QModelIndex()
        return self.createIndex(parentItem.row(), 0, parentItem)
