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
)


from bimsemantic.util import IfcFiles
from bimsemantic.ui import IfcTabs, DetailsTreeModel, OverviewTreeModel, ColumnsTreeModel, WorkerAddFiles


class MainWindow(QMainWindow):
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

        self.threadpool = QThreadPool()
        self.workers = []

        self.setup_menus()
        self.create_dock_windows()
        self.tabs = IfcTabs(self) 
        self.setCentralWidget(self.tabs)
        self.setAcceptDrops(True)



    # For drag and drop
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        filenames = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if filenames:
            ifc_filenames = [filename for filename in filenames if filename.endswith(".ifc")]
            self.open_ifc_files(ifc_filenames)


    def open_file_dlg(self):
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Open IFC file"),
            "",
            self.tr("IFC Files (*.ifc)"),
        )
        self.open_ifc_files(filenames)

    def open_ifc_files(self, filenames):
        if filenames:
            self.progressbar.setRange(0, 0)
            self.ignoredfiles = []
            worker = WorkerAddFiles(self.ifcfiles, filenames)
            worker.signals.result.connect(self.add_ifcs_to_trees)
            worker.signals.error.connect(self.on_error)
            worker.signals.finished.connect(self.on_finished)
            worker.signals.feedback.connect(lambda s: self.statusbar.showMessage(self.tr("Open file %s") % s))
            worker.signals.progress.connect(self.on_progress)
            self.threadpool.start(worker)
                

    def add_ifcs_to_trees(self, ifcfiles):
        self.progressbar.setRange(0, len(ifcfiles))
        self.statusbar.showMessage(self.tr("Add files to treeviews"))
        for i, ifcfile in enumerate(ifcfiles):
            self.column_treeview.addFile(ifcfile)
            self.tabs.addFile(ifcfile)
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
        if self.progressbar.maximum() == 0:
            self.progressbar.setRange(0, 100)
        self.progressbar.setValue(progress)

    def on_error(self, error):
        errortype = error[0]
        errorstring = error[1]
        if errortype == "File already open":
            self.ignoredfiles.append(errorstring)
            return
        msg = f"{error[0]}: {error[1]}" 
        QMessageBox.critical(self, "Error", msg)

    def on_finished(self): 
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
        self.statusbar.showMessage(self.tr("Close all files"))
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

    def select_by_guid(self):
        dlg = SelectByDialog("GUID", self)
        if dlg.exec():
            guid = dlg.get_text()
            if not guid:
                return
            count = self.tabs.select_item_by_guid(guid)
            if count == 0:
                self.statusbar.showMessage(self.tr("No element found with GUID %s") % guid, 5000)

    def select_by_id(self):
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

    def setup_menus(self):
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

        self._file_menu.addSeparator()

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

        self._edit_selection_menu = self._edit_menu.addMenu(self.tr("&Selection"))

        self._select_by_guid_act = QAction(
            self.tr("Select by GUID"),
            self,
            statusTip=self.tr("Select IFC element by GUID"),
            triggered=self.select_by_guid,
        )

        self._edit_selection_menu.addAction(self._select_by_guid_act)

        self._select_by_id_act = QAction(
            self.tr("Select by ID"),
            self,
            statusTip=self.tr("Select IFC element by ID and filename"),
            triggered=self.select_by_id,
        )

        self._edit_selection_menu.addAction(self._select_by_id_act)

        # View menu
        self._view_menu = self.menuBar().addMenu(self.tr("&View"))

        # Help menu
        self._help_menu = self.menuBar().addMenu(self.tr("&Help"))

        self._about_act = QAction(
            self.tr("&About"),
            self,
            triggered=self.about,
        )

        self._help_menu.addAction(self._about_act)

    def create_dock_windows(self):
        # Details dock
        self.detailsdock = QDockWidget(self.tr("Details"), self)
        self.detailsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        label = QLabel(self.tr("No open file"))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detailsdock.setWidget(label)
        self.addDockWidget(Qt.RightDockWidgetArea, self.detailsdock)
        self._view_menu.addAction(self.detailsdock.toggleViewAction())


        # Columns dock
        self.columnsdock = QDockWidget(self.tr("Columns"), self)
        self.columnsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.columnsdock.setWidget(self.column_treeview)
        self.addDockWidget(Qt.RightDockWidgetArea, self.columnsdock)
        self._view_menu.addAction(self.columnsdock.toggleViewAction())

    
        self.tabifyDockWidget(self.detailsdock, self.columnsdock)

    def show_details(self, id=None, filenames=None):
        if self.ifcfiles.count() == 0:
            return
        if not id:
            self.detailsdock.setWidget(self.overviewtree)
            return
        detailModel = DetailsTreeModel(id, self, filenames)
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
    def __init__(self, label, parent):
        super().__init__(parent=parent)

        self.setWindowTitle(self.tr("Select element by {label}"))

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
        return self.textfield.text().strip()
    
    def get_combotext(self):
        if self.label != "ID":
            return None
        return self.combo.currentText()