from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass
import ifcopenshell.util.element
from PySide6.QtWidgets import QDockWidget, QTreeView
from bimsemantic.ui import CopyMixin, ContextMixin, IdsEditDialog
from bimsemantic.util import IdsValidator, IntegrityValidator, Validators


class ValidationDockWidget(CopyMixin, ContextMixin, QDockWidget):
    """Dock widget with the validators and their results

    :param parent: The parent widget (main window)
    """

    def __init__(self, parent):
        super().__init__(self.tr("&Validation"), parent)
        self.mainwindow = parent
        self.validators = Validators()
        integ_validator = IntegrityValidator(
            self.mainwindow.ifcfiles,
            self.mainwindow.tabs,
        )
        self.validators.add_validator(integ_validator)

        self.treemodel = ValidationTreeModel([integ_validator], self)
        self.proxymodel = QSortFilterProxyModel()
        self.proxymodel.setSourceModel(self.treemodel)
        self.tree = QTreeView()
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(3, 250)
        self.setWidget(self.tree)
        self.tree.selectionModel().selectionChanged.connect(self.on_selection_changed)

        # Setup Context Menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

    def on_selection_changed(self, selected, deselected):
        """Update the context menu when the selection changes"""
        active = self.tree.currentIndex()
        if not active.isValid():
            return
        item = self.proxymodel.mapToSource(active).internalPointer()
        row = item.row()
        level = item.level()

        validator_id = self.get_validator_id(item)

        reporters = self.validators.reporters.get(validator_id, None)
        if not reporters:
            return
        data = {}
        if validator_id == "integrity":
            reporter = reporters
            if level == 0:
                data[self.tr("Integrity")] = reporter.results
            elif level == 1:
                data[self.tr("Integrity")] = reporter.results["specifications"][row]
            elif level == 2:
                data[self.tr("Integrity")] = reporter.results["specifications"][
                    item.parent().row()
                ]["requirements"][row]
        else:
            for filename, reporter in reporters.items():
                if level == 0:
                    data[filename] = reporter.results
                elif level == 1:
                    data[filename] = reporter.results["specifications"][row]
                elif level == 2:
                    data[filename] = reporter.results["specifications"][
                        item.parent().row()
                    ]["requirements"][row]

        self.mainwindow.detailsdock.show_details(data)

    def add_file(self, filename):
        """Add IDS validator"""
        validator = IdsValidator(filename)
        self.validators.add_validator(validator)
        self.treemodel.add_file(validator)
        self.tree.expandAll()

    def close_file(self):
        """Close the selected IDS validator"""
        validator_id = self.selected_validator_id()
        if not validator_id:
            return
        if validator_id == "integrity":
            return
        self.validators.remove_validator(validator_id)
        self.treemodel.remove_file(validator_id)
        self.update_ifc_views()

    def close_all_files(self):
        """Close all IDS validators"""
        # Keep only integrity validator
        for validator in self.validators.validators[1:]:
            self.treemodel.remove_file(validator.id)
        self.validators.validators = self.validators.validators[0:1]
        self.validators.reporters = {}
        self.validators.results_by_guid = {}

        self.tree.expandAll()
        self.update_ifc_views()

    def edit_ids(self, ascopy=False, new=False):
        """Open IDS editor

        Either edit the selected IDS file or create a new one
        (emtpy or as copy of existing IDS).

        :param ascopy: Create a copy of the selected IDS file
        :type ascopy: bool
        :param new: Create a new IDS file
        :type new: bool
        """
        if new:
            filename = None
        else:
            validator_id = self.selected_validator_id()
            if not validator_id:
                return

            if validator_id == "integrity":
                self.mainwindow.statusbar.showMessage(
                    self.tr("No IDS file selected"), 5000
                )
                return

            validator = self.validators.get_validator(validator_id)
            filename = validator.abspath

        dialog = IdsEditDialog(self.mainwindow, filename, ascopy)
        if dialog.exec():
            if new:
                self.show()
            filename = dialog.filename
            if not (new or ascopy):
                # Remove the old version of the IDS file
                self.validators.remove_validator(validator_id)
                self.treemodel.remove_file(validator_id)
            self.add_file(filename)
            self.update_ifc_views()

    def selected_validator_id(self):
        """Get the ID (filename) of the selected validator"""
        active = self.tree.currentIndex()
        if not active.isValid():
            self.mainwindow.statusbar.showMessage(
                self.tr("No validator selected"), 5000
            )
            return None
        item = self.proxymodel.mapToSource(active).internalPointer()
        return self.get_validator_id(item)

    def get_validator_id(self, item):
        """Get the ID of the validator for tree item

        Also works for child items (specifications and requirements)

        :param item: The tree item
        :type item: TreeItem
        :return: The ID of the validator
        :rtype: str
        """
        if item.level() > 0:
            return self.get_validator_id(item.parent())
        return item.id

    def run_all_validations(self):
        """Run all validators and update the views"""
        self.validators.validate()
        self.update_results_column()
        self.update_ifc_views()
        self.mainwindow.save_validation_act.setEnabled(True)
        self.show()  # Show the dock in case it was hidden

    def run_selected_validation(self):
        """Run only the selected validator and update the views"""
        validator_id = self.selected_validator_id()
        if not validator_id:
            return
        self.validators.validate(validator_id)
        self.update_results_column()
        self.update_ifc_views()
        self.mainwindow.save_validation_act.setEnabled(True)

    def update_results_column(self):
        """Update the results column in the validators dock"""
        column = 4
        root = self.treemodel._rootItem
        self.treemodel.beginResetModel()
        for validator_item in root.children:
            for spec_item in validator_item.children:
                passed_checks = 0
                failed_checks = 0
                # valreporters is dict with filename as key and reporter as value
                # or None if the validator has not been run
                # or reporter if it is the integrity validator
                valreporters = self.validators.reporters.get(validator_item.id, None)
                if valreporters is None:
                    spec_item.set_data(column, "")
                    for req_item in spec_item.children:
                        req_item.set_data(column, "")
                    continue

                # Integrity validator (only one for all IFC files)
                if validator_item.id == "integrity":
                    reporter = valreporters
                    spec = reporter.results["specifications"][spec_item.row()]
                    passed_checks += spec["total_checks_pass"]
                    failed_checks += spec["total_checks_fail"]
                    spec_item.set_data(
                        column, f"{failed_checks} failed, {passed_checks} passed"
                    )
                    for i, req_item in enumerate(spec_item.children):
                        passed_checks = 0
                        failed_checks = 0
                        req = spec["requirements"][i]
                        passed_checks += len(req["passed_entities"])
                        failed_checks += len(req["failed_entities"])
                        req_item.set_data(
                            column, f"{failed_checks} failed, {passed_checks} passed"
                        )
                    continue

                # All other validators
                for ifc_file in self.mainwindow.ifcfiles:
                    # Not all files must be in the keys of the dict
                    reporter = valreporters.get(ifc_file.filename, None)
                    if reporter:
                        spec = reporter.results["specifications"][spec_item.row()]
                        passed_checks += spec["total_checks_pass"]
                        failed_checks += spec["total_checks_fail"]

                spec_item.set_data(
                    column, f"{failed_checks} failed, {passed_checks} passed"
                )

                # Update the requirement items
                for i, req_item in enumerate(spec_item.children):
                    passed_checks = 0
                    failed_checks = 0
                    for ifc_file in self.mainwindow.ifcfiles:
                        reporter = valreporters.get(ifc_file.filename, None)
                        if reporter:
                            spec = reporter.results["specifications"][spec_item.row()]
                            req = spec["requirements"][i]
                            passed_checks += len(req["passed_entities"])
                            failed_checks += len(req["failed_entities"])

                    req_item.set_data(
                        column, f"{failed_checks} failed, {passed_checks} passed"
                    )

        self.treemodel.endResetModel()
        self.tree.expandAll()

    def update_ifc_views(self):
        """Tell all views in the ifc tabs that the column data changed"""
        # Update column 10 in the ifc tree views and eventually unhide it
        for i in range(self.mainwindow.tabs.tabs.count()):
            proxymodel = self.mainwindow.tabs.tabs.widget(i).proxymodel
            top_left = proxymodel.index(0, 10)
            bottom_right = proxymodel.index(proxymodel.rowCount() - 1, 10)
            proxymodel.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])
            tree = self.mainwindow.tabs.tabs.widget(i).tree
            tree.setColumnHidden(10, False)


