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

from bimsemantic.util.ifcfile import IfcFile
from bimsemantic.ui.ifctrees import LocationTreeModel



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIM Semantic Viewer")
        self.ifc = None

        # Provisorisch ################################################################################
        filename = "/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_KIB_EU_003_AA_003-Franz-Liszt-Strasse.ifc"
        self.ifc = IfcFile(filename)

        # File menu
        self._file_menu = self.menuBar().addMenu("&File")

        icon = QIcon.fromTheme("document-new")
        self._open_act = QAction(
            icon,
            "&Open...",
            self,
            shortcut=QKeySequence.Open,
            statusTip="Open IFC file",
            triggered=self.open_file,
        )

        self._file_menu.addAction(self._open_act)

        self._quit_act = QAction(
            "&Quit",
            self,
            shortcut="Ctrl+Q",
            statusTip="Quit the application",
            triggered=self.close,
        )

        self._file_menu.addAction(self._quit_act)

        # View menu
        self._view_menu = self.menuBar().addMenu("&View")

        # Help menu
        self._help_menu = self.menuBar().addMenu("&Help")

        self._about_act = QAction(
            "&About",
            self,
            statusTip="Show the application's About box",
            triggered=self.about,
        )

        self._help_menu.addAction(self._about_act)

        self.create_dock_windows()

        # Provisorisch ################################################################################
        sourceModel = LocationTreeModel(self.ifc.model)
        proxyModel = QSortFilterProxyModel(self)
        proxyModel.setSourceModel(sourceModel)
        treeview = QTreeView()
        treeview.setModel(proxyModel)
        treeview.setAlternatingRowColors(True)
        treeview.setSortingEnabled(True)
        treeview.setColumnHidden(1, True)
        treeview.expandAll()
        self.setCentralWidget(treeview)

    def create_dock_windows(self):
        dock = QDockWidget("Details", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setWidget(QLabel("No open file"))
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self._view_menu.addAction(dock.toggleViewAction())

    def about(self):
        QMessageBox.about(
            self,
            "BIM Semantic Viewer",
            "Bla "
            "Bla "
            "Bla "
            "Bla ",
        )

    def open_file(self):
        pass
