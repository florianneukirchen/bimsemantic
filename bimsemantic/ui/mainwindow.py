from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTreeView,
    QLabel,
    QProgressBar,
)

import ifcopenshell

from bimsemantic.util import IfcFile, IfcFiles
from bimsemantic.ui import IfcTabs, DetailsTreeModel, ColumnsTreeModel, WorkerAddFiles, WorkerSignals


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIM Semantic Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.statusbar = self.statusBar()
        self.progressbar = QProgressBar()
        self.statusbar.addPermanentWidget(self.progressbar)
        self.threadpool = QThreadPool()
        self.workers = []
        self.ifcfiles = IfcFiles()
        self.column_treeview = ColumnsTreeModel(parent=self)
        self.setup_menus()
        self.create_dock_windows()
        self.tabs = IfcTabs(self) 
        self.setCentralWidget(self.tabs)


        # Provisorisch ################################################################################
        filenames = ["/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_KIB_EU_003_AA_003-Franz-Liszt-Strasse.ifc",
                     "/media/riannek/PortableSSD/share/FranzLiszt/combined.ifc",
                     "/media/riannek/PortableSSD/share/AC20-FZK-Haus.ifc",
                     "/media/riannek/PortableSSD/share/VST_Röntgental.ifc",
                     "/media/riannek/PortableSSD/share/linkedin.ifc"]
        fl = ['/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_KIB_EU_003_AA_003-Franz-Liszt-Strasse.ifc',
                '/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_VEA_SB_003_AA_003-Franz-Liszt-Strasse.ifc',
                '/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_VEA_ST_003_AA_003-Franz-Liszt-Strasse.ifc']
        filename = filenames[2]

        # self.addIfcFile(filename)

        # for filename in fl:
        #     self.addIfcFile(filename)


    def open_file(self):
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Open IFC file"),
            "",
            self.tr("IFC Files (*.ifc)"),
        )

        if filenames:
            self.progressbar.setRange(0, 0)
            self.ignoredfiles = []
            worker = WorkerAddFiles(self.ifcfiles, filenames)
            worker.signals.result.connect(self.add_ifcs_to_trees)
            worker.signals.error.connect(self.on_error)
            worker.signals.finished.connect(self.on_finished)
            worker.signals.feedback.connect(lambda s: self.statusbar.showMessage(self.tr("Open file %s") % s))
            worker.signals.progress.connect(self.on_progress)
            # worker.signals.feedback.connect(self.on_feedback)
            self.threadpool.start(worker)
                
    def on_progress(self, progress):
        if self.progressbar.maximum() == 0:
            self.progressbar.setRange(0, 100)
        self.progressbar.setValue(progress)

    def add_ifcs_to_trees(self, ifcfiles):
        self.progressbar.setRange(0, len(ifcfiles))
        self.statusbar.showMessage(self.tr("Add files to treeviews"))
        for i, ifcfile in enumerate(ifcfiles):
            self.column_treeview.addFile(ifcfile)
            self.tabs.addFile(ifcfile)
            self.progressbar.setValue(i + 1)
        self.statusbar.clearMessage()
        self.progressbar.reset()

    def on_error(self, error):
        errortype = error[0]
        errorstring = error[1]
        if errortype == "File already open":
            self.ignoredfiles.append(errorstring)
            return
        msg = f"{error[0]}: {error[1]}" 
        QMessageBox.critical(self, "Error", msg)

    # def on_feedback(self, feedback):
    #     self.statusbar.showMessage(self.tr("Open file %s") % feedback)

    def on_finished(self): 
        self.workers = [worker for worker in self.workers if not worker.isFinished()]
        self.statusbar.clearMessage()
        if self.ignoredfiles:
            n = len(self.ignoredfiles)
            msg = self.tr(f"{n} files were ignored because they are already open")
            self.ignoredfiles = []
            self.statusbar.showMessage(msg, 5000)

    def closeEvent(self, event):
        """Stop running workers if main window is closed"""
        for worker in self.workers:
            worker.stop()
        event.accept()

    # def openIfcFile(self, filename):
    #     ifcfile = IfcFile(filename)
    #     return ifcfile


    # def addIfcFile(self, filename):

    #     self.statusbar.showMessage(self.tr("Open file %s") % filename)
    #     try:
    #         ifcfile = self.ifcfiles.add_file(filename)
    #     except FileNotFoundError as e:
    #         QMessageBox.critical(self, "Error", str(e))
    #         return
    #     except ValueError as e:
    #         QMessageBox.critical(self, "Error", str(e))
    #         return
    #     print(f"Added {filename} to ifcfiles")
    #     self.statusbar.showMessage(self.tr("Add file %s to treeviews") % filename)
    #     self.column_treeview.addFile(ifcfile)
    #     self.tabs.addFile(ifcfile)
    #     self.statusbar.clearMessage()
    #     print(f"Added {filename} to trees")

    def close_all(self):
        self.statusbar.showMessage(self.tr("Close all files"))
        self.detailsdock.setWidget(QLabel(self.tr("No open file")))
        self.ifcfiles = IfcFiles()
        self.column_treeview = ColumnsTreeModel(parent=self)
        self.tabs = IfcTabs(self)
        self.columnsdock.setWidget(self.column_treeview)
        self.setCentralWidget(self.tabs)
        
        self.statusbar.clearMessage()


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
            triggered=self.open_file,
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
        self.detailsdock.setWidget(QLabel(self.tr("No open file")))
        self.addDockWidget(Qt.RightDockWidgetArea, self.detailsdock)
        self._view_menu.addAction(self.detailsdock.toggleViewAction())

        # Files Dock
        # self.filesdock = QDockWidget(self.tr("Files"), self)
        # self.filesdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        # self.filesdock.setWidget(QLabel(self.tr("No open file")))
        # self.addDockWidget(Qt.RightDockWidgetArea, self.filesdock)
        # self._view_menu.addAction(self.filesdock.toggleViewAction())

        # Columns dock
        self.columnsdock = QDockWidget(self.tr("Columns"), self)
        self.columnsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.columnsdock.setWidget(self.column_treeview)
        self.addDockWidget(Qt.RightDockWidgetArea, self.columnsdock)
        self._view_menu.addAction(self.columnsdock.toggleViewAction())

    
        self.tabifyDockWidget(self.detailsdock, self.columnsdock)
        # self.tabifyDockWidget(self.detailsdock, self.filesdock)

    def show_details(self, id, filenames=None):
        detailModel = DetailsTreeModel(id, self, filenames)
        treeview = QTreeView()
        treeview.setModel(detailModel)
        treeview.setColumnWidth(0, 170)
        # treeview.setColumnWidth(1, 200)
        treeview.expandAll()
        treeview.adjustSize()
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


