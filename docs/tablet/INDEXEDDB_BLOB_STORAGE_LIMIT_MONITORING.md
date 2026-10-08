# Tablet IndexedDB Blob Storage Limits & Quota Monitoring

> **Target Version:** v4.2.5  
> **Status:** Web Platform Architecture  
> **Date:** October 8, 2026  
> **Audience:** PWA Frontend Developers

---

## 1. Browser Storage Quotas on Low-End Tablets
Android tablets (e.g., Samsung Tab A 32GB) restrict web app IndexedDB storage if device storage dips below 1GB available.

## 2. Storage Estimation API Routine
```javascript
if (navigator.storage && navigator.storage.estimate) {
    const { quota, usage } = await navigator.storage.estimate();
    const percentUsed = (usage / quota) * 100;
    if (percentUsed > 80 || (quota - usage) < 500 * 1024 * 1024) {
        console.warn("[Storage] Warning: Low device storage quota remaining.");
        purgeOldOfflineReceiptPdfs();
    }
}
```
Evict stored receipt PDF blobs older than 7 calendar days while preserving structured JSON booking metadata.
