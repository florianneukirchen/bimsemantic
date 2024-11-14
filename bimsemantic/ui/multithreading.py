from PySide6.QtCore import QRunnable, Slot, Signal, QObject
from bimsemantic.util import IfcFile, IfcFiles

class WorkerSignals(QObject):

    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)
    feedback = Signal(str)


class WorkerAddFiles(QRunnable):
    def __init__(self, ifcfiles, filenames):
        super(WorkerAddFiles, self).__init__()
        self.ifcfiles = ifcfiles
        self.filenames = filenames
        self._count = len(filenames)
        self.signals = WorkerSignals()
        self._is_interrupted = False

    @Slot()
    def run(self):
        results = []
        for i, filename in enumerate(self.filenames):
            if self._is_interrupted:
                break
            self.signals.feedback.emit(filename)
            try:
                ifc_file = self.ifcfiles.add_file(filename)
                if self._is_interrupted:
                    break
                if ifc_file:
                    results.append(ifc_file)
                else:
                    self.signals.error.emit(("File already open", filename))
            except FileNotFoundError as e:
                self.signals.error.emit((type(e), str(e)))
            except ValueError as e:
                self.signals.error.emit((type(e), str(e)))
            self.signals.progress.emit((i + 1) / self._count * 100)

        self.signals.result.emit(results)
        self.signals.finished.emit()

    def stop(self):
        self._is_interrupted = True
