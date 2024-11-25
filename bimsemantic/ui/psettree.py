from PySide6.QtCore import Qt, QModelIndex
from bimsemantic.ui import TreeItem, TreeModelBaseclass, CustomTreeMaker, CustomFieldType
import ifcopenshell.util.element

class PsetTreeModel(TreeModelBaseclass):

    def setup_root_item(self):
        self._rootItem = TreeItem(["Property Set", "Info"])

    def setup_model_data(self, data, parent):
        self.ifc_files = data
        
        for file in self.ifc_files:
            self.add_file(file)

    def add_file(self, ifc_file):

        elements = ifc_file.by_type("IfcElement")

        for element in elements:
            psets = ifcopenshell.util.element.get_psets(element, psets_only=True)
            if not psets:
                continue
            for pset_name, pset in psets.items():
                pset_item = self.get_child_by_label(self._rootItem, pset_name)
                if not pset_item:
                    pset_item = TreeItem([pset_name, ""])
                    self._rootItem.appendChild(pset_item)
                for prop_name, prop_value in pset.items():
                    prop_item = self.get_child_by_label(pset_item, prop_name)
                    if not prop_item:
                        prop_item = TreeItem([prop_name, ""])
                        pset_item.appendChild(prop_item)
                    #prop_item.set_data(1, prop_value)