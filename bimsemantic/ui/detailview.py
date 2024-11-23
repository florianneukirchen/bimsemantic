import ifcopenshell.util.element
from .treebase import TreeItem, TreeModelBaseclass

class DetailsBaseclass(TreeModelBaseclass):
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
        history_item = TreeItem([f"Owner History (ID {owner_history.id()})"], parent=parent)
        parent.appendChild(history_item)

        owning_user_item = TreeItem(["Owning User"], parent=history_item)
        history_item.appendChild(owning_user_item)

        person = owner_history.OwningUser.ThePerson
        person_item = TreeItem([f"Person {person.GivenName}"], parent=owning_user_item)
        owning_user_item.appendChild(person_item)

        for k,v in person.get_info().items():
            if v and not k in ["id", "type"]:
                person_item.appendChild(
                    TreeItem([k,v], parent=person_item)
                )

        org = owner_history.OwningUser.TheOrganization
        self.item_with_subitems(org, owning_user_item, f"Organization {org.Name}")

        owning_app = owner_history.OwningApplication

        owning_app_item = TreeItem([f"Owning Application {owning_app.ApplicationFullName}"], parent=history_item)
        history_item.appendChild(owning_app_item)

        for k,v in owning_app.get_info().items():
            try:
                is_org = v.is_a("IfcOrganization")
            except AttributeError:
                is_org = False
            if is_org: 
                self.item_with_subitems(v, owning_app_item, f"Organization {v.Name}")
            elif k not in ["id", "type"]:
                owning_app_item.appendChild(
                    TreeItem([k,v], parent=owning_app_item)
                )

        for k,v in owner_history.get_info().items():
            if v and not k in ["id", "type", "OwningUser", "OwningApplication"]:
                history_item.appendChild(
                    TreeItem([k,v], parent=history_item)
                )

        return history_item    

    def item_with_subitems(self, entity, parent, label):
        """Create a tree item with several key-value pair subitems

        Make subitems for the key value pairs in the dict returned by 
        entity.get_info().
        
        :param entity: The IfcOpenShell entity
        :type org: ifcopenshell entity
        :param parent: The parent tree item
        :type parent: TreeItem
        :param label: The label for the main item
        :type label: str
        :return: The tree item
        :rtype: TreeItem
        """
        main_item = TreeItem([label], parent=parent)
        parent.appendChild(main_item)

        for k,v in entity.get_info().items():
            if v and not k in ["id", "type"]:
                main_item.appendChild(
                    TreeItem([k,v], parent=main_item)
                )

        return main_item

    def address_item(self, address, parent):
        """Create a tree item for an address
        
        :param address: The IfcPostalAddress entity
        :type address: ifcopenshell entity
        :param parent: The parent tree item
        :type parent: TreeItem
        :return: The tree item
        :rtype: TreeItem
        """
        add_item = TreeItem(["Address"], parent=parent)
        parent.appendChild(add_item)
        address_lines = address.AddressLines
        for i, line in enumerate(address_lines):
            add_item.appendChild(
                TreeItem([f"Address line {i+1}", line], parent=add_item)
            )
        for k,v in address.get_info().items():
            if v and k not in ["id", "type", "AddressLines"]:
                add_item.appendChild(
                    TreeItem([k,v], parent=add_item)
            )
                
        return add_item

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

    def new_item(self, key, value, parent):
        """Helper to create new items of key-value pairs
        :param key: The key
        :param value: The value
        :param parent: The parent tree item
        """
        if isinstance(value, ifcopenshell.entity_instance):
            if value.is_a("IfcOwnerHistory"):
                return self.owner_history_item(value, parent)
            elif value.is_a("IfcOrganization"):
                return self.item_with_subitems(value, parent, "Organization {value.Name}")
            elif value.is_a("IfcPostalAddress"):
                return self.address_item(value, parent)

            try:
                name = value.Name
            except AttributeError:
                name = ""

            value = f"{value.is_a()} <{value.id()}> {name}"

        item = TreeItem([key, value], parent)
        parent.appendChild(item)
        return item


    def setup_model_data(self, data, parent):
        """Build the tree view
        
        :param data: The IfcOpenShell entity
        :parent: The root item of the tree
        """
        self.rows_spanned = []

        object_item = parent
        ifc_object = data

        info = ifc_object.get_info()
        object_item.appendChild(
            TreeItem(["Name", ifc_object.Name], parent=object_item)
        )
        object_item.appendChild(
            TreeItem(["Type", info["type"]], parent=object_item)
        )
        if info.get("ObjectType") is not None:
            object_item.appendChild(
                TreeItem(["Object Type", info["ObjectType"]], parent=object_item)
            )
        object_item.appendChild(
            TreeItem(["IFC ID", ifc_object.id()], parent=object_item)
        )

        # Check if the ID is alway the same
        if len(self.filenames) > 1:
            ids = []
            for filename in self.filenames[1:]:
                inotherfile = self._mainwindow.ifcfiles.get_element_by_guid(ifc_object.GlobalId, filename)
                ids.append(inotherfile.id())
            if not all([id == ifc_object.id() for id in ids]):
                for i, id in enumerate(ids):
                    object_item.appendChild(
                        TreeItem([f"IFC ID ({i+1})", id], parent=object_item)
                    )
        

        object_item.appendChild(
            TreeItem(["Global ID", ifc_object.GlobalId], parent=object_item)
        )


        info_item = TreeItem([self.tr("Info")], parent=object_item)
        object_item.appendChild(info_item)
        
        for k,v in info.items():
            if k not in ["Name", "id", "GlobalId", "type", "ObjectType", "OwnerHistory"]:
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
                self.new_item("Contained in", ifc_object.ContainedInStructure[0].RelatingStructure, info_item)
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
                    TreeItem([element.is_a(), element.id(), element.Name], parent=contains_item)
                )
            iscomposedby = ifc_object.IsDecomposedBy
            if iscomposedby:
                for obj in list(iscomposedby[0].RelatedObjects):
                    contains_item.appendChild(
                        TreeItem([obj.is_a(), obj.id(), obj.Name], parent=contains_item)
                    )

        # Property Sets
        psets = ifcopenshell.util.element.get_psets(ifc_object)
        for pset_name, pset in psets.items():
            pset_item = TreeItem([pset_name], parent=object_item)
            self.rows_spanned.append(pset_item)
            object_item.appendChild(pset_item)
            for k, v in pset.items():
                pset_item.appendChild(
                    TreeItem([k,v], parent=pset_item)
                )


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
                    for k,v in material.get_info().items():
                        if k not in ["Name"]:
                            self.new_item(k, v, mat_item)
                elif material.is_a("IfcMaterialConstituentSet"):
                    for constituent in material.MaterialConstituents:
                        mat_item = TreeItem([constituent.Name], parent=materials_item)
                        materials_item.appendChild(mat_item)
                        for k,v in constituent.get_info().items():
                            if k not in ["Name"]:
                                self.new_item(k, v, mat_item)
                               




