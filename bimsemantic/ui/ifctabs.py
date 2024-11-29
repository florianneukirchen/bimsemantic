from PySide6.QtCore import Qt, QSortFilterProxyModel, QTimer, QItemSelection, QItemSelectionModel, QModelIndex, QEvent
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QTreeView, QAbstractItemView, QWidget, QMenu, QTabWidget, QTabBar, QVBoxLayout, QPushButton, QStyle, QApplication
from PySide6.QtGui import QAction
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
        self.tabs.addTab(self.typetab, self.tr("Class"))

        self.flattab = IfcTreeTab(FlatTreeModel, self.ifcfiles, self) 
        self.tabs.addTab(self.flattab, self.tr("Flat"))

        self.mainwindow.column_treemodel.columnsChanged.connect(self.update_columns)




    def add_file(self, ifc_file):
        """Add data of an IFC file to the tree views
        
        :param ifc_file: bimsemantic IFC file instance
        :type ifc_file: IfcFile
        """
        self.locationtab.treemodel.add_file(ifc_file)
        self.typetab.treemodel.add_file(ifc_file)
        self.flattab.treemodel.add_file(ifc_file)
        for tab in self.customtabs:
            tab.treemodel.add_file(ifc_file)

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
        return self.flattab.treemodel.elements_item.child_count()
    
    def count_ifc_types(self):
        """Get the number of all IFC element types of the open files"""
        return self.typetab.treemodel._rootItem.child_count()

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
            custom_tab.treemodel.add_file(ifc_file)
        
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

    def expand_active_view(self, level):
        """Expand items in active tree up to a certain level"""
        active_tab = self.tabs.currentWidget()
        if not active_tab:
            return
        if level == -1:
            active_tab.tree.collapseAll()
        elif level == "all":
            active_tab.tree.expandAll()
        else:
            active_tab.tree.expandToDepth(level - 1) 

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
        self.count_ifc_elements = parent.count_ifc_elements
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

        self.close_button = None

        # Setup Context Menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        

    def on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        """Slot for the selectionChanged signal of the QTreeView
        
        If the selection on the active tab changes, the details view is updated
        and the selection of the other tabs is synchronized.
        With no selection or (almost) all rows selected, the details view 
        shows the basic info about the open files.
        """
        if not self.is_active_tab():
            return

        # Note: using selected.indexes() is not enough: after selecting multiple rows, 
        # and pressing arrow or clicking on a row, one row is still selected, but 
        # no index is passed. The following line works.
        indexes = self.tree.selectionModel().selectedRows()
        if not indexes:
            self.mainwindow.detailsdock.show_details()
            print("n")
            return
        
        # Check if all (or most) rows are selected to avoid iterating 
        # over all items on Ctrl+A
        elementcount = self.count_ifc_elements()
        if len(indexes) >= elementcount:
            self.mainwindow.detailsdock.show_details()
            return
    
        items = []

        for index in indexes:
            source_index = self.proxymodel.mapToSource(index)
            item = source_index.internalPointer()
            items.append(item)
    
        # Show the details of the first selected item
        item = items[0]
        if isinstance(item, IfcTreeItem):
            self.mainwindow.detailsdock.show_details(item.ifc, item.filenames)
        else:
            self.mainwindow.detailsdock.show_details(item.id)
            print("selected", item, item.id)

        # SOM list
        if self.mainwindow.somdock and self.mainwindow.somdock.isVisible():
            self.mainwindow.somdock.autosearch(item.ifc)

        items = [item for item in items if isinstance(item, IfcTreeItem)]

        # Synchronize the selection in the other tabs
        if len(items) > 1:
            self.mainwindow.statusbar.showMessage(self.tr("%i items selected") % len(items))
        else:
            self.mainwindow.statusbar.clearMessage()

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

    def copy_selection_to_clipboard(self):
        """Copy the selected rows to the clipboard"""

        add_header = self.mainwindow.chk_copy_with_headers.isChecked()
        add_level = self.mainwindow.chk_copy_with_level.isChecked()

        # rows_to_csv is a generator
        txt = "".join(self.rows_to_csv(sep=";", add_header=add_header, add_level=add_level))

        clipboard = QApplication.clipboard()
        clipboard.setText(txt)

    def copy_active_cell_to_clipboard(self):
        """Copy the active cell to the clipboard"""

        index = self.tree.currentIndex()
        if index.isValid():
            data = index.data()
            if data:
                data = str(data)
            else:
                data = ""
            clipboard = QApplication.clipboard()
            clipboard.setText(data)    

    def rows_to_csv(self, sep=";", all=False, add_header=False, add_level=False):
        """Generator, yields the selected rows as CSV string
        
        The columns are separated by the given separator.
        Using a generator allows to write the rows to a file line by line.
        """
        if all:
            indexes = self.get_all_row_indexes()
        else:
            indexes = self.tree.selectionModel().selectedRows()
            # Sort the indexes by the visual order in the tree view
            indexes.sort(key=lambda index: self.tree.visualRect(index).top())

        if add_header:
            headerrow = [self.treemodel.headerData(i) for i in range(self.treemodel.columnCount()) if not self.tree.isColumnHidden(i)]
            if add_level:
                headerrow.insert(0, "Level")
            yield sep.join(headerrow) + "\n"

        for index in indexes:
            source_index = self.proxymodel.mapToSource(index)
            item = source_index.internalPointer()
            row = [str(item.data(i)) for i in range(self.treemodel.columnCount()) if not self.tree.isColumnHidden(i)]

            # Empty cells are returned as str "None"
            for i in range(len(row)):
                if row[i] == "None":
                    row[i] = ""

            if add_level:
                row.insert(0, str(item.level()))
            yield sep.join(row) + "\n"


    def get_all_row_indexes(self, parent_index=QModelIndex()):
        """Recursively get all row indexes of the tree view
        
        These indexes are required to serialize the complete tree view.
        :param parent_index: The parent index, default is the root of the tree view.
        :return: List of QModelIndex instances
        """
        indexes = []
        for row in range(self.proxymodel.rowCount(parent_index)):
            index = self.proxymodel.index(row, 0, parent_index)
            indexes.append(index)
            if self.proxymodel.hasChildren(index):
                indexes.extend(self.get_all_row_indexes(index))
        return indexes

    def show_context_menu(self, position):
        index = self.tree.indexAt(position)
        context_menu = QMenu(self)
        context_menu.addAction(self.mainwindow.copy_rows_act)
        context_menu.addAction(self.mainwindow.copy_cell_act)

        if self.mainwindow.somdock and self.mainwindow.somdock.isVisible():
            context_menu.addAction(self.mainwindow.search_som_act)

        expand_menu = QMenu(self.tr("Expand/Collapse"), self)
        for action in self.mainwindow.expand_menu.actions():
            expand_menu.addAction(action)
        context_menu.addMenu(expand_menu)
        context_menu.addSeparator()
        if index.isValid() and index.column() > 0:
            context_menu.addAction(QAction(
            self.tr("Remove column"), 
            self,
            triggered=lambda: self.treemodel.columntree.remove_column(index.column())
        ))

        context_menu.exec(self.tree.viewport().mapToGlobal(position))

    def __repr__(self):
        return f"IfcTreeTab({self.treemodel.__class__.__name__})"
