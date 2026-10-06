# Desktop Event Calendar 'Today' Highlighting & Visual Theming

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Event Calendar, Desktop UI, Custom Widgets

---

## 1. Feature Overview

Catering coordinators frequently view the calendar month view to identify active banquet setups, scheduled tastings, and staff dispatch times. To eliminate friction in locating the current operational day amidst dense calendar cells, the calendar grid highlights **Today** with an emerald theme badge.

---

## 2. Visual Specifications

1. **Cell Accent Border:**
   - Active day cell bounded by a 2px emerald solid border (`#10B981`).
   - Cell background receives a subtle gradient tint: `qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(16, 185, 129, 0.08), stop:1 rgba(16, 185, 129, 0.02))`.
2. **Date Number Header:**
   - Date number displayed inside an emerald badge pill:
     - Background: `#10B981`
     - Foreground: `#FFFFFF` (Bold text)
     - Border radius: `12px` (circular badge)
3. **Indicator Dot System:**
   - Red dot (`#EF4444`): Confirmed wedding or high-pax catering.
   - Blue dot (`#3B82F6`): Food order / packed meals delivery.
   - Amber dot (`#F59E0B`): Client tasting or ocular inspection.
