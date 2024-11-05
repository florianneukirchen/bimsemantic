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
from bimsemantic.ui.detailview import DetailsTreeModel



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIM Semantic Viewer")
        self.ifc = None

        # Provisorisch ################################################################################
        filenames = ["/media/riannek/PortableSSD/share/FranzLiszt/GE_2000_3TM_KIB_EU_003_AA_003-Franz-Liszt-Strasse.ifc",
                     "/media/riannek/PortableSSD/share/FranzLiszt/combined.ifc",
                     "/media/riannek/PortableSSD/share/AC20-FZK-Haus.ifc",
                     "/media/riannek/PortableSSD/share/VST_Röntgental.ifc",
                     "/media/riannek/PortableSSD/share/linkedin.ifc"]
        filename = filenames[0]
        self.ifc = IfcFile(filename)
        print("Loaded file")

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
        # treeview.setColumnHidden(1, True)
        treeview.expandAll()
        self.setCentralWidget(treeview)

        wall = self.ifc.model.by_type('IfcWall')[0]
        self.show_details(wall)



    def create_dock_windows(self):
        self.detailsdock = QDockWidget("Details", self)
        self.detailsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.detailsdock.setWidget(QLabel("No open file"))
        self.addDockWidget(Qt.RightDockWidgetArea, self.detailsdock)
        self._view_menu.addAction(self.detailsdock.toggleViewAction())

    def show_details(self, ifc_objects):
        detailModel = DetailsTreeModel(ifc_objects)
        treeview = QTreeView()
        treeview.setModel(detailModel)
        treeview.expandAll()
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

    def open_file(self):
        pass
