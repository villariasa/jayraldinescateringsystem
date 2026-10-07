# Dynamic System Configuration Hot-Reloading Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Config Manager, App State, File Watcher

---

## 1. Feature Intent
Changing business profile details, tax percentages, or printer port assignments should take effect immediately across all active dialogs without requiring a complete application restart.

---

## 2. File Watcher & Signal Dispatch

The system watches `config.json` using `QFileSystemWatcher`:

```python
from PySide6.QtCore import QFileSystemWatcher, QObject, Signal

class ConfigWatcher(QObject):
    config_changed = Signal(dict)

    def __init__(self, config_path):
        super().__init__()
        self.config_path = config_path
        self.watcher = QFileSystemWatcher([config_path])
        self.watcher.fileChanged.connect(self._on_file_changed)

    def _on_file_changed(self, path):
        new_conf = load_config_file(path)
        self.config_changed.emit(new_conf)
```

---

## 3. Subscribed UI Components
- **OrderPrintDialog:** Updates business address and phone numbers immediately.
- **CashierTopBar:** Updates active terminal ID and branch name.
- **TaxEngine:** Updates BIR VAT / Non-VAT percentage dynamically.\n