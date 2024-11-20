from PySide6.QtCore import Qt, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass
import ifcopenshell.util.element



class ColheaderTreeItem(TreeItem):
    """TreeItem for the column headers
    
    Gets the column names from the ColumnsTreeModel.

    :param data: Instance of ColumnsTreeModel
    :type data: ColumnsTreeModel
    :param parent: Parent tree item, defaults to None
    :type parent: TreeItem (or derived class), optional
    """
    def __init__(self, data, parent=None):
        self._columntree = data
        self._parent = parent
        self._children = []

    def data(self, column):
        """Get the column name at the column index
        
        :param column: Column index
        :type column: int
        :return: Column name
        :rtype: str
        """
        if column < 0 or column >= self._columntree.count():
            return None
        return self._columntree.column_name(column)


class IfcTreeItem(TreeItem):
    """TreeItem for the Ifc objects
    
    :param data: IFC entity (e.g. IfcElement) from IfcOpenShell
    :type data: IfcOpenShell entity
    :param parent: Parent tree item, defaults to None
    :type parent: TreeItem (or derived class), optional
    :param columntree: ColumnsTreeModel instance
    :type columntree: ColumnsTreeModel
    :param filename: Filename of the IFC file, defaults to None
    :type filename: str, optional
    """
    def __init__(self, data, parent=None, columntree=None, filename=None):
        self._ifc_item = data
        self._parent = parent
        self._id = self._ifc_item.id()
        self._guid = self._ifc_item.GlobalId
        self._children = []
        self._filenames = []
        self._columntree = columntree

        if filename:
            self._filenames.append(filename)
        

    def data(self, column):
        """Get the data for the column using IfcOpenShell
        
        The info colums are always part of the view, but may be hidden.
        Pset columns are handled dynamically based on the state of the 
        ColumnsTreeModel. The data is read directly from the IfcOpenShell
        entity stored in the item.

        :param column: Column index
        :type column: int
        :return: Data for the column
        :rtype: str or None
        """
        if column < 0 or column >= self._columntree.count():
            return None
        if column == 0:
            # IFC-class and counters
            count_children = self.childCount()
            if count_children > 0:
                count_leaves = self.leavesCount()
                if count_leaves != count_children:
                    return f"{self._ifc_item.is_a()} ({count_children}/{count_leaves})"
                else:
                    return f"{self._ifc_item.is_a()} ({count_children})"
            return self._ifc_item.is_a()
        if column == 1:
            return self._ifc_item.id()
        if column == 2:
            return self._ifc_item.Name
        if column == 3:
            return self._ifc_item.GlobalId
        if column == 4:
            try:
                tag = self._ifc_item.Tag
            except AttributeError:
                tag = None
            return tag
        if column == 5:
            return self._ifc_item.ObjectType
        if column == 6:
            return self._ifc_item.Description
        if column == 7:
            return self.filenames_str
        if column == 8:
            try:
                container = self._ifc_item.ContainedInStructure[0].RelatingStructure.Name
            except (IndexError, AttributeError):
                container = None
            return container
        if column == 9:
            # Validation
            return None
        
        psets = ifcopenshell.util.element.get_psets(self._ifc_item)
        pset_name, attribute = self._columntree.col(column)
        try:
            return psets[pset_name][attribute]
        except KeyError:
            return None

    def add_filename(self, filename):
        """Add a filename to the list of filenames
        
        Used if the object is already present when adding a new IFC file.
        The filename is used to populate the filenames column.

        :param filename: Filename of the IFC file
        :type filename: str
        """
        self._filenames.append(filename)

    # def remove_filename(self, filename):
    #     self._filenames.remove(filename)
    
    def find_item_by_guid(self, guid):
        """Find an item by its GUID
        
        Recursively search the children for an item with the given GUID.

        :param guid: GUID of the item to find
        :type guid: str
        :return: IfcTreeItem instance or None
        """
        if self._guid == guid:
            return self
        for child in self._children:
            result = child.find_item_by_guid(guid)
            if result:
                return result
        return None
    
    def find_item_by_tag(self, tag):
        """Find an item by its tag
        
        Recursively search the children for an item with the given tag.

        :param tag: Tag of the item to find
        :type tag: str
        :return: IfcTreeItem instance or None
        """
        try:
            item_tag = self._ifc_item.Tag
        except AttributeError: # Only IfcElement instances have a tag
            item_tag = None

        if item_tag == tag:
            return self
        for child in self._children:
            result = child.find_item_by_tag(tag)
            if result:
                return result
        return None

    @property
    def filenames(self):
        """List of IFC files containing the object (list of str)"""
        return self._filenames
    
    @property
    def filenames_str(self):
        """String representation of the list of IFC files"""
        return ", ".join(self._filenames)

    @property
    def id(self):
        """IFC ID of the object. If ambiguous: object ID in the first IFC file"""
        return self._id
    
    @property
    def guid(self):
        """Global unique ID (GlobalID) of the object (str)"""
        return self._guid
    
    def __repr__(self):
        return f"IfcTreeItem: {self._ifc_item.is_a()} {self._ifc_item.id()}"



