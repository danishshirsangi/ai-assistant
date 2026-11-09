from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(str)
    stage = Signal(str)


class FunctionWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.with_progress = kwargs.pop("with_progress", False)
        self.with_stage = kwargs.pop("with_stage", False)
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            kwargs = dict(self.kwargs)
            if self.with_progress:
                kwargs["on_chunk"] = self.signals.progress.emit
            if self.with_stage:
                kwargs["on_stage"] = self.signals.stage.emit
            self.signals.result.emit(self.fn(*self.args, **kwargs))
        except Exception as exc:
            self.signals.error.emit(str(exc))
