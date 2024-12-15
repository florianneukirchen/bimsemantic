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
    QButtonGroup,
    QRadioButton,
    QSpacerItem,
    QSizePolicy,
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

        self.current_applicability = []
        self.current_requirement = []

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
        self.addspecification = QPushButton(self.tr("New Specification"))
        self.addspecification.clicked.connect(self.add_specification)
        buttonlayout.addWidget(self.addspecification)
        self.removespecification = QPushButton(self.tr("Remove Specification"))
        self.removespecification.clicked.connect(self.remove_specification)
        buttonlayout.addWidget(self.removespecification)
        self.editspecification = QPushButton(self.tr("Edit Specification"))
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
        self.spec_instructions = QLineEdit()
        layout.addWidget(self.spec_instructions, 2, 1)

        layout.addWidget(QLabel(self.tr("Identifier")), 3, 0)
        self.identifier = QLineEdit()
        layout.addWidget(self.identifier, 3, 1)

        layout.addWidget(QLabel(self.tr("Cardinality")), 4, 0)
        self.spec_cardinality = QComboBox()
        self.spec_cardinality.addItems(self.cardinalities)
        layout.addWidget(self.spec_cardinality, 4, 1)

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
        layout = self.facet_layout.layout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.used_for_label = QLabel()
        self.facet_type_label = QLabel()
        font = self.facet_type_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.facet_type_label.setFont(font)
        self.used_for_label.setFont(font)
        layout.addWidget(self.facet_type_label, 0, 0)
        layout.addWidget(self.used_for_label, 0, 1)
        
        self.label1 = QLabel()
        self.label2 = QLabel()
        self.label3 = QLabel()
        self.label4 = QLabel()
        self.label5 = QLabel()
        self.instructions_label = QLabel("Instructions")
        self.cardinality_label = QLabel("Cardinality")

        layout.addWidget(self.label1, 1, 0)
        layout.addWidget(self.label2, 2, 0)
        layout.addWidget(self.label3, 3, 0)
        layout.addWidget(self.label4, 4, 0)
        layout.addWidget(self.label5, 5, 0)
        layout.addWidget(self.instructions_label, 6, 0)
        layout.addWidget(self.cardinality_label, 7, 0)

        self.parameter1 = QLineEdit()
        self.parameter2 = QLineEdit()
        self.parameter3 = QLineEdit()
        self.parameter4 = QLineEdit()
        self.parameter5 = QLineEdit()
        self.facet_instructions = QLineEdit()
        self.facet_cardinality = QComboBox()
        self.facet_cardinality.addItems(self.cardinalities)

        layout.addWidget(self.parameter1, 1, 1)
        layout.addWidget(self.parameter2, 2, 1)
        layout.addWidget(self.parameter3, 3, 1)
        layout.addWidget(self.parameter4, 4, 1)
        layout.addWidget(self.parameter5, 5, 1)
        layout.addWidget(self.facet_instructions, 6, 1)
        layout.addWidget(self.facet_cardinality, 7, 1)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer, 8, 1)

        buttonlayout = QHBoxLayout()
        layout.addLayout(buttonlayout, 9, 1)
        self.back_to_spec = QPushButton(self.tr("Cancel"))
        self.back_to_spec.clicked.connect(self.show_spec_layout)
        buttonlayout.addWidget(self.back_to_spec)
        self.save_fac_btn = QPushButton(self.tr("Save"))
        self.save_fac_btn.clicked.connect(self.save_facet)
        buttonlayout.addWidget(self.save_fac_btn)

    def show_main_layout(self):
        self.stacked_layout.setCurrentWidget(self.main_layout)

    def show_spec_layout(self):
        self.stacked_layout.setCurrentWidget(self.spec_layout)

    def show_facet_layout(self, facet_type, facet=None):
        self.facet_type_label.setText(facet_type)
        if facet:
            self.facet_instructions.setText(facet.instructions)
            try:
                self.facet_cardinality.setCurrentIndex(self.cardinalities.index(facet.cardinality.capitalize()))
            except AttributeError:
                pass
        else:
            self.facet_instructions.clear()
            self.facet_cardinality.setCurrentIndex(0)
        if facet_type == "Entity":
            self.label1.setText("Name")
            self.label2.setText("predefinedType")
            self.label3.hide()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.hide()
            self.parameter3.hide()
            self.parameter4.hide()
            self.parameter5.hide()
            self.facet_cardinality.hide()
            if facet:
                self.parameter1.setText(facet.name)
                self.parameter2.setText(facet.predefinedType)
            else:
                self.parameter1.clear()
                self.parameter2.clear()
        elif facet_type == "Attribute":
            self.label1.setText("Name")
            self.label2.setText("Value")
            self.label3.hide()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.show()
            self.parameter3.hide()
            self.parameter4.hide()
            self.parameter5.hide()
            self.facet_cardinality.show()
            if facet:
                self.parameter1.setText(facet.name)
                self.parameter2.setText(facet.value)
            else:
                self.parameter1.clear()
                self.parameter2.clear()
        elif facet_type == "Property":
            self.label1.setText("Property Set")
            self.label2.setText("Property Name")
            self.label3.setText("Value")
            self.label4.setText("Data Type")
            self.label5.setText("URI")
            self.label3.show()
            self.label4.show()
            self.label5.show()
            self.cardinality_label.show()
            self.parameter3.show()
            self.parameter4.show()
            self.parameter5.show()
            self.facet_cardinality.show()
            if facet:
                self.parameter1.setText(facet.propertySet)
                self.parameter2.setText(facet.baseName)
                self.parameter3.setText(facet.value)
                self.parameter4.setText(facet.dataType)
                self.parameter5.setText(facet.uri)
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.parameter3.clear()
                self.parameter4.clear()
                self.parameter5.clear()
        elif facet_type == "PartOf":
            self.label1.setText("Name")
            self.label2.setText("Predifined Type")
            self.label3.setText("Relation")
            self.label3.show()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.show()
            self.parameter3.show()
            self.parameter4.hide()
            self.parameter5.hide()
            self.facet_cardinality.show()
            if facet:
                self.parameter1.setText(facet.name)
                self.parameter2.setText(facet.predefinedType)
                self.parameter3.setText(facet.relation)
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.parameter3.clear()
        elif facet_type == "Material":
            self.label1.setText("Value")
            self.label2.setText("URI")
            self.label3.hide()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.show()
            self.parameter3.hide()
            self.parameter4.hide()
            self.parameter5.hide()
            self.facet_cardinality.show()
            if facet:
                self.parameter1.setText(facet.value)
                self.parameter2.setText(facet.uri)
            else:
                self.parameter1.clear()
                self.parameter2.clear()
        elif facet_type == "Classification":
            self.label1.setText("Value")
            self.label2.setText("System")
            self.label3.setText("URI")
            self.label3.show()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.show()
            self.parameter3.show()
            self.parameter4.hide()
            self.parameter5.hide()
            self.facet_cardinality.show()
            if facet:
                self.parameter1.setText(facet.value)
                self.parameter2.setText(facet.system)
                self.parameter3.setText(facet.uri)
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.parameter3.clear()
        else:
            return
            
        self.stacked_layout.setCurrentWidget(self.facet_layout)

    def add_specification(self):
        self.current_spec = None
        self.spec_name.setText(self.tr("New Specification"))
        self.stacked_layout.setCurrentWidget(self.spec_layout)
        self.spec_description.clear()
        self.spec_instructions.clear()
        self.identifier.clear()
        self.spec_cardinality.setCurrentIndex(0)
        self.applicability.clear()
        self.requirements.clear()
        self.current_applicability = []
        self.current_requirement = []

    def edit_specification(self):
        selected_items = self.specifications.selectedItems()
        if not selected_items:
            return
        self.current_spec = selected_items[0]  
        spec = self.ids.specifications[self.specifications.row(self.current_spec)]
        self.current_applicability = spec.applicability
        for facet in spec.applicability:
            item = QListWidgetItem(facet.to_string("applicability"))
            self.applicability.addItem(item)
        self.current_requirement = spec.requirements
        for facet in spec.requirements:
            item = QListWidgetItem(facet.to_string("requirement"))
            self.requirements.addItem(item)
        self.spec_name.setText(spec.name)
        self.spec_description.setText(spec.description)
        self.spec_instructions.setText(spec.instructions)
        self.identifier.setText(spec.identifier)
        cardinality = spec.get_usage().capitalize()
        self.spec_cardinality.setCurrentIndex(self.cardinalities.index(cardinality))
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
        spec.instructions = self.spec_instructions.text()
        spec.identifier = self.identifier.text()
        cardinality = self.spec_cardinality.currentText().lower()
        spec.applicability = self.current_applicability
        spec.requirements = self.current_requirement
        spec.set_usage(cardinality)
        # missing: ifcVersion
        self.show_main_layout()

    def remove_specification(self):
        selected_items = self.specifications.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.ids.specifications.pop(self.specifications.row(item))
            self.specifications.takeItem(self.specifications.row(item))

    def add_applicability(self):
        dialog = ChooseFacetDialog(self)
        if dialog.exec():
            facet_type = dialog.get_facet()
            if facet_type:
                self.current_facet = None
                self.used_for_label.setText("Applicability")
                self.show_facet_layout(facet_type)

    def edit_applicability(self):
        selected_items = self.applicability.selectedItems()
        if not selected_items:
            return
        self.current_facet = selected_items[0]
        facet = self.current_applicability[self.applicability.row(self.current_facet)]
        self.used_for_label.setText("Applicability")
        self.show_facet_layout(facet.__class__.__name__, facet)

    def remove_applicability(self):
        selected_items = self.applicability.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            print("item", item)
            print("row", self.applicability.row(item))
            self.current_applicability.pop(self.applicability.row(item))
            self.applicability.takeItem(self.applicability.row(item))


    def add_requirement(self):
        dialog = ChooseFacetDialog(self)
        if dialog.exec():
            facet_type = dialog.get_facet()
            if facet_type:
                self.current_facet = None
                self.used_for_label.setText("Requirement")
                self.show_facet_layout(facet_type)

    def edit_requirement(self):
        selected_items = self.requirements.selectedItems()
        if not selected_items:
            return
        self.current_facet = selected_items[0]
        facet = self.current_requirement[self.requirements.row(self.current_facet)]
        self.used_for_label.setText("Requirement")
        self.show_facet_layout(facet.__class__.__name__, facet)

    def remove_requirement(self):
        selected_items = self.requirements.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            print("item", item)
            print("row", self.applicability.row(item))
            self.current_requirement.pop(self.requirements.row(item))
            self.requirements.takeItem(self.requirements.row(item))

    def save_facet(self):
        used_for = self.used_for_label.text().lower()
        if used_for == "applicability":
            listview = self.applicability
            spec_part = self.current_applicability
            spec = None # not used
        else:
            listview = self.requirements
            spec_part = self.current_requirement
            # Create a dummy spec, only the cardinality is required
            spec = ifctester.ids.Specification()
            spec.set_usage(self.spec_cardinality.currentText().lower())

        if self.current_facet is None:
            # New facet
            facet_type = self.facet_type_label.text()
            if facet_type == "Entity":
                facet = ifctester.ids.Entity()
            elif facet_type == "Attribute":
                facet = ifctester.ids.Attribute()
            elif facet_type == "Property":
                facet = ifctester.ids.Property()
            elif facet_type == "PartOf":
                facet = ifctester.ids.PartOf()
            elif facet_type == "Material":
                facet = ifctester.ids.Material()
            elif facet_type == "Classification":
                facet = ifctester.ids.Classification()
            else:
                return
            
            
            spec_part.append(facet)
            item = QListWidgetItem()
            listview.addItem(item)

        else:
            # Update existing facet
            facet = self.current_spec.facets[self.current_spec.facets.index(self.current_facet)]
            item = listview.item(listview.row(self.current_facet))

        # Set data
        facet.instructions = self.facet_instructions.text()

        if not isinstance(facet, ifctester.ids.Entity):
            facet.cardinality = self.facet_cardinality.currentText().lower()

        if isinstance(facet, ifctester.ids.Entity):
            facet.name = self.parameter1.text()
            facet.predefinedType = self.parameter2.text()
            facet.cardinality = None
        elif isinstance(facet, ifctester.ids.Attribute):
            facet.name = self.parameter1.text()
            facet.value = self.parameter2.text()
        elif isinstance(facet, ifctester.ids.Property):
            facet.propertySet = self.parameter1.text()
            facet.baseName = self.parameter2.text()
            facet.value = self.parameter3.text()
            facet.dataType = self.parameter4.text()
            facet.uri = self.parameter5.text()
        elif isinstance(facet, ifctester.ids.PartOf):
            facet.name = self.parameter1.text()
            facet.predefinedType = self.parameter2.text()
            facet.relation = self.parameter3.text()
        elif isinstance(facet, ifctester.ids.Material):
            facet.value = self.parameter1.text()
            facet.uri = self.parameter2.text()
        elif isinstance(facet, ifctester.ids.Classification):
            facet.value = self.parameter1.text()
            facet.system = self.parameter2.text()
            facet.uri = self.parameter3.text()
        else:
            raise NotImplementedError
        item.setText(facet.to_string(used_for, spec, facet))
        self.show_spec_layout()

class ChooseFacetDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.mainwindow = parent

        self.setWindowTitle(self.tr("Choose Facet"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel(self.tr("Choose Facet")))

        self.button_group = QButtonGroup(self)
        self.radio_button1 = QRadioButton(self.tr("Entity"))
        self.radio_button2 = QRadioButton(self.tr("Attribute"))
        self.radio_button3 = QRadioButton(self.tr("Property"))
        self.radio_button4 = QRadioButton(self.tr("PartOf"))
        self.radio_button5 = QRadioButton(self.tr("Material"))
        self.radio_button6 = QRadioButton(self.tr("Classification"))

        self.button_group.addButton(self.radio_button1)
        self.button_group.addButton(self.radio_button2)
        self.button_group.addButton(self.radio_button3)
        self.button_group.addButton(self.radio_button4)
        self.button_group.addButton(self.radio_button5)
        self.button_group.addButton(self.radio_button6)

        self.radio_button1.setChecked(True)

        layout.addWidget(self.radio_button1)
        layout.addWidget(self.radio_button2)
        layout.addWidget(self.radio_button3)
        layout.addWidget(self.radio_button4)
        layout.addWidget(self.radio_button5)
        layout.addWidget(self.radio_button6)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_facet(self):
        selected_button = self.button_group.checkedButton()
        if selected_button:
            return selected_button.text()
        return None
    


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = IdsEditDialog(None)
    dialog.show()
    sys.exit(app.exec_())