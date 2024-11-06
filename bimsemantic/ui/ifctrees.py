from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt, QSortFilterProxyModel
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView, QWidget, QTabWidget, QVBoxLayout
from bimsemantic.ui import TreeItem, TreeModelBaseclass
import ifcopenshell.util.element

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

        self.locationtab = IfcTreeTab(LocationTreeModel(self.ifc), self)
        self.tabs.addTab(self.locationtab, self.tr("Location"))

        self.typetab = IfcTreeTab(TypeTreeModel(self.ifc), self)
        self.tabs.addTab(self.typetab, self.tr("Type"))

        self.create_column_actions(self.locationtab, parent)
        self.parent.statusbar.clearMessage()

    def create_column_actions(self, tab, mainwindow):
        tree = tab.tree
        header = tree.header()
        for column in range(1, header.count()):
            column_name = header.model().headerData(column, Qt.Horizontal)
            action = QAction(column_name, self, checkable=True, checked=True)
            action.triggered.connect(lambda checked, col=column: self.toggle_column_visibility(col, checked))
            mainwindow._view_cols_menu.addAction(action)   
            mainwindow.column_actions.append(action)     

    def toggle_column_visibility(self, column, visible):
        self.locationtab.tree.setColumnHidden(column, not visible)
        self.typetab.tree.setColumnHidden(column, not visible)

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
    def setupRootItem(self, data):
        self.column_names = ["Type", "ID", "Name", "Guid"] + data.get_pset_cols()
        self._rootItem = TreeItem(self.column_names)
        self.column_count = len(self.column_names)

    def newItem(self, ifc_item, parent):
        psets = ifcopenshell.util.element.get_psets(ifc_item)
        pset_values = []
        for pset_name, pset_prop in self.ifc.pset_items():
            try:
                pset_values.append(psets[pset_name][pset_prop])
            except KeyError:
                pset_values.append(None)

        data = [ifc_item.is_a(), ifc_item.id(), ifc_item.Name, ifc_item.GlobalId] + pset_values

        item = TreeItem(
            data,
            ifc_item.id(),
            parent,
        )
        return item


class LocationTreeModel(IfcTreeModelBaseClass):
    def setupModelData(self, data, parent):
        self.ifc = data  # ifcopenshell ifc model

        project = self.ifc.model.by_type("IfcProject")[0]
        project_item = self.newItem(project, parent)
        parent.appendChild(project_item)

        for site in self.ifc.model.by_type("IfcSite"):
            self.addItems(site, project_item)

    def addItems(self, ifc_object, parent):
        item = self.newItem(ifc_object, parent)
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
            element_item = self.newItem(element, item)
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
            if not element.ObjectType in modeldict[ifc_class]:
                modeldict[ifc_class][element.ObjectType] = []
            modeldict[ifc_class][element.ObjectType].append(element)

        for ifc_class, types in modeldict.items():
            class_item = TreeItem([ifc_class], "class:" + ifc_class, parent)
            parent.appendChild(class_item)

            for objecttype, elements in types.items():
                objecttype_item = TreeItem([objecttype], "type:" + objecttype, class_item)
                class_item.appendChild(objecttype_item)
                for element in elements:
                    element_item = self.newItem(element, objecttype_item)
                    objecttype_item.appendChild(element_item)


