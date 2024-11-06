import ifcopenshell
from collections import OrderedDict
import os


class IfcFile():
    def __init__(self, filename):
        self._abspath = os.path.abspath(filename)
        self._filename = os.path.basename(self._abspath)
        if not os.path.exists(self._abspath):
            raise FileNotFoundError(f"File {self._abspath} not found.")

        self._model = ifcopenshell.open(self._abspath)
        self._pset_info = self._get_pset_info()

    @property
    def model(self):
        return self._model
    
    @property
    def filename(self):
        return self._filename
    
    @property
    def abspath(self):
        return self._abspath
    
    @property
    def pset_info(self):
        return self._pset_info
    
    def _get_pset_info(self):
        pset_info = OrderedDict()
        psets = self._model.by_type("IfcPropertySet")
        for pset in psets:
            if not pset.Name in pset_info:
                pset_info[pset.Name] = []
            for prop in pset.HasProperties:
                if not prop.Name in pset_info[pset.Name]:
                    pset_info[pset.Name].append(prop.Name)
        return pset_info
    
    def get_pset_cols(self):
        cols = []
        for _, pset_props in self.pset_info.items():
            for prop in pset_props:
                cols.append(prop)
        return cols
    
    def pset_items(self):
        for pset_name, pset_props in self.pset_info.items():
            for prop in pset_props:
                yield pset_name, prop
