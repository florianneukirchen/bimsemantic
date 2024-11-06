from PySide6.QtCore import QDate, QFile, Qt, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import QTreeView
import ifcopenshell.util.element
from .treebase import TreeItem, TreeModelBaseclass


class DetailsTreeModel(TreeModelBaseclass):
    def setupRootItem(self):
        self._rootItem = TreeItem()
        self.column_count = 2

    def newItem(self, key, value, parent):
        if isinstance(value, ifcopenshell.entity_instance):
            value = f"{value.is_a()} {value.id()}"

        item = TreeItem([key, value], parent=parent)
        return item


    def setupModelData(self, data, parent):
        self.rows_spanned = []
        if not isinstance(data, list):
            data = [data]
        self.ifc_objects = data

        for object in self.ifc_objects:
            if len(self.ifc_objects) > 1:
                object_item = TreeItem([f"{object.Name} (ID {object.id()})"], parent=parent)
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
            if info["ObjectType"] is not None:
                object_item.appendChild(
                    TreeItem(["Object Type", info["ObjectType"]], parent=object_item)
                )
            object_item.appendChild(
                TreeItem(["IFC ID", object.id()], parent=object_item)
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
            
            psets = ifcopenshell.util.element.get_psets(object)
            for pset_name, pset in psets.items():
                pset_item = TreeItem([pset_name], parent=object_item)
                self.rows_spanned.append(pset_item)
                object_item.appendChild(pset_item)
                for k, v in pset.items():
                    pset_item.appendChild(
                        TreeItem([k,v], parent=pset_item)
                    )



        






