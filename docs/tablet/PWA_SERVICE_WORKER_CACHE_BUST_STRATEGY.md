# Progressive Web App Service Worker Cache-Busting Architecture

> **Target Version:** v4.2.5  
> **Status:** Web Architecture Spec  
> **Date:** October 8, 2026  
> **Audience:** Frontend Engineers, DevOps

---

## 1. Cache Invalidation Mechanics
PWA kiosks must never run outdated wizard scripts after a desktop server release.

## 2. Dual-Tier Version Verification
1. **Service Worker Version Header:** `CACHE_NAME = 'jayraldines-pwa-v4.2.5'`.
2. **Hash-Manifest Verification:** The service worker fetches `/api/health` containing current system build hash.
3. If build hash mismatches, trigger `self.skipWaiting()` and broadcast `REFRESH_REQUIRED` message to client windows for seamless hot-reload.
