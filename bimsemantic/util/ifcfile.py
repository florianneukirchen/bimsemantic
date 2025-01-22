"""
/***************************************************************************
                              BIM Semantic Viewer
                              -------------------
        begin                : 2024-10-03
        copyright            : (C) 2025 by Florian Neukirchen
        email                : mail@riannek.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import ifcopenshell
import os


class IfcFile:
    """Represents an IFC file that is opened with ifcopenshell.

    Includes attributes such as file name and path and some methods as shortcuts
    to the ifcopenshell model.

    :param filename: The path to the IFC file to be opened.
    :type filename: str
    :raises FileNotFoundError: File does not exist
    :raises ValueError: File is not a valid IFC file
    """

    def __init__(self, filename):
        self._abspath = os.path.abspath(filename)
        self._filename = os.path.basename(self._abspath)
        if not os.path.exists(self._abspath):
            raise FileNotFoundError(f"File {self._abspath} not found.")
        self._megabytes = round(os.path.getsize(self._abspath) / 1048576, 1)

        # Open the file with ifcopenshell
        try:
            self._model = ifcopenshell.open(self._abspath)
        except RuntimeError:
            raise ValueError(f"File {self._abspath} is not a valid IFC file.")

        self._project = self._model.by_type("IfcProject")[0]
        self._pset_info = self._get_pset_info()
        self._qset_info = self._get_qset_info()

    @property
    def model(self):
        """The ifcopenshell file object"""
        return self._model

    @property
    def project(self):
        """The IfcProject object"""
        return self._project

    @property
    def filename(self):
        """The name of the file"""
        return self._filename

    @property
    def abspath(self):
        """The absolute path of the file"""
        return self._abspath

    @property
    def pset_info(self):
        """A dictionary with the property sets and their properties"""
        return self._pset_info

    @property
    def qset_info(self):
        """A dictionary with the quantity sets and their quantities"""
        return self._qset_info

    @property
    def megabytes(self):
        """The size of the file in megabytes"""
        return self._megabytes

    def count_ifc_elements(self):
        """Returns the number of IfcElement objects in the file"""
        return len(self._model.by_type("IfcElement"))

    def get_element(self, id):
        """Returns an IFC object by its ID"""
        try:
            element = self.model.by_id(id)
        except RuntimeError:
            return None
        return element

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

    def _get_qset_info(self):
        if self._model.schema_version[0] < 4:
            return {}
        qset_info = {}
        qsets = self._model.by_type("IfcQuantitySet")
        for qset in qsets:
            if not qset.Name in qset_info:
                qset_info[qset.Name] = []
            for q in qset.Quantities:
                if not q.Name in qset_info[qset.Name]:
                    qset_info[qset.Name].append(q.Name)
        return qset_info

    def pset_count(self):
        """The number of property sets in the file"""
        return len(self.pset_info)

    def qset_count(self):
        """The number of quantity sets in the file"""
        return len(self.qset_info)

    def __repr__(self):
        return f"IfcFile({self.filename})"

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


class IfcFiles:
    """A collection of IfcFile objects

    Used to represent all opened IFC files as IfcFile objects.
    Files are added with add_file().
    It is possible to iterate over the IfcFile objects or to get
    a specific file by its index or filename.

    Example::

        ifcfiles = IfcFiles()
        ifcfiles.add_file("file1.ifc")
        ifcfiles.add_file("file2.ifc")

        ifcfiles[0] # returns the first file
        ifcfiles["file1.ifc"] # returns the first file

        for ifcfile in ifcfiles:
            print(ifcfile.filename)



    """

    def __init__(self):
        self._ifcfiles = []

    def add_file(self, filename):
        """Adds an IFC file to the collection

        Opens the file and returns the IfcFile object that contains the
        IfcOpenShell file object.

        If the file is already open, it is not added again. If the GUID of the
        IfcProject object is different from the first file, a ValueError is raised.

        :raises FileNotFoundError: File does not exist
        :raises ValueError: File is not a valid IFC file
        :raises ValueError: All files must belong to the same project

        """
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
        """Returns an IFC object by its GUID

        If filename is provided, the search is limited to that file.
        Otherwise the element is returned from the first file that contains it.
        Returns None if the element is not found.

        :param guid: The GUID of the element
        :type guid: str
        :param filename: The name of the file where the element is located
        :type filename: str, Optional
        :return: The IFC object
        :rtype: ifcopenshell entity
        """
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
        """Returns an IFC object of a given file by its ID

        :param filename: The name of the file
        :type filename: str
        :param id: The ID of the element
        :type id: int
        :return: The IFC object
        :rtype: ifcopenshell entity
        """
        try:
            ifc_file = self[filename]
        except IndexError:
            return None
        try:
            element = ifc_file.model.by_id(id)
        except RuntimeError:
            return None
        return element

    def get_project(self):
        """Returns the IfcProject object of the first file

        :return: The IfcProject object
        :rtype: ifcopenshell entity
        """
        try:
            project = self._ifcfiles[0].model.by_type("IfcProject")[0]
        except IndexError:
            return None
        return project

    def count(self):
        """The number of files in the collection"""
        return len(self._ifcfiles)

    def filenames(self):
        """Returns a list of the filenames of the files in the collection"""
        return [ifcfile.filename for ifcfile in self._ifcfiles]

    @property
    def pset_info(self):
        """A dictionary with the property sets and their properties for all files

        The names of property sets and properties are unique.
        """
        pset_info = {}
        for ifcfile in self._ifcfiles:
            for pset_name, pset_props in ifcfile.pset_info.items():
                if not pset_name in pset_info:
                    pset_info[pset_name] = []
                for prop in pset_props:
                    if not prop in pset_info[pset_name]:
                        pset_info[pset_name].append(prop)
        return pset_info
