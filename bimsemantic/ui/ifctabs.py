from PySide6.QtCore import QSortFilterProxyModel, QTimer, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QTreeView, QAbstractItemView, QWidget, QTabWidget, QTabBar, QVBoxLayout, QPushButton, QStyle
from bimsemantic.ui import LocationTreeModel, TypeTreeModel, FlatTreeModel, IfcTreeItem, CustomFieldType, CustomTreeMaker, IfcCustomTreeModel


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

        self.customtabs = []

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
        for tab in self.customtabs:
            tab.treemodel.addFile(ifc_file)

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

    def make_custom_tab(self, name, custom_fields):
        """Create a custom tab with
        
        The hierarchy of the tree view is defined by the custom_fields list,
        which contains instances of CustomFieldType.
        :param name: The name of the tab
        :param custom_fields: List of CustomFieldType instances
        :return: The created tab
        """
        ifc_files = self.mainwindow.ifcfiles

        custom_tab = IfcTreeTab(IfcCustomTreeModel, ifc_files, self)
        custom_tab.treemodel.set_custom_fields(custom_fields)
        
        for ifc_file in ifc_files:
            custom_tab.treemodel.addFile(ifc_file)
        
        custom_tab.treemodel.name = name

        self.tabs.addTab(custom_tab, custom_tab.treemodel.name)
        self.customtabs.append(custom_tab)

        custom_tab.close_button = QPushButton("")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DockWidgetCloseButton)
        custom_tab.close_button.setIcon(icon)
        custom_tab.close_button.setFixedSize(16, 16)

        custom_tab.close_button.clicked.connect(lambda: self.remove_custom_tab(custom_tab))

        tab_index = self.tabs.indexOf(custom_tab)
        self.tabs.tabBar().setTabButton(tab_index, QTabBar.RightSide, custom_tab.close_button)

        return custom_tab

    def remove_custom_tab(self, custom_tab):
        """Remove a custom tab after clicking the close button"""
        tab_index = self.tabs.indexOf(custom_tab)
        if tab_index != -1:
            self.tabs.removeTab(tab_index)
            self.customtabs.remove(custom_tab)
            custom_tab.deleteLater()

    def clear_selection(self):
        """Clear the selection in all tree views"""
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            tab.clear_selection()

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

        # Use a Proxy model to enable sorting
        self.proxymodel = QSortFilterProxyModel(self)
        self.proxymodel.setSourceModel(self.treemodel)

        self.tree = QTreeView()
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(2, 250)

        # Allow selection of multiple rows instead of only one row
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        for column in self.treemodel.columntree.hidden_info_columns():
            self.tree.setColumnHidden(column, True)
        
        self.tree.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.setLayout(self.layout)
        self.layout.addWidget(self.tree)

        self.closebutton = None
        

    def on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        """Slot for the selectionChanged signal of the QTreeView
        
        If the selection on the active tab changes, the details view is updated
        and the selection of the other tabs is synchronized.
        """
        if not self.is_active_tab():
            return

        # Note: using selected.indexes() is not enough: after selecting multiple rows, 
        # and pressing arrow or clicking on a row, one row is still selected, but 
        # no index is passed. The following line works.
        indexes = self.tree.selectionModel().selectedIndexes()
        if not indexes:
            self.mainwindow.show_details()
            print("n")
            return
        
        # Only use the indexes of the first column
        indexes = [index for index in indexes if index.column() == 0]
        items = []

        for index in indexes:
            source_index = self.proxymodel.mapToSource(index)
            item = source_index.internalPointer()
            items.append(item)
    
        # Show the details of the first selected item
        if isinstance(items[0], IfcTreeItem):
            self.mainwindow.show_details(item.ifc, item.filenames)
        else:
            self.mainwindow.show_details(item.id)
            print("selected", item, item.id)

        items = [item for item in items if isinstance(item, IfcTreeItem)]

        # Synchronize the selection in the other tabs
        if len(items) > 1:
            self.mainwindow.statusbar.showMessage(self.tr("%i items selected") % len(items))

        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab != self:
                tab.clear_selection()

        for item in items:  
            guid = item.guid
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if tab != self:
                    tab.select_item_by_guid(guid, add=True)


    def clear_selection(self):
        """Clear the selection in the QTreeView"""
        self.tree.selectionModel().clearSelection()


    def select_item_by_guid(self, guid, add=False):
        """Select an item by its GUID
        
        Select the item in the tree view and scroll to it.
        If the item is found, return True, otherwise False.
        """
        index = self.treemodel.find_index_by_guid(guid)
        if index.isValid():
            proxy_index = self.proxymodel.mapFromSource(index)
            if add:
                selection_model = self.tree.selectionModel()
                selection_model.select(proxy_index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            else:
                # Only select the new item
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

    def __repr__(self):
        return f"IfcTreeTab({self.treemodel.__class__.__name__})"
