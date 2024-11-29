from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt, QObject
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView

class TreeItem(QObject):
    """Basic item for a tree model.
    
    Can be used directly or subclassed to add more functionality.
    Data in this case is a list of strings, with one entry for each column.

    :param data: The data for the item
    :type data: list  (Optional only for the root item)
    :param parent: The parent tree item (None for the root item)
    :type parent: TreeItem or derived class
    :param id: An optional identifier for the item
    """
    def __init__(self, data=None, parent=None, id=None, showchildcount=True):
        self._data = data
        if data is None:
            self._data = []
        self._parent = parent
        self._id = id
        self._children = []
        self.showchildcount = showchildcount

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

    def child_count(self):
        """Get the number of children"""
        return len(self._children)
    
    def leaves_count(self):
        """Recursively get the number of leave nodes connected to/as children of this item"""
        leaves = 0
        for child in self._children:
            leaves += child.leaves_count()
        if leaves == 0:
            return 1
        return leaves
    
    def level(self):
        """Get the level of the item in the tree"""
        level = -1 # Do not include the root item
        parent = self._parent
        while parent:
            level += 1
            parent = parent.parent()
        return level

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
            if not self.showchildcount:
                return self._data[0]
            count_children = self.child_count()
            if count_children > 0:
                count_leaves = self.leaves_count()
                if count_leaves != count_children:
                    return f"{self._data[0]} ({count_children}/{count_leaves})"
                else:
                    return f"{self._data[0]} ({count_children})"
        return self._data[column]

    def set_data(self, column, value):
        """Set the data for a column
        
        :param column: The column number
        :type column: int
        :param value: The value to set
        """
        if column < 0 or column >= len(self._data):
            return
        self._data[column] = value

    @property
    def label(self):
        """Get the the data of the first column without the count of children"""
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

    def search(self, text, column=0, case_sensitive=False, how="="):
        """Find all items with a given text in column
        
        Recursively search the children for items with the given label.

        :param text: String to search for
        :type tag: str
        :param column: The column to search in
        :type column: int
        :param case_sensitive: Flag for case sensitive search
        :type case_sensitive: bool
        :return: List of IfcTreeItem instances
        """
        items = []
        if column == 0:
            column_data = self.label
            if column_data is None:
                column_data = ""
        else:
            column_data = str(self.data(column))
        
        if not case_sensitive:
            column_data = column_data.lower()
            text = text.lower()
        if how == "=":
            if text == column_data:
                items.append(self)
        elif how == "in":
            if text in column_data:
                items.append(self)
        for child in self._children:
            items.extend(child.search(text, column, case_sensitive, how))
        return items
        
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
        return f"TreeItem ({self.label})"

    

class TreeModelBaseclass(QAbstractItemModel):
    """Base class for a tree model, supposed to be subclassed.
    
    On init, the root item is created in setupRootItem() and the model data is 
    set up in setupModelData(). These functions are supposed to be overridden
    in derived classes.

    Most methods are required for the model to work with a QTreeView,
    some may be overwritten in derived classes, e.g. columnCount().

    :param data: The data for the model
    :type data: Any
    :param parent: The parent widget
    """
    def __init__(self, data, parent=None):
        super(TreeModelBaseclass, self).__init__(parent)
        self.column_count = 2
        self.nan = self.tr("<NULL>")

        self.setup_root_item()
        self.setup_model_data(data, self._rootItem)

    def setup_root_item(self):
        """Set up the root item for the model, can be overridden in derived classes"""
        self._rootItem = TreeItem()
       
    def setup_model_data(self, data, parent):
        """Set up the model data, called by init, must be overridden in derived classes"""
        pass

    def get_child_by_label(self, parent, label):
        """Get the child item with a given label (data of first column) if already present, otherwise None"""
        for child in parent.children:
            try:
                childlabel = child.label
            except AttributeError:
                continue
            if childlabel == label:
                return child
        return None
        
    def rowCount(self, parent=QModelIndex()):
        """Get the number of rows (children) for a parent item"""
        if parent.column() > 0:
            return 0
        parentItem = parent.internalPointer() if parent.isValid() else self._rootItem
        return parentItem.child_count()

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

    def headerData(self, section, orientation=Qt.Horizontal, role=Qt.DisplayRole):
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
    
    @property
    def root_item(self):
        """The root item of the model"""
        return self._rootItem

