# Event Motif & Theme Color Normalization Engine

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** UI Design Tokens, Exporter Normalizer, Booking Forms

---

## 1. Specification Overview

During booking setup, event themes are frequently entered as hex codes (e.g., `#2563EB`, `#10B981`) or freeform text (`"Emerald Green & Gold"`, `"Dusty Blue"`, `"Standard"`).

Printing raw hex strings like `#2563EB` on formal client receipts degrades document quality. The Theme Motif Normalization Engine maps raw inputs to client-presentable names:

---

## 2. Normalization Rules

```python
HEX_TO_COLOR_NAME = {
    "#2563eb": "Royal Blue",
    "#10b981": "Emerald Green",
    "#ef4444": "Ruby Red",
    "#f59e0b": "Golden Amber",
    "#8b5cf6": "Royal Purple",
    "#ec4899": "Blush Pink",
    "#64748b": "Slate Gray",
    "#000000": "Classic Black",
    "#ffffff": "Pearl White"
}

def normalize_motif_display(raw_motif: str) -> str:
    if not raw_motif:
        return "Standard"
    cleaned = str(raw_motif).strip()
    if cleaned.startswith("#"):
        return HEX_TO_COLOR_NAME.get(cleaned.lower(), "Standard")
    if cleaned.lower() in ("standard", "default", "none"):
        return "Standard"
    return cleaned
```

---

## 3. Consistency Matrix Across Platforms

- **Desktop Print Slip:** Displays resolved label (e.g., "Royal Blue").
- **PDF ReportLab:** Encodes resolved label directly into contract header.
- **Tablet jsPDF:** Normalizes string before rendering receipt title block.
