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

from bimsemantic.util import IfcFile
from bimsemantic.ui import LocationTreeModel, IfcTabs, DetailsTreeModel, TreeItem


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIM Semantic Viewer")
        self.statusbar = self.statusBar()
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

        self.tabs = IfcTabs(self.ifc, self)
        self.setCentralWidget(self.tabs)
        # Provisorisch ################################################################################
        # sourceModel = LocationTreeModel(self.ifc.model)
        # self.locProxyModel = QSortFilterProxyModel(self)
        # self.locProxyModel.setSourceModel(sourceModel)
        # self.loctreeview = QTreeView()
        # self.loctreeview.setModel(self.locProxyModel)
        # self.loctreeview.setAlternatingRowColors(True)
        # self.loctreeview.setSortingEnabled(True)
        # self.loctreeview.setColumnWidth(0, 200)
        # self.loctreeview.setColumnWidth(2, 250)
        # # self.loctreeview.setColumnHidden(1, True)
        # self.loctreeview.expandAll()
        # self.setCentralWidget(self.loctreeview)
        # self.loctreeview.clicked.connect(self.on_treeview_clicked)




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
        treeview.setColumnWidth(0, 200)
        treeview.setColumnWidth(1, 200)
        treeview.expandAll()
        treeview.adjustSize()
        for item in detailModel.rows_spanned:
            treeview.setFirstColumnSpanned(item.row(), treeview.rootIndex(), True)
        self.detailsdock.setWidget(treeview)

    # def on_treeview_clicked(self, index):
    #     if not index.isValid():
    #         print("Invalid index")
    #         return
    #     source_index = self.locProxyModel.mapToSource(index)
    #     item = source_index.internalPointer()
    #     if isinstance(item, TreeItem):
    #         element_id = item.id
    #         ifc_element = self.ifc.model.by_id(element_id)
    #         self.show_details(ifc_element)

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
