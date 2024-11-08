from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt, QSortFilterProxyModel
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView, QWidget, QTabWidget, QVBoxLayout
from bimsemantic.ui import TreeItem, TreeModelBaseclass
import ifcopenshell.util.element


class PsetColumns:
    def __init__(self):
        self._columns = []

    def add_column(self, pset_name, attribute):
        self._columns.append((pset_name, attribute))
        print(self._columns)
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
        if column < 0 or column >= (self._pset_columns.count() + self._count_first_cols):
            return None
        if column < self._count_first_cols:
            return self._first_cols[column]
        return self._pset_columns.column_name(column - self._count_first_cols)


class IfcTreeItem(TreeItem):
    def __init__(self, data, parent=None, pset_columns=None):
        self._ifc_item = data
        self._parent = parent
        self._id = self._ifc_item.id()
        self._children = []
        self._pset_columns = pset_columns

    def data(self, column):
        if column < 0 or column >= self._pset_columns.count() + 4:
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


class IfcTabs(QWidget):
    def __init__(self, ifc_file, parent):
        super(IfcTabs, self).__init__(parent)
        self.ifc = ifc_file

        self.parent = parent
        self.layout = QVBoxLayout(self)

        self.parent.statusbar.showMessage(self.tr("Creating treeviews"))

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.West)
        self.tabs.setMovable(True)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.pset_columns = PsetColumns()

        # Add col
        print("Add col")
        pset_info = self.ifc.pset_info
        pset = list(pset_info)[0]
        attr = pset_info[pset][0]
        self.pset_columns.add_column(pset, attr)
        # #################

        self.locationtab = IfcTreeTab(LocationTreeModel(self.ifc, self.pset_columns), self)
        self.tabs.addTab(self.locationtab, self.tr("Location"))

        # self.typetab = IfcTreeTab(TypeTreeModel(self.ifc, self.pset_columns), self)
        # self.tabs.addTab(self.typetab, self.tr("Type"))

        # self.flattab = IfcTreeTab(FlatTreeModel(self.ifc, self.pset_columns), self)
        # self.tabs.addTab(self.flattab, self.tr("Flat"))

        # Add hide/show columns actions
        # self.create_column_actions(self.locationtab, parent)
        self.parent.statusbar.clearMessage()



    # def create_column_actions(self, tab, mainwindow):
    #     tree = tab.tree
    #     header = tree.header()
    #     for column in range(1, header.count()):
    #         column_name = header.model().headerData(column, Qt.Horizontal)
    #         action = QAction(column_name, self, checkable=True, checked=True)
    #         action.triggered.connect(lambda checked, col=column: self.toggle_column_visibility(col, checked))
    #         mainwindow._view_cols_menu.addAction(action)   
    #         mainwindow.column_actions.append(action)     

    # def toggle_column_visibility(self, column, visible):
    #     self.locationtab.tree.setColumnHidden(column, not visible)
    #     self.typetab.tree.setColumnHidden(column, not visible)


class IfcTreeTab(QWidget):
    def __init__(self, treemodel, parent):
        super(IfcTreeTab, self).__init__(parent)
        self.parent = parent
        self.mainwindow = parent.parent
        self.model = treemodel
        self.ifc = treemodel.ifc
        self.layout = QVBoxLayout(self)

        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.model)
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
            element_id = item.id
            ifc_element = self.ifc.model.by_id(element_id)
            self.mainwindow.show_details(ifc_element)


class IfcTreeModelBaseClass(TreeModelBaseclass):
    def __init__(self, data, pset_columns, parent=None):
        self.pset_columns = pset_columns
        self.first_cols = ["Type", "ID", "Name", "GUID"]
        super(IfcTreeModelBaseClass, self).__init__(data, parent)
        print("Init done")

    def setupRootItem(self):
        self._rootItem = ColheaderTreeItem(self.pset_columns, parent=None, first_cols=self.first_cols)
        
    def columnCount(self, parent=QModelIndex()):
        return len(self.first_cols) + self.pset_columns.count()


class LocationTreeModel(IfcTreeModelBaseClass):


    def setupModelData(self, data, parent):
        print("setupModelData")
        self.ifc = data  # ifcopenshell ifc model

        project = self.ifc.model.by_type("IfcProject")[0]
        project_item = IfcTreeItem(project, parent, self.pset_columns)
        print(project_item)
        parent.appendChild(project_item)

        for site in self.ifc.model.by_type("IfcSite"):
            self.addItems(site, project_item)

    def addItems(self, ifc_object, parent):
        item = IfcTreeItem(ifc_object, parent, self.pset_columns)
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
            element_item = IfcTreeItem(element, item, self.pset_columns) 
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
                    element_item = IfcTreeItem(element, objecttype_item, self.pset_columns)
                    objecttype_item.appendChild(element_item)


class FlatTreeModel(IfcTreeModelBaseClass):
    def setupModelData(self, data, parent):
        self.ifc = data  # ifcopenshell ifc model

        elements = self.ifc.model.by_type("IfcElement")

        elements_item = TreeItem(["Elements"], parent, "Elements")
        parent.appendChild(elements_item)

        for element in elements:
            element_item = IfcTreeItem(element, elements_item, self.pset_columns)
            elements_item.appendChild(element_item)

        types_item = TreeItem(["Types"], parent, "Types")
        parent.appendChild(types_item)

        element_types = self.ifc.model.by_type("IfcElementType")


        for element_type in element_types:
            type_item = IfcTreeItem(element_type, types_item, self.pset_columns)
            types_item.appendChild(type_item)