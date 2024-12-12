import ifctester
import ifctester.reporter
import ifcopenshell
import os


class Validators:
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
        self.validators.append(validator)

    def validate(self):
        for validator in self.validators:
            if not validator.title in self.reporters:
                self.reporters[validator.title] = {}
            for ifc_file in self.ifc_files:
                reporter = validator.validate_file(ifc_file)
                self.reporters[validator.title][ifc_file.filename] = reporter
                self.analyze_results(reporter)
        print(self.results_by_guid)
                
    def analyze_results(self, reporter):
        for spec in reporter.results['specifications']:
            for requirement in spec['requirements']:
                for entity in requirement['failed_entities']:
                    element = entity['element']
                    self.add_failed(element.GlobalId) 
                for entity in requirement['passed_entities']:
                    element = entity['element']
                    self.add_passed(element.GlobalId) 

    def add_passed(self, guid):
        if not guid in self.results_by_guid:
            self.results_by_guid[guid] = [1,0]
        else:
            self.results_by_guid[guid][0] += 1

    def add_failed(self, guid):
        if not guid in self.results_by_guid:
            self.results_by_guid[guid] = [0,1]
        else:
            self.results_by_guid[guid][1] += 1

    def save_bcf(self, validator_title, ifc_filename, output_filename):
        reporter = self.reporters[validator_title][ifc_filename]
        reporter.to_file(output_filename)

    @property
    def is_validated(self):
        return self.results_by_guid == {}

class IfsValidator:
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File {filename} not found.")
        self._abspath = os.path.abspath(filename)
        self._filename = os.path.basename(self._abspath)

        self.rules = ifctester.ids.open(filename)
        self._title = self.rules.info['title']

    def validate_file(self, ifc_file):
        self.rules.validate(ifc_file.model)
        reporter = ifctester.reporter.Bcf(self.rules)
        reporter.report()
        return reporter
    
    

    @property
    def filename(self):
        return self._filename
    
    @property
    def abspath(self):
        return self._abspath
    
    @property
    def title(self):
        return self._title
    
    def __repr__(self):
        return f"IfsValidator({self._title}, {self._filename})"



