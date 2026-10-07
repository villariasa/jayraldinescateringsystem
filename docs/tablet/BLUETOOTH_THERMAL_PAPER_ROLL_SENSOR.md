# Bluetooth Thermal Printer Paper-Out & Cover-Open Detection

> **Target Version:** v1.2.8  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Hardware Bridge, Thermal Printer, Android APK

---

## 1. ESC/POS Status Polling
Before dispatching a print job, the Android bridge sends real-time status inquiry command `DLE EOT 1` to detect:
1. Paper roll empty / near empty.
2. Printer cover open.
3. Thermal head overheating.\n