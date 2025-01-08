import re
from xmlschema.validators.exceptions import XMLSchemaValidationError
from xmlschema.validators import identities
from elementpath.regex.codepoints import RegexError
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QStackedLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QWidget,
    QComboBox,
    QButtonGroup,
    QRadioButton,
    QSpacerItem,
    QSizePolicy,
    QMessageBox,
    QCheckBox,
    QDateEdit,
    QFileDialog,
)
import ifctester

# IFC Versions allowed in IDS Version 1.0
ALLOWED_IFC_VERSIONS = ["IFC2X3", "IFC4", "IFC4X3_ADD2"]


def extract_bounds(expression):
    """Extracts min and max values and operators from a string expression

    From a string expression like '1 < value <= 10' it extracts the values and
    operators and returns them as a dictionary with the keys 'min_value',
    'min_op', 'var_name', 'max_op' and 'max_value'.

    If the expression is not valid it returns an empty dictionary. String must
    always start with lower value. It is also allowed to give only min or
    max value, e.g. 'value <= 10' or '5 < value'.

    :param expression: A string expression with min and max values and operators
    :type expression: str
    :return: A dictionary with min and max values and operators
    :rtype: dict
    """
    pattern = re.compile(
        r"(?P<min_value>\d*\.?\d+)?\s*(?P<min_op><=|<)?\s*\b(?P<var_name>\w+)\b\s*(?P<max_op><=|<)?\s*(?P<max_value>\d*\.?\d+)?"
    )
    match = pattern.match(expression)
    if match:
        return match.groupdict()
    return {}