class IfcTreeModelBaseClass(TreeModelBaseclass):
    """Base class for the different IFC tree models
    
    Implements the basic functionality for the tree models, based on TreeModelBaseclass.
    At least the addFile method has to be implemented in the derived classes.

    :param data: Instance if IfcFiles (from bimsemantic), contains references to the IfcFile objects.
    :type data: IfcFiles
    :param parent: Parent widget should be the IfcTreeTab instance
    """
    def __init__(self, data, parent):
        self.tab = parent
        self.columntree = self.tab.mainwindow.column_treeview
        self.first_cols = self.columntree.first_cols
        super(IfcTreeModelBaseClass, self).__init__(data, parent)
        

        #self.columntree.columnsChanged.connect(self.pset_columns_changed)
        self.columntree.hideInfoColumn.connect(self.hide_info_column)

    def setupModelData(self, data, parent):
        """Setup the model data by calling addFile for each IFC file instance"""
        self.ifc_files = data  

        for file in self.ifc_files:
            self.addFile(file)

    def addFile(self, ifc_file):
        """To be implemented in derived classes"""
        pass

    def setupRootItem(self):
        """"Setup the root item of the tree, containing the column headers"""
        self._rootItem = ColheaderTreeItem(self.columntree, parent=None)
        
    def columnCount(self, parent=QModelIndex()):
        """Get the number of columns"""
        return self.columntree.count()
    
    def pset_columns_changed(self):
        """Update the tree view when the pset columns have changed in the ColumnsTreeModel"""
        self.beginResetModel()
        self.layoutChanged.emit()
        self.endResetModel()
        self.tab.tree.expandAll()

    def hide_info_column(self, col_index, ishidden):
        """Toggle visibility of the info columns"""
        self.tab.tree.setColumnHidden(col_index, ishidden)

    def get_child_by_guid(self, parent, guid):
        """Get the child item with a given GUID if already present, otherwise None"""
        for child in parent.children:
            if child.guid == guid:
                return child
        return None

    def get_child_by_label(self, parent, label):
        """Get the child item with a given label (data of first column) if already present, otherwise None"""
        for child in parent.children:
            try:
                childlabel = child.label
            except AttributeError:
                continue
            if child.label == label:
                return child
        return None
    
    def find_index_by_guid(self, guid):
        """Search the tree for an item by its GUID and return the QModelIndex"""
        item = self._rootItem.find_item_by_guid(guid)
        if item:
            return self.createIndex(item.row(), 0, item)
        return QModelIndex()
    
    def find_index_by_tag(self, tag):
        """Search the tree for an item by its tag and return the QModelIndex"""
        item = self._rootItem.find_item_by_tag(tag)
        if item:
            return self.createIndex(item.row(), 0, item)
        return QModelIndex()
    

class LocationTreeModel(IfcTreeModelBaseClass):
    """Model for the Location tree view

    The tree view is organized by the location of elements in the project,
    i.e. IfcProject, IfcSite, IfcBuilding, IfcBuildingStorey, IfcSpace, etc.
    The data of several IFC files can be added to the tree with addFile().

    :param data: Instance if IfcFiles 
    :param parent: Parent widget should be the IfcTreeTab instance
    """

    def addFile(self, ifc_file):
        """Add data of an IfcFile instance to the tree view
        
        If an element with a certain GUID is already present in the tree, 
        the existing item is used (and the filename is added to the list of filenames),
        otherwise a new item is created.
        :param ifc_file: bimsemantic IFC file instance
        :type ifc_file: IfcFile
        """
        self.beginResetModel()

        filename = ifc_file.filename
        project = ifc_file.model.by_type("IfcProject")[0]

        # Check if the project is already in the tree
        project_item = self.get_child_by_guid(self._rootItem, project.GlobalId)
        if project_item:
            project_item.add_filename(filename)
        else:
            project_item = IfcTreeItem(project, self._rootItem, self.columntree, filename)
            self._rootItem.appendChild(project_item)

        for site in ifc_file.model.by_type("IfcSite"):
            self.addItems(site, project_item, filename)

        label = self.tr("Without container")
        notcontained_item = self.get_child_by_label(self._rootItem, label)
        if not notcontained_item:
            notcontained_item = TreeItem([label], self._rootItem)
            self._rootItem.appendChild(notcontained_item)

        # Also add the elements that don't have a spatial container
        for element in ifc_file.model.by_type("IfcElement"):
            if not element.ContainedInStructure:
                element_item = self.get_child_by_guid(notcontained_item, element.GlobalId)
                if element_item:
                    element_item.add_filename(filename)
                else:
                    element_item = IfcTreeItem(element, notcontained_item, self.columntree, filename)
                    notcontained_item.appendChild(element_item)

        self.endResetModel()

        self.tab.proxymodel.sort(0, Qt.SortOrder.AscendingOrder)
        self.tab.tree.expandAll()

    def addItems(self, ifc_object, parent, filename):
        """Helper method for addFile to add items to the tree recursively"""
        # Check if the object is already in the tree
        item = self.get_child_by_guid(parent, ifc_object.GlobalId)
        if item:
            item.add_filename(filename)
        else:
            item = IfcTreeItem(ifc_object, parent, self.columntree, filename)
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
            element_item = self.get_child_by_guid(item, element.GlobalId)
            if element_item:
                element_item.add_filename(filename)
            else:
                element_item = IfcTreeItem(element, item, self.columntree, filename) 
                item.appendChild(element_item)

        for child in children:
            self.addItems(child, item, filename)


    def __repr__(self):
        return "LocationTreeModel"

