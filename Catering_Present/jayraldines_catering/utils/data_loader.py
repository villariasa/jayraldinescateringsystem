"""
utils/data_loader.py
--------------------
Reusable background data-loading worker built on QThread.
Maintains a global strong reference set so no running thread is ever prematurely
destroyed or garbage collected by Python while the underlying OS/Qt thread executes.
"""

from PySide6.QtCore import QThread, Signal, QObject

_LIVE_LOADERS = set()


class DataLoader(QThread):
    """
    Drop-in background loader. Subclasses QThread directly and executes fn in run().
    Automatically registers in _LIVE_LOADERS to guarantee it is not destroyed while running.
    """

    data_ready = Signal(object)
    load_error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._is_stopped = False

        # Keep strong reference while thread is active
        _LIVE_LOADERS.add(self)
        self.finished.connect(self._on_finished)

    def run(self):
        try:
            if self._is_stopped:
                return
            result = self._fn(*self._args, **self._kwargs)
            if not self._is_stopped:
                self.data_ready.emit(result)
        except Exception as exc:
            if not self._is_stopped:
                self.load_error.emit(str(exc))

    def stop(self):
        self._is_stopped = True
        try:
            self.quit()
        except Exception:
            pass

    def _on_finished(self):
        _LIVE_LOADERS.discard(self)


def run_async(page, fn, on_success, on_error=None, *args, **kwargs):
    """
    Convenience helper. Starts a DataLoader on *page* for the callable *fn*.
    Automatically tracks request generations so rapid tab switching or repeated
    nav clicks discard stale background results and avoid redundant UI repaints.
    """
    if not hasattr(page, "_active_loaders"):
        page._active_loaders = set()
    if not hasattr(page, "_async_generations"):
        page._async_generations = {}

    fn_key = getattr(fn, "__name__", str(fn))
    current_gen = page._async_generations.get(fn_key, 0) + 1
    page._async_generations[fn_key] = current_gen

    def _safe_success(data, gen=current_gen):
        if getattr(page, "_async_generations", {}).get(fn_key) != gen:
            return  # Superseded by newer fetch — ignore stale result
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

    def _safe_error(msg, gen=current_gen):
        if getattr(page, "_async_generations", {}).get(fn_key) != gen:
            return  # Superseded
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
