# PySide6 High-DPI Desktop Scaling & Multi-Monitor Layout Guide

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Desktop UI Runtime, PySide6, High-DPI Display Subsystem

---

## 1. Problem Statement

Commissary workstations range from legacy 1366x768 checkout displays to modern 4K (3840x2160) office monitors. Without proper DPI scaling flags, font metrics clip and button layouts squash or overflow their containers.

---

## 2. Configuration Standards

To ensure razor-sharp vector rendering and non-clipped text across all screens, the PySide6 application initialization sequence must enforce:

```python
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

def init_high_dpi_environment():
    # Enable automatic High-DPI pixel scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    
    # Configure fractional scaling policy
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
```

---

## 3. Font Metrics & Layout Guidelines

1. **Avoid Hardcoded Pixels for Text Containers:** Use `sizeHint` and responsive `QGridLayout` with stretch factors.
2. **Dynamic Minimum Size:** Top-level dialogs enforce minimum size ratios based on `QScreen.availableGeometry()`.
