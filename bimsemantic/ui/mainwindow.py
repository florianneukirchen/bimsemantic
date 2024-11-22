from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction, QIcon, QKeySequence, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QMainWindow,
    QMessageBox,
    QTreeView,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QWidgetAction,
    QWidget,
    QHBoxLayout,
    QGridLayout,
    QFrame,
)

from ifcopenshell import entity_instance
from bimsemantic.util import IfcFiles
from bimsemantic.ui import IfcTabs, IfcDetailsTreeModel, OverviewTreeModel, ColumnsTreeModel, WorkerAddFiles, CustomTreeDialog


class MainWindow(QMainWindow):
    """Main window of the application"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIM Semantic Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.ifcfiles = IfcFiles()

        self.statusbar = self.statusBar()
        self.progressbar = QProgressBar()
        self.progressbar.setMaximumWidth(150)
        self.infolabel = QLabel(self.tr("No open file"))
        self.statusbar.addPermanentWidget(self.infolabel)
        self.statusbar.addPermanentWidget(self.progressbar)
        self.overviewtree = QTreeView()
        self.column_treeview = ColumnsTreeModel(parent=self)
        self.tabs = IfcTabs(self)

        self.threadpool = QThreadPool()
        self.workers = []

        self.setup_menus()
        self.create_dock_windows()
         
        self.setCentralWidget(self.tabs)
        self.setAcceptDrops(True)




    def dragEnterEvent(self, event: QDragEnterEvent):
        """Required to accept drag and drop events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Open files dropped on the main window"""
        urls = event.mimeData().urls()
        filenames = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if filenames:
            ifc_filenames = [filename for filename in filenames if filename.endswith(".ifc")]
            self.open_ifc_files(ifc_filenames)


    def open_file_dlg(self):
        """Open file dialog for IFC files"""
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Open IFC files"),
            "",
            self.tr("IFC Files (*.ifc)"),
        )
        self.open_ifc_files(filenames)

    def open_ifc_files(self, filenames):
        """Open IFC files
        
        Open the files passed as filenames as IfcFile objects (based on IfcOpenShell)
        using multithreading to keep the GUI responsive.
        """
        if filenames:
            self.progressbar.setRange(0, 0) # Range 0,0 means indeterminate but active
            self.ignoredfiles = []
            worker = WorkerAddFiles(self.ifcfiles, filenames)
            worker.signals.result.connect(self.add_ifcs_to_trees)
            worker.signals.error.connect(self.on_error)
            worker.signals.finished.connect(self.on_finished)
            worker.signals.feedback.connect(lambda s: self.statusbar.showMessage(self.tr("Open file %s") % s))
            worker.signals.progress.connect(self.on_progress)
            self.threadpool.start(worker)

    def add_ifcs_to_trees(self, ifcfiles):
        """Add data of IfcFile objects to the treeviews
        
        Callback of the WorkerAddFiles worker. Adds the data of the IfcFile objects
        to the column treeview and all IFC treeviews in self.tabs.
        If no file was open before, the details dock is set to show an overview.

        :param ifcfiles: List of IfcFile objects
        """
        self.progressbar.setRange(0, len(ifcfiles))
        self.statusbar.showMessage(self.tr("Add files to treeviews"))
        for i, ifcfile in enumerate(ifcfiles):
            self.column_treeview.addFile(ifcfile)
            self.tabs.add_file(ifcfile)
            self.progressbar.setValue(i + 1)
        self.statusbar.clearMessage()
        self.progressbar.reset()

        filecount = self.ifcfiles.count()
        elementcount = self.tabs.count_ifc_elements()
        typecount = self.tabs.count_ifc_types()
        psetscount = self.column_treeview.count_psets()
        self.infolabel.setText(self.tr("{0} files, {1} elements, {2} types, {3} psets").format(filecount, elementcount, typecount, psetscount))

        overview = OverviewTreeModel(self)
        self.overviewtree.setModel(overview)
        self.overviewtree.expandAll()
        self.overviewtree.setColumnWidth(0, 170)

        for item in overview.rows_spanned:
            self.overviewtree.setFirstColumnSpanned(item.row(), self.overviewtree.rootIndex(), True)

        if isinstance(self.detailsdock.widget(), QLabel):
            self.show_details()

    def on_progress(self, progress):
        """Callback for progress bar updates of the WorkerAddFiles worker"""
        if self.progressbar.maximum() == 0:
            self.progressbar.setRange(0, 100)
        self.progressbar.setValue(progress)

    def on_error(self, error):
        """Callback for error messages of the WorkerAddFiles worker"""
        errortype = error[0]
        errorstring = error[1]
        if errortype == "File already open":
            self.ignoredfiles.append(errorstring)
            return
        msg = f"{error[0]}: {error[1]}" 
        QMessageBox.critical(self, "Error", msg)

    def on_finished(self): 
        """Callback for the finished signal of the WorkerAddFiles worker"""
        self.workers = [worker for worker in self.workers if not worker.isFinished()]
        self.statusbar.clearMessage()
        self.progressbar.setRange(0,100)
        self.progressbar.reset()
        if self.ignoredfiles:
            n = len(self.ignoredfiles)
            msg = self.tr("{} files were ignored because they are already open").format(n)
            self.ignoredfiles = []
            self.statusbar.showMessage(msg, 5000)

    def closeEvent(self, event):
        """Stop running workers if main window is closed"""
        for worker in self.workers:
            worker.stop()
        event.accept()


    def close_all(self):
        """Close all IFC files"""
        self.statusbar.showMessage(self.tr("Close all files"), 5000)

        # Close custom tabs
        for custom_tab in self.tabs.customtabs:
            tab_index = self.tabs.tabs.indexOf(custom_tab)
            if tab_index != -1:
                self.tabs.tabs.removeTab(tab_index)
                self.tabs.customtabs.remove(custom_tab)
                custom_tab.deleteLater()

        label = QLabel(self.tr("No open file"))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detailsdock.setWidget(label)
        self.ifcfiles = IfcFiles()
        self.column_treeview = ColumnsTreeModel(parent=self)
        self.tabs = IfcTabs(self)
        self.columnsdock.setWidget(self.column_treeview)
        self.setCentralWidget(self.tabs)
        self.infolabel.setText(self.tr("No open file"))
        self.statusbar.clearMessage()

    def export_to_csv(self):
        """Export data to CSV"""
        dialog = QFileDialog(self, self.tr("Export to CSV"))
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter(self.tr("CSV Files (*.csv)"))

        # Add widgets for options
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog_layout = dialog.layout()

        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        dialog_layout.addWidget(hline, 4, 1)

        label = QLabel(self.tr("Separator:"))
        separator_combo = QComboBox()
        separator_combo.addItems([",", ";", "TAB", "|"])

        dialog_layout.addWidget(label, 5, 0)
        dialog_layout.addWidget(separator_combo, 5, 1)

        label = QLabel(self.tr("Options:"))
        dialog_layout.addWidget(label, 6, 0)

        chk_with_level = QCheckBox(self.tr("With column for hierarchical level"))
        chk_with_level.setChecked(False)
        dialog_layout.addWidget(chk_with_level, 6, 1)

        # Get the number of selected rows
        active_tab = self.tabs.tabs.currentWidget()
        selected_rows = len(active_tab.tree.selectionModel().selectedRows())

        if selected_rows > 1:
            only_selected = QCheckBox(self.tr("Export only selected rows (%i rows)") % selected_rows)
            only_selected.setChecked(False)
            dialog_layout.addWidget(only_selected, 7, 1)

        if dialog.exec():
            csv_file = dialog.selectedFiles()[0]
            if not csv_file.lower().endswith(".csv"):
                csv_file += ".csv"
            sep = separator_combo.currentText()
            if sep == "TAB":
                sep = "\t"
            add_level = chk_with_level.isChecked()
            if selected_rows > 1:
                all = not only_selected.isChecked()
            else:
                all = True

            csv_lines = active_tab.rows_to_csv(sep=sep, all=all, add_header=True, add_level=add_level)
            self.progressbar.setRange(0, 0)

            with open(csv_file, "w") as f:
                for line in csv_lines:
                    f.write(line)

            self.progressbar.setRange(0, 100)
            self.statusbar.showMessage(self.tr("Exported to %s") % csv_file, 5000)


    def select_by_guid(self):
        """Dialog to select an IFC element by GUID and call the algorithm to select it"""
        dlg = SelectByDialog("GUID", self)
        if dlg.exec():
            guid = dlg.get_text()
            if not guid:
                return
            count = self.tabs.select_item_by_guid(guid)
            if count == 0:
                self.statusbar.showMessage(self.tr("No element found with GUID %s") % guid, 5000)

    def select_by_tag(self):
        """Dialog to select an IFC element by Tag and call the algorithm to select it"""
        dlg = SelectByDialog("Tag", self)
        if dlg.exec():
            tag = dlg.get_text()
            if not tag:
                return
            count = self.tabs.select_item_by_tag(tag)
            if count == 0:
                self.statusbar.showMessage(self.tr("No element found with Tag %s") % tag, 5000)

    def select_by_id(self):
        """Dialog to select an IFC element by ID and filename and call the algorithm to select it
        
        The dialog also contains a combobox to select the filename. If the filename is set to "Any",
        the item from the first file in the list containing an IfcElement with the given ID is used.
        Note that the ID may not be unique between different IFC files of the same project.
        """
        dlg = SelectByDialog("ID", self)
        if dlg.exec():
            id = dlg.get_text()
            if not id:
                return
            try:
                id = int(id)
            except ValueError:
                self.statusbar.showMessage(self.tr("Invalid ID %s"), 5000)
                return
            filename = dlg.get_combotext()
            if filename == self.tr("Any"):
                for ifcfile in self.ifcfiles:
                    element = ifcfile.get_element(id)

                    if element and element.is_a("IfcElement"):
                        break
            else:
                element = self.ifcfiles.get_element(filename, id)
            if not element:
                self.statusbar.showMessage(self.tr("No element found with ID %i") % id, 5000)
                return

            try:
                guid = element.GlobalId
            except AttributeError:
                self.statusbar.showMessage(self.tr("No element found with ID %i") % id, 5000)
                return
            count = self.tabs.select_item_by_guid(guid)

            if count == 0:
                self.statusbar.showMessage(self.tr("No element found with ID %i") % id, 5000)

    def add_custom_tree(self):
        """Add a custom tree view to the IFC tabs"""
        dlg = CustomTreeDialog(self)
        if dlg.exec():
            name = dlg.get_name()
            items = dlg.get_items()
            if not items:
                return
            self.tabs.make_custom_tab(name, items)

    def setup_menus(self):
        """Setup the menu and actions of the main window"""
        # File menu
        self._file_menu = self.menuBar().addMenu(self.tr("&File"))

        icon = QIcon.fromTheme("document-open")
        self._open_act = QAction(
            icon,
            self.tr("&Open IFC..."),
            self,
            shortcut=QKeySequence.Open,
            statusTip=self.tr("Open IFC files"),
            triggered=self.open_file_dlg,
        )
        self._file_menu.addAction(self._open_act)

        self._export_cvs_act = QAction(
            self.tr("&Export View to CSV..."),
            self,
            shortcut=self.tr("Ctrl+E"),
            statusTip=self.tr("Export the current view or the current selection to CSV"),
            triggered=self.export_to_csv,
        )
        self._file_menu.addAction(self._export_cvs_act)


        self._file_menu.addSeparator()

        icon = QIcon.fromTheme("document-close")
        self._close_act = QAction(
            icon,
            self.tr("&Close all IFCs"),
            self,
            shortcut=self.tr("Ctrl+W"),
            statusTip=self.tr("Close all IFC files"),
            triggered=self.close_all,
        )
        self._file_menu.addAction(self._close_act)

        self._quit_act = QAction(
            self.tr("&Quit"),
            self,
            shortcut=self.tr("Ctrl+Q"),
            statusTip=self.tr("Quit the application"),
            triggered=self.close,
        )

        self._file_menu.addAction(self._quit_act)

        # Edit menu
        self._edit_menu = self.menuBar().addMenu(self.tr("&Edit"))

        self._copy_rows_act = QAction(
            self.tr("&Copy rows"),
            self,
            shortcut=self.tr("Ctrl+C"),
            statusTip=self.tr("Copy selected rows to clipboard"),
            triggered=self.tabs.copy_selection_to_clipboard,
        )
        self._edit_menu.addAction(self._copy_rows_act)

        self._copy_cell_act = QAction(
            self.tr("Copy cell"),
            self,
            shortcut=self.tr("Shift+Ctrl+C"),
            statusTip=self.tr("Copy selected cell to clipboard"),
            triggered=self.tabs.copy_active_cell_to_clipboard,
        )
        self._edit_menu.addAction(self._copy_cell_act)

        self._copyoptions_menu = self._edit_menu.addMenu(self.tr("Copy options"))

        self.chk_copy_with_headers = QAction(self.tr("Copy with headers"), self, checkable=True)
        self.chk_copy_with_headers.setChecked(False)
        self._copyoptions_menu.addAction(self.chk_copy_with_headers)

        self.chk_copy_with_level = QAction(self.tr("Copy with column of hierarchic level"), self, checkable=True)
        self.chk_copy_with_level.setChecked(False)
        self._copyoptions_menu.addAction(self.chk_copy_with_level)

        self._edit_menu.addSeparator()

        self._edit_selection_menu = self._edit_menu.addMenu(self.tr("&Selection"))

        self._select_by_guid_act = QAction(
            self.tr("Select by &GUID"),
            self,
            statusTip=self.tr("Select IFC element by GUID"),
            triggered=self.select_by_guid,
        )
        self._edit_selection_menu.addAction(self._select_by_guid_act)

        self._select_by_id_act = QAction(
            self.tr("Select by &ID"),
            self,
            statusTip=self.tr("Select IFC element by ID and filename"),
            triggered=self.select_by_id
        )
        self._edit_selection_menu.addAction(self._select_by_id_act)

        self._select_by_tag_act = QAction(
            self.tr("Select by &Tag"),
            self,
            statusTip=self.tr("Select IFC element (IfcElement) by Tag"),
            triggered=self.select_by_tag
        )
        self._edit_selection_menu.addAction(self._select_by_tag_act)

        self._edit_selection_menu.addSeparator()

        self._clearselection_act = QAction(
            self.tr("Clear selection"),
            self,
            statusTip=self.tr("Clear selection in all IFC tabs"),
            triggered=self.tabs.clear_selection
        )
        self._edit_selection_menu.addAction(self._clearselection_act)

        # View menu
        self._view_menu = self.menuBar().addMenu(self.tr("&View"))

        self._overview_act = QAction(
            self.tr("&Files in details dock"),
            self,
            triggered=self.show_details,
        )
        self._view_menu.addAction(self._overview_act)

        self._addcustomtree_act = QAction(
            self.tr("&Add custom IFC treeview"),
            self,
            triggered=self.add_custom_tree,
        )
        self._view_menu.addAction(self._addcustomtree_act)

        self._expand_menu = self._view_menu.addMenu(self.tr("&Expand/Collapse active tree"))
        self._view_menu.addMenu(self._expand_menu)

        self._collapse_act = QAction(
            self.tr("&Collapse"),
            self,
            # Using lambda makes it possible to pass an argument to the function
            triggered=(lambda: self.tabs.expand_active_view(-1)),
        )
        self._expand_menu.addAction(self._collapse_act)

        self._expand_level1_act = QAction(
            self.tr("Expand to level &1"),
            self,
            triggered=(lambda: self.tabs.expand_active_view(1)),
        )
        self._expand_menu.addAction(self._expand_level1_act)

        self._expand_level2_act = QAction(
            self.tr("Expand to level &2"),
            self,
            triggered=(lambda: self.tabs.expand_active_view(2)),
        )
        self._expand_menu.addAction(self._expand_level2_act)

        self._expand_level3_act = QAction(
            self.tr("Expand to level &3"),
            self,
            triggered=(lambda: self.tabs.expand_active_view(3)),
        )
        self._expand_menu.addAction(self._expand_level3_act)

        self._expand_level4_act = QAction(
            self.tr("Expand to level &4"),
            self,
            triggered=(lambda: self.tabs.expand_active_view(4)),
        )
        self._expand_menu.addAction(self._expand_level4_act)

        self._expand_all_act = QAction(
            self.tr("Expand &all"),
            self,
            triggered=(lambda: self.tabs.expand_active_view("all")),
        )
        self._expand_menu.addAction(self._expand_all_act)

        self._view_menu.addSeparator()

        # Help menu
        self._help_menu = self.menuBar().addMenu(self.tr("&Help"))

        self._about_act = QAction(
            self.tr("&About"),
            self,
            triggered=self.about,
        )

        self._help_menu.addAction(self._about_act)

    def create_dock_windows(self):
        """Create the dock widgets"""
        # Details dock
        self.detailsdock = QDockWidget(self.tr("&Details"), self)
        self.detailsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        label = QLabel(self.tr("No open file"))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detailsdock.setWidget(label)
        self.addDockWidget(Qt.RightDockWidgetArea, self.detailsdock)
        self._view_menu.addAction(self.detailsdock.toggleViewAction())


        # Columns dock
        self.columnsdock = QDockWidget(self.tr("&Columns"), self)
        self.columnsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.columnsdock.setWidget(self.column_treeview)
        self.addDockWidget(Qt.RightDockWidgetArea, self.columnsdock)
        self._view_menu.addAction(self.columnsdock.toggleViewAction())

    
        self.tabifyDockWidget(self.detailsdock, self.columnsdock)

    def show_details(self, data=None, filenames=None):
        """Show the details of an IFC element
        
        ID is the ID of the element, as in the first file of the list of filenames.
        Filenames is the list of filenames of all files containing the element.
        If ID is None, the overview tree is shown.
        
        :param id: The ID of the element
        :type id: int
        :param filenames: The list of filenames
        :type filenames: list of str
        """
        if self.ifcfiles.count() == 0:
            return
        if isinstance(data, entity_instance):
            detailModel = IfcDetailsTreeModel(data, self, filenames)
        else:
            self.detailsdock.setWidget(self.overviewtree)
            return
        treeview = QTreeView()
        treeview.setModel(detailModel)
        treeview.setColumnWidth(0, 170)

        # treeview.setColumnWidth(1, 200)
        treeview.expandAll()
        # treeview.adjustSize()
        for item in detailModel.rows_spanned:
            treeview.setFirstColumnSpanned(item.row(), treeview.rootIndex(), True)
        self.detailsdock.setWidget(treeview)


    def about(self):
        QMessageBox.about(
            self,
            "BIM Semantic Viewer",
            "Bla "
            "Bla "
            "Bla "
            "Bla ",
        )


class SelectByDialog(QDialog):
    """Dialog for selecting an IFC element by GUID or ID

    If searching for ID, a combobox is shown to select the filename.
    
    :param label: The label of the input field: "GUID" or "ID"
    :type label: str
    :param parent: The parent widget (main window)
    """
    def __init__(self, label, parent):
        super().__init__(parent=parent)

        self.setWindowTitle(self.tr("Select element by %s") % label)

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        self.label = label

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        self.combo = QComboBox()
        if label == "ID":
            layout.addWidget(QLabel(self.tr("IFC File")))
            layout.addWidget(self.combo)
            self.combo.addItems([self.tr("Any")] + parent.ifcfiles.filenames())

        self.textfield = QLineEdit()
        layout.addWidget(QLabel(label))
        layout.addWidget(self.textfield)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def get_text(self):
        """Get the text from the input field"""
        return self.textfield.text().strip()
    
    def get_combotext(self):
        """Get the text from the combobox"""
        if self.label != "ID":
            return None
        return self.combo.currentText()