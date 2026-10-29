# Jayraldine's Catering System - Release Notes v2.7.5

> **Release Version:** v2.7.5  
> **Release Date:** October 29, 2026  
> **Target Platforms:** Desktop (PyQt6 / Python 3.11), Tablet PWA, Android APK

---

## Highlights & Major Features

### 1. Tablet Kiosk & Booking Wizard (v2.7.5)
- **Dynamic Set Inclusions:** Food set cards now display detailed inclusion chips formatted with clear bullet separators (`•`).
- **Client Customization Badges:** Prominent gold badge indicates count of dishes removed by the client for replacement in the menu customization tab.
- **Pricing Clarity:** Contextual price tags adapt dynamically to display `/ pax` for buffet tiers or `/ set` for fixed set packages.
- **Android APK Build 65:** Bumped target SDK 34 compatibility, improved WebView performance, and hardware acceleration tuning.

### 2. Operational & Commissary Documentation
- Comprehensive SOP documentation suite across 6 core domains:
  1. Tablet Kiosk & Mobile Architecture
  2. Banquet Logistics & Event Operations
  3. Food Safety, HACCP & Commissary Standards
  4. Crew Operations, Staffing & HR
  5. Billing, Contracts, Database & Multi-Terminal Sync
  6. Daily Devlogs & Audit Logs

### 3. Stability & Reliability
- SQLite WAL mode tuning for high-concurrency read/write operations.
- ESC/POS thermal receipt canvas raster rendering optimizations.
- Zero-downtime database synchronization with conflict resolution logging.
