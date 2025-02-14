"""
/***************************************************************************
                              BIM Semantic Viewer
                              -------------------
        begin                : 2024-10-03
        copyright            : (C) 2025 by Florian Neukirchen
        email                : mail@riannek.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PySide6.QtCore import Qt, QThreadPool, QEvent, QSize
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
    QFrame,
    QApplication,
    QStyle,
    QToolButton,
    QMenu,
)

# from ifcopenshell import entity_instance
import bimsemantic
from bimsemantic.util import IfcFiles, Validators
from bimsemantic.ui import (
    IfcTabs,
    IfcTreeTab,
    ColumnsTreeModel,
    WorkerAddFiles,
    CustomTreeDialog,
    PsetDockWidget,
    DetailsDock,
    SomDockWidget,
    FilterIndicator,
    ValidationDockWidget,
)
from bimsemantic.resources import resources


class MainWindow(QMainWindow):
    """Main window of the application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIM Semantic Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.ifcfiles = IfcFiles()
        self.validators = Validators(self.ifcfiles)
        self.idsrules = []

        self.statusbar = self.statusBar()
        self.progressbar = QProgressBar()
        self.progressbar.setMaximumWidth(150)
        self.infolabel = QLabel(self.tr("No open file"))
        self.filterindicator = FilterIndicator(self)
        self.statusbar.addPermanentWidget(self.filterindicator)
        self.statusbar.addPermanentWidget(self.infolabel)
        self.statusbar.addPermanentWidget(self.progressbar)

        self.column_treemodel = ColumnsTreeModel(parent=self)
        self.tabs = IfcTabs(self)

        self.threadpool = QThreadPool()
        self.workers = []

        self.setup_menus()
        self.create_dock_widgets()
        self.somdock = None

        self.setCentralWidget(self.tabs)

        self.installEventFilter(self)
        self.setAcceptDrops(True)

    def eventFilter(self, source, event):
        """Event filter to catch the copy event

        Otherwise Ctrl+C would copy only the active cell.
        """

        # https://stackoverflow.com/questions/40225270/copy-paste-multiple-items-from-qtableview-in-pyqt4
        if event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Copy):
                self.copy_to_clipboard()
                return True
        return super().eventFilter(source, event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Required to accept drag and drop events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Open files dropped on the main window"""
        urls = event.mimeData().urls()
        filenames = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if filenames:
            ifc_filenames = [
                filename for filename in filenames if filename.endswith(".ifc")
            ]
            json_filenames = [
                filename for filename in filenames if filename.endswith(".json")
            ]
            ids_filenames = [
                filename for filename in filenames if filename.endswith(".ids")
            ]
            self.open_ifc_files(ifc_filenames)
            if json_filenames:
                self.open_som(json_filenames[0])
            if ids_filenames:
                for filename in ids_filenames:
                    try:
                        self.validationdock.add_file(filename)
                    except ValueError:
                        self.statusbar.showMessage(
                            self.tr("File is not a valid IDS file"), 5000
                        )
                self.validationdock.show()

    def get_active_dock(self):
        """Get the dock or tab widget of a treeview widget"""
        widget = QApplication.focusWidget()
        if not isinstance(widget, QTreeView):
            return
        parent = widget.parent()
        while parent:
            if isinstance(parent, (IfcTreeTab, QDockWidget)):
                return parent
            parent = parent.parent()
        return None

    def copy_to_clipboard(self, only_cell=False):
        """Call the copy method of the active widget"""

        dock = self.get_active_dock()
        try:
            if only_cell:
                dock.copy_active_cell_to_clipboard()
            else:
                dock.copy_selection_to_clipboard()
        except AttributeError:
            pass

    def somsearch(self):
        """Search the content of the active cell in the SOM"""
        if not self.somdock:
            return

        widget = QApplication.focusWidget()
        if isinstance(widget, QTreeView):
            index = widget.currentIndex()
            if index.isValid():
                data = str(index.data())
                self.somdock.searchbar.show()
                self.somdock.searchbar.search_text.setText(data)
                self.somdock.searchbar.search()

    def search_active(self, filtermode=False):
        """Search or show filterbar

        Shof the searchbar or the filterbar. If the SOM dock is the active
        widget, the searchbar or filterbar of the SOM dock is shown,
        otherwise the searchbar or filterbar of the main view.

        :param filtermode: If True, the filterbar is shown, otherwise the searchbar
        """
        dock = self.get_active_dock()

        if not (hasattr(dock, "autosearch")):
            # The SOM dock is not the active widget
            # Always use the searchbar of the main view in this case
            dock = self.tabs

        if filtermode:
            searchbar = dock.filterbar
        else:
            searchbar = dock.searchbar

        searchbar.show()
        searchbar.search_text.setFocus()

    def open_som_dlg(self):
        """Open SOM file dialog to load a SOM list from a JSON file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open SOM list"),
            "",
            self.tr("JSON files (*.json)"),
        )
        if filename:
            self.open_som(filename)

    def open_som(self, filename):
        """Open a SOM list from a JSON file"""
        self.progressbar.setRange(0, 0)
        self.statusbar.showMessage(self.tr("Loading SOM list"))

        if self.somdock:
            self.close_som()
        # self.somdock = SomDockWidget(self, filename) # Debug, to be removed!!!
        try:
            self.somdock = SomDockWidget(self, filename)
        except (ValueError, AttributeError, IndexError):
            self.statusbar.showMessage(self.tr("Failed to parse JSON file"), 5000)
            self.progressbar.setRange(0, 100)
            return
        except FileNotFoundError:
            self.statusbar.showMessage(self.tr("File not found"), 5000)
            self.progressbar.setRange(0, 100)
            return

        self.addDockWidget(Qt.BottomDockWidgetArea, self.somdock)
        self.view_menu.addAction(self.somdock.toggleViewAction())
        self.search_som_act.setEnabled(True)
        self.progressbar.setRange(0, 100)
        self.statusbar.showMessage(self.tr("SOM loaded"), 5000)

    def close_som(self):
        """Delete the SOM dockwidget"""
        if self.somdock:
            self.view_menu.removeAction(self.somdock.toggleViewAction())
            for action in self.expand_som_menu.actions():
                self.expand_som_menu.removeAction(action)
            self.search_som_act.setEnabled(False)
            self.somdock.deleteLater()
            self.somdock = None

    def load_ids_dlg(self):
        """Open a dialog to load IDS rules"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Load IDS rules"),
            "",
            self.tr("IDS files (*.ids)"),
        )
        if filename:
            try:
                self.validationdock.add_file(filename)
            except FileNotFoundError:
                self.statusbar.showMessage(self.tr("File not found"), 5000)
            except ValueError:
                self.statusbar.showMessage(
                    self.tr("File is not a valid IDS file"), 5000
                )
            self.validationdock.show()

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
            self.progressbar.setRange(0, 0)  # Range 0,0 means indeterminate but active
            self.ignoredfiles = []
            worker = WorkerAddFiles(self.ifcfiles, filenames)
            worker.signals.result.connect(self.add_ifcs_to_trees)
            worker.signals.error.connect(self.on_error)
            worker.signals.finished.connect(self.on_finished)
            worker.signals.feedback.connect(
                lambda s: self.statusbar.showMessage(self.tr("Open file %s") % s)
            )
            worker.signals.progress.connect(self.on_progress)
            self.threadpool.start(worker)

    def add_ifcs_to_trees(self, ifcfiles):
        """Add data of IfcFile objects to the treeviews

        Callback of the WorkerAddFiles worker. Adds the data of the IfcFile objects
        to the column treeview and all IFC treeviews in self.tabs.
        If no file was open before, the details dock is set to show an overview.

        :param ifcfiles: List of IfcFile objects
        """
        self.progressbar.setRange(0, len(ifcfiles) + 1)
        self.statusbar.showMessage(self.tr("Add files to treeviews"))
        self.psetdock.add_files(ifcfiles)
        if self.qsetdock is not None:
            self.qsetdock.add_files(ifcfiles)
        self.progressbar.setValue(1)
        for i, ifcfile in enumerate(ifcfiles):
            self.column_treemodel.add_file(ifcfile)
            self.tabs.add_file(ifcfile)
            self.progressbar.setValue(i + 2)
        self.detailsdock.new_files()
        self.statusbar.clearMessage()
        self.progressbar.reset()

        filecount = self.ifcfiles.count()
        elementcount = self.tabs.count_ifc_elements()
        typecount = self.tabs.count_ifc_types()
        psetscount = self.column_treemodel.count_psets()
        qsetscount = self.column_treemodel.count_qsets()
        self.infolabel.setText(
            self.tr(
                "{0} files, {1} elements in {2} IFC classes, {3} psets, {4} qsets"
            ).format(filecount, elementcount, typecount, psetscount, qsetscount)
        )

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
        self.progressbar.setRange(0, 100)
        self.progressbar.reset()
        if self.ignoredfiles:
            n = len(self.ignoredfiles)
            msg = self.tr("{} files were ignored because they are already open").format(
                n
            )
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

        self.detailsdock.reset()
        self.ifcfiles = IfcFiles()
        Validators().reset(self.ifcfiles)
        self.validationdock.update_results_column()

        self.column_treemodel = ColumnsTreeModel(parent=self)
        self.psetdock.reset()
        if self.qsetdock is not None:
            self.qsetdock.reset()
        self.tabs = IfcTabs(self)
        self.columnsdock.setWidget(self.column_treemodel)
        self.setCentralWidget(self.tabs)
        self.infolabel.setText(self.tr("No open file"))
        self.statusbar.clearMessage()

    def export_to_csv(self):
        """Export data to CSV"""
        dialog = QFileDialog(self, self.tr("Export to CSV"))
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter(self.tr("CSV Files (*.csv)"))
        dialog.setDefaultSuffix("csv")

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
        selected_rows = len(self.tabs.tree.selectionModel().selectedRows())

        if selected_rows > 1:
            only_selected = QCheckBox(
                self.tr("Export only selected rows (%i rows)") % selected_rows
            )
            only_selected.setChecked(False)
            dialog_layout.addWidget(only_selected, 7, 1)

        if dialog.exec():
            csv_file = dialog.selectedFiles()[0]
            sep = separator_combo.currentText()
            if sep == "TAB":
                sep = "\t"
            add_level = chk_with_level.isChecked()
            if selected_rows > 1:
                all_rows = not only_selected.isChecked()
            else:
                all_rows = True

            csv_lines = self.tabs.active.rows_to_csv(
                sep=sep, all_rows=all_rows, add_header=True, add_level=add_level
            )
            self.progressbar.setRange(0, 0)

            with open(csv_file, "w") as f:
                for line in csv_lines:
                    f.write(line)

            self.progressbar.setRange(0, 100)
            self.statusbar.showMessage(self.tr("Exported to %s") % csv_file, 5000)

    def save_validation_dlg(self):
        """Save validation results to a zipped BCF file or as JSON"""

        dialog = QFileDialog(self, self.tr("Save validation results"))
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters([self.tr("BCF (*.bcfzip)"), self.tr("JSON (*.json)")])
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog_layout = dialog.layout()
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        dialog_layout.addWidget(hline, 4, 1)
        label = QLabel(self.tr("Select Validator:"))
        dialog_layout.addWidget(label, 5, 0)
        validator_combo = QComboBox()
        validator_combo.addItems(self.validators.reporters.keys())
        dialog_layout.addWidget(validator_combo, 5, 1)

        selected_validator = self.validationdock.selected_validator_id()
        if (
            selected_validator
            and selected_validator in self.validators.reporters.keys()
        ):
            validator_combo.setCurrentText(selected_validator)

        if len(self.ifcfiles) > 1:
            label = QLabel(self.tr("Select IFC file:"))
            dialog_layout.addWidget(label, 6, 0)
            ifc_combo = QComboBox()
            ifc_combo.addItems([ifc.filename for ifc in self.ifcfiles])
            dialog_layout.addWidget(ifc_combo, 6, 1)

        def update_default_suffix():
            """Callback to change suffix when combo is toggled"""
            current_filter = dialog.selectedNameFilter()
            if "BCF" in current_filter:
                dialog.setDefaultSuffix("bcfzip")
            elif "JSON" in current_filter:
                dialog.setDefaultSuffix("json")

        dialog.filterSelected.connect(update_default_suffix)
        update_default_suffix()

        if dialog.exec():
            filename = dialog.selectedFiles()[0]
            validator_id = validator_combo.currentText()
            if len(self.ifcfiles) == 1:
                ifc_filename = self.ifcfiles[0].filename
            else:
                ifc_filename = ifc_combo.currentText()
            as_bcf = dialog.selectedNameFilter() == self.tr("BCF (*.bcfzip)")
            self.validators.save_results(validator_id, ifc_filename, filename, as_bcf)
            self.statusbar.showMessage(self.tr("Saved to %s") % filename, 5000)

    def select_by_guid(self):
        """Dialog to select an IFC element by GUID and call the algorithm to select it"""
        dlg = SelectByDialog("GUID", self)
        if dlg.exec():
            guid = dlg.get_text()
            if not guid:
                return
            count = self.tabs.select_item_by_guid(guid)
            if count == 0:
                self.statusbar.showMessage(
                    self.tr("No element found with GUID %s") % guid, 5000
                )

    def select_by_tag(self):
        """Dialog to select an IFC element by Tag and call the algorithm to select it"""
        dlg = SelectByDialog("Tag", self)
        if dlg.exec():
            tag = dlg.get_text()
            if not tag:
                return
            count = self.tabs.select_item_by_tag(tag)
            if count == 0:
                self.statusbar.showMessage(
                    self.tr("No element found with Tag %s") % tag, 5000
                )

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
                self.statusbar.showMessage(
                    self.tr("No element found with ID %i") % id, 5000
                )
                return

            try:
                guid = element.GlobalId
            except AttributeError:
                self.statusbar.showMessage(
                    self.tr("No element found with ID %i") % id, 5000
                )
                return
            count = self.tabs.select_item_by_guid(guid)

            if count == 0:
                self.statusbar.showMessage(
                    self.tr("No element found with ID %i") % id, 5000
                )

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
        """Setup the menu and toolbars and actions of the main window"""

        self.toolbar = self.addToolBar(self.tr("Toolbar"))
        self.toolbar.setIconSize(QSize(16, 16))

        # File menu
        self.file_menu = self.menuBar().addMenu(self.tr("&File"))

        icon = QIcon.fromTheme("document-open", QIcon(":/icons/document-open.png"))
        self.open_act = QAction(
            icon,
            self.tr("&Open IFC..."),
            self,
            shortcut=QKeySequence.Open,
            statusTip=self.tr("Open IFC files"),
            triggered=self.open_file_dlg,
        )
        self.file_menu.addAction(self.open_act)
        self.toolbar.addAction(self.open_act)

        self.export_cvs_act = QAction(
            QIcon(":/icons/export-csv.png"),
            self.tr("&Export View to CSV..."),
            self,
            shortcut="Ctrl+E",
            statusTip=self.tr(
                "Export the current view or the current selection to CSV"
            ),
            triggered=self.export_to_csv,
        )
        self.file_menu.addAction(self.export_cvs_act)
        self.toolbar.addAction(self.export_cvs_act)

        self.file_menu.addSeparator()

        self.close_act = QAction(
            QIcon(":/icons/document-close.png"),
            self.tr("&Close all IFCs"),
            self,
            shortcut="Ctrl+W",
            statusTip=self.tr("Close all IFC files"),
            triggered=self.close_all,
        )
        self.file_menu.addAction(self.close_act)
        self.toolbar.addAction(self.close_act)

        self.quit_act = QAction(
            self.tr("&Quit"),
            self,
            shortcut="Ctrl+Q",
            statusTip=self.tr("Quit the application"),
            triggered=self.close,
        )

        self.file_menu.addAction(self.quit_act)

        # Edit menu
        self.edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
        self.toolbar.addSeparator()

        self.copy_rows_act = QAction(
            QIcon(":/icons/edit-copy.png"),
            self.tr("&Copy"),
            self,
            shortcut="Ctrl+C",
            statusTip=self.tr("Copy selected rows to clipboard"),
            triggered=self.copy_to_clipboard,
        )
        self.edit_menu.addAction(self.copy_rows_act)

        self.copy_cell_act = QAction(
            QIcon(":/icons/copy-cell.png"),
            self.tr("Copy cell"),
            self,
            shortcut="Shift+Ctrl+C",
            statusTip=self.tr("Copy selected cell to clipboard"),
            triggered=lambda: self.copy_to_clipboard(only_cell=True),
        )
        self.edit_menu.addAction(self.copy_cell_act)

        self.copyoptions_menu = self.edit_menu.addMenu(self.tr("Copy options"))

        self.chk_copy_with_headers = QAction(
            self.tr("Copy with headers"), self, checkable=True
        )
        self.chk_copy_with_headers.setChecked(False)
        self.copyoptions_menu.addAction(self.chk_copy_with_headers)

        self.chk_copy_with_level = QAction(
            self.tr("Copy with column of hierarchic level"), self, checkable=True
        )
        self.chk_copy_with_level.setChecked(False)
        self.copyoptions_menu.addAction(self.chk_copy_with_level)

        # Toolbar
        copybutton = QToolButton()
        copybutton.setIcon(QIcon(":/icons/edit-copy.png"))
        copybutton.setPopupMode(QToolButton.MenuButtonPopup)
        copybutton.setToolTip(self.tr("Copy selected rows to clipboard"))
        copybutton.setDefaultAction(self.copy_rows_act)
        copybutton.addAction(self.chk_copy_with_headers)
        copybutton.addAction(self.chk_copy_with_level)
        self.toolbar.addWidget(copybutton)

        self.toolbar.addAction(self.copy_cell_act)

        # Edit - Search

        self.search_act = QAction(
            QIcon(":/icons/binocular.png"),
            self.tr("&Search"),
            self,
            statusTip=self.tr("Search in the active view"),
            shortcut="Ctrl+F",
            triggered=self.search_active,
        )
        self.edit_menu.addAction(self.search_act)
        self.toolbar.addAction(self.search_act)

        self.filter_act = QAction(
            QIcon(":/icons/funnel.png"),
            self.tr("&Filter"),
            self,
            statusTip=self.tr("Filter the active view"),
            shortcut="Shift+Ctrl+F",
            triggered=lambda: self.search_active(True),
        )
        self.edit_menu.addAction(self.filter_act)
        self.toolbar.addAction(self.filter_act)

        self.search_som_act = QAction(
            QIcon(":/icons/binocular--arrow.png"),
            self.tr("Search content in SOM"),
            self,
            statusTip=self.tr("Search content of active cell in SOM"),
            triggered=self.somsearch,
            enabled=False,
        )
        self.edit_menu.addAction(self.search_som_act)
        self.toolbar.addAction(self.search_som_act)

        self.edit_menu.addSeparator()

        self.edit_selection_menu = self.edit_menu.addMenu(self.tr("&Selection"))

        self.select_by_guid_act = QAction(
            self.tr("Select by &GUID"),
            self,
            statusTip=self.tr("Select IFC element by GUID"),
            triggered=self.select_by_guid,
        )
        self.edit_selection_menu.addAction(self.select_by_guid_act)

        self.select_by_id_act = QAction(
            self.tr("Select by &ID"),
            self,
            statusTip=self.tr("Select IFC element by ID and filename"),
            triggered=self.select_by_id,
        )
        self.edit_selection_menu.addAction(self.select_by_id_act)

        self.select_by_tag_act = QAction(
            self.tr("Select by &Tag"),
            self,
            statusTip=self.tr("Select IFC element (IfcElement) by Tag"),
            triggered=self.select_by_tag,
        )
        self.edit_selection_menu.addAction(self.select_by_tag_act)

        self.edit_selection_menu.addSeparator()

        self.clearselection_act = QAction(
            self.tr("Clear selection"),
            self,
            statusTip=self.tr("Clear selection in all IFC tabs"),
            triggered=self.tabs.clear_selection,
        )
        self.edit_selection_menu.addAction(self.clearselection_act)

        # View menu
        self.view_menu = self.menuBar().addMenu(self.tr("&View"))

        self.addcustomtree_act = QAction(
            QIcon(":/icons/custom-tree.png"),
            self.tr("&Add custom IFC treeview"),
            self,
            triggered=self.add_custom_tree,
        )
        self.view_menu.addAction(self.addcustomtree_act)
        self.toolbar.addAction(self.addcustomtree_act)

        # View expand/collapse menu
        self.expand_menu = self.view_menu.addMenu(
            self.tr("&Expand/Collapse active tree")
        )

        self.collapse_act = QAction(
            self.tr("&Collapse"),
            self,
            # Using lambda makes it possible to pass an argument to the function
            triggered=(lambda: self.tabs.expand_active_view(-1)),
        )
        self.expand_menu.addAction(self.collapse_act)

        self.expand_level1_act = QAction(
            self.tr("Expand to level &1"),
            self,
            triggered=(lambda: self.tabs.expand_active_view(1)),
        )
        self.expand_menu.addAction(self.expand_level1_act)

        self.expand_level2_act = QAction(
            self.tr("Expand to level &2"),
            self,
            triggered=(lambda: self.tabs.expand_active_view(2)),
        )
        self.expand_menu.addAction(self.expand_level2_act)

        self.expand_level3_act = QAction(
            self.tr("Expand to level &3"),
            self,
            triggered=(lambda: self.tabs.expand_active_view(3)),
        )
        self.expand_menu.addAction(self.expand_level3_act)

        self.expand_level4_act = QAction(
            self.tr("Expand to level &4"),
            self,
            triggered=(lambda: self.tabs.expand_active_view(4)),
        )
        self.expand_menu.addAction(self.expand_level4_act)

        self.expand_all_act = QAction(
            self.tr("Expand &all"),
            self,
            triggered=(lambda: self.tabs.expand_active_view("all")),
        )
        self.expand_menu.addAction(self.expand_all_act)

        # SOM menu
        self.som_menu = self.menuBar().addMenu(self.tr("&Semantic"))
        self.toolbar.addSeparator()

        self.open_som_act = QAction(
            QIcon(":/icons/open-som.png"),
            self.tr("&Open SOM"),
            self,
            statusTip=self.tr("Load SOM list from a JSON file"),
            triggered=self.open_som_dlg,
        )
        self.som_menu.addAction(self.open_som_act)
        self.toolbar.addAction(self.open_som_act)

        self.close_som_act = QAction(
            QIcon(":/icons/close-som.png"),
            self.tr("&Close SOM"),
            self,
            statusTip=self.tr("Close the SOM list"),
            triggered=self.close_som,
        )
        self.som_menu.addAction(self.close_som_act)

        self.expand_som_menu = self.som_menu.addMenu(
            self.tr("&Expand/Collapse SOM tree")
        )

        self.stop_auto_act = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserStop),
            self.tr("Stop auto search"),
            self,
            statusTip=self.tr("Stop the auto search in the SOM"),
            triggered=lambda: self.somdock.set_autosearch_attribute(None),
            enabled=False,
        )
        self.som_menu.addAction(self.stop_auto_act)
        self.toolbar.addAction(self.stop_auto_act)

        # Validation menu
        self.validation_menu = self.menuBar().addMenu(self.tr("&Validation"))
        self.toolbar.addSeparator()

        self.load_ids_act = QAction(
            QIcon(":/icons/open-ids.png"),
            self.tr("&Load IDS file"),
            self,
            statusTip=self.tr("Load IDS file with validation rules"),
            triggered=self.load_ids_dlg,
        )
        self.validation_menu.addAction(self.load_ids_act)
        self.toolbar.addAction(self.load_ids_act)

        self.close_ids_act = QAction(
            QIcon(":/icons/close-ids.png"),
            self.tr("&Close IDS file"),
            self,
            statusTip=self.tr("Close selected IDS file"),
        )
        self.validation_menu.addAction(self.close_ids_act)
        self.toolbar.addAction(self.close_ids_act)

        self.close_all_ids_act = QAction(
            self.tr("Close all IDS files"),
            self,
            statusTip=self.tr("Close all IDS files"),
        )
        self.validation_menu.addAction(self.close_all_ids_act)

        self.validation_menu.addSeparator()

        self.new_ids_act = QAction(
            QIcon(":/icons/new-ids.png"),
            self.tr("&New IDS file"),
            self,
            statusTip=self.tr("Create a new IDS file with validation rules"),
        )
        self.validation_menu.addAction(self.new_ids_act)
        self.toolbar.addAction(self.new_ids_act)

        self.edit_ids_act = QAction(
            QIcon(":/icons/edit-ids.png"),
            self.tr("&Edit IDS file"),
            self,
            statusTip=self.tr("Edit the specifications of the selected IDS file"),
        )
        self.validation_menu.addAction(self.edit_ids_act)
        self.toolbar.addAction(self.edit_ids_act)

        self.edit_ids_copy_act = QAction(
            QIcon(":/icons/edit-ids-copy.png"),
            self.tr("E&dit copy of IDS file"),
            self,
            statusTip=self.tr("Edit a copy of the selected IDS file"),
        )
        self.validation_menu.addAction(self.edit_ids_copy_act)
        self.toolbar.addAction(self.edit_ids_copy_act)

        self.validation_menu.addSeparator()

        self.run_all_validations_act = QAction(
            QIcon(":/icons/run-all.png"),
            self.tr("&Run all validations"),
            self,
            statusTip=self.tr("Run validation using all validation rules"),
        )
        self.validation_menu.addAction(self.run_all_validations_act)
        self.toolbar.addAction(self.run_all_validations_act)

        self.run_selected_validation_act = QAction(
            QIcon(":/icons/run-selected.png"),
            self.tr("Run selected &validation"),
            self,
            statusTip=self.tr("Run validation with the selected validator"),
        )
        self.validation_menu.addAction(self.run_selected_validation_act)
        self.toolbar.addAction(self.run_selected_validation_act)

        self.validation_menu.addSeparator()

        self.save_validation_act = QAction(
            QIcon(":/icons/save-ids.png"),
            self.tr("&Save validation result"),
            self,
            statusTip=self.tr(
                "Save the validation result of the selected validator as BCF or JSON"
            ),
            triggered=self.save_validation_dlg,
            enabled=False,
        )
        self.validation_menu.addAction(self.save_validation_act)
        self.toolbar.addAction(self.save_validation_act)

        # Help menu
        self.help_menu = self.menuBar().addMenu(self.tr("&Help"))

        self.about_act = QAction(
            self.tr("&About"),
            self,
            triggered=self.about,
        )

        self.help_menu.addAction(self.about_act)

    def create_dock_widgets(self):
        """Create the dock widgets"""

        # Details dock
        self.detailsdock = DetailsDock(self)
        self.detailsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        label = QLabel(self.tr("No open file"))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detailsdock.setWidget(label)
        self.addDockWidget(Qt.RightDockWidgetArea, self.detailsdock)

        # Columns dock
        self.columnsdock = QDockWidget(self.tr("&Columns"), self)
        self.columnsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.columnsdock.setWidget(self.column_treemodel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.columnsdock)

        # Pset docks
        self.psetdock = PsetDockWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.psetdock)

        self.tabifyDockWidget(self.detailsdock, self.columnsdock)
        self.tabifyDockWidget(self.columnsdock, self.psetdock)
        self.detailsdock.raise_()

        # Validaton dock
        self.validationdock = ValidationDockWidget(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.validationdock)
        self.validationdock.hide()
        self.run_all_validations_act.triggered.connect(
            self.validationdock.run_all_validations
        )
        self.run_selected_validation_act.triggered.connect(
            self.validationdock.run_selected_validation
        )
        self.close_ids_act.triggered.connect(self.validationdock.close_file)
        self.close_all_ids_act.triggered.connect(self.validationdock.close_all_files)
        self.edit_ids_act.triggered.connect(self.validationdock.edit_ids)
        self.edit_ids_copy_act.triggered.connect(
            lambda: self.validationdock.edit_ids(ascopy=True)
        )
        self.new_ids_act.triggered.connect(
            lambda: self.validationdock.edit_ids(new=True)
        )

        # Add actions to menu
        self.overview_act = QAction(
            self.tr("&Files in details dock"),
            self,
            triggered=self.detailsdock.show_details,
        )
        self.view_menu.addAction(self.overview_act)

        self.view_menu.addSeparator()

        self.view_menu.addAction(self.detailsdock.toggleViewAction())
        self.view_menu.addAction(self.columnsdock.toggleViewAction())
        self.view_menu.addAction(self.psetdock.toggleViewAction())

        # Add checkbox for Qset dock but do not create it yet (only on demand)
        # to speed up loading of files
        self.chk_show_qsets = QAction(self.tr("&Qsets"), self, checkable=True)
        self.chk_show_qsets.setChecked(False)
        self.chk_show_qsets.triggered.connect(self.toggle_qset_dock)
        self.view_menu.addAction(self.chk_show_qsets)
        self.qsetdock = None

        # more toggle actions
        self.view_menu.addAction(self.validationdock.toggleViewAction())
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.toolbar.toggleViewAction())

    def toggle_qset_dock(self):
        """Toggle the visibility of the Qset dock and create it if still None"""
        if self.chk_show_qsets.isChecked():
            if self.qsetdock is None:
                self.qsetdock = PsetDockWidget(self, qset=True)
                self.addDockWidget(Qt.RightDockWidgetArea, self.qsetdock)
                self.tabifyDockWidget(self.psetdock, self.qsetdock)
                self.qsetdock.raise_()
            else:
                self.qsetdock.show()
        else:
            self.qsetdock.hide()

    def about(self):
        QMessageBox.about(
            self,
            "About",
            f"""
            <p><b>BIM Semantic Viewer</b></p>
            <p>Version {bimsemantic.__version__}</p>
            <p>© 2024 Florian Neukirchen<br/>
            Berliner Hochschule für Technik (BHT)<br/>
            Geoprojektarbeit</p>

            <p>Contains Icons of the 
            <a href="https://p.yusukekamiyamane.com/">Fugue Icons</a> 
            by Yusuke Kamiyamane <br/>
            (Creative Commons Attribution 3.0 License)
            </p>

            <p>
            The app icon is AI generated with <a href="https://leonardo.ai/">Leonardo.ai</a>.
            </p>
            """,
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

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

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
