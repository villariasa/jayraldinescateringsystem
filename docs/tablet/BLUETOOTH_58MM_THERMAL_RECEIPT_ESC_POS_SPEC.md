# Bluetooth 58mm Thermal Receipt ESC/POS Formatting Specification

> **Target Version:** v4.2.5  
> **Status:** Hardware Driver Spec  
> **Date:** October 8, 2026  
> **Audience:** Android & Mobile Device Engineers

---

## 1. Physical Constraints (58mm Paper Roll)
- Printable character width: strictly **32 characters** per line in standard font mode (`ESC ! 0x00`).
- Print speed: 90 mm/sec, 203 DPI.

## 2. Line Item Formatting Layout
```text
--------------------------------
JAYRALDINE'S CATERING MANAGEMENT
Official Customer Booking Slip
Ref: BK-20261021-0042
Date: 2026-10-08 09:15 AM
--------------------------------
ITEM               QTY     TOTAL
Set A (4 Dishes)     2   7,000.00
Fish Fillet Lemon    1     850.00
--------------------------------
Subtotal:                7,850.00
Downpayment Paid:        4,000.00
BALANCE DUE:             3,850.00
--------------------------------
Thank you for choosing us!
```
Uses native ESC/POS commands: `ESC @` (init), `ESC a 1` (center), `GS V 66 0` (cut).
