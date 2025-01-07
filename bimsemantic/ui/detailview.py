from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QDockWidget, QLabel, QTreeView
import ifcopenshell.util.element
from .treebase import TreeItem, TreeModelBaseclass
from ifcopenshell import entity_instance
from bimsemantic.ui import CopyMixin, ContextMixin
from bimsemantic.util import Validators

class DetailsDock(CopyMixin, ContextMixin, QDockWidget):
    """Dock widget for showing details of IFC elements or overview of files

    The overview is updated with new_files(ifc_files) and shown with show_details().
    The details of an IFC element are shown with show_details(data, filenames).

    :param parent: The parent widget (main window)
    """

    def __init__(self, parent):
        super(DetailsDock, self).__init__(self.tr("&Details"), parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.placeholder = QLabel(self.tr("No open file"))
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWidget(self.placeholder)
        self.mainwindow = parent
        self.overviewtree = QTreeView()
        self.overviewmodel = None
        self.validators = Validators()

    def reset(self):
        """Show the placeholder label"""
        self.setWidget(self.placeholder)

    def new_files(self):
        """Simply create a new overview model and show it"""
        self.overviewmodel = OverviewTreeModel(self)
        self.overviewtree = QTreeView()
        self.overviewtree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.overviewtree.customContextMenuRequested.connect(self.show_context_menu)
        self.overviewtree.setModel(self.overviewmodel)
        self.overviewtree.expandAll()
        self.overviewtree.setColumnWidth(0, 170)

        for row in self.overviewmodel.rows_spanned:
            self.overviewtree.setFirstColumnSpanned(
                row, self.overviewtree.rootIndex(), True
            )

        self.show_details()

    def show_details(self, data=None, filenames=None):
        """Show the details of an IFC element

        ID is the ID of the element, as in the first file of the list of filenames.
        Filenames is the list of filenames of all files containing the element.
        If ID is None, the overview tree is shown.

        :data: The IFC element
        :type data: ifcopenshell entity
        :param filenames: The list of filenames, shown in the details view
        :type filenames: list of str
        """
        if self.mainwindow.ifcfiles.count() == 0:
            return
        if isinstance(data, entity_instance):
            detail_model = IfcDetailsTreeModel(data, self, filenames)
        elif isinstance(data, dict):
            detail_model = ValidationResultTreeModel(data, self)
        else:
            self.setWidget(self.overviewtree)
            return
        treeview = QTreeView()
        treeview.setContextMenuPolicy(Qt.CustomContextMenu)
        treeview.customContextMenuRequested.connect(self.show_context_menu)

        treeview.setModel(detail_model)
        treeview.setColumnWidth(0, 170)

        treeview.expandToDepth(1)

        # First column spanned for some rows
        for row, parent_index in detail_model.rows_spanned:
            if not parent_index:
                parent_index = treeview.rootIndex()
            treeview.setFirstColumnSpanned(row, parent_index, True)
        self.setWidget(treeview)

    def get_pset_tuple(self, index):
        """Get the pset tuple for the autosearch"""
        if not index.isValid():
            return None
        item = index.internalPointer()
        if not item:
            return None
        try:
            if not item.parent().parent().label == self.tr("Property Sets"):
                return None
        except (AttributeError, IndexError):
            return None
        pset_name = item.parent().label
        prop_name = item.label
        return (pset_name, prop_name)


class DetailsBaseclass(TreeModelBaseclass):
    """Base class for the details dock widget models"""

    def new_item(self, key, value, parent):
        """Helper to create new items of key-value pairs, including subitems

        :param key: The key
        :param value: The value
        :param parent: The parent tree item
        """
        if value is None:
            return None

        if isinstance(value, ifcopenshell.entity_instance):
            ifc_class = value.is_a()

            if ifc_class in [
                "IfcPerson",
                "IfcOrganization",
                "IfPostalAddress",
                "IfcTelecomAddress",
            ]:
                try:
                    name = value.Name
                except AttributeError:
                    name = ""
                return self.item_with_subitems(value, parent, ifc_class, name)
            # All other ifc instances
            try:
                name = value.Name
            except AttributeError:
                name = ""

            value = f"{value.is_a()} <{value.id()}> {name}"

        item = TreeItem([key, str(value)], parent)  # Might be tuple, therefore str()
        parent.appendChild(item)
        return item

    def owner_history_item(self, owner_history, parent):
        """Create a tree item for the owner history

        Including sub-items for the owning person, organization and application.
        Also adds the item to parent.

        :param owner_history: The IfcOwnerHistory entity
        :type owner_history: ifcopenshell entity
        :param parent: The parent tree item
        :type parent: TreeItem
        :return: The tree item
        :rtype: TreeItem
        """
        history_item = TreeItem(
            ["Owner History", f"ID {owner_history.id()}"], parent=parent
        )
        parent.appendChild(history_item)

        owning_user_item = TreeItem(["Owning User"], parent=history_item)
        history_item.appendChild(owning_user_item)

        person = owner_history.OwningUser.ThePerson

        self.item_with_subitems(person, owning_user_item, "Person", person.GivenName)

        org = owner_history.OwningUser.TheOrganization
        self.item_with_subitems(org, owning_user_item, "Organization", org.Name)

        owning_app = owner_history.OwningApplication

        owning_app_item = TreeItem(
            ["Owning Application", owning_app.ApplicationFullName], parent=history_item
        )
        history_item.appendChild(owning_app_item)

        for k, v in owning_app.get_info().items():
            try:
                is_org = v.is_a("IfcOrganization")
            except AttributeError:
                is_org = False
            if is_org:
                self.item_with_subitems(v, owning_app_item, "Organization", v.Name)
            elif k not in ["id", "type"]:
                owning_app_item.appendChild(TreeItem([k, v], parent=owning_app_item))

        for k, v in owner_history.get_info().items():
            if v and not k in ["id", "type", "OwningUser", "OwningApplication"]:
                history_item.appendChild(TreeItem([k, v], parent=history_item))

        return history_item

    def item_with_subitems(self, entity, parent, key_label, value_label=None):
        """Create a tree item with several key-value pair subitems

        Make subitems for the key value pairs in the dict returned by
        entity.get_info(). If the value is a tuple (such as several addresses),
        create several subitems.

        :param entity: The IfcOpenShell entity
        :type org: ifcopenshell entity
        :param parent: The parent tree item
        :type parent: TreeItem
        :param label: The label for the main item
        :type label: str
        :return: The tree item
        :rtype: TreeItem
        """
        main_item = TreeItem([key_label, value_label], parent=parent)
        parent.appendChild(main_item)

        # entity may be a dict if showing validation results
        if isinstance(entity, dict):
            entity_info = entity
        else:

            entity_info = entity.get_info()

        for k, v in  entity_info.items():
            if v and not k in ["id", "type", "HasPropertySets"]:
                if isinstance(v, (tuple, list)):
                    for i, v in enumerate(v):
                        if isinstance(v, ifcopenshell.entity_instance):
                            self.item_with_subitems(v, main_item, f"{k} {i+1}")
                        elif isinstance(v, dict):
                            # For validators
                            self.item_with_subitems(v, main_item, f"{k} {i+1}")
                        else:
                            main_item.appendChild(
                                TreeItem([f"{k} {i+1}", v], parent=main_item)
                            )
                elif isinstance(v, dict):
                    # For validators
                    self.item_with_subitems(v, main_item, k)
                else:
                    main_item.appendChild(TreeItem([k, str(v)], parent=main_item))

        return main_item


class IfcDetailsTreeModel(DetailsBaseclass):
    """Model for the tree view of the details dock widget

    :param id: The ID of the element in the first file of filenames
    :type id: int
    :param parent: The parent widget (main window)
    :param filenames: The list of filenames
    """

    def __init__(self, ifc_element, parent, filenames=None):
        self.filenames = filenames
        self._mainwindow = parent.mainwindow
        element = ifc_element
        super(IfcDetailsTreeModel, self).__init__(element, parent)

    def setup_model_data(self, data, parent):
        """Build the tree view

        :param data: The IfcOpenShell entity
        :parent: The root item of the tree
        """
        self.rows_spanned = []

        object_item = parent
        ifc_object = data

        info = ifc_object.get_info()
        if ifc_object.is_a("IfcElementType"):
            # get_type() on a element type item would return the item itself
            linked_object_type = None
        else:
            linked_object_type = ifcopenshell.util.element.get_type(ifc_object)

        object_item.appendChild(TreeItem(["Name", ifc_object.Name], parent=object_item))
        object_item.appendChild(
            TreeItem([self.tr("IFC Class"), info["type"]], parent=object_item)
        )
        objtype = info.get("ObjectType", self.nan)
        if objtype is None:
            objtype = self.nan
        object_item.appendChild(TreeItem(["ObjectType", objtype], parent=object_item))
        if linked_object_type:
            linked_object_type_name = linked_object_type.Name
            if linked_object_type_name is None:
                linked_object_type_name = self.tr("Unnamed")
            object_item.appendChild(
                TreeItem(
                    [self.tr("Linked Object Type"), linked_object_type_name],
                    parent=object_item,
                )
            )
        object_item.appendChild(
            TreeItem(["IFC ID", ifc_object.id()], parent=object_item)
        )

        # Check if the ID is always the same
        if len(self.filenames) > 1:
            ids = []
            for filename in self.filenames[1:]:
                inotherfile = self._mainwindow.ifcfiles.get_element_by_guid(
                    ifc_object.GlobalId, filename
                )
                ids.append(inotherfile.id())
            if not all([id == ifc_object.id() for id in ids]):
                for i, id in enumerate(ids):
                    object_item.appendChild(
                        TreeItem([f"IFC ID ({i+1})", id], parent=object_item)
                    )

        object_item.appendChild(
            TreeItem(["Global ID", ifc_object.GlobalId], parent=object_item)
        )

        info_item = TreeItem([self.tr("Main Attributes")], parent=object_item)
        object_item.appendChild(info_item)

        for k, v in info.items():
            if k not in [
                "Name",
                "id",
                "GlobalId",
                "type",
                "ObjectType",
                "OwnerHistory",
            ]:
                self.new_item(k, v, info_item)

        self.owner_history_item(ifc_object.OwnerHistory, info_item)

        # Filenames
        info_item.appendChild(
            TreeItem(["File count", len(self.filenames)], parent=info_item)
        )
        if len(self.filenames) == 1:
            info_item.appendChild(
                TreeItem(["Filename", self.filenames[0]], parent=info_item)
            )
        else:
            for i, filename in enumerate(self.filenames):
                info_item.appendChild(
                    TreeItem([f"Filename ({i})", filename], parent=info_item)
                )

        # Relations
        relation_item = TreeItem([self.tr("Relations")], parent=info_item)
        info_item.appendChild(relation_item)

        contained_in = []

        try:
            for rel in ifc_object.ContainedInStructure:
                contained_in.append(rel.RelatingStructure)
        except AttributeError:
            pass

        try:
            for rel in ifc_object.Decomposes:
                contained_in.append(rel.RelatingObject)
        except AttributeError:
            pass

        if len(contained_in) == 1:
            self.new_item(self.tr("Contained in"), contained_in[0], relation_item)
        elif len(contained_in) > 1:
            contained_in_item = TreeItem([self.tr("Contained in")], parent=relation_item)
            relation_item.appendChild(contained_in_item)
            for element in contained_in:
                contained_in_item.appendChild(
                    TreeItem(
                        [f"{element.is_a()} <{element.id()}>", element.Name],
                        parent=contained_in_item,
                    )
                )

        contains = []

        try:
            for rel in ifc_object.ContainsElements:
                contains.extend(rel.RelatedElements)
        except AttributeError:
            pass

        try:
            for rel in ifc_object.IsDecomposedBy:
                contains.extend(rel.RelatedObjects)
        except AttributeError:
            pass

        if contains:
            contains_item = TreeItem(["Contains"], parent=relation_item)
            relation_item.appendChild(contains_item)
            for element in contains:
                contains_item.appendChild(
                    TreeItem(
                        [f"{element.is_a()} <{element.id()}>", element.Name],
                        parent=contains_item,
                    )
                )

        # Openings and fillings (only show voids with filling)
        openings = []
        fillings = []

        try:
            has_openings = ifc_object.HasOpenings
        except AttributeError:
            has_openings = []

        for rel in has_openings:
            openings.append(rel.RelatedOpeningElement)

        for opening in openings:
            try:
                has_fillings = opening.HasFillings
            except AttributeError:
                continue
            for rel in has_fillings:
                fillings.append(rel.RelatedBuildingElement)
        if fillings:
            openings_item = TreeItem([self.tr("Filled openings")], parent=relation_item)
            relation_item.appendChild(openings_item)
            for opening in fillings:
                openings_item.appendChild(
                    TreeItem(
                        [f"{opening.is_a()} <{opening.id()}>", opening.Name],
                        parent=openings_item,
                    )
                )


        # The other element with a void filled by this element
        try:
            voids = ifc_object.FillsVoids
        except AttributeError:
            voids = []
        
        voids = [rel.RelatingOpeningElement.VoidsElements for rel in voids]
        voided_elements = [] 
        for void in voids:
            for rel in void:
                voided_elements.append(rel.RelatingBuildingElement)

        if len(voided_elements) == 1:
            self.new_item(self.tr("Fills void in"), voided_elements[0], relation_item)
        elif len(voided_elements) > 1:
            voided_item = TreeItem([self.tr("Fills void in")], parent=relation_item)
            relation_item.appendChild(voided_item)
            for element in voided_elements:
                voided_item.appendChild(
                    TreeItem(
                        [f"{element.is_a()} <{element.id()}>", element.Name],
                        parent=voided_item,
                    )
                )

        # Connected to
        connected_to = []
        try:
            for rel in ifc_object.ConnectedTo:
                connected_to.extend(rel.RelatedElements)
        except AttributeError:
            pass

        if connected_to:
            connected_item = TreeItem([self.tr("Connected to")], parent=relation_item)
            relation_item.appendChild(connected_item)
            for element in connected_to:
                connected_item.appendChild(
                    TreeItem(
                        [f"{element.is_a()} <{element.id()}>", element.Name],
                        parent=connected_item,
                    )
                )

        # Property Sets
        psets = ifcopenshell.util.element.get_psets(ifc_object, psets_only=True)
        if psets:
            psets_item = TreeItem([self.tr("Property Sets")], parent=object_item)
            object_item.appendChild(psets_item)
            parent_index = self.index(psets_item.row(), 0)
            for pset_name, pset in psets.items():
                pset_item = TreeItem([pset_name], parent=psets_item)
                psets_item.appendChild(pset_item)
                # This tuple can be used to span rows:
                self.rows_spanned.append((pset_item.row(), parent_index))
                for k, v in pset.items():
                    if k != "id":
                        pset_item.appendChild(TreeItem([k, v], parent=pset_item))

        # Quantity Sets
        qsets = ifcopenshell.util.element.get_psets(ifc_object, qtos_only=True)
        if qsets:
            qsets_item = TreeItem([self.tr("Quantity Sets")], parent=object_item)
            object_item.appendChild(qsets_item)
            parent_index = self.index(qsets_item.row(), 0)
            for qset_name, qset in qsets.items():
                qset_item = TreeItem([qset_name], parent=qsets_item)
                qsets_item.appendChild(qset_item)
                self.rows_spanned.append((qset_item.row(), parent_index))
                for k, v in qset.items():
                    qset_item.appendChild(TreeItem([k, v], parent=qset_item))

        # Materials
        materials = []
        if ifc_object.HasAssociations:
            for association in ifc_object.HasAssociations:
                if association.is_a("IfcRelAssociatesMaterial"):
                    materials.append(association.RelatingMaterial)

        if materials:
            materials_item = TreeItem(["Materials"], parent=object_item)
            object_item.appendChild(materials_item)
            for material in materials:
                if material.is_a("IfcMaterial"):
                    mat_item = TreeItem([material.Name], parent=materials_item)
                    materials_item.appendChild(mat_item)
                    for k, v in material.get_info().items():
                        if k not in ["Name"]:
                            self.new_item(k, v, mat_item)
                elif material.is_a("IfcMaterialConstituentSet"):
                    for constituent in material.MaterialConstituents:
                        mat_item = TreeItem([constituent.Name], parent=materials_item)
                        materials_item.appendChild(mat_item)
                        for k, v in constituent.get_info().items():
                            if k not in ["Name"]:
                                self.new_item(k, v, mat_item)

        if linked_object_type:
            # Object type Property Sets
            psets = ifcopenshell.util.element.get_psets(linked_object_type)
            type_item = self.item_with_subitems(
                linked_object_type,
                parent,
                self.tr("Linked Object Type"),
                value_label=linked_object_type_name,
            )
            if psets:
                psets_item = TreeItem([self.tr("Property Sets")], parent=type_item)
                type_item.appendChild(psets_item)
                parent_index = self.index(
                    psets_item.row(), 0, self.index(type_item.row(), 0)
                )
                for pset_name, pset in psets.items():
                    pset_item = TreeItem([pset_name], parent=psets_item)
                    psets_item.appendChild(pset_item)
                    self.rows_spanned.append((pset_item.row(), parent_index))
                    for k, v in pset.items():
                        pset_item.appendChild(TreeItem([k, v], parent=pset_item))

        # Validation results
        validators = Validators()
        failed_specs, passed_specs = validators.get_validation_for_element(
            ifc_object.GlobalId, self.filenames
        )

        if failed_specs or passed_specs:
            validation_item = TreeItem(["Validation"], parent=object_item)
            object_item.appendChild(validation_item)

            if failed_specs:
                failed_item = TreeItem(
                    [self.tr("Failed"), ""], parent=validation_item
                )
                validation_item.appendChild(failed_item)
                for spec in failed_specs:
                    spec_item = TreeItem([spec["spec"]], parent=failed_item)
                    failed_item.appendChild(spec_item)
                    for k, v in spec.items():
                        if v and k != "spec":
                            spec_item.appendChild(TreeItem([k, v], parent=spec_item))

            if passed_specs:
                passed_item = TreeItem(
                    [self.tr("Passed"), ""], parent=validation_item
                )
                validation_item.appendChild(passed_item)
                for spec in passed_specs:
                    spec_item = TreeItem([spec["spec"]], parent=passed_item)
                    passed_item.appendChild(spec_item)
                    for k, v in spec.items():
                        if v and k != "spec":
                            spec_item.appendChild(TreeItem([k, v], parent=spec_item))


class OverviewTreeModel(DetailsBaseclass):
    """Overview model for the details dock widget showing info about the files

    :param parent: The parent widget (main window)
    """

    def __init__(self, parent):
        self._mainwindow = parent.mainwindow

        super(OverviewTreeModel, self).__init__(None, parent)

    def setup_model_data(self, data, parent):
        """Build the tree view

        Data is ignored, but passed by the parent class.
        :param parent: The root item of the tree
        """
        ifc_files = self._mainwindow.ifcfiles
        root_item = parent

        self.rows_spanned = []

        for ifcfile in ifc_files:
            ifcfile_item = TreeItem([ifcfile.filename], parent=root_item)
            root_item.appendChild(ifcfile_item)
            self.rows_spanned.append(ifcfile_item.row())

            self.new_item(self.tr("IFC Version"), ifcfile.model.schema, ifcfile_item)
            self.new_item(self.tr("File size"), f"{ifcfile.megabytes} MB", ifcfile_item)
            self.new_item(self.tr("Project name"), ifcfile.project.Name, ifcfile_item)

            longname = ifcfile.project.LongName
            if longname:
                self.new_item(self.tr("Long name"), longname, ifcfile_item)

            phase = ifcfile.project.Phase
            if phase:
                self.new_item(self.tr("Project phase"), phase, ifcfile_item)

            # Project base point can be linked to IfcProject or IfcSite (or even both)
            try:
                coordinates = ifcfile.project.RepresentationContexts[
                    0
                ].WorldCoordinateSystem.Location.Coordinates
            except (AttributeError, IndexError):
                coordinates = None
            if coordinates and coordinates[0] and coordinates[1]:
                # Only show if not 0,0,0
                self.new_item(
                    self.tr("Project base point"), str(coordinates), ifcfile_item
                )

            try:
                coordinates = ifcfile.model.by_type("IfcSite")[0].ObjectPlacement.RelativePlacement.Location.Coordinates
            except (AttributeError, IndexError):
                coordinates = None
            if coordinates and coordinates[0] and coordinates[1]:
                # Only show if not 0,0,0
                self.new_item(
                    self.tr("IfcSite base point"), str(coordinates), ifcfile_item
                )
                
            self.new_item(
                self.tr("Project owner"),
                ifcfile.project.OwnerHistory.OwningUser.ThePerson.GivenName,
                ifcfile_item,
            )
            self.new_item(
                self.tr("Application"),
                ifcfile.project.OwnerHistory.OwningApplication.ApplicationFullName,
                ifcfile_item,
            )

            address_item = TreeItem([self.tr("Addresses")], parent=ifcfile_item)

            for site in ifcfile.model.by_type("IfcSite"):
                address = site.SiteAddress
                if address:
                    self.item_with_subitems(address, address_item, "Site", site.Name)

                buildings = site.IsDecomposedBy[0].RelatedObjects

                for building in buildings:
                    try:
                        address = building.BuildingAddress
                    except AttributeError:
                        address = None
                    if address:
                        self.item_with_subitems(
                            address, address_item, "Building", building.Name
                        )

            if address_item.child_count() > 0:
                ifcfile_item.appendChild(address_item)

            try:
                crs = ifcfile.model.by_type("IfcCoordinateReferenceSystem")[0]
            except (IndexError, RuntimeError):
                # IfcOpenShell throws RuntimeError with IFC2x3: not found in schema
                crs = None
            if crs:
                self.new_item(self.tr("CRS"), crs.Name, ifcfile_item)

            self.new_item(
                self.tr("IFC Elements"), ifcfile.count_ifc_elements(), ifcfile_item
            )
            self.new_item(self.tr("Pset count"), ifcfile.pset_count(), ifcfile_item)
            self.new_item(self.tr("Qset count"), ifcfile.qset_count(), ifcfile_item)

class ValidationResultTreeModel(DetailsBaseclass):
    """Tree model for the validation results
    
    Simply show json-like data in a tree view

    :param data: The validation data as json-like dict
    :type data: dict
    """


    def setup_model_data(self, data, parent):
        root_item = parent
        self.rows_spanned = []

        for k, v in data.items():
            label = self.tr("Validation of %s") % k
            self.item_with_subitems(v, root_item, label)

        for i in range(0, root_item.child_count()):
            self.rows_spanned.append((i, QModelIndex()))


