from PySide6.QtCore import QRunnable, Slot, Signal, QObject
from bimsemantic.util import IfcFile, IfcFiles

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value)

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    """
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
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        self.signals.feedback.emit("start")
        results = []
        for filename in self.filenames:
            self.signals.feedback.emit(filename)
            try:
                ifc_file = self.ifcfiles.add_file(filename)
                results.append(ifc_file)
            except FileNotFoundError as e:
                self.signals.error.emit((type(e), str(e)))
            except ValueError as e:
                self.signals.error.emit((type(e), str(e)))
            self.signals.result.emit(results)
        
        self.signals.finished.emit()


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @Slot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            payload = (type(e), e.args[0],)
            self.signals.error.emit(payload)
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done