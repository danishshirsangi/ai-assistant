from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(str)
    stage = Signal(str)
    finished = Signal(object)


class FunctionWorker(QRunnable):
    """QRunnable whose Python wrapper is retained by MainWindow until finished."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        # MainWindow owns this runnable and releases it after the finished signal.
        # Letting QThreadPool delete it can invalidate the Python-owned signal object
        # while queued signal deliveries are still being processed.
        self.setAutoDelete(False)
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
            result = self.fn(*self.args, **kwargs)
        except Exception as exc:
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(result)
        finally:
            # Emitted after result/error so the GUI can release this runnable only
            # after its earlier queued deliveries have been posted.
            self.signals.finished.emit(self)
