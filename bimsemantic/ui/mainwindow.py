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
        self._file_menu = self.menuBar().addMenu(self.tr("&File"))

        icon = QIcon.fromTheme("document-new")
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
        self._view_cols_menu = self._view_menu.addMenu(self.tr("Columns"))
        self.column_actions = []
        select_all_action = QAction(self.tr("Show All"), self)
        select_all_action.triggered.connect(self.select_all_columns)
        self._view_cols_menu.addAction(select_all_action)

        unselect_all_action = QAction(self.tr("Hide All"), self)
        unselect_all_action.triggered.connect(self.unselect_all_columns)
        self._view_cols_menu.addAction(unselect_all_action)
        self._view_cols_menu.addSeparator()

        # Help menu
        self._help_menu = self.menuBar().addMenu(self.tr("&Help"))

        self._about_act = QAction(
            self.tr("&About"),
            self,
            triggered=self.about,
        )

        self._help_menu.addAction(self._about_act)

        self.create_dock_windows()

        self.tabs = IfcTabs(self.ifc, self)
        self.setCentralWidget(self.tabs)

    def select_all_columns(self):
        for action in self.column_actions:
            action.setChecked(True)
            # First Column can't be hidden in the treeview, so add +1 to index
            self.tabs.toggle_column_visibility(self.column_actions.index(action) + 1, True)

    def unselect_all_columns(self):
        for action in self.column_actions:
            action.setChecked(False)
            # First Column can't be hidden in the treeview, so add +1 to index
            self.tabs.toggle_column_visibility(self.column_actions.index(action) + 1, False)


    def create_dock_windows(self):
        self.detailsdock = QDockWidget(self.tr("Details"), self)
        self.detailsdock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.detailsdock.setWidget(QLabel(self.tr("No open file")))
        self.addDockWidget(Qt.RightDockWidgetArea, self.detailsdock)
        self._view_menu.addSeparator()
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
