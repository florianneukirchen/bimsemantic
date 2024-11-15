from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, QTimer, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QTreeView, QWidget, QTabWidget, QVBoxLayout
from bimsemantic.ui import TreeItem, TreeModelBaseclass
import ifcopenshell.util.element



class ColheaderTreeItem(TreeItem):
    def __init__(self, data, parent=None):
        self._columntree = data
        self._parent = parent
        self._children = []

    def data(self, column):
        if column < 0 or column >= self._columntree.count():
            return None
        return self._columntree.column_name(column)


class IfcTreeItem(TreeItem):
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
        if column < 0 or column >= self._columntree.count():
            return None
        if column == 0:
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
        self._filenames.append(filename)

    def remove_filename(self, filename):
        self._filenames.remove(filename)
        
    @property
    def filenames(self):
        return self._filenames
    
    @property
    def filenames_str(self):
        return ", ".join(self._filenames)

    @property
    def id(self):
        return self._id
    
    @property
    def guid(self):
        return self._guid
    
    def __repr__(self):
        return f"IfcTreeItem: {self._ifc_item.is_a()} {self._ifc_item.id()}"

class IfcTabs(QWidget):
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
        self.locationtab.treemodel.addFile(ifc_file)
        self.typetab.treemodel.addFile(ifc_file)
        self.flattab.treemodel.addFile(ifc_file)

    def update_columns(self):

        active_tab = self.tabs.currentWidget()

        active_tab.treemodel.pset_columns_changed()

        self.remaining_models = [self.tabs.widget(i).treemodel for i in range(self.tabs.count())]
        self.remaining_models.remove(active_tab.treemodel)

        self.mainwindow.progressbar.setRange(0, self.tabs.count())
        self.mainwindow.progressbar.setValue(1)
        
        self.timer.timeout.connect(self.update_next_model)
        self.timer.start(200)


    def update_next_model(self):
        if self.remaining_models:
            model = self.remaining_models.pop(0)
            model.pset_columns_changed()
            self.mainwindow.progressbar.setValue(self.mainwindow.progressbar.value() + 1)
        else:
            self.timer.stop()
            self.mainwindow.statusbar.clearMessage()
            self.mainwindow.progressbar.reset()

    def count_ifc_elements(self):
        return self.flattab.treemodel.elements_item.childCount()
    
    def count_ifc_types(self):
        return self.typetab.treemodel._rootItem.childCount()


class IfcTreeTab(QWidget):
    def __init__(self, treemodelclass, ifc_files, parent):
        super(IfcTreeTab, self).__init__(parent)
        self.mainwindow = parent.mainwindow
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
        indexes = selected.indexes()
        if not indexes:
            self.mainwindow.show_details()
        
        index = indexes[0]
        source_index = self.proxymodel.mapToSource(index)
        item = source_index.internalPointer()
    
        if isinstance(item, IfcTreeItem):
            self.mainwindow.show_details(item.id, item.filenames)
        else:
            # TreeItem
            print(item)




class IfcTreeModelBaseClass(TreeModelBaseclass):
    def __init__(self, data, parent):
        self.tab = parent
        self.columntree = self.tab.mainwindow.column_treeview
        self.first_cols = self.columntree.first_cols
        super(IfcTreeModelBaseClass, self).__init__(data, parent)
        

        #self.columntree.columnsChanged.connect(self.pset_columns_changed)
        self.columntree.hideInfoColumn.connect(self.hide_info_column)

    def setupModelData(self, data, parent):
        self.ifc_files = data  

        for file in self.ifc_files:
            self.addFile(file)

    def addFile(self, ifc_file):
        pass

    def setupRootItem(self):
        self._rootItem = ColheaderTreeItem(self.columntree, parent=None)
        
    def columnCount(self, parent=QModelIndex()):
        return self.columntree.count()
    
    def pset_columns_changed(self):
        self.beginResetModel()
        self.layoutChanged.emit()
        self.endResetModel()
        self.tab.tree.expandAll()

    def hide_info_column(self, col_index, ishidden):
        self.tab.tree.setColumnHidden(col_index, ishidden)

    def get_child_by_guid(self, parent, guid):
        for child in parent.children:
            if child.guid == guid:
                return child
        return None

    def get_child_by_label(self, parent, label):
        for child in parent.children:
            if child.data(0) == label:
                return child
        return None

class LocationTreeModel(IfcTreeModelBaseClass):


    def addFile(self, ifc_file):
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




    def addFile(self, ifc_file):
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


    def addFile(self, ifc_file):
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
