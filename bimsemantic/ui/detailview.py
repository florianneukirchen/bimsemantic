import ifcopenshell.util.element
from .treebase import TreeItem, TreeModelBaseclass


class DetailsTreeModel(TreeModelBaseclass):
    """Model for the tree view of the details dock widget
    
    :param id: The ID of the element in the first file of filenames
    :type id: int
    :param parent: The parent widget (main window)
    :param filenames: The list of filenames
    """
    def __init__(self, id, parent, filenames=None):
        self.filenames = filenames
        self._mainwindow = parent
        element = parent.ifcfiles.get_element(self.filenames[0], id)
        super(DetailsTreeModel, self).__init__(element, parent)

    def newItem(self, key, value, parent):
        """Helper to create new items of key-value pairs
        :param key: The key
        :param value: The value
        :param parent: The parent tree item
        """
        if isinstance(value, ifcopenshell.entity_instance):
            try:
                name = value.Name
            except AttributeError:
                name = ""

            value = f"{value.is_a()} <{value.id()}> {name}"

        item = TreeItem([key, value], parent)
        return item


    def setupModelData(self, data, parent):
        """Build the tree view
        
        :param data: The IfcOpenShell entity
        :parent: The root item of the tree
        """
        self.rows_spanned = []

        object_item = parent
        object = data

        info = object.get_info()
        object_item.appendChild(
            TreeItem(["Name", object.Name], parent=object_item)
        )
        object_item.appendChild(
            TreeItem(["Type", info["type"]], parent=object_item)
        )
        if info.get("ObjectType") is not None:
            object_item.appendChild(
                TreeItem(["Object Type", info["ObjectType"]], parent=object_item)
            )
        object_item.appendChild(
            TreeItem(["IFC ID", object.id()], parent=object_item)
        )

        # Check if the ID is alway the same
        if len(self.filenames) > 1:
            ids = []
            for filename in self.filenames[1:]:
                inotherfile = self._mainwindow.ifcfiles.get_element_by_guid(object.GlobalId, filename)
                ids.append(inotherfile.id())
            if not all([id == object.id() for id in ids]):
                for i, id in enumerate(ids):
                    object_item.appendChild(
                        TreeItem([f"IFC ID ({i+1})", id], parent=object_item)
                    )
        

        object_item.appendChild(
            TreeItem(["Global ID", object.GlobalId], parent=object_item)
        )


        info_item = TreeItem(["Info"], parent=object_item)
        object_item.appendChild(info_item)
        
        for k,v in info.items():
            if k not in ["Name", "id", "GlobalId", "type", "ObjectType"]:
                info_item.appendChild(
                    self.newItem(k, v, info_item)
                )

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
        if object.is_a("IfcElement"):
            try:
                info_item.appendChild(
                    self.newItem("Contained in", object.ContainedInStructure[0].RelatingStructure, info_item)
                )
            except IndexError:
                pass

        elif object.is_a("IfcSpatialStructureElement"):
            decomposes = object.Decomposes
            if decomposes:
                info_item.appendChild(
                self.newItem("Contained in", decomposes[0].RelatingObject, info_item)
                )

            contains_item = TreeItem(["Contains"], parent=info_item)
            info_item.appendChild(contains_item)
            try:
                elements = object.ContainsElements[0].RelatedElements
            except IndexError:
                elements = []
            for element in elements:
                contains_item.appendChild(
                    TreeItem([element.is_a(), element.id(), element.Name], parent=contains_item)
                )
            iscomposedby = object.IsDecomposedBy
            if iscomposedby:
                for obj in list(iscomposedby[0].RelatedObjects):
                    contains_item.appendChild(
                        TreeItem([obj.is_a(), obj.id(), obj.Name], parent=contains_item)
                    )

        # Property Sets
        psets = ifcopenshell.util.element.get_psets(object)
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
        if object.HasAssociations:
            for association in object.HasAssociations:
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
                            mat_item.appendChild(
                                self.newItem(k, v, mat_item)
                        )
                elif material.is_a("IfcMaterialConstituentSet"):
                    for constituent in material.MaterialConstituents:
                        mat_item = TreeItem([constituent.Name], parent=materials_item)
                        materials_item.appendChild(mat_item)
                        for k,v in constituent.get_info().items():
                            if k not in ["Name"]:
                                mat_item.appendChild(
                                    self.newItem(k, v, mat_item)
                            )
                                




class OverviewTreeModel(TreeModelBaseclass):
    """Overview model for the details dock widget showing info about the files
    
    :param parent: The parent widget (main window)
    """
    def __init__(self, parent):
        self._mainwindow = parent
        self.ifcfiles = parent.ifcfiles

        super(OverviewTreeModel, self).__init__(None, parent)

    def newItem(self, key, value, parent):
        """Helper to create new items of key-value pairs"""
        item = TreeItem([key, value], parent)
        return item


    def setupModelData(self, data, parent):
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
                self.newItem(self.tr("IFC Version"), ifcfile.model.schema, ifcfile_item)
            )
            ifcfile_item.appendChild(
                self.newItem(self.tr("File size"), f"{ifcfile.megabytes} MB", ifcfile_item)
            )
            ifcfile_item.appendChild(
                self.newItem(self.tr("IFC Elements"), ifcfile.count_ifc_elements(), ifcfile_item)
            )
            ifcfile_item.appendChild(
                self.newItem(self.tr("Pset count"), ifcfile.pset_count(), ifcfile_item)
            )




