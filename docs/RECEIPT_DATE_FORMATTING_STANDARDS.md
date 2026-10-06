# Cross-Platform Receipt & Contract Date Formatting Standards

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** ReportLab PDF Exporter, jsPDF Tablet Exporter, Order Print Dialog

---

## 1. Specification Goal

In printed booking receipts and client order slips, numeric dates (such as `2026-10-21` or `10/21/2026`) can cause confusion between American (`MM/DD/YYYY`) and international formats. To ensure total clarity for catering clients and event coordinators, all dates must follow a standardized **Long English Format**:

> **Standard Event Date:** `October 21, 2026`  
> **Standard Issue Date:** `October 6, 2026`

---

## 2. Implementation Specifications

### 2.1 Python Desktop Implementation (ReportLab & PySide6)

```python
from datetime import datetime, date

def format_receipt_date(d_raw):
    if not d_raw or str(d_raw).strip() in ("—", "-"):
        return "—"
    if isinstance(d_raw, (datetime, date)):
        return f"{d_raw.strftime('%B')} {d_raw.day}, {d_raw.year}"
    try:
        s = str(d_raw).strip()[:10]
        dt = datetime.strptime(s, "%Y-%m-%d")
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    except Exception:
        return str(d_raw)
```

### 2.2 JavaScript Tablet Implementation (jsPDF in PWA & APK)

```javascript
function formatEventDate(dRaw) {
  if (!dRaw || dRaw === "—" || dRaw === "-") return "—";
  try {
    const s = String(dRaw).trim();
    const parts = s.split(/[-/]/);
    if (parts.length >= 3 && parts[0].length === 4) {
      const y = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10) - 1;
      const d = parseInt(parts[2].slice(0, 2), 10);
      const dt = new Date(y, m, d);
      return dt.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
    }
    const d = new Date(dRaw);
    if (isNaN(d.getTime())) return String(dRaw);
    return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  } catch (_) {
    return String(dRaw);
  }
}
```
