# Asynchronous PDF Export Worker Thread Specification

## Thread Isolation
Heavy PDF canvas rendering executes on dedicated `QThread` workers, emitting progress signals (`0%` to `100%`) without blocking the PySide6 UI event loop.
