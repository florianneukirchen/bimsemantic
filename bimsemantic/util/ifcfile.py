import ifcopenshell
import os


class IfcFile():
    def __init__(self, filename):
        self._abspath = os.path.abspath(filename)
        self._filename = os.path.basename(self._abspath)
        if not os.path.exists(self._abspath):
            raise FileNotFoundError(f"File {self._abspath} not found.")
        self._megabytes = round(os.path.getsize(self._abspath) / 1048576, 1)
        try:
            self._model = ifcopenshell.open(self._abspath)
        except RuntimeError:
            raise ValueError(f"File {self._abspath} is not a valid IFC file.")
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
    
    @property
    def megabytes(self):
        return self._megabytes

    def count_ifc_elements(self):
        return len(self._model.by_type("IfcElement"))
    
    def _get_pset_info(self):
        pset_info = {}
        psets = self._model.by_type("IfcPropertySet")
        for pset in psets:
            if not pset.Name in pset_info:
                pset_info[pset.Name] = []
            for prop in pset.HasProperties:
                if not prop.Name in pset_info[pset.Name]:
                    pset_info[pset.Name].append(prop.Name)
        return pset_info
    
    
    def pset_count(self):
        return len(self.pset_info)
    
    # def get_pset_cols(self):
    #     cols = []
    #     for _, pset_props in self.pset_info.items():
    #         for prop in pset_props:
    #             cols.append(prop)
    #     return cols
    
    # def pset_items(self):
    #     for pset_name, pset_props in self.pset_info.items():
    #         for prop in pset_props:
    #             yield pset_name, prop


class IfcFiles():
    def __init__(self):
        self._ifcfiles = []
    
    def add_file(self, filename):
        # Before opening, check if the file is already open
        abspath = os.path.abspath(filename)
        for ifcfile in self._ifcfiles:
            if ifcfile.abspath == abspath:
                return None
        ifcfile = IfcFile(filename)
        if len(self._ifcfiles) > 0:
            project_guid = self[0].model.by_type("IfcProject")[0].GlobalId
            new_project_guid = ifcfile.model.by_type("IfcProject")[0].GlobalId
            if project_guid != new_project_guid:
                raise ValueError("All files must belong to the same project.")
        self._ifcfiles.append(ifcfile)
        return ifcfile

    def __getitem__(self, index):
        if isinstance(index, int):
            return self._ifcfiles[index]
        elif isinstance(index, str):
            for ifcfile in self._ifcfiles:
                if ifcfile.filename == index:
                    return ifcfile
        raise IndexError(f"Index {index} not found.")
    
    def __len__(self):
        return len(self._ifcfiles)
    
    def __iter__(self):
        for ifcfile in self._ifcfiles:
            yield ifcfile

    def get_element_by_guid(self, guid, filename=None):
        if filename:
            ifcfile = self[filename]
            element = ifcfile.model.by_guid(guid)
            if element:
                return element
            return None
        else:
            for ifcfile in self._ifcfiles:
                element = ifcfile.model.by_guid(guid)
                if element:
                    return element
            return None

    def get_element(self, filename, id):
        try:
            ifc_file = self[filename]
        except IndexError:
            None
        try:
            element = ifc_file.model.by_id(id)
        except RuntimeError:
            return None
        return element

    def get_project(self):
        try:
            project = self._ifcfiles[0].model.by_type("IfcProject")[0]
        except IndexError:
            return None
        return project

    def count(self):
        return len(self._ifcfiles)
    
    def filenames(self):
        return [ifcfile.filename for ifcfile in self._ifcfiles]

    @property
    def pset_info(self):
        pset_info = {}
        for ifcfile in self._ifcfiles:
            for pset_name, pset_props in ifcfile.pset_info.items():
                if not pset_name in pset_info:
                    pset_info[pset_name] = []
                for prop in pset_props:
                    if not prop in pset_info[pset_name]:
                        pset_info[pset_name].append(prop)
        return pset_info