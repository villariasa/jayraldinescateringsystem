# Tablet Kiosk v2.7.5 Architecture & Release Overview

> **Target Version:** v2.7.5  
> **Status:** Production Standard  
> **Date:** October 29, 2026  
> **Audience:** Frontend Engineers, Mobile APK Developers, Tablet Deployment Leads

---

## 1. Executive Summary
The v2.7.5 update to Jayraldine's Catering Tablet Kiosk (both PWA and native Android WebView APK wrapper) resolves key UI regressions and enhances the event booking wizard. Key updates include:
- **Food Set Cards Display:** Direct dynamic rendering of `set.inclusions` chips (`•` delimited) on customer-facing package cards.
- **Removed Dishes Notice:** Visual gold badge counter reflecting dishes removed by the client for replacement in the custom menu tab.
- **Kiosk Card Descriptions:** Intelligent fallbacks between package descriptions and inclusion item tags.
- **Dynamic Pricing Labels:** Context-aware price suffixing supporting both `/ pax` and `/ set` paradigms.

## 2. Shared Codebase Synchronization
The tablet logic is maintained in parity across:
1. `Tablet_PWA/frontend/js/` (Browser PWA for browser-based kiosk tablets)
2. `Tablet_Android_APK/app/src/main/assets/js/` (Bundled asset engine for offline-first Android terminals)

Both runtimes consume the unified REST sync endpoints with offline SQLite/IndexedDB fallback caching.
