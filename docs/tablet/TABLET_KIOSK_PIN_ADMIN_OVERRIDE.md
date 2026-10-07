# Tablet Kiosk Mode Lockdown & Administrator PIN Override

> **Target Version:** v1.2.8  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Kiosk Mode, Security, Device Admin

---

## 1. Scope
Prevents waiters from exiting POS interface to open third-party apps or system settings.
- Pinning app using Android LockTask API.
- Triple-tap on top-right logo prompts for Master Admin PIN to exit lockdown.\n