class IdsEditDialog(QDialog):
    """Dialog for editing an IDS

    The layout changes depending on the current state of the dialog: The data
    of the IDS itself and its specifications; the data of a specification including
    its applicability and requirements; the data of a applicability or requirement
    (i.e. a facet).

    :param parent: The parent widget (main window)
    :type parent: QWidget
    :param filename: The filename (path) of the IDS to edit (None if it is a new file)
    :type filename: str
    :param ascopy: If True, the IDS is edited as a copy (a new filename must be given when saving)
    :type ascopy: bool
    """

    def __init__(self, parent, filename=None, ascopy=False):
        super().__init__(parent=parent)
        self.mainwindow = parent
        self.filename = filename

        self.current_spec = None  # Will hold item of list view self.specifications
        self.current_facet = (
            None  # Will hold item of list view self.applicability or self.requirements
        )

        self.current_spec_applicability = []  # ifctester.ids.Facet instances
        self.current_spec_requirement = []  # ifctester.ids.Facet instances

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
        self.restrictions = [
            self.tr("Simple value"),
            self.tr("Enumeration (list)"),
            self.tr("Bounds (range)"),
            self.tr("Pattern (regex)"),
            self.tr("Length (of string)"),
            self.tr("Min lenght"),
            self.tr("Max length"),
            self.tr("Min, max lenght"),
        ]

        self.setup_main_layout()
        self.setup_spec_layout()
        self.setup_facet_layout()

        if filename:
            self.ids = ifctester.ids.open(filename)
            self.setWindowTitle(self.tr("Edit IDS %s") % filename)
            self.prefill_main_layout()
        else:
            self.ids = ifctester.ids.Ids()
            self.setWindowTitle(self.tr("New IDS"))
            self.buttonBox.button(QDialogButtonBox.Save).setEnabled(False)

        if ascopy:
            self.filename = None
            self.setWindowTitle(self.tr("Edit copy of %s") % filename)

    def prefill_main_layout(self):
        """Fill the fields of the main layout form with data of the IDS file"""
        self.title.setText(self.ids.info.get("title", "Unnamed"))
        self.description.setText(self.ids.info.get("description", ""))
        self.purpose.setText(self.ids.info.get("purpose", ""))
        self.author.setText(self.ids.info.get("author", ""))
        self.copyright.setText(self.ids.info.get("copyright", ""))
        self.version.setText(self.ids.info.get("version", ""))
        self.milestone.setText(self.ids.info.get("milestone", ""))
        self.date.setDate(QDate.fromString(self.ids.info.get("date", ""), "yyyy-MM-dd"))
        self.specifications.clear()
        for spec in self.ids.specifications:
            item = QListWidgetItem(spec.name)
            self.specifications.addItem(item)

    def setup_main_layout(self):
        """Generate the main layout form (data of the IDS itself)"""
        layout = self.main_layout.layout()
        layout.addWidget(QLabel(self.tr("Title")), 0, 0)
        self.title = QLineEdit()
        self.title.setText("Unnamed")
        layout.addWidget(self.title, 0, 1)

        layout.addWidget(QLabel(self.tr("Description")), 1, 0)
        self.description = QLineEdit()
        layout.addWidget(self.description, 1, 1)

        layout.addWidget(QLabel(self.tr("Purpose")), 2, 0)
        self.purpose = QLineEdit()
        layout.addWidget(self.purpose, 2, 1)

        layout.addWidget(QLabel(self.tr("Author")), 3, 0)
        self.author = QLineEdit()
        self.author.setPlaceholderText(self.tr("Email"))
        layout.addWidget(self.author, 3, 1)

        layout.addWidget(QLabel(self.tr("Copyright")), 4, 0)
        self.copyright = QLineEdit()
        layout.addWidget(self.copyright, 4, 1)

        sublayout = QHBoxLayout()
        layout.addLayout(sublayout, 5, 1)
        self.version = QLineEdit()
        self.version.setPlaceholderText(self.tr("Version"))
        sublayout.addWidget(self.version)
        self.milestone = QLineEdit()
        self.milestone.setPlaceholderText(self.tr("Milestone"))
        sublayout.addWidget(self.milestone)
        self.date = QDateEdit()
        self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setDate(QDate.currentDate())
        self.date.setToolTip(self.tr("Date of publication of the IDS"))
        self.date.setCalendarPopup(True)
        sublayout.addWidget(self.date)

        layout.addWidget(QLabel(self.tr("Specifications")), 6, 0)
        self.specifications = QListWidget()
        layout.addWidget(self.specifications, 6, 1)

        buttonlayout = QHBoxLayout()
        layout.addLayout(buttonlayout, 7, 1)
        self.addspecification = QPushButton(self.tr("New Specification"))
        self.addspecification.clicked.connect(self.add_specification)
        buttonlayout.addWidget(self.addspecification)
        self.removespecification = QPushButton(self.tr("Remove Specification"))
        self.removespecification.clicked.connect(self.remove_specification)
        buttonlayout.addWidget(self.removespecification)
        self.editspecification = QPushButton(self.tr("Edit Specification"))
        self.editspecification.clicked.connect(self.edit_specification)
        buttonlayout.addWidget(self.editspecification)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)
        layout.addItem(spacer, 8, 1)

        QBtn = QDialogButtonBox.Save | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.main_layout.layout().addWidget(self.buttonBox, 9, 1)

    def setup_spec_layout(self):
        """Setup the specification form"""
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
        self.spec_cardinality.currentTextChanged.connect(self.cardinality_changed)

        layout.addWidget(QLabel(self.tr("IFC Versions")), 5, 0)
        checklayout = QHBoxLayout()
        layout.addLayout(checklayout, 5, 1)
        self.ifc_versions = [QCheckBox(version) for version in ALLOWED_IFC_VERSIONS]
        for cb in self.ifc_versions:
            cb.setChecked(True)
            checklayout.addWidget(cb)

        # Applicability
        layout.addWidget(QLabel(self.tr("Applicability")), 6, 0)
        self.applicability = QListWidget()
        layout.addWidget(self.applicability, 6, 1)

        buttonlayout1 = QHBoxLayout()
        layout.addLayout(buttonlayout1, 7, 1)
        self.addapplicability = QPushButton(self.tr("New"))
        self.addapplicability.clicked.connect(self.add_applicability)
        buttonlayout1.addWidget(self.addapplicability)
        self.removeapplicability = QPushButton(self.tr("Remove"))
        self.removeapplicability.clicked.connect(self.remove_applicability)
        buttonlayout1.addWidget(self.removeapplicability)
        self.editapplicability = QPushButton(self.tr("Edit"))
        self.editapplicability.clicked.connect(self.edit_applicability)
        buttonlayout1.addWidget(self.editapplicability)

        spacer = QSpacerItem(5, 5, QSizePolicy.Minimum, QSizePolicy.Minimum)
        layout.addItem(spacer, 8, 1)

        layout.addWidget(QLabel(self.tr("Requirements")), 9, 0)
        self.requirements = QListWidget()
        layout.addWidget(self.requirements, 9, 1)

        buttonlayout2 = QHBoxLayout()
        layout.addLayout(buttonlayout2, 10, 1)
        self.addrequirements = QPushButton(self.tr("New"))
        self.addrequirements.clicked.connect(self.add_requirement)
        buttonlayout2.addWidget(self.addrequirements)
        self.removerequirements = QPushButton(self.tr("Remove"))
        self.removerequirements.clicked.connect(self.remove_requirement)
        buttonlayout2.addWidget(self.removerequirements)
        self.editrequirements = QPushButton(self.tr("Edit"))
        self.editrequirements.clicked.connect(self.edit_requirement)
        buttonlayout2.addWidget(self.editrequirements)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)
        layout.addItem(spacer, 11, 1)

        buttonlayout3 = QHBoxLayout()
        self.spec_layout.layout().addLayout(buttonlayout3, 12, 1)
        self.back_to_main = QPushButton(self.tr("Cancel"))
        self.back_to_main.clicked.connect(self.show_main_layout)
        buttonlayout3.addWidget(self.back_to_main)
        self.save_spec_btn = QPushButton(self.tr("Save Specification"))
        self.save_spec_btn.clicked.connect(self.save_specification)
        buttonlayout3.addWidget(self.save_spec_btn)

    def setup_facet_layout(self):
        """Setup the facet form (used for a requirement or applicability)"""
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

        self.restriction1 = QComboBox()
        self.restriction1.addItems(self.restrictions)
        self.restriction2 = QComboBox()
        self.restriction2.addItems(self.restrictions)
        self.restriction3 = QComboBox()
        self.restriction3.addItems(self.restrictions)
        self.restriction4 = QComboBox()
        self.restriction4.addItems(self.restrictions)
        self.restriction5 = QComboBox()
        self.restriction5.addItems(self.restrictions)

        layout.addWidget(self.restriction1, 1, 2)
        layout.addWidget(self.restriction2, 2, 2)
        layout.addWidget(self.restriction3, 3, 2)
        layout.addWidget(self.restriction4, 4, 2)
        layout.addWidget(self.restriction5, 5, 2)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer, 8, 1)

        buttonlayout = QHBoxLayout()
        layout.addLayout(buttonlayout, 9, 1)
        self.back_to_spec = QPushButton(self.tr("Cancel"))
        self.back_to_spec.clicked.connect(self.show_spec_layout)
        buttonlayout.addWidget(self.back_to_spec)
        self.save_fac_btn = QPushButton(self.tr("OK"))
        self.save_fac_btn.clicked.connect(self.save_facet)
        buttonlayout.addWidget(self.save_fac_btn)

    def cardinality_changed(self, text):
        """Callback for toggeling the cardinality"""
        # In theory this influences the text of the requirements, see line 131 in
        # https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.8.0/src/ifctester/ifctester/facet.py
        # However it does not have an effect, seems to be a bug in ifctester
        for index in range(self.requirements.count()):
            requirement = self.current_spec_requirement[index]
            if not isinstance(requirement, ifctester.ids.Entity):
                dummy_spec = ifctester.ids.Specification()
                dummy_spec.set_usage(text.lower())
                item = self.requirements.item(index)
                # If requirement, to_string() must be called with a spec (with cardinality set)
                # and the requirement itself (why? Why not using self?)
                # See: https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.8.0/src/ifctester/ifctester/reporter.py#L188
                item.setText(
                    requirement.to_string("requirement", dummy_spec, requirement)
                )

    def show_main_layout(self):
        """Show the main form in the dialog"""
        self.stacked_layout.setCurrentWidget(self.main_layout)

    def show_spec_layout(self):
        """Show the specification form in the dialog"""
        self.stacked_layout.setCurrentWidget(self.spec_layout)

    def set_parameter_and_restriction(self, value, parameter, combo):
        """Set parameter and restriction-combo box in the facet layout

        Used when editing an existing applicability or requirement. The value
        can be a simple value or a restriction.

        :param value: The value of the parameter (numeric, string or restriction)
        :type value: str or ifctester.facet.Restriction
        """
        if isinstance(value, ifctester.facet.Restriction):
            keys = value.options.keys()
            if "enumeration" in keys:
                combo.setCurrentIndex(1)
                parameter.setText(", ".join(value.options["enumeration"]))
            elif "pattern" in keys:
                combo.setCurrentIndex(3)
                parameter.setText(value.options["pattern"])
            elif "minLength" in keys and "maxLength" in keys:
                combo.setCurrentIndex(7)
                parameter.setText(
                    f"{value.options['minLength']}, {value.options['maxLength']}"
                )
            elif "minLength" in keys:
                combo.setCurrentIndex(5)
                parameter.setText(value.options["minLength"])
            elif "maxLength" in keys:
                combo.setCurrentIndex(6)
                parameter.setText(value.options["maxLength"])
            else:
                combo.setCurrentIndex(2)
                min_value, max_value = "", ""
                for k, v in value.options.items():
                    if k.startswith("min"):
                        min_value = str(v)
                        if k.endswith("Inclusive"):
                            min_value += " <="
                        else:
                            min_value += " < "
                    if k.startswith("max"):
                        max_value = str(v)
                        if k.endswith("Inclusive"):
                            max_value = " <= " + max_value
                        else:
                            max_value = " < " + max_value

                parameter.setText(f"{min_value} value {max_value}")
        else:
            combo.setCurrentIndex(0)
            parameter.setText(str(value))

    def get_parameter_or_restriction(self, parameter, combo):
        """Get parameter as simple value or as restriction

        The parameter can be a simple value (string) or a restriction (if the
        combo box is not at index 0). The restriction is returned as an instance
        of ifctester.facet.Restriction.

        :param parameter: The QLineEdit widget with the parameter value
        :type parameter: QLineEdit
        :param combo: The QComboBox widget with the restriction type
        :type combo: QComboBox
        :return: The parameter value as simple value or restriction
        :rtype: str or ifctester.facet.Restriction
        """
        combo_index = combo.currentIndex()
        text = parameter.text().strip()
        if not text:
            return None
        if combo_index == 0:
            return text
        elif combo_index == 1:
            enumeration = [s.strip() for s in text.split(",")]
            return ifctester.facet.Restriction({"enumeration": enumeration})
        elif combo_index == 2:
            bounds = extract_bounds(text)
            if bounds:
                options = {}
                if bounds["min_op"] == "<=":
                    options["minInclusive"] = bounds["min_value"]
                elif bounds["min_op"] == "<":
                    options["minExclusive"] = bounds["min_value"]
                if bounds["max_op"] == "<=":
                    options["maxInclusive"] = bounds["max_value"]
                elif bounds["max_op"] == "<":
                    options["maxExclusive"] = bounds["max_value"]
                restriction = ifctester.facet.Restriction(options)
                restriction.base = "double"
                return restriction
            else:
                return None  # Fallback for invalid input
        elif combo_index == 3:
            return ifctester.facet.Restriction({"pattern": text})
        elif combo_index == 4:
            return ifctester.facet.Restriction({"length": int(text)})
        elif combo_index == 5:
            return ifctester.facet.Restriction({"minLength": int(text)})
        elif combo_index == 6:
            return ifctester.facet.Restriction({"maxLength": int(text)})
        else:
            min_length, max_length = text.split(",")
            return ifctester.facet.Restriction(
                {"minLength": int(min_length), "maxLength": int(max_length)}
            )

    def required_parameters(self, indexes):
        """Set placeholder text for required parameters"""
        parameters = [
            self.parameter1,
            self.parameter2,
            self.parameter3,
            self.parameter4,
            self.parameter5,
        ]
        for i, parameter in enumerate(parameters):
            if i + 1 in indexes:
                parameter.setPlaceholderText(self.tr("Required"))
            else:
                parameter.setPlaceholderText("")

    def show_facet_layout(self, facet_type, facet=None):
        """Show the facet layout for a given facet type"""
        self.facet_type_label.setText(facet_type)
        if facet:
            self.facet_instructions.setText(facet.instructions)
            try:
                self.facet_cardinality.setCurrentIndex(
                    self.cardinalities.index(facet.cardinality.capitalize())
                )
            except AttributeError:
                pass
        else:
            self.facet_instructions.clear()
            self.facet_cardinality.setCurrentIndex(0)
        if facet_type == "Entity":
            self.required_parameters([1])
            self.label1.setText("Name")
            self.label2.setText("predefinedType")
            self.label3.hide()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.hide()
            self.parameter3.hide()
            self.parameter4.hide()
            self.parameter5.hide()
            self.restriction3.hide()
            self.restriction4.hide()
            self.restriction5.hide()
            self.facet_cardinality.hide()
            if facet:
                self.set_parameter_and_restriction(
                    facet.name, self.parameter1, self.restriction1
                )
                self.set_parameter_and_restriction(
                    facet.predefinedType, self.parameter2, self.restriction2
                )
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.restriction1.setCurrentIndex(0)
                self.restriction2.setCurrentIndex(0)
        elif facet_type == "Attribute":
            self.required_parameters([1])
            self.label1.setText("Name")
            self.label2.setText("Value")
            self.label3.hide()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.show()
            self.parameter3.hide()
            self.parameter4.hide()
            self.parameter5.hide()
            self.restriction3.hide()
            self.restriction4.hide()
            self.restriction5.hide()
            self.facet_cardinality.show()
            if facet:
                self.set_parameter_and_restriction(
                    facet.name, self.parameter1, self.restriction1
                )
                self.set_parameter_and_restriction(
                    facet.value, self.parameter2, self.restriction2
                )
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.restriction1.setCurrentIndex(0)
                self.restriction2.setCurrentIndex(0)
        elif facet_type == "Property":
            self.required_parameters([1, 2])
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
            self.restriction3.show()
            self.restriction4.show()
            self.restriction5.show()
            self.facet_cardinality.show()
            if facet:
                self.set_parameter_and_restriction(
                    facet.propertySet, self.parameter1, self.restriction1
                )
                self.set_parameter_and_restriction(
                    facet.baseName, self.parameter2, self.restriction2
                )
                self.set_parameter_and_restriction(
                    facet.value, self.parameter3, self.restriction3
                )
                self.set_parameter_and_restriction(
                    facet.dataType, self.parameter4, self.restriction4
                )
                self.set_parameter_and_restriction(
                    facet.uri, self.parameter5, self.restriction5
                )
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.parameter3.clear()
                self.parameter4.clear()
                self.parameter5.clear()
                self.restriction1.setCurrentIndex(0)
                self.restriction2.setCurrentIndex(0)
                self.restriction3.setCurrentIndex(0)
                self.restriction4.setCurrentIndex(0)
                self.restriction5.setCurrentIndex(0)
        elif facet_type == "PartOf":
            self.required_parameters([1])
            self.label1.setText("Entity")
            self.label2.setText("Predifined Type")
            self.label3.setText("Relation")
            self.label3.show()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.show()
            self.parameter3.show()
            self.parameter4.hide()
            self.parameter5.hide()
            self.restriction3.show()
            self.restriction4.hide()
            self.restriction5.hide()
            self.facet_cardinality.show()
            if facet:
                self.set_parameter_and_restriction(
                    facet.name, self.parameter1, self.restriction1
                )
                self.set_parameter_and_restriction(
                    facet.predefinedType, self.parameter2, self.restriction2
                )
                self.set_parameter_and_restriction(
                    facet.relation, self.parameter3, self.restriction3
                )
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.parameter3.clear()
                self.restriction1.setCurrentIndex(0)
                self.restriction2.setCurrentIndex(0)
                self.restriction3.setCurrentIndex(0)
        elif facet_type == "Material":
            self.required_parameters([])
            self.label1.setText("Value")
            self.label2.setText("URI")
            self.label3.hide()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.show()
            self.parameter3.hide()
            self.parameter4.hide()
            self.parameter5.hide()
            self.restriction3.hide()
            self.restriction4.hide()
            self.restriction5.hide()
            self.facet_cardinality.show()
            if facet:
                self.set_parameter_and_restriction(
                    facet.value, self.parameter1, self.restriction1
                )
                self.set_parameter_and_restriction(
                    facet.uri, self.parameter2, self.restriction2
                )
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.restriction1.setCurrentIndex(0)
                self.restriction2.setCurrentIndex(0)
        elif facet_type == "Classification":
            self.required_parameters([1])
            self.label1.setText("System")
            self.label2.setText("Value")
            self.label3.setText("URI")
            self.label3.show()
            self.label4.hide()
            self.label5.hide()
            self.cardinality_label.show()
            self.parameter3.show()
            self.parameter4.hide()
            self.parameter5.hide()
            self.restriction3.show()
            self.restriction4.hide()
            self.restriction5.hide()
            self.facet_cardinality.show()
            if facet:
                self.set_parameter_and_restriction(
                    facet.value, self.parameter1, self.restriction1
                )
                self.set_parameter_and_restriction(
                    facet.system, self.parameter2, self.restriction2
                )
                self.set_parameter_and_restriction(
                    facet.uri, self.parameter3, self.restriction3
                )
            else:
                self.parameter1.clear()
                self.parameter2.clear()
                self.parameter3.clear()
                self.restriction1.setCurrentIndex(0)
                self.restriction2.setCurrentIndex(0)
                self.restriction3.setCurrentIndex(0)
        else:
            return

        self.stacked_layout.setCurrentWidget(self.facet_layout)

    def add_specification(self):
        """Add a new specification to the IDS and edit it"""
        self.current_spec = None
        self.spec_name.setText(self.tr("New Specification"))
        self.stacked_layout.setCurrentWidget(self.spec_layout)
        self.spec_description.clear()
        self.spec_instructions.clear()
        self.identifier.clear()
        self.spec_cardinality.setCurrentIndex(0)
        self.applicability.clear()
        self.requirements.clear()
        self.current_spec_applicability = []
        self.current_spec_requirement = []

    def edit_specification(self):
        """Edit the selected specification"""
        selected_items = self.specifications.selectedItems()
        if not selected_items:
            return
        self.current_spec = selected_items[0]
        spec = self.ids.specifications[self.specifications.row(self.current_spec)]
        self.current_spec_applicability = spec.applicability
        self.current_spec_requirement = spec.requirements
        # Prepare the list views
        self.applicability.clear()
        self.requirements.clear()
        for facet in spec.applicability:
            title = f'{facet.__class__.__name__}: {facet.to_string("applicability")}'
            item = QListWidgetItem(title)
            self.applicability.addItem(item)
        self.current_spec_requirement = spec.requirements
        for facet in spec.requirements:
            title = f'{facet.__class__.__name__}: {facet.to_string("requirement", spec, facet)}'
            item = QListWidgetItem(title)
            self.requirements.addItem(item)
        self.spec_name.setText(spec.name)
        self.spec_description.setText(spec.description)
        self.spec_instructions.setText(spec.instructions)
        self.identifier.setText(spec.identifier)
        cardinality = spec.get_usage().capitalize()
        self.spec_cardinality.setCurrentIndex(self.cardinalities.index(cardinality))
        self.stacked_layout.setCurrentWidget(self.spec_layout)

    def save_specification(self):
        """Save the specification data"""
        spec_name = self.spec_name.text().strip() or "Unnamed"  # Use a default if ""
        if self.current_spec is None:
            spec = ifctester.ids.Specification()
            self.ids.specifications.append(spec)
            item = QListWidgetItem()
            self.specifications.addItem(item)
        else:
            spec = self.ids.specifications[self.specifications.row(self.current_spec)]
            item = self.current_spec  # in list view
        spec.name = spec_name
        item.setText(spec_name)
        spec.description = self.spec_description.text().strip() or None
        spec.instructions = self.spec_instructions.text().strip() or None
        spec.identifier = self.identifier.text().strip() or None
        cardinality = self.spec_cardinality.currentText().lower()
        spec.applicability = self.current_spec_applicability
        spec.requirements = self.current_spec_requirement
        spec.set_usage(cardinality)
        ifc_versions = [cb.text() for cb in self.ifc_versions if cb.isChecked()]
        if not ifc_versions:
            ifc_versions = ALLOWED_IFC_VERSIONS
        spec.ifcVersion = ifc_versions
        self.show_main_layout()
        if self.specifications.count() > 0:
            self.buttonBox.button(QDialogButtonBox.Save).setEnabled(True)

    def remove_specification(self):
        """Remove the selected specification"""
        selected_items = self.specifications.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.ids.specifications.pop(self.specifications.row(item))
            self.specifications.takeItem(self.specifications.row(item))

        if self.specifications.count() == 0:
            self.buttonBox.button(QDialogButtonBox.Save).setEnabled(False)

    def add_applicability(self):
        """Add a new applicability to the current specification and edit it"""
        dialog = ChooseFacetDialog(self)
        if dialog.exec():
            facet_type = dialog.get_facet()
            if facet_type:
                self.current_facet = None
                self.used_for_label.setText("Applicability")
                self.show_facet_layout(facet_type)

    def edit_applicability(self):
        """Edit the selected applicability"""
        selected_items = self.applicability.selectedItems()
        if not selected_items:
            return
        self.current_facet = selected_items[0]
        facet = self.current_spec_applicability[
            self.applicability.row(self.current_facet)
        ]
        self.used_for_label.setText("Applicability")
        self.show_facet_layout(facet.__class__.__name__, facet)

    def remove_applicability(self):
        """Remove the selected applicability"""
        selected_items = self.applicability.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.current_spec_applicability.pop(self.applicability.row(item))
            self.applicability.takeItem(self.applicability.row(item))

    def add_requirement(self):
        """Add a new requirement to the current specification and edit it"""
        dialog = ChooseFacetDialog(self)
        if dialog.exec():
            facet_type = dialog.get_facet()
            if facet_type:
                self.current_facet = None
                self.used_for_label.setText("Requirement")
                self.show_facet_layout(facet_type)

    def edit_requirement(self):
        """Edit the selected requirement"""
        selected_items = self.requirements.selectedItems()
        if not selected_items:
            return
        self.current_facet = selected_items[0]
        facet = self.current_spec_requirement[self.requirements.row(self.current_facet)]
        self.used_for_label.setText("Requirement")
        self.show_facet_layout(facet.__class__.__name__, facet)

    def remove_requirement(self):
        """Remove the selected requirement"""
        selected_items = self.requirements.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.current_spec_requirement.pop(self.requirements.row(item))
            self.requirements.takeItem(self.requirements.row(item))

    def save_facet(self):
        """Save the facet data as applicability or requirement

        Also validates the input according to the IDS spec.
        """
        # Check if all required parameters are set
        parameter_list = [
            self.parameter1,
            self.parameter2,
            self.parameter3,
            self.parameter4,
            self.parameter5,
        ]
        for parameter in parameter_list:
            if (
                parameter.placeholderText() == self.tr("Required")
                and not parameter.text()
            ):
                mb = QMessageBox()
                mb.setText(self.tr("All required parameters must be specified"))
                mb.setWindowTitle(self.tr("Missing required parameter"))
                mb.exec()
                return

        # Validate parameters
        combo_list = [
            self.restriction1,
            self.restriction2,
            self.restriction3,
            self.restriction4,
            self.restriction5,
        ]
        for combo, parameter in zip(combo_list, parameter_list):
            if combo.currentIndex() == 2:
                bounds = extract_bounds(parameter.text().strip())
                if bounds:
                    min_value = bounds.get("min_value", "0")
                    max_value = bounds.get("max_value", "0")
                    if min_value is None and max_value is None:
                        min_value = "invalid"  # Trigger the exception
                    try:
                        if min_value is not None:
                            min_value = float(min_value)
                        if max_value is not None:
                            max_value = float(max_value)
                        if min_value >= max_value:
                            raise ValueError
                    except ValueError:
                        mb = QMessageBox()
                        mb.setText(
                            self.tr(
                                "Invalid bounds:\nShould be in the form of\n2 < value <= 10"
                            )
                        )
                        mb.setWindowTitle(self.tr("Invalid bounds"))
                        mb.exec()
                        return
            elif combo.currentIndex() == 3:
                pattern = parameter.text().strip()
                try:
                    # This is how the pattern is used in ifctester
                    # Make sure it will not throw an exception when validating
                    identities.translate_pattern(pattern)
                except RegexError:
                    mb = QMessageBox()
                    mb.setText(self.tr("Invalid regex pattern:\n%s") % pattern)
                    mb.setWindowTitle(self.tr("Invalid regex pattern"))
                    mb.exec()
                    return
            elif combo.currentIndex() in [4, 5, 6]:
                try:
                    _ = int(parameter.text().strip())
                except ValueError:
                    mb = QMessageBox()
                    mb.setText(self.tr("Invalid length:\nShould be an integer"))
                    mb.setWindowTitle(self.tr("Invalid length"))
                    mb.exec()
                    return
            elif combo.currentIndex() == 7:
                try:
                    min_length, max_length = parameter.text().split(",")
                    _ = int(min_length)
                    _ = int(max_length)
                except ValueError:
                    mb = QMessageBox()
                    mb.setText(
                        self.tr(
                            "Invalid length:\nShould be two integers separated by a comma"
                        )
                    )
                    mb.setWindowTitle(self.tr("Invalid length"))
                    mb.exec()

        # Save the Facet as Aplicability or Requirement
        used_for = self.used_for_label.text().lower()
        if used_for == "applicability":
            listview = self.applicability
            spec_part = self.current_spec_applicability
            spec = None  # not used
        else:
            listview = self.requirements
            spec_part = self.current_spec_requirement
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
            index = listview.row(self.current_facet)
            item = listview.item(index)
            facet = spec_part[index]

        # Set data
        facet.instructions = self.facet_instructions.text().strip()

        if not isinstance(facet, ifctester.ids.Entity):
            facet.cardinality = self.facet_cardinality.currentText().lower()

        if isinstance(facet, ifctester.ids.Entity):
            facet.name = self.get_parameter_or_restriction(
                self.parameter1, self.restriction1
            )
            facet.predefinedType = self.get_parameter_or_restriction(
                self.parameter2, self.restriction2
            )
            facet.cardinality = None
        elif isinstance(facet, ifctester.ids.Attribute):
            facet.name = self.get_parameter_or_restriction(
                self.parameter1, self.restriction1
            )
            facet.value = self.get_parameter_or_restriction(
                self.parameter2, self.restriction2
            )
        elif isinstance(facet, ifctester.ids.Property):
            facet.propertySet = self.get_parameter_or_restriction(
                self.parameter1, self.restriction1
            )
            facet.baseName = self.get_parameter_or_restriction(
                self.parameter2, self.restriction2
            )
            facet.value = self.get_parameter_or_restriction(
                self.parameter3, self.restriction3
            )
            facet.dataType = self.get_parameter_or_restriction(
                self.parameter4, self.restriction4
            )
            facet.uri = self.get_parameter_or_restriction(
                self.parameter5, self.restriction5
            )
        elif isinstance(facet, ifctester.ids.PartOf):
            facet.name = self.get_parameter_or_restriction(
                self.parameter1, self.restriction1
            )
            facet.predefinedType = self.get_parameter_or_restriction(
                self.parameter2, self.restriction2
            )
            facet.relation = self.get_parameter_or_restriction(
                self.parameter3, self.restriction3
            )
        elif isinstance(facet, ifctester.ids.Material):
            facet.value = self.get_parameter_or_restriction(
                self.parameter1, self.restriction1
            )
            facet.uri = self.get_parameter_or_restriction(
                self.parameter2, self.restriction2
            )
        elif isinstance(facet, ifctester.ids.Classification):
            facet.system = self.get_parameter_or_restriction(
                self.parameter1, self.restriction1
            )
            facet.value = self.get_parameter_or_restriction(
                self.parameter2, self.restriction2
            )
            facet.uri = self.get_parameter_or_restriction(
                self.parameter3, self.restriction3
            )
        else:
            raise NotImplementedError
        title = f"{facet.__class__.__name__}: {facet.to_string(used_for, spec, facet)}"
        item.setText(title)
        self.show_spec_layout()

    def accept(self):
        """Save the IDS.

        This method is run if the user clicks OK (overwriting the default method).
        Final validation of the data (and return with a message if not valid),
        eventually ask for a filename, and save the file.
        """

        author = self.author.text().strip()
        if author:
            # This pattern is used to validate the email address in the IDS Spec
            # If author does not comply, the IDS cannot be saved
            pattern = r"[^@]+@[^\.]+\..+"
            if not re.match(pattern, author):
                mb = QMessageBox()
                mb.setText(
                    self.tr(
                        "Optional field <i>author</i> must be a valid email address"
                    )
                )
                mb.setWindowTitle(self.tr("Invalid email address"))
                mb.exec()
                return

        self.ids.info = {}

        if author:
            self.ids.info["author"] = author
        self.ids.info["title"] = self.title.text().strip() or "Unnamed"
        description = self.description.text().strip()
        if description:
            self.ids.info["description"] = self.description.text().strip()
        purpose = self.purpose.text().strip()
        if purpose:
            self.ids.info["purpose"] = purpose
        copyright = self.copyright.text().strip()
        if copyright:
            self.ids.info["copyright"] = copyright
        version = self.version.text().strip()
        if version:
            self.ids.info["version"] = version
        milestone = self.milestone.text().strip()
        if milestone:
            self.ids.info["milestone"] = milestone

        self.ids.info["date"] = self.date.date().toString("yyyy-MM-dd")

        if not self.filename:
            # Ask for filename if not set
            dialog = QFileDialog()
            dialog.setAcceptMode(QFileDialog.AcceptSave)
            dialog.setNameFilter("IDS files (*.ids)")
            dialog.setDefaultSuffix("ids")
            dialog.setFileMode(QFileDialog.AnyFile)
            if dialog.exec():
                self.filename = dialog.selectedFiles()[0]
            else:
                return

        try:
            self.ids.to_xml(self.filename)
        except XMLSchemaValidationError as e:
            # Invalid IDS, file not found etc.
            # Show error message and do not close the dialog
            mb = QMessageBox()
            msg = self.tr("<b>Could not save IDS file:</b>") + f"<br><br>{e}"
            mb.setText(msg)
            mb.setWindowTitle(self.tr("Could not save IDS file"))
            mb.exec()
            return

        super().accept()


class ChooseFacetDialog(QDialog):
    """Dialog to choose the facet type

    Needed when user adds a new applicability or requirement. There are six types
    of facets in the IDS spec: Entity, Attribute, Property, PartOf, Material,
    Classification.

    :param parent: The parent widget
    :type parent: QWidget
    """

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.mainwindow = parent

        self.setWindowTitle(self.tr("Choose Facet"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel(self.tr("Choose Facet")))

        self.button_group = QButtonGroup(self)
        self.radio_button1 = QRadioButton("Entity")
        self.radio_button2 = QRadioButton("Attribute")
        self.radio_button3 = QRadioButton("Property")
        self.radio_button4 = QRadioButton("PartOf")
        self.radio_button5 = QRadioButton("Material")
        self.radio_button6 = QRadioButton("Classification")

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

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_facet(self):
        """Get the selected facet type"""
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
    sys.exit(app.exec())
