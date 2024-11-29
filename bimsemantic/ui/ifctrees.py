from PySide6.QtCore import Qt, QModelIndex
from bimsemantic.ui import (
    TreeItem,
    TreeModelBaseclass,
    CustomTreeMaker,
    CustomFieldType,
)
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
        self._id = None

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

    @property
    def label(self):
        """For compatibility with search of the TreeItem class"""
        return ""


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
        if self._ifc_item.is_a("IfcElementType"):
            linked_object_type = None
        else:
            linked_object_type = ifcopenshell.util.element.get_type(self._ifc_item)
        if linked_object_type:
            self._linked_type_name = linked_object_type.Name
            if self._linked_type_name is None:
                self._linked_type_name = self.tr("Unnamed")
        else:
            self._linked_type_name = None

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
            count_children = self.child_count()
            if count_children > 0:
                count_leaves = self.leaves_count()
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
            try:
                return self._ifc_item.ObjectType
            except AttributeError:
                return None
        if column == 6:
            return self._linked_type_name
        if column == 7:
            return self._ifc_item.Description
        if column == 8:
            return self.filenames_str
        if column == 9:
            try:
                container = self._ifc_item.ContainedInStructure[
                    0
                ].RelatingStructure.Name
            except (IndexError, AttributeError):
                container = None
            return container
        if column == 10:
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
        except AttributeError:  # Only IfcElement instances have a tag
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

    @property
    def ifc(self):
        """IFC entity instance from IfcOpenShell"""
        return self._ifc_item

    @property
    def label(self):
        """First column without counter"""
        return self._ifc_item.is_a()

    def __repr__(self):
        return f"IfcTreeItem: {self._ifc_item.is_a()} {self._ifc_item.id()}"


