# Package Inclusion Chip Rendering Specification

> **Target Version:** v2.7.5  
> **Status:** UI Component Spec  
> **Date:** October 29, 2026  
> **Audience:** Frontend Engineers, CSS Developers

---

## 1. Component Requirements
On customer-facing tablet cards, inclusions must render cleanly without overflowing card boundaries:
- **Font Size:** Strict `11.5px` with line-height `1.4`.
- **Delimiters:** Centered bullet (`•`) separating inclusion labels.
- **Label Resolution:** Supports multi-field resolution `item.label || item.pinc_label || item`.
- **Safety Clamping:** Truncate to maximum 3 items on summary view, with "+N more" badge expander on modal details.

## 2. DOM Structure
```html
<div class="kiosk-inclusions-list">
  <b style="color:var(--text);">Inclusions:</b>
  <span>Lechon Belly • Chicken Pandan • Sotanghon Guisado</span>
</div>
```