class TypeTreeModel(IfcTreeModelBaseClass):
    """Model for the Type tree view
    
    The tree view is organized by the IFC-class and object type of elements.
    The data of several IFC files can be added to the tree with addFile().

    :param data: Instance if IfcFiles 
    :param parent: Parent widget should be the IfcTreeTab instance
    """

    def addFile(self, ifc_file):
        """Add data of an IfcFile instance to the tree view
        
        If an element with a certain GUID is already present in the tree, 
        the existing item is used (and the filename is added to the list of filenames),
        otherwise a new item is created.
        :param ifc_file: bimsemantic IFC file instance
        :type ifc_file: IfcFile
        """
        self.beginResetModel()

        filename = ifc_file.filename

        elements = ifc_file.model.by_type("IfcElement")

        for element in elements:
            ifc_class = element.is_a()
            objecttype = element.ObjectType

            class_item = self.get_child_by_label(self._rootItem, ifc_class)
            if not class_item:
                class_item = TreeItem([ifc_class], self._rootItem)
                self._rootItem.appendChild(class_item)

            type_item = self.get_child_by_label(class_item, objecttype)
            if not type_item:
                type_item = TreeItem([objecttype], class_item)
                class_item.appendChild(type_item)
            
            element_item = self.get_child_by_guid(type_item, element.GlobalId)
            if element_item:
                element_item.add_filename(filename)
            else:
                element_item = IfcTreeItem(element, type_item, self.columntree, filename)
                type_item.appendChild(element_item)

        self.endResetModel()

        self.tab.tree.expandAll()

    def __repr__(self):
        return "TypeTreeModel"
        

class FlatTreeModel(IfcTreeModelBaseClass):
    """Model for the Flat tree view
    
    The tree view only has two top level nodes, for IfcElements and IfcElementTypes.
    The data of several IFC files can be added to the tree with addFile().

    :param data: Instance if IfcFiles 
    :param parent: Parent widget should be the IfcTreeTab instance
    """

    def addFile(self, ifc_file):
        """Add data of an IfcFile instance to the tree view
        
        If an element with a certain GUID is already present in the tree, 
        the existing item is used (and the filename is added to the list of filenames),
        otherwise a new item is created.
        :param ifc_file: bimsemantic IFC file instance
        :type ifc_file: IfcFile
        """
        self.beginResetModel()

        filename = ifc_file.filename

        elements = ifc_file.model.by_type("IfcElement")
        element_types = ifc_file.model.by_type("IfcElementType")

        self.elements_item = self.get_child_by_label(self._rootItem, "IfcElement")
        if not self.elements_item:
            self.elements_item = TreeItem(["IfcElement"], self._rootItem, "IfcElement")
            self._rootItem.appendChild(self.elements_item)

        for element in elements:
            element_item = self.get_child_by_guid(self.elements_item, element.GlobalId)
            if element_item:
                element_item.add_filename(filename)
            else:
                element_item = IfcTreeItem(element, self.elements_item, self.columntree, filename)
            self.elements_item.appendChild(element_item)

        types_item = self.get_child_by_label(self._rootItem, "IfcElementType")
        if not types_item:
            types_item = TreeItem(["IfcElementType"], self._rootItem, "IfcElementType")
            self._rootItem.appendChild(types_item)

        for element_type in element_types:
            type_item = self.get_child_by_guid(types_item, element_type.GlobalId)
            if type_item:
                type_item.add_filename(filename)
            else:
                type_item = IfcTreeItem(element_type, types_item, self.columntree, filename)
            types_item.appendChild(type_item)

        self.endResetModel()

        self.tab.tree.expandAll()

    def __repr__(self):
        return "FlatTreeModel"