class OverviewTreeModel(DetailsBaseclass):
    """Overview model for the details dock widget showing info about the files
    
    :param parent: The parent widget (main window)
    """
    def __init__(self, parent):
        self._mainwindow = parent
        self.ifcfiles = parent.ifcfiles

        super(OverviewTreeModel, self).__init__(None, parent)

    def new_item(self, key, value, parent):
        """Helper to create new items of key-value pairs"""
        item = TreeItem([key, value], parent)
        return item


    def setup_model_data(self, data, parent):
        """Build the tree view
        
        Data is ignored, but passed by the parent class.
        :param parent: The root item of the tree
        """
        root_item = parent

        self.rows_spanned = []

        for ifcfile in self.ifcfiles:
            ifcfile_item = TreeItem([ifcfile.filename], parent=root_item)
            root_item.appendChild(ifcfile_item)
            self.rows_spanned.append(ifcfile_item)

            ifcfile_item.appendChild(
                self.new_item(self.tr("IFC Version"), ifcfile.model.schema, ifcfile_item)
            )
            ifcfile_item.appendChild(
                self.new_item(self.tr("File size"), f"{ifcfile.megabytes} MB", ifcfile_item)
            )

            ifcfile_item.appendChild(
                self.new_item(self.tr("Project name"), ifcfile.project.Name, ifcfile_item)
            )

            longname = ifcfile.project.LongName
            if longname:
                ifcfile_item.appendChild(
                    self.new_item(self.tr("Long name"), longname, ifcfile_item)
                )

            phase = ifcfile.project.Phase
            if phase:
                ifcfile_item.appendChild(
                    self.new_item(self.tr("Project phase"), phase, ifcfile_item)
                )

            ifcfile_item.appendChild(
                self.new_item(self.tr("Project owner"), ifcfile.project.OwnerHistory.OwningUser.ThePerson.GivenName, ifcfile_item)
            )

            ifcfile_item.appendChild(
                self.new_item(self.tr("Application"), ifcfile.project.OwnerHistory.OwningApplication.ApplicationFullName, ifcfile_item)
            )

            for building in ifcfile.model.by_type("IfcBuilding"):
                building_item = TreeItem([f"Building {building.Name}"], parent=ifcfile_item)
                ifcfile_item.appendChild(building_item)

                longname = building.LongName
                if longname:
                    building_item.appendChild(
                        self.new_item(self.tr("Long name"), longname, building_item)
                    )
                address = building.BuildingAddress
                if address:
                    self.address_item(address, building_item)

            try:
                crs = ifcfile.model.by_type("IfcCoordinateReferenceSystem")[0]
            except IndexError:
                crs = None
            if crs:
                ifcfile_item.appendChild(
                    self.new_item(self.tr("CRS"), crs.Name, ifcfile_item)
                )
                

            ifcfile_item.appendChild(
                self.new_item(self.tr("IFC Elements"), ifcfile.count_ifc_elements(), ifcfile_item)
            )
            ifcfile_item.appendChild(
                self.new_item(self.tr("Pset count"), ifcfile.pset_count(), ifcfile_item)
            )
            ifcfile_item.appendChild(
                self.new_item(self.tr("Qset count"), ifcfile.qset_count(), ifcfile_item)
            )