class IfcTreeModelBaseClass(TreeModelBaseclass):
    """Base class for the different IFC tree models

    Implements the basic functionality for the tree models, based on TreeModelBaseclass.
    At least the add_file method has to be implemented in the derived classes.

    :param data: Instance if IfcFiles (from bimsemantic), contains references to the IfcFile objects.
    :type data: IfcFiles
    :param parent: Parent widget should be the IfcTreeTab instance
    """

    def __init__(self, data, parent):
        self.tab = parent
        self.columntree = self.tab.mainwindow.column_treemodel
        self.first_cols = self.columntree.first_cols
        super(IfcTreeModelBaseClass, self).__init__(data, parent)

        # self.columntree.columnsChanged.connect(self.pset_columns_changed)
        self.columntree.hideInfoColumn.connect(self.hide_info_column)

    def setup_model_data(self, data, parent):
        """Called by init: setup the model data"""
        self.ifc_files = data

        for file in self.ifc_files:
            self.add_file(file)

    def add_file(self, ifc_file):
        """To be implemented in derived classes"""
        pass

    def setup_root_item(self):
        """ "Setup the root item of the tree, containing the column headers"""
        self._rootItem = ColheaderTreeItem(self.columntree, parent=None)

    def columnCount(self, parent=QModelIndex()):
        """Get the number of columns"""
        return self.columntree.count()

    def pset_columns_changed(self):
        """Update the tree view when the pset columns have changed in the ColumnsTreeModel"""
        self.beginResetModel()
        self.layoutChanged.emit()
        self.endResetModel()
        self.expand_default()

    def expand_default(self):
        """Called when the tree view is updated to expand the tree

        If not overwritten in derived classes, expand all levels
        """
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
    The data of several IFC files can be added to the tree with add_file().

    :param data: Instance if IfcFiles
    :param parent: Parent widget should be the IfcTreeTab instance
    """

    def add_file(self, ifc_file):
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
            project_item = IfcTreeItem(
                project, self._rootItem, self.columntree, filename
            )
            self._rootItem.appendChild(project_item)

        for site in ifc_file.model.by_type("IfcSite"):
            self.add_items(site, project_item, filename)

        self.notcontainedlabel = self.tr("Container is %s") % self.nan
        notcontained_item = self.get_child_by_label(
            self._rootItem, self.notcontainedlabel
        )
        if not notcontained_item:
            notcontained_item = TreeItem([self.notcontainedlabel], self._rootItem)
            self._rootItem.appendChild(notcontained_item)

        # Also add the elements that don't have a spatial container
        for element in ifc_file.model.by_type("IfcElement"):
            if not element.ContainedInStructure:
                element_item = self.get_child_by_guid(
                    notcontained_item, element.GlobalId
                )
                if element_item:
                    element_item.add_filename(filename)
                else:
                    element_item = IfcTreeItem(
                        element, notcontained_item, self.columntree, filename
                    )
                    notcontained_item.appendChild(element_item)

        self.endResetModel()

        self.tab.proxymodel.sort(0, Qt.SortOrder.AscendingOrder)
        self.expand_default()

    def add_items(self, ifc_object, parent, filename):
        """Helper method for add_file to add items to the tree recursively"""
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
            self.add_items(child, item, filename)

    def expand_default(self):
        """Called when the tree view is updated to expand the tree

        If not overwritten in derived classes, expand all levels
        """
        self.tab.tree.expandAll()
        notcontained_item = self.get_child_by_label(
            self._rootItem, self.notcontainedlabel
        )
        if notcontained_item:
            source_index = self.index(notcontained_item.row(), 0, QModelIndex())
            proxy_index = self.tab.proxymodel.mapFromSource(source_index)
            self.tab.tree.collapse(proxy_index)

    def __repr__(self):
        return "LocationTreeModel"


class TypeTreeModel(IfcTreeModelBaseClass):
    """Model for the Type tree view

    The tree view is organized by the IFC-class and object type of elements.
    The data of several IFC files can be added to the tree with add_file().

    :param data: Instance if IfcFiles
    :param parent: Parent widget should be the IfcTreeTab instance
    """

    def add_file(self, ifc_file):
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
                element_item = IfcTreeItem(
                    element, type_item, self.columntree, filename
                )
                type_item.appendChild(element_item)

        self.endResetModel()

        self.expand_default()

    def expand_default(self):
        self.tab.tree.expandToDepth(0)

    def __repr__(self):
        return "TypeTreeModel"


class FlatTreeModel(IfcTreeModelBaseClass):
    """Model for the Flat tree view

    The tree view has top level nodes for IfcElements, IfcElementTypes,
    and IfcSpatialElemements.
    The data of several IFC files can be added to the tree with add_file().

    :param data: Instance if IfcFiles
    :param parent: Parent widget should be the IfcTreeTab instance
    """

    def setup_root_item(self):
        """ "Setup the root item and top level nodes of the tree"""
        self._rootItem = ColheaderTreeItem(self.columntree, parent=None)

        self.elements_item = TreeItem(["IfcElement"], self._rootItem, "IfcElement")
        self._rootItem.appendChild(self.elements_item)

        self.types_item = TreeItem(["IfcElementType"], self._rootItem, "IfcElementType")
        self._rootItem.appendChild(self.types_item)

        self.spatialelements_item = TreeItem(
            ["IfcSpatialElement"], self._rootItem, "IfcSpatialElement"
        )
        self._rootItem.appendChild(self.spatialelements_item)

    def add_file(self, ifc_file):
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
            element_item = self.get_child_by_guid(self.elements_item, element.GlobalId)
            if element_item:
                element_item.add_filename(filename)
            else:
                element_item = IfcTreeItem(
                    element, self.elements_item, self.columntree, filename
                )
                self.elements_item.appendChild(element_item)

        element_types = ifc_file.model.by_type("IfcElementType")

        for element_type in element_types:
            type_item = self.get_child_by_guid(self.types_item, element_type.GlobalId)
            if type_item:
                type_item.add_filename(filename)
            else:
                type_item = IfcTreeItem(
                    element_type, self.types_item, self.columntree, filename
                )
                self.types_item.appendChild(type_item)

        if ifc_file.model.schema_version[0] == 2:
            spatialelements = ifc_file.model.by_type("IfcSpatialStructureElement")
            self.spatialelements_item.set_data(0, "IfcSpatialStructureElement")
        elif ifc_file.model.schema_version[0] >= 4:
            spatialelements = ifc_file.model.by_type("IfcSpatialElement")
        else:
            spatialelements = []

        for spatialelement in spatialelements:
            spatial_item = self.get_child_by_guid(
                self.spatialelements_item, spatialelement.GlobalId
            )
            if spatial_item:
                spatial_item.add_filename(filename)
            else:
                spatial_item = IfcTreeItem(
                    spatialelement, self.spatialelements_item, self.columntree, filename
                )
                self.spatialelements_item.appendChild(spatial_item)

        self.endResetModel()

    def expand_default(self):
        """Do not expand the treeview in this case"""
        pass

    def __repr__(self):
        return "FlatTreeModel"


