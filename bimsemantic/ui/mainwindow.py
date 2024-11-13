from PySide6.QtCore import QFile, Qt, QSortFilterProxyModel
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTreeView,
    QLabel,
)

import ifcopenshell

from bimsemantic.util import IfcFile, IfcFiles
from bimsemantic.ui import IfcTabs, DetailsTreeModel, ColumnsTreeModel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIM Semantic Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.statusbar = self.statusBar()
        self.ifcfiles = IfcFiles()
        self.column_treeview = None

        # File menu
        self._file_menu = self.menuBar().addMenu(self.tr("&File"))

        icon = QIcon.fromTheme("document-open")
        self._open_act = QAction(
            icon,
            self.tr("&Open..."),
            self,
            shortcut=QKeySequence.Open,
            statusTip=self.tr("Open IFC file"),
            triggered=self.open_file,
        )

        self._file_menu.addAction(self._open_act)

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

        self.create_dock_windows()

        # Provisorisch ################################################################################
        filenames = ["/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_KIB_EU_003_AA_003-Franz-Liszt-Strasse.ifc",
                     "/media/riannek/PortableSSD/share/FranzLiszt/combined.ifc",
                     "/media/riannek/PortableSSD/share/AC20-FZK-Haus.ifc",
                     "/media/riannek/PortableSSD/share/VST_Röntgental.ifc",
                     "/media/riannek/PortableSSD/share/linkedin.ifc"]
        fl = ['/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_KIB_EU_003_AA_003-Franz-Liszt-Strasse.ifc',
                '/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_VEA_SB_003_AA_003-Franz-Liszt-Strasse.ifc',
                '/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_VEA_ST_003_AA_003-Franz-Liszt-Strasse.ifc']
        filename = filenames[0]
        self.ifcfiles.add_file(filename)

        # for filename in fl:
        #     self.ifcfiles.add_file(filename)

        self.setup_column_tree()


        self.tabs = IfcTabs(self) 
        self.setCentralWidget(self.tabs)

    def setup_column_tree(self):
        self.column_treeview = ColumnsTreeModel(self.ifcfiles)
        self.columnsdock.setWidget(self.column_treeview)


    def open_file(self):
        pass


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
        self.columnsdock.setWidget(QLabel(self.tr("No open file")))
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


