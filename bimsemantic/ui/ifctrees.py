from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, QTimer, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QTreeView, QWidget, QTabWidget, QVBoxLayout
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
            return self.filenames_str
        
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

class IfcTabs(QWidget):
    """Widget containig the tabs for the different tree views
    
    Includes functionality to work with the different tree views.

    :param parent: Parent widget should be the main window.
    """
    def __init__(self, parent):
        super(IfcTabs, self).__init__(parent)
        self.ifcfiles = parent.ifcfiles
        self.remaining_models = None

        self.mainwindow = parent
        self.timer = QTimer()

        self.layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.West)
        self.tabs.setMovable(True)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.locationtab = IfcTreeTab(LocationTreeModel, self.ifcfiles, self)
        self.tabs.addTab(self.locationtab, self.tr("Location"))

        self.typetab = IfcTreeTab(TypeTreeModel, self.ifcfiles, self) 
        self.tabs.addTab(self.typetab, self.tr("Type"))

        self.flattab = IfcTreeTab(FlatTreeModel, self.ifcfiles, self) 
        self.tabs.addTab(self.flattab, self.tr("Flat"))

        self.mainwindow.column_treeview.columnsChanged.connect(self.update_columns)


    def addFile(self, ifc_file):
        """Add data of an IFC file to the tree views
        
        :param ifc_file: bimsemantic IFC file instance
        :type ifc_file: IfcFile
        """
        self.locationtab.treemodel.addFile(ifc_file)
        self.typetab.treemodel.addFile(ifc_file)
        self.flattab.treemodel.addFile(ifc_file)

    def update_columns(self):
        """Update the columns in all tree views
        
        Called when the columns in the ColumnsTreeModel have changed.
        The active column is updated immediately, updating the other tree views
        is triggered by a timer to keep the GUI responsive. 
        """

        active_tab = self.tabs.currentWidget()

        active_tab.treemodel.pset_columns_changed()

        self.remaining_models = [self.tabs.widget(i).treemodel for i in range(self.tabs.count())]
        self.remaining_models.remove(active_tab.treemodel)

        self.mainwindow.progressbar.setRange(0, self.tabs.count())
        self.mainwindow.progressbar.setValue(1)
        
        self.timer.timeout.connect(self.update_next_model)
        self.timer.start(200)


    def update_next_model(self):
        """Update the next tree view, triggered by the timer in update_columns"""   
        if self.remaining_models:
            model = self.remaining_models.pop(0)
            model.pset_columns_changed()
            self.mainwindow.progressbar.setValue(self.mainwindow.progressbar.value() + 1)
        else:
            self.timer.stop()
            self.mainwindow.statusbar.clearMessage()
            self.mainwindow.progressbar.reset()

    def select_item_by_guid(self, guid):
        """Select an item by its GUID in all tree views
        
        Returns the number of tabs where the item with the given GUID was found.
        """
        counter = 0
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            found = tab.select_item_by_guid(guid)
            if found:
                counter += 1
        return counter

    def select_item_by_tag(self, tag):
        """Select an item by its tag in all tree views
        
        Returns the number of tabs where the item with the given tag was found.
        """
        counter = 0
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            found = tab.select_item_by_tag(tag)
            if found:
                counter += 1
        return counter

    def count_ifc_elements(self):
        """Get the number of all IFC elements of the open files"""
        return self.flattab.treemodel.elements_item.childCount()
    
    def count_ifc_types(self):
        """Get the number of all IFC element types of the open files"""
        return self.typetab.treemodel._rootItem.childCount()


class IfcTreeTab(QWidget):
    """Class for the tabs with different IFC tree views
    
    The data model class is passed as an argument to the constructor.
    
    :param treemodelclass: Class of the data model, derived from IfcTreeModelBaseClass
    :param ifc_files: Instance of IfcFiles 
    :param parent: Parent widget should be the IfcTabs instance
    """
    def __init__(self, treemodelclass, ifc_files, parent):
        super(IfcTreeTab, self).__init__(parent)
        self.mainwindow = parent.mainwindow
        self.tabs = parent.tabs
        self.treemodel = treemodelclass(ifc_files, self)
        self.ifc_files = ifc_files
        self.layout = QVBoxLayout(self)

        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.treemodel)
        self.tree = QTreeView()
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)

        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(2, 250)
        
        for column in self.treemodel.columntree.hidden_info_columns():
            self.tree.setColumnHidden(column, True)
        
        self.tree.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.setLayout(self.layout)
        self.layout.addWidget(self.tree)
        

    def on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        """Slot for the selectionChanged signal of the QTreeView
        
        If the selection on the active tab changes, the details view is updated
        and the selection of the other tabs is synchronized.
        """
        if not self.is_active_tab():
            return

        indexes = selected.indexes()
        if not indexes:
            self.mainwindow.show_details()
            print("n")
        
        index = indexes[0]
        source_index = self.proxymodel.mapToSource(index)
        item = source_index.internalPointer()
    
        if isinstance(item, IfcTreeItem):
            print(item)
            self.mainwindow.show_details(item.id, item.filenames)
            guid = item.guid
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if tab != self:
                    tab.select_item_by_guid(guid)
        else:
            # TreeItem
            print(item)


    def select_item_by_guid(self, guid):
        """Select an item by its GUID
        
        Select the item in the tree view and scroll to it.
        If the item is found, return True, otherwise False.
        """
        index = self.treemodel.find_index_by_guid(guid)
        if index.isValid():
            proxy_index = self.proxymodel.mapFromSource(index)
            self.tree.setCurrentIndex(proxy_index)
            self.tree.scrollTo(proxy_index)
            return True
        return False
    
    def select_item_by_tag(self, tag):
        """Select an item by its tag
        
        Select the item in the tree view and scroll to it.
        If the item is found, return True, otherwise False.
        """
        index = self.treemodel.find_index_by_tag(tag)
        if index.isValid():
            proxy_index = self.proxymodel.mapFromSource(index)
            self.tree.setCurrentIndex(proxy_index)
            self.tree.scrollTo(proxy_index)
            return True
        return False

    def is_active_tab(self):
        """Check if the tab is the active tab, returns bool"""
        return self.tabs.currentWidget() == self


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
            if child._data[0] == label:
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

        self.endResetModel()
        
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