class IfcCustomTreeModel(IfcTreeModelBaseClass):
    """Model for the Custom tree view

    The tree view is organized by the custom fields specified as a list of
    CustomTreeMaker instances. After init, the data must be added to the tree
    with add_file().

    :param data: Instance if IfcFiles
    :param parent: Parent widget should be the IfcTreeTab instance
    :param customfields: List of instances of CustomTreeMaker
    """

    def __init__(self, data, parent):
        self.name = self.tr("Custom")
        self._customfields = []
        super(IfcCustomTreeModel, self).__init__(data, parent)

    def set_custom_fields(self, customfields):
        """Set the custom fields for the tree view

        :param customfields: List of instances of CustomTreeMaker
        """
        if not isinstance(customfields, list):
            raise ValueError("Customfields must be a list of CustomTreeMaker instances")
        for customfield in customfields:
            if not isinstance(customfield, CustomTreeMaker):
                raise ValueError(
                    "Customfields must be a list of CustomTreeMaker instances"
                )
        self._customfields = customfields

    def get_custom_fields(self):
        """Get the custom fields"""
        return self._customfields

    def add_file(self, ifc_file):
        """Add data of an IfcFile instance to the tree view

        If an element with a certain GUID is already present in the tree,
        the existing item is used (and the filename is added to the list of filenames),
        otherwise a new item is created.
        :param ifc_file: bimsemantic IFC file instance
        :type ifc_file: IfcFile
        """
        if not self._customfields:
            # This happens because add_file() is called on init but
            # set_custom_fields() must be called first
            return

        self.beginResetModel()

        filename = ifc_file.filename

        elements = ifc_file.model.by_type("IfcElement")

        for element in elements:
            parent_item = self._rootItem
            for customfield in self._customfields:
                if customfield.fieldtype == CustomFieldType.IFCCLASS:
                    data = element.is_a()
                elif customfield.fieldtype == CustomFieldType.OBJECTTYPE:
                    data = element.ObjectType
                    if not data:
                        data = self.nan

                elif customfield.fieldtype == CustomFieldType.LINKEDOBJECTTYPE:
                    linked_type = ifcopenshell.util.element.get_type(element)
                    if linked_type:
                        data = linked_type.Name
                        if data is None:
                            data = self.tr("Unnamed")
                    else:
                        data = self.nan
                elif customfield.fieldtype == CustomFieldType.PSET:
                    psets = ifcopenshell.util.element.get_psets(element)
                    try:
                        data = psets[customfield.keys[0]][customfield.keys[1]]
                    except KeyError:
                        data = self.nan
                elif customfield.fieldtype == CustomFieldType.FILENAME:
                    data = filename
                elif customfield.fieldtype == CustomFieldType.CONTAINEDIN:
                    try:
                        container = element.ContainedInStructure[0].RelatingStructure
                        data = f"{container.is_a()} {container.Name}"
                    except (IndexError, AttributeError):
                        data = self.nan
                else:
                    raise ValueError("Invalid field type")

                customfield_item = self.get_child_by_label(parent_item, data)
                if not customfield_item:
                    customfield_item = TreeItem([data], parent_item)
                    parent_item.appendChild(customfield_item)

                parent_item = customfield_item

            item = self.get_child_by_guid(parent_item, element.GlobalId)
            if item:
                item.add_filename(filename)
            else:
                item = IfcTreeItem(element, parent_item, self.columntree, filename)
                parent_item.appendChild(item)

        self.endResetModel()

        self.expand_default()

    def __repr__(self):
        return f"CustomTreeModel {self.name}"
