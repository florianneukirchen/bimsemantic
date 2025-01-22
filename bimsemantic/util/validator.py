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
import xml.etree.ElementTree as ET
import os
import json
import ifctester
import ifctester.reporter
import ifcopenshell
import ifcopenshell.util.element


class Validators:
    """Singleton with all validators and their results.

    The parameter ifc_files is only required at the first initialization.

    For each element that was validated (according to applicability of the validator),
    the dict self.results_by_guid contains the number of failed and passed validations
    as a list [passed, failed], under the key of the element's GUID.

    self.reporters is a nested dict with the keys "validator_id" and "ifc filename"
    and contains the reporter object of the validation (ifctester.reporter.Bcf).
    Only exception is the integrity check, which is stored directly under the key
    "integrity".

    :param ifc_files: The IfcFiles object of the main window
    :type ifc_files: IfcFiles
    """

    _instance = None

    def __new__(cls, ifc_files=None):
        # Singleton pattern
        # https://python-patterns.guide/gang-of-four/singleton/
        if cls._instance is None:
            cls._instance = super(Validators, cls).__new__(cls)
            cls._instance.__init__(ifc_files)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, ifc_files=None):
        if hasattr(self, "_initialized"):
            return
        self.validators = []
        self.reporters = {}
        self.results_by_guid = {}
        self.ifc_files = ifc_files
        self._initialized = True

    def reset(self, ifc_files):
        """Reset the validation results"""
        self.reporters = {}
        self.results_by_guid = {}
        # Otherwise it still uses the old files after reset
        self.ifc_files = ifc_files

    def add_validator(self, validator):
        """Add a validator to the collection

        :param validator: The validator to add
        :type validator: IdsValidator
        """
        self.validators.append(validator)

    def remove_validator(self, validator_id):
        """Remove an IDS validator from the collection

        :param validator_id: The ID of the validator to remove
        :type validator_id: str
        """
        for validator in self.validators:
            if validator.id == validator_id:
                self.validators.remove(validator)
                if validator.id in self.reporters:
                    del self.reporters[validator.id]
                break

        self.results_by_guid = {}

    def get_validator(self, validator_id):
        """Get a validator by its ID (filename in case of IDS)

        :param validator_id: The ID (filename) of the validator
        :type validator_id: str
        """
        for validator in self.validators:
            if validator.id == validator_id:
                return validator
        return None

    def validate(self, validator_id=None):
        """Run the validation for all validators or a specific validator

        :param validator_id: The ID of the validator to run, defaults to None (all validators)
        :type validator_id: str, optional
        """
        if validator_id is None:
            validators = self.validators
        else:
            for validator in self.validators:
                if validator.id == validator_id:
                    validators = [validator]
                    break

        self.results_by_guid = {}
        self.reporters = {}

        for validator in validators:
            if not validator.id in self.reporters:
                self.reporters[validator.id] = {}

            if validator.id == "integrity":
                # This is the only one not to be run on the IFC files seperately
                reporter = validator.validate()
                self.analyze_results(reporter)
                self.reporters[validator.id] = reporter
            else:
                for ifc_file in self.ifc_files:
                    reporter = validator.validate_file(ifc_file)
                    self.reporters[validator.id][ifc_file.filename] = reporter
                    self.analyze_results(reporter)

    def analyze_results(self, reporter):
        """Count the number of passed and failed validations for each element

        :param reporter: The reporter object of the validation
        :type reporter: ifctester.reporter.Bcf
        """
        for spec in reporter.results["specifications"]:
            for requirement in spec["requirements"]:
                for entity in requirement["failed_entities"]:
                    element = entity["element"]
                    try:
                        self.add_failed(element.GlobalId)
                    except AttributeError:
                        # No GlobalId for IfcMaterialConstituentSet
                        pass
                for entity in requirement["passed_entities"]:
                    element = entity["element"]
                    try:
                        self.add_passed(element.GlobalId)
                    except AttributeError:
                        # No GlobalId for IfcMaterialConstituentSet
                        pass

    def add_passed(self, guid):
        """Helper to add a passed validation to the results"""
        if not guid in self.results_by_guid:
            self.results_by_guid[guid] = [1, 0]
        else:
            self.results_by_guid[guid][0] += 1

    def add_failed(self, guid):
        """Helper to add a failed validation to the results"""
        if not guid in self.results_by_guid:
            self.results_by_guid[guid] = [0, 1]
        else:
            self.results_by_guid[guid][1] += 1

    def get_validation_for_element(self, guid, filenames):
        """Get the complete validation results for a specific element

        Used by the details view.

        :param guid: The GUID of the element
        :type guid: str
        :param filenames: The list of filenames to search in
        :type filenames: list
        :return: The failed and passed validations
        :rtype: tuple of list of dicts
        """

        failed_specs = []
        passed_specs = []

        if self.reporters == {}:
            return failed_specs, passed_specs

        for validator_id, validator_files in self.reporters.items():

            for filename in filenames:
                if validator_id == "integrity":
                    specs = validator_files.results["specifications"]
                else:
                    specs = validator_files[filename].results["specifications"]

                for spec in specs:
                    for requirement in spec["requirements"]:
                        for entity in requirement["failed_entities"]:
                            if entity["element"].GlobalId == guid:
                                info = {
                                    "validator": validator_id,
                                    "spec": spec["name"],
                                    "requirement": requirement["description"],
                                    "reason": entity["reason"],
                                    "spec description": spec["description"],
                                }
                                if not validator_id == "integrity":
                                    info["ICF file"] = filename
                                failed_specs.append(info)
                        for entity in requirement["passed_entities"]:
                            if entity["element"].GlobalId == guid:
                                info = {
                                    "validator": validator_id,
                                    "spec": spec["name"],
                                    "requirement": requirement["description"],
                                    "spec description": spec["description"],
                                }
                                if not validator_id == "integrity":
                                    info["ICF file"] = filename
                                passed_specs.append(info)
                if validator_id == "integrity":
                    # Only add one entry for integrity check
                    break
        return failed_specs, passed_specs

    def save_results(self, validator_id, ifc_filename, output_filename, as_bcf):
        """Save the validation result to BCF or JSON

        Saves the result of a specific reporter, i.e. for a specific validator
        and IFC file. Format is zipped BCF or JSON.

        :param validator_id: The ID of the validator
        :type validator_id: str
        :param ifc_filename: The filename of the IFC file
        :type ifc_filename: str
        :param output_filename: The output filename
        :type output_filename: str
        :param as_bcf: Save as BCF if True, otherwise as JSON
        :type as_bcf: bool
        """
        if validator_id == "integrity":
            reporter = self.reporters[validator_id]
        else:
            reporter = self.reporters[validator_id][ifc_filename]
        if as_bcf:
            reporter.to_file(output_filename)
        else:
            # Need to turn all the ifcopenshell objects into strings
            results = reporter.results.copy()
            for spec in results["specifications"]:
                for requirement in spec["requirements"]:
                    for entity in requirement["failed_entities"]:
                        entity["element"] = " "  # entity['element'].to_string()
                        try:
                            entity["element_type"] = (
                                " "  # entity['element_type'].to_string()
                            )
                        except KeyError:
                            pass
                    for entity in requirement["passed_entities"]:
                        entity["element"] = " "  # entity['element'].to_string()
                        try:
                            entity["element_type"] = (
                                " "  # entity['element_type'].to_string()
                            )
                        except KeyError:
                            pass
                    for k, v in requirement.items():
                        if isinstance(v, ifctester.facet.Restriction):
                            requirement[k] = str(v)

            with open(output_filename, "w") as f:
                json.dump(results, f, indent=4)

    def status(self, validator_id):
        """True if the validator has been run"""
        return validator_id in self.reporters


