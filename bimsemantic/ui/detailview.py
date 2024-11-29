from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QLabel, QTreeView
import ifcopenshell.util.element
from .treebase import TreeItem, TreeModelBaseclass
from ifcopenshell import entity_instance
from bimsemantic.ui import CopyMixin, ContextMixin


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

        for k, v in entity.get_info().items():
            if v and not k in ["id", "type", "HasPropertySets"]:
                if isinstance(v, tuple):
                    for i, v in enumerate(v):
                        if isinstance(v, ifcopenshell.entity_instance):
                            self.item_with_subitems(v, main_item, f"{k} {i+1}")
                        else:
                            main_item.appendChild(
                                TreeItem([f"{k} {i+1}", v], parent=main_item)
                            )
                else:
                    main_item.appendChild(TreeItem([k, v], parent=main_item))

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
        self._mainwindow = parent
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

        # Spatial relations
        if ifc_object.is_a("IfcElement"):
            try:
                self.new_item(
                    "Contained in",
                    ifc_object.ContainedInStructure[0].RelatingStructure,
                    info_item,
                )
            except IndexError:
                pass

        elif ifc_object.is_a("IfcSpatialStructureElement"):
            decomposes = ifc_object.Decomposes
            if decomposes:
                self.new_item("Contained in", decomposes[0].RelatingObject, info_item)

            contains_item = TreeItem(["Contains"], parent=info_item)
            info_item.appendChild(contains_item)
            try:
                elements = ifc_object.ContainsElements[0].RelatedElements
            except IndexError:
                elements = []
            for element in elements:
                contains_item.appendChild(
                    TreeItem(
                        [f"{element.is_a()} <{element.id()}>", element.Name],
                        parent=contains_item,
                    )
                )
            iscomposedby = ifc_object.IsDecomposedBy
            if iscomposedby:
                for obj in list(iscomposedby[0].RelatedObjects):
                    contains_item.appendChild(
                        TreeItem(
                            [f"{obj.is_a()} <{obj.id()}>", obj.Name],
                            parent=contains_item,
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

            try:
                world_coordinates = ifcfile.project.RepresentationContexts[
                    0
                ].WorldCoordinateSystem.Location.Coordinates
            except (AttributeError, IndexError):
                world_coordinates = None
            if world_coordinates:
                self.new_item(
                    self.tr("Project coordinates"), str(world_coordinates), ifcfile_item
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
