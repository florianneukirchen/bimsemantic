from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt, QSortFilterProxyModel
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView, QWidget, QTabWidget, QVBoxLayout, QTreeWidgetItem
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
    def __init__(self, data, parent=None, columntree=None):
        self._ifc_item = data
        self._parent = parent
        self._id = self._ifc_item.id()
        self._children = []
        self._columntree = columntree

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
        
        psets = ifcopenshell.util.element.get_psets(self._ifc_item)
        pset_name, attribute = self._columntree.col(column)
        try:
            return psets[pset_name][attribute]
        except KeyError:
            return None


class IfcTabs(QWidget):
    def __init__(self, ifc_file, parent):
        super(IfcTabs, self).__init__(parent)
        self.ifc = ifc_file

        self.mainwindow = parent
        self.layout = QVBoxLayout(self)

        self.mainwindow.statusbar.showMessage(self.tr("Creating treeviews"))

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.West)
        self.tabs.setMovable(True)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.locationtab = IfcTreeTab(LocationTreeModel, self.ifc, self)
        self.tabs.addTab(self.locationtab, self.tr("Location"))

        self.typetab = IfcTreeTab(TypeTreeModel, self.ifc, self) 
        self.tabs.addTab(self.typetab, self.tr("Type"))

        self.flattab = IfcTreeTab(FlatTreeModel, self.ifc, self) 
        self.tabs.addTab(self.flattab, self.tr("Flat"))

        self.mainwindow.statusbar.clearMessage()






class IfcTreeTab(QWidget):
    def __init__(self, treemodelclass, ifc, parent):
        super(IfcTreeTab, self).__init__(parent)
        self._parent = parent
        self.mainwindow = self._parent.parent()
        self.treemodel = treemodelclass(ifc, self)
        self.ifc = ifc
        self.layout = QVBoxLayout(self)

        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.treemodel)
        self.tree = QTreeView()
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(2, 250)
        # self.tree.setColumnHidden(1, True)
        self.tree.expandAll()
        self.tree.clicked.connect(self.on_treeview_clicked)
        self.setLayout(self.layout)
        self.layout.addWidget(self.tree)
        

    def on_treeview_clicked(self, index):
        if not index.isValid():
            print("Invalid index")
            return
        source_index = self.proxymodel.mapToSource(index)
        item = source_index.internalPointer()
        if isinstance(item, TreeItem):
            element = self.ifc.model.by_id(item.id)
            self.mainwindow.show_details(element)




class IfcTreeModelBaseClass(TreeModelBaseclass):
    def __init__(self, data, parent):
        mainwindow = parent.mainwindow
        self.columntree = mainwindow.column_treeview
        self.first_cols = self.columntree.first_cols
        super(IfcTreeModelBaseClass, self).__init__(data, parent)
        self._parent = parent

        self.columntree.columnsChanged.connect(self.pset_columns_changed)


    def setupRootItem(self):
        self._rootItem = ColheaderTreeItem(self.columntree, parent=None)
        
    def columnCount(self, parent=QModelIndex()):
        return self.columntree.count()
    
    def pset_columns_changed(self):
        
        self.beginResetModel()
        self.layoutChanged.emit()
        self.endResetModel()
        self._parent.tree.expandAll()




class LocationTreeModel(IfcTreeModelBaseClass):


    def setupModelData(self, data, parent):
        self.ifc = data  # ifcopenshell ifc model

        project = self.ifc.model.by_type("IfcProject")[0]
        project_item = IfcTreeItem(project, parent, self.columntree)

        parent.appendChild(project_item)

        for site in self.ifc.model.by_type("IfcSite"):
            self.addItems(site, project_item)

    def addItems(self, ifc_object, parent):
        item = IfcTreeItem(ifc_object, parent, self.columntree)
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
            element_item = IfcTreeItem(element, item, self.columntree) 
            item.appendChild(element_item)

        for child in children:
            self.addItems(child, item)

class TypeTreeModel(IfcTreeModelBaseClass):
    def setupModelData(self, data, parent):
        self.ifc = data  # ifcopenshell ifc model

        modeldict = {}
        elements = self.ifc.model.by_type("IfcElement")

        for element in elements:
            ifc_class = element.is_a()
            if not ifc_class in modeldict:
                modeldict[ifc_class] = {}
            objecttype = element.ObjectType
            if objecttype is None:
                objecttype = "None"
            if not objecttype in modeldict[ifc_class]:
                modeldict[ifc_class][objecttype] = []
            modeldict[ifc_class][objecttype].append(element)

        for ifc_class, types in modeldict.items():
            class_item = TreeItem([ifc_class], parent, "class:" + ifc_class)
            parent.appendChild(class_item)

            for objecttype, elements in types.items():
                objecttype_item = TreeItem([objecttype], class_item, "type:" + objecttype)
                class_item.appendChild(objecttype_item)
                for element in elements:
                    element_item = IfcTreeItem(element, objecttype_item, self.columntree)
                    objecttype_item.appendChild(element_item)


class FlatTreeModel(IfcTreeModelBaseClass):
    def setupModelData(self, data, parent):
        self.ifc = data  # ifcopenshell ifc model

        elements = self.ifc.model.by_type("IfcElement")

        elements_item = TreeItem(["Elements"], parent, "Elements")
        parent.appendChild(elements_item)

        for element in elements:
            element_item = IfcTreeItem(element, elements_item, self.columntree)
            elements_item.appendChild(element_item)

        types_item = TreeItem(["Types"], parent, "Types")
        parent.appendChild(types_item)

        element_types = self.ifc.model.by_type("IfcElementType")


        for element_type in element_types:
            type_item = IfcTreeItem(element_type, types_item, self.columntree)
            types_item.appendChild(type_item)