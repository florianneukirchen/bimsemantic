from PySide6.QtCore import QRunnable, Slot, Signal, QObject

class WorkerSignals(QObject):
    """Helper class to transport signals from Workers to the main thread
    
    QRunnable is not derived from QObject and therefore does not have signals.
    Enables workers to emit the signals: 
        finished 
        error (as tuple of type and errormessage)
        progress (int, percentage) 
        feedback (str)
        result (object with the result)
    """

    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)
    feedback = Signal(str)


class WorkerAddFiles(QRunnable):
    """
    Worker to open IFC files

    Opens the IFC files passed as filenames using IfcOpenShell by adding them
    to the IfcFiles object used by the main window to manage the opened files.
    The worker is supposed to run by QThreadpool. Opening large files takes
    a long time, multithreading keeps the GUI responsive.

    :param ifcfiles: IfcFiles object of the main window
    :type ifcfiles: IfcFiles instance
    :return: List of IfcFile instances of the opened files
    """
    def __init__(self, ifcfiles, filenames):
        super(WorkerAddFiles, self).__init__()
        self.ifcfiles = ifcfiles
        self.filenames = filenames
        self._count = len(filenames)
        self.signals = WorkerSignals()
        self._is_interrupted = False

    @Slot()
    def run(self):
        """Run the worker"""
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
