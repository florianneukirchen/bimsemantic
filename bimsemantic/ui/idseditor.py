from enum import Enum
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QStackedLayout,
    QLineEdit,
    QPlainTextEdit,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QStyle,
    QCalendarWidget,
    QWidget,
    QComboBox,
)
import ifctester

class IdsEditDialog(QDialog):

    def __init__(self, parent, filename=None):
        super().__init__(parent=parent)
        self.mainwindow = parent
        self.filename = filename
        self.dirty = False

        self.current_spec = None
        self.current_facet = None

        self.setWindowTitle(self.tr("Edit IDS"))

        self.stacked_layout = QStackedLayout()
        self.setLayout(self.stacked_layout)

        self.main_layout = QWidget()
        self.main_layout.setLayout(QGridLayout())
        self.stacked_layout.addWidget(self.main_layout)

        self.spec_layout = QWidget()
        self.spec_layout.setLayout(QGridLayout())
        self.stacked_layout.addWidget(self.spec_layout)

        self.facet_layout = QWidget()
        self.facet_layout.setLayout(QGridLayout())
        self.stacked_layout.addWidget(self.facet_layout)

        self.cardinalities = ["Required", "Optional", "Prohibited"]

        self.setup_main_layout()
        self.setup_spec_layout()
        self.setup_facet_layout()

        QBtn = QDialogButtonBox.Save | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.main_layout.layout().addWidget(self.buttonBox, 5, 1)

        if filename:
            self.ids = ifctester.ids.open(filename)
        else:
            self.ids = ifctester.ids.Ids()


    def setup_main_layout(self):
        layout = self.main_layout.layout()
        layout.addWidget(QLabel(self.tr("Title")), 0, 0)
        self.title = QLineEdit()
        self.title.setText("No Title")
        layout.addWidget(self.title, 0, 1)

        layout.addWidget(QLabel(self.tr("Description")), 1, 0)
        self.description = QLineEdit()
        layout.addWidget(self.description, 1, 1)

        layout.addWidget(QLabel(self.tr("Specifications")), 2, 0)
        self.specifications = QListWidget()
        layout.addWidget(self.specifications, 2, 1)

        buttonlayout = QHBoxLayout()
        layout.addLayout(buttonlayout, 3, 1)
        self.addspecification = QPushButton(self.tr("New"))
        self.addspecification.clicked.connect(self.add_specification)
        buttonlayout.addWidget(self.addspecification)
        self.removespecification = QPushButton(self.tr("Remove"))
        self.removespecification.clicked.connect(self.remove_specification)
        buttonlayout.addWidget(self.removespecification)
        self.editspecification = QPushButton(self.tr("Edit"))
        self.editspecification.clicked.connect(self.edit_specification)
        buttonlayout.addWidget(self.editspecification)

    def setup_spec_layout(self):
        layout = self.spec_layout.layout()
        layout.addWidget(QLabel(self.tr("Specification Name")), 0, 0)
        self.spec_name = QLineEdit()
        layout.addWidget(self.spec_name, 0, 1)

        layout.addWidget(QLabel(self.tr("Description")), 1, 0)
        self.spec_description = QLineEdit()
        layout.addWidget(self.spec_description, 1, 1)

        layout.addWidget(QLabel(self.tr("Instructions")), 2, 0)
        self.instructions = QLineEdit()
        layout.addWidget(self.instructions, 2, 1)

        layout.addWidget(QLabel(self.tr("Identifier")), 3, 0)
        self.identifier = QLineEdit()
        layout.addWidget(self.identifier, 3, 1)

        layout.addWidget(QLabel(self.tr("Cardinality")), 4, 0)
        self.cardinality = QComboBox()
        self.cardinality.addItems(self.cardinalities)
        layout.addWidget(self.cardinality, 4, 1)

        # missing: ifcVersion

        # Applicability
        layout.addWidget(QLabel(self.tr("Applicability")), 5, 0)
        self.applicability = QListWidget()
        layout.addWidget(self.applicability, 5, 1)

        buttonlayout1 = QHBoxLayout()
        layout.addLayout(buttonlayout1, 6, 1)
        self.addapplicability = QPushButton(self.tr("New"))
        self.addapplicability.clicked.connect(self.add_applicability)
        buttonlayout1.addWidget(self.addapplicability)
        self.removeapplicability = QPushButton(self.tr("Remove"))
        self.removeapplicability.clicked.connect(self.remove_applicability)
        buttonlayout1.addWidget(self.removeapplicability)
        self.editapplicability = QPushButton(self.tr("Edit"))
        self.editapplicability.clicked.connect(self.edit_applicability)
        buttonlayout1.addWidget(self.editapplicability)

        layout.addWidget(QLabel(self.tr("Requirements")), 7, 0)
        self.requirements = QListWidget()
        layout.addWidget(self.requirements, 7, 1)

        buttonlayout2 = QHBoxLayout()
        layout.addLayout(buttonlayout2, 8, 1)
        self.addrequirements = QPushButton(self.tr("New"))
        self.addrequirements.clicked.connect(self.add_requirement)
        buttonlayout2.addWidget(self.addrequirements)
        self.removerequirements = QPushButton(self.tr("Remove"))
        self.removerequirements.clicked.connect(self.remove_requirement)
        buttonlayout2.addWidget(self.removerequirements)
        self.editrequirements = QPushButton(self.tr("Edit"))
        self.editrequirements.clicked.connect(self.edit_requirement)
        buttonlayout2.addWidget(self.editrequirements)

        buttonlayout3 = QHBoxLayout()
        self.spec_layout.layout().addLayout(buttonlayout3, 9, 1)
        self.back_to_main = QPushButton(self.tr("Cancel"))
        self.back_to_main.clicked.connect(self.show_main_layout)
        buttonlayout3.addWidget(self.back_to_main)
        self.save_spec_btn = QPushButton(self.tr("Save Specification"))
        self.save_spec_btn.clicked.connect(self.save_specification)
        buttonlayout3.addWidget(self.save_spec_btn)

    def setup_facet_layout(self):
        self.facet_layout.layout().addWidget(QLabel(self.tr("Requirement Name")), 0, 0)
        self.facet_name = QLineEdit()
        self.facet_layout.layout().addWidget(self.facet_name, 0, 1)

        buttonlayout = QHBoxLayout()
        self.facet_layout.layout().addLayout(buttonlayout, 1, 1)
        self.back_to_spec = QPushButton(self.tr("Back"))
        self.back_to_spec.clicked.connect(self.show_spec_layout)
        buttonlayout.addWidget(self.back_to_spec)

    def show_main_layout(self):
        self.stacked_layout.setCurrentWidget(self.main_layout)

    def show_spec_layout(self):
        self.stacked_layout.setCurrentWidget(self.spec_layout)

    def show_facet_layout(self):
        self.stacked_layout.setCurrentWidget(self.facet_layout)

    def add_specification(self):
        self.current_spec = None
        self.spec_name.setText(self.tr("New Specification"))
        self.stacked_layout.setCurrentWidget(self.spec_layout)
        self.spec_description.clear()
        self.instructions.clear()
        self.identifier.clear()
        self.cardinality.setCurrentIndex(0)
        self.applicability.clear()
        self.requirements.clear()

    def edit_specification(self):
        selected_items = self.specifications.selectedItems()
        if not selected_items:
            return
        self.current_spec = selected_items[0]  
        spec = self.ids.specifications[self.specifications.row(self.current_spec)]
        self.spec_name.setText(spec.name)
        self.spec_description.setText(spec.description)
        self.instructions.setText(spec.instructions)
        self.identifier.setText(spec.identifier)
        cardinality = spec.get_usage().capitalize()
        self.cardinality.setCurrentIndex(self.cardinalities.index(cardinality))
        self.stacked_layout.setCurrentWidget(self.spec_layout)

    def save_specification(self):
        if self.current_spec is None:
            spec = ifctester.ids.Specification()
            self.ids.specifications.append(spec)
            item = QListWidgetItem(spec.name)
            self.specifications.addItem(item)
        else:
            self.current_spec.setText(self.spec_name.text())
            spec = self.ids.specifications[self.specifications.row(self.current_spec)]
        spec.name = self.spec_name.text()
        spec.description = self.spec_description.text()
        spec.instructions = self.instructions.text()
        spec.identifier = self.identifier.text()
        cardinality = self.cardinality.currentText().lower()
        spec.set_usage(cardinality)
        # missing: ifcVersion
        self.show_main_layout()

    def remove_specification(self):
        selected_items = self.specifications.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.ids.specifications.remove(self.specifications.row(item))
            self.specifications.takeItem(self.specifications.row(item))

    def add_applicability(self):
        pass

    def edit_applicability(self):
        pass

    def remove_applicability(self):
        pass

    def add_requirement(self):
        pass

    def edit_requirement(self):
        pass

    def remove_requirement(self):
        pass





if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = IdsEditDialog(None)
    dialog.show()
    sys.exit(app.exec_())