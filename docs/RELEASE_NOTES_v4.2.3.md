# Release Notes — Version v4.2.3

> **Release Date:** October 6, 2026  
> **Target Audience:** All Deployments (Desktop POS, Tablet PWA, Android APK)  
> **Status:** Production Release  

---

## 1. Summary of Changes

Version 4.2.3 is a major stability, financial reporting, and document optimization release addressing contract storage efficiency, cashflow ledger usability, and cross-platform template synchronization.

---

## 2. Key Highlights

### 2.1 Large Contract PDF Binary Storage
- Completely phased out memory-intensive base64 encoding for client contract attachments.
- Introduced chunked binary file storage and on-demand desktop preview rendering for multi-page documents up to 30 MB.

### 2.2 Cashflow Management Improvements
- Chronological inverted sorting (newest transactions always appear at top).
- Dynamic account-level balance metrics when filtering by GCash, Cash on Hand, Maya, or Bank.
- Removed legacy BDO Savings classification.
- Redesigned entry modal with structured ergonomics and prominent currency formatting.

### 2.3 Menu Item Dialog Redesign
- Realigned `MenuItemDialog` to mirror the dual-pane layout of `PackageDialog` with dedicated left-hand image staging.

### 2.4 Reports Multi-Period Filtering
- Added presets for Today, This Week, This Month, This Year, and Custom Date ranges.

### 2.5 Receipt & Contract Standardization
- Synchronized long English date formatting (`October 6, 2026`) across Desktop, Tablet PWA, and Android APK.
- Corrected canonical commissary address to `518 V. Rama Ave., Cebu City`.
- Normalized theme motif codes to descriptive color names.
- Clarified downpayment row status to `PAID` upon receipt of initial deposit.
