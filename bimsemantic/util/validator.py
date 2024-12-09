import ifctester
import ifctester.reporter
import ifcopenshell
import os

class IfsValidator:
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File {filename} not found.")
        self._abspath = os.path.abspath(filename)
        self._filename = os.path.basename(self._abspath)

        self.rules = ifctester.ids.open(filename)
        self.report = None

    def validate(self, model):
        self.rules.validate(model)
        self.report = ifctester.reporter.Bcf(self.rules)
        # Return the report as JSON
        return self.report.report()
    
    def save_bcf(self, filename):
        if not self.report:
            raise ValueError("No report. Run validate() first.")
        self.report.to_file(filename)

    @property
    def filename(self):
        return self._filename
    
    @property
    def abspath(self):
        return self._abspath


if __name__ == "__main__":
    folder = '/media/riannek/PortableSSD/ids_testcases'
    ifc_file = os.path.join(folder, "IDS_wooden-windows_IFC.ifc")
    model = ifcopenshell.open(ifc_file)
    ids_file = os.path.join(folder, "IDS_wooden-windows.ids")
    validator = IfsValidator(ids_file)
    report = validator.validate(model)
    print(report)
    validator.save_bcf("report.bcfzip")