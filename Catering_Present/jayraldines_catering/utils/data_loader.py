"""
utils/data_loader.py
--------------------
Reusable background data-loading worker built on QThread.

Usage example in any page:
    def _do_reload(self):
        self._start_loader(repo.get_all_customers_with_loyalty, self._on_data_ready)

    def _on_data_ready(self, data):
        self._customers = data or []
        self._populate_table()
"""

from PySide6.QtCore import QThread, Signal, QObject


class _LoaderWorker(QObject):
    """Runs a callable in a background thread and emits the result."""
    finished = Signal(object)
    errored  = Signal(str)

    def __init__(self, fn, args, kwargs):
        super().__init__()
        self._fn     = fn
        self._args   = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as exc:
            self.errored.emit(str(exc))


class DataLoader(QThread):
    """
    Drop-in background loader.  Creates a worker, moves it to this thread,
    emits data_ready(result) on completion, or load_error(msg) on failure.

    The caller is responsible for keeping a reference to the DataLoader
    so it is not garbage-collected while the thread is running.
    """

    data_ready = Signal(object)
    load_error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._worker = _LoaderWorker(fn, args, kwargs)
        self._worker.moveToThread(self)
        self.started.connect(self._worker.run)
        self._worker.finished.connect(self.data_ready)
        self._worker.errored.connect(self.load_error)
        self._worker.finished.connect(self.quit)
        self._worker.errored.connect(self.quit)
        self.finished.connect(self._cleanup)

    def _cleanup(self):
        self._worker.deleteLater()


def run_async(page, fn, on_success, on_error=None, *args, **kwargs):
    """
    Convenience helper. Starts a DataLoader on *page* for the callable *fn*.
    Supports multiple concurrent workers on the same page.
    """
    if not hasattr(page, "_active_loaders"):
        page._active_loaders = set()

    def _safe_success(data):
        try:
            from shiboken6 import isValid
            if hasattr(page, "isVisible") and not isValid(page):
                return
        except Exception:
            pass
        try:
            on_success(data)
        except Exception as exc:
            import traceback
            print(f"[run_async] Error in callback {getattr(on_success, '__name__', str(on_success))}: {exc}\n{traceback.format_exc()}")

    def _safe_error(msg):
        try:
            from shiboken6 import isValid
            if hasattr(page, "isVisible") and not isValid(page):
                return
        except Exception:
            pass
        if on_error:
            try:
                on_error(msg)
            except Exception as exc:
                print(f"[run_async] Error in on_error callback: {exc}")
        else:
            print(f"[DataLoader] Error in {getattr(fn, '__name__', str(fn))}: {msg}")

    loader = DataLoader(fn, *args, **kwargs)
    loader.data_ready.connect(_safe_success)
    loader.load_error.connect(_safe_error)
    
    page._active_loaders.add(loader)
    loader.finished.connect(lambda: _clear_loader(page, loader))
    loader.start()


def _clear_loader(page, loader):
    """Remove the loader from the page's active set after it finishes."""
    try:
        if hasattr(page, "_active_loaders"):
            page._active_loaders.discard(loader)
    except Exception:
        pass
