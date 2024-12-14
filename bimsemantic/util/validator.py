import xml.etree.ElementTree as ET
import os
import json
import ifctester
import ifctester.reporter
import ifcopenshell




class Validators:
    """Singleton with all validators and their results.

    The parameter ifc_files is only required at the first initialization.

    For each element that was validated (according to applicability of the validator),
    the dict self.results_by_guid contains the number of failed and passed validations 
    as a list [passed, failed], under the key of the element's GUID.

    self.reporters is a nested dict with the keys "validator_id" and "ifc filename" 
    and contains the reporter object of the validation (ifctester.reporter.Bcf).

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
        if hasattr(self, '_initialized'):
            return
        self.validators = []
        self.reporters = {}
        self.results_by_guid = {}
        self.ifc_files = ifc_files
        self._initialized = True


    def add_validator(self, validator):
        """Add a validator to the collection
        
        :param validator: The validator to add
        :type validator: IdsValidator
        """
        self.validators.append(validator)

    def remove_validator(self, validator_id):
        """Remove a validator from the collection
        
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
        """Get a validator by its ID
        
        :param validator_id: The ID of the validator
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
            for ifc_file in self.ifc_files:
                reporter = validator.validate_file(ifc_file)
                self.reporters[validator.id][ifc_file.filename] = reporter
                self.analyze_results(reporter)

    def analyze_results(self, reporter):
        """Count the number of passed and failed validations for each element
        
        :param reporter: The reporter object of the validation
        :type reporter: ifctester.reporter.Bcf
        """
        for spec in reporter.results['specifications']:
            for requirement in spec['requirements']:
                for entity in requirement['failed_entities']:
                    element = entity['element']
                    self.add_failed(element.GlobalId) 
                for entity in requirement['passed_entities']:
                    element = entity['element']
                    self.add_passed(element.GlobalId) 

    def add_passed(self, guid):
        """Helper to add a passed validation to the results"""
        if not guid in self.results_by_guid:
            self.results_by_guid[guid] = [1,0]
        else:
            self.results_by_guid[guid][0] += 1

    def add_failed(self, guid):
        """Helper to add a failed validation to the results"""
        if not guid in self.results_by_guid:
            self.results_by_guid[guid] = [0,1]
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
                #for reporter in validator_files[filename]:
                for spec in validator_files[filename].results['specifications']:
                    for requirement in spec['requirements']:
                        for entity in requirement['failed_entities']:
                            if entity['element'].GlobalId == guid:
                                info = {
                                    'validator': validator_id,
                                    'spec': spec['name'],
                                    'requirement': requirement['description'],
                                    'reason': entity['reason'],
                                    'spec description': spec['description'],
                                    'ICF file': filename,
                                }
                                failed_specs.append(info)
                        for entity in requirement['passed_entities']:
                            if entity['element'].GlobalId == guid:
                                info = {
                                    'validator': validator_id,
                                    'spec': spec['name'],
                                    'requirement': requirement['description'],
                                    'spec description': spec['description'],
                                    'ICF file': filename,
                                }
                                passed_specs.append(info)
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
        reporter = self.reporters[validator_id][ifc_filename]
        if as_bcf:
            reporter.to_file(output_filename)
        else:
            # Need to turn all the ifcopenshell objects into strings
            results = reporter.results.copy()
            for spec in results['specifications']:
                for requirement in spec['requirements']:
                    for entity in requirement['failed_entities']:
                        entity['element'] = entity['element'].to_string()
                    for entity in requirement['passed_entities']:
                        entity['element'] = entity['element'].to_string()

            with open(output_filename, 'w') as f:
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
        self._title = self.rules.info['title']

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