class ValidationTreeModel(TreeModelBaseclass):
    """Model for the validators and their results

    :param data: List of build in validators
    """

    def __init__(self, data, parent):
        super(ValidationTreeModel, self).__init__(data, parent)
        self.column_count = 5

    def setup_root_item(self):
        self._rootItem = TreeItem(
            [
                self.tr("Rules"), 
                self.tr("Description"), 
                self.tr("Instructions"), 
                self.tr("If/then"), 
                self.tr("Results")
            ],
            showchildcount=False,
        )

    def setup_model_data(self, data, parent):
        for validator in data:
            self.add_file(validator)

    def add_file(self, validator):
        """Add a IDS validator to the tree

        :param validator: The IDS validator
        :type validator: IdsValidator
        """
        self.beginResetModel()
        validator_item = TreeItem(
            [
                f"{validator.title} | {validator.filename}",
                validator.rules.info.get("description", None),
                # Only specs and facets have instructions, show purpose instead
                validator.rules.info.get("purpose", None),
            ],
            parent=self._rootItem,
            id=validator.id,
        )
        self._rootItem.appendChild(validator_item)

        # IfcTester is undocumented, for info on the to_sting() method
        # of Facet (and subclasses) see the source code in:
        # https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.8.0/src/ifctester/ifctester/facet.py
        # https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.8.0/src/ifctester/ifctester/reporter.py

        for spec in validator.rules.specifications:
            applicability = [a.to_string("applicability") for a in spec.applicability]
            applicability = " / ".join(applicability)
            spec_item = TreeItem(
                [spec.name, spec.description, spec.instructions, applicability, ""],
                parent=validator_item,
            )
            validator_item.appendChild(spec_item)

            for req in spec.requirements:
                namestring = self.tr("Requirement (%s)") % req.__class__.__name__
                req_item = TreeItem(
                    [
                        namestring,
                        None,
                        req.instructions,
                        f"⇒ {req.to_string('requirement', spec, req)}",
                        "",
                    ],
                    parent=spec_item,
                )
                spec_item.appendChild(req_item)
        self.endResetModel()

    def remove_file(self, filename):
        """Remove a IDS validator from the tree

        :param filename: The filename of the IDS validator
        :type filename: str
        """
        for child in self._rootItem.children:
            if child.id == filename:
                file_item = child
                break
        self.beginResetModel()
        self._rootItem.removeChild(file_item)
        self.endResetModel()
