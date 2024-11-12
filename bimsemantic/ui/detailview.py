from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView
import ifcopenshell.util.element
from .treebase import TreeItem, TreeModelBaseclass


class DetailsTreeModel(TreeModelBaseclass):

    def newItem(self, key, value, parent):
        if isinstance(value, ifcopenshell.entity_instance):
            try:
                name = value.Name
            except AttributeError:
                name = ""

            value = f"{value.is_a()} <{value.id()}> {name}"

        item = TreeItem([key, value], parent)
        return item


    def setupModelData(self, data, parent):
        self.rows_spanned = []

        if not isinstance(data, list):
            data = [data]

        for object in data:
            if len(data) > 1:
                object_item = TreeItem([f"{object.Name} <{object.id()}>"], parent)
                parent.appendChild(object_item)
            else:
                object_item = parent
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
            object_item.appendChild(
                TreeItem(["Global ID", object.GlobalId], parent=object_item)
            )

            if object.is_a("IfcElement"):
                try:
                    object_item.appendChild(
                        self.newItem("Contained in", object.ContainedInStructure[0].RelatingStructure, object_item)
                    )
                except IndexError:
                    pass

            elif object.is_a("IfcSpatialStructureElement"):
                decomposes = object.Decomposes
                if decomposes:
                    object_item.appendChild(
                    self.newItem("Contained in", decomposes[0].RelatingObject, object_item)
                    )

                contains_item = TreeItem(["Contains"], parent=object_item)
                object_item.appendChild(contains_item)
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


            info_item = TreeItem(["Info"], parent=object_item)
            object_item.appendChild(info_item)
            
            for k,v in info.items():
                if k not in ["Name", "id", "GlobalId", "type", "ObjectType"]:
                    info_item.appendChild(
                        self.newItem(k, v, info_item)
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
                                    






