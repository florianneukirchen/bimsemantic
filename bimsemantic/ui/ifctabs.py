from PySide6.QtCore import QSortFilterProxyModel, QTimer, QItemSelection
from PySide6.QtWidgets import QTreeView, QWidget, QTabWidget, QVBoxLayout
from bimsemantic.ui import LocationTreeModel, TypeTreeModel, FlatTreeModel, IfcTreeItem

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