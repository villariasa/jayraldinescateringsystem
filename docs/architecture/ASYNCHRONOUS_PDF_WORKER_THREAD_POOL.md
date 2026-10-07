# Asynchronous PDF Generation & Worker Thread Pool Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** ReportLab Exporter, PySide6 Concurrency, Task Scheduler

---

## 1. Problem Statement
Compiling high-resolution PDF booking agreements with embedded banquet terms, food selection tables, and company seals using ReportLab takes between 800ms and 2.5s. Executing this on PySide6's main GUI thread results in noticeable "Application Not Responding" stutter.

---

## 2. Architecture & Concurrency Model

```python
from PySide6.QtCore import QRunnable, QThreadPool, QObject, Signal

class PdfExportSignals(QObject):
    finished = Signal(str)  # Output file path
    error = Signal(str)     # Error message
    progress = Signal(int)  # Percent completion

class PdfExportWorker(QRunnable):
    def __init__(self, booking_data, output_path):
        super().__init__()
        self.booking_data = booking_data
        self.output_path = output_path
        self.signals = PdfExportSignals()

    def run(self):
        try:
            # ReportLab heavy PDF compilation executes in background worker
            generate_booking_agreement(self.booking_data, self.output_path)
            self.signals.finished.emit(self.output_path)
        except Exception as e:
            self.signals.error.emit(str(e))
```

---

## 3. UI Integration
While the worker executes, the UI displays a smooth spinner overlay and disables the Export button, preventing concurrent generation race conditions.\n