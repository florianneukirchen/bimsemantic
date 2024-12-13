from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass
import ifcopenshell.util.element
from PySide6.QtWidgets import QDockWidget, QTreeView
from bimsemantic.ui import CopyMixin, ContextMixin
from bimsemantic.util import IfsValidator, Validators


class ValidationDockWidget(CopyMixin, ContextMixin, QDockWidget):
    def __init__(self, parent):
        super().__init__(self.tr("&Validation"), parent)
        self.mainwindow = parent
        self.validators = Validators(self.mainwindow.ifcfiles)
        
        self.treemodel = ValidationTreeModel(None, self)
        self.proxymodel = QSortFilterProxyModel()
        self.proxymodel.setSourceModel(self.treemodel)
        self.tree = QTreeView()
        self.tree.setModel(self.proxymodel)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 250)
        self.setWidget(self.tree)


    def add_file(self, filename):
        validator = IfsValidator(filename)
        self.validators.add_validator(validator)
        self.treemodel.add_file(validator)
        self.tree.expandAll()

    def close_file(self):
        active = self.tree.currentIndex()
        if not active.isValid():
            self.mainwindow.statusbar.showMessage(self.tr("No file selected"), 5000)
            return
        item = self.proxymodel.mapToSource(active).internalPointer()
        filename = self._item_filename(item)
        self.validators.remove_validator(filename)
        self.treemodel.remove_file(filename)
        self.update_ifc_views()

    def _item_filename(self, item):
        if item.level() > 0:
            return self._item_filename(item.parent())
        return item.id

    def run_all_validations(self):
        self.validators.validate()
        self.update_results_column()
        self.tree.expandAll()
        self.update_ifc_views()

    def update_results_column(self):
        root = self.treemodel._rootItem
        self.treemodel.beginResetModel()
        for validator_item in root.children:
            for spec_item in validator_item.children:
                passed_checks = 0
                failed_checks = 0
                for ifc_file in self.mainwindow.ifcfiles:
                    reporter = self.validators.reporters[validator_item.id][ifc_file.filename]
                    spec = reporter.results['specifications'][spec_item.row()]
                    passed_checks += spec['total_checks_pass']
                    failed_checks += spec['total_checks_fail']
                spec_item.set_data(3, f"{failed_checks} failed, {passed_checks} passed")
                for i, req_item in enumerate(spec_item.children):
                    passed_checks = 0
                    failed_checks = 0
                    for ifc_file in self.mainwindow.ifcfiles:
                        reporter = self.validators.reporters[validator_item.id][ifc_file.filename]
                        spec = reporter.results['specifications'][spec_item.row()]
                        req = spec['requirements'][i]
                        passed_checks += len(req['passed_entities'])
                        failed_checks += len(req['failed_entities'])
                    req_item.set_data(3, f"{failed_checks} failed, {passed_checks} passed")
        self.treemodel.endResetModel()


    def update_ifc_views(self):
        # Update column 10 in the ifc tree views and eventually unhide it
        for i in range(self.mainwindow.tabs.tabs.count()):
            proxymodel = self.mainwindow.tabs.tabs.widget(i).proxymodel
            top_left = proxymodel.index(0, 10)
            bottom_right = proxymodel.index(proxymodel.rowCount() - 1, 10)
            proxymodel.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])
            tree = self.mainwindow.tabs.tabs.widget(i).tree
            tree.setColumnHidden(10, False)
        
class ValidationTreeModel(TreeModelBaseclass):
    def __init__(self, data, parent):
        super(ValidationTreeModel, self).__init__(data, parent)
        self.column_count = 4

    def setup_root_item(self):
        self._rootItem = TreeItem(
            ["Rules", "Description", "If/then", "Results"],
            showchildcount=False,
        )

    def add_file(self, validator):
        self.beginResetModel()
        validator_item = TreeItem(
            [
                f"{validator.title} | {validator.filename}", 
                validator.rules.info.get('description', None)
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
                [
                    spec.name, 
                    spec.description, 
                    applicability,
                    ""
                ],
                parent=validator_item,
            )
            validator_item.appendChild(spec_item)

            for req in spec.requirements:
                namestring = self.tr("Requirement (%s)") % req.__class__.__name__
                req_item = TreeItem(
                    [
                        namestring, 
                        req.instructions, 
                        f"⇒ {req.to_string('requirement', spec, req)}",
                        "",
                    ],
                    parent=spec_item,
                )
                spec_item.appendChild(req_item)
        self.endResetModel()

    def remove_file(self, filename):
        for child in self._rootItem.children:
            if child.id == filename:
                file_item = child
                break
        self.beginResetModel()
        self._rootItem.removeChild(file_item)
        self.endResetModel()