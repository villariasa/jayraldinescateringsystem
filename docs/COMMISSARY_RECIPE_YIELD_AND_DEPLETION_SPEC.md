# Commissary Kitchen Recipe Yield & Automatic Depletion Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Kitchen Module, Inventory Engine, Recipe Management

---

## 1. Specification Overview

When a confirmed catering booking is locked for prep (T-minus 48 hours), the kitchen dispatch engine calculates gross raw material requirements based on the event's guest count (Pax) and dish selections.

---

## 2. Yield Multiplier Formula

For a given dish $D$ with base yield per 10 pax:

$$\text{Required Quantity} = \left(\frac{\text{Pax Count}}{10}\right) \times \text{Base Portion (kg)} \times (1 + \text{Buffer Margin})$$

Where **Buffer Margin** is standard $0.05$ (5%) to prevent buffet shortages.

### 2.1 Ingredient Depletion Mapping Example

For **Beef Caldereta Special (100 Pax)**:
- Beef Brisket / Chuck: 15.0 kg
- Tomato Paste / Sauce: 2.5 kg
- Bell Peppers (Tri-color): 2.0 kg
- Potatoes & Carrots: 5.0 kg
- Cheddar Cheese & Liver Spread: 1.2 kg

---

## 3. Stock Level Thresholds & Warnings

If raw material requirements exceed warehouse stock on hand, the system generates a **High-Priority Procurement Requisition** alert on the commissary manager dashboard.
