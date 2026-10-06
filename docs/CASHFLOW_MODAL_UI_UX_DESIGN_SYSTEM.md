# Cashflow Entry Modal UI/UX Design System Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** UI Design System, Dialogs, Desktop Application

---

## 1. Problem Statement

Previous cashflow entry dialogs utilized standard default dialog boxes with rudimentary stacked form fields, lacking clear visual hierarchy, keyboard navigation ergonomics, and validation status indicators. Operators described the layout as utilitarian and prone to data entry errors.

This specification modernizes the Cashflow Modal into a **premium, standard-compliant dialog experience** aligned with the application's modern theme.

---

## 2. Dialog Layout Architecture

### 2.1 Modal Structure

The modal adheres to a structured three-tier layout:

```
+-------------------------------------------------------------+
| [Header] Title & Icon + Close Button                        |
| "Record Cash Flow Entry" | Account & Flow Selector          |
+-------------------------------------------------------------+
| [Body - Two Column Grid]                                    |
| Left Column:                          Right Column:         |
| - Flow Type (Inflow / Outflow) Toggle - Target Account (Pills)|
| - Amount (Big currency input)         - Date & Time Picker  |
| - Category Selection (Searchable)     - Reference / Voucher |
| - Counterparty / Payee / Customer     - Detailed Memo/Notes |
+-------------------------------------------------------------+
| [Footer]                                                    |
| [Cancel (Esc)]                   [Save Entry (Ctrl+Enter)]  |
+-------------------------------------------------------------+
```

### 2.2 Visual Styling & Ergonomics

1. **Large Amount Display:**
   - Amount input field styled with prominent typography (22pt font, emerald green border focus for inflows, crimson red for outflows).
   - Real-time formatted thousands separators as user types.
2. **Segmented Flow Selector:**
   - Dual-state segmented pill toggle for `Inflow (Money In)` and `Outflow (Money Out)` with clear color-coded states.
3. **Smooth Micro-interactions:**
   - Backdrop blur dimming over parent window (`rgba(15, 23, 42, 0.4)`).
   - Subtle entry scale animation (scale 0.96 to 1.0, 150ms ease-out).
4. **Keyboard Accessibility:**
   - `Enter` advances through fields; `Ctrl+Enter` commits entry; `Escape` closes modal safely with confirmation if dirty.