class IdsValidator:
    """Validator using rules from IDS file

    The filename is used as the id of the validator.

    :param filename: The filename or path of the IDS file
    :type filename: str
    """

    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File {filename} not found.")
        self._abspath = os.path.abspath(filename)
        self._filename = os.path.basename(self._abspath)
        self.id = self._filename

        try:
            self.rules = ifctester.ids.open(filename)
        except ET.ParseError:
            raise ValueError(f"File {self._abspath} is not a valid IDS file.")
        self._title = self.rules.info["title"]

    def validate_file(self, ifc_file):
        """Run the validation on an IFC file

        :param ifc_file: The IFC file to validate
        :type ifc_file: IfcFile
        :return: The reporter object of the validation
        :rtype: ifctester.reporter.Bcf
        """
        self.rules.validate(ifc_file.model)
        reporter = ifctester.reporter.Bcf(self.rules)
        reporter.report()
        return reporter

    @property
    def filename(self):
        """The name of the IDS file"""
        return self._filename

    @property
    def abspath(self):
        """Absolute path of the IDS file"""
        return self._abspath

    @property
    def title(self):
        """Title of the IDS file"""
        return self._title

    def __repr__(self):
        return f"IdsValidator({self._title}, {self._filename})"


class IntegrityValidator:
    """If entities are in several IFC files, they should be the same

    Checks the attributes and psets for entities with the same GUID
    in different IFC files.

    The interface mimics IdsValidator, but the rules are hardcoded.
    """

    def __init__(self, ifc_files, ifc_tabs):
        self.ifc_files = ifc_files
        self.treemodel = ifc_tabs.locationtab.treemodel
        self.title = "Integrity check"
        self.filename = ""
        self.id = "integrity"
        self.reset_results()

    def reset_results(self):
        # Dict with the structure required by the BCF reporter
        self.results = {
            "title": self.title,
            "specifications": [
                {
                    "name": self.title,
                    "description": "Check if entities with the same GUID are the same",
                    "applicability": ["All entities"],
                    "status": True,  # True means all passed
                    "requirements": [],
                    "total_checks_pass": 0,
                    "total_checks_fail": 0,
                }
            ],
        }

        requirements = [
            "The ID should be the same in all files",
            "The attributes should be the same in all files",
            "The property sets should be the same in all files",
        ]

        for requirement in requirements:
            self.results["specifications"][0]["requirements"].append(
                {
                    "description": requirement,
                    "passed_entities": [],
                    "failed_entities": [],
                    "status": True,
                }
            )

        self.requirements = self.results["specifications"][0]["requirements"]
        self.spec = self.results["specifications"][0]

    def validate(self):
        """Run the validation on all IFC files"""
        self.reset_results()
        for item in self.treemodel._rootItem.children:
            self.check_item(item)
        # Init a BCF reporter without IDS, and set the results
        # Undocumented API, see
        # https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.8.0/src/ifctester/ifctester/reporter.py#L35
        reporter = ifctester.reporter.Bcf(None)
        reporter.results = self.results
        return reporter

    def check_item(self, item):
        """Check a tree item and all its childs"""
        for child in item.children:
            self.check_item(child)

        if hasattr(item, "filenames") and len(item.filenames) > 1:
            guid = item.guid
            left_filename = item.filenames[0]
            left = self.ifc_files.get_element_by_guid(guid, left_filename)

            left_info = left.get_info()
            left_id = left_info.pop("id")
            for k, v in left_info.items():
                if isinstance(v, (ifcopenshell.entity_instance, tuple)):
                    left_info[k] = str(v)

            left_psets = ifcopenshell.util.element.get_psets(left)

            passed_id = True
            passed_info = True
            passed_psets = True

            for filename in item.filenames[1:]:
                right = self.ifc_files.get_element_by_guid(guid, filename)
                right_info = right.get_info()
                right_id = right_info.pop("id")

                for k, v in right_info.items():
                    if isinstance(v, (ifcopenshell.entity_instance, tuple)):
                        right_info[k] = str(v)

                right_psets = ifcopenshell.util.element.get_psets(right)

                if left_id != right_id:
                    passed_id = False

                if left_info != right_info:
                    passed_info = False

                if left_psets != right_psets:
                    passed_psets = False

            if not passed_id:
                self.requirements[0]["status"] = False
                self.requirements[0]["failed_entities"].append(
                    {
                        "element": left,
                        "reason": f"ID mismatch: {left_id} != {right_id}",
                    }
                )
                self.spec["total_checks_fail"] += 1
                self.spec["status"] = False
            else:
                self.requirements[0]["passed_entities"].append(
                    {
                        "element": left,
                    }
                )
                self.spec["total_checks_pass"] += 1

            if not passed_info:
                self.requirements[1]["status"] = False
                self.requirements[1]["failed_entities"].append(
                    {
                        "element": left,
                        "reason": f"Attribute mismatch: {left_info} != {right_info}",
                    }
                )
                self.spec["total_checks_fail"] += 1
                self.spec["status"] = False
            else:
                self.requirements[1]["passed_entities"].append(
                    {
                        "element": left,
                    }
                )
                self.spec["total_checks_pass"] += 1

            if not passed_psets:
                self.requirements[2]["status"] = False
                self.requirements[2]["failed_entities"].append(
                    {
                        "element": left,
                        "reason": f"Pset mismatch: {left_psets} != {right_psets}",
                    }
                )
                self.spec["total_checks_fail"] += 1
                self.spec["status"] = False
            else:
                self.requirements[2]["passed_entities"].append(
                    {
                        "element": left,
                    }
                )
                self.spec["total_checks_pass"] += 1

    # Helpers to mimic the interface of IdsValidator
    class Spec:
        def __init__(self, spec):
            self.spec = spec
            self.applicability = [self.Applicability()]
            self.requirements = [self.Requirement(req) for req in spec["requirements"]]
            self.name = spec["name"]
            self.description = spec["description"]
            self.instructions = ""

        class Applicability:
            def to_string(self, *args):
                return "All entities"

        class Requirement:
            def __init__(self, req):
                self.req = req
                self.description = req["description"]
                self.instructions = ""

            def to_string(self, *args):
                return self.req["description"]

    class Rules:
        def __init__(self, specs):
            self.info = {"title": "Integrity check"}
            self.specifications = [IntegrityValidator.Spec(spec) for spec in specs]

    @property
    def rules(self):
        """The rules of the validator"""
        return self.Rules(self.results["specifications"])
