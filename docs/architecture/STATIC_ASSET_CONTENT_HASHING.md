# Static Asset Content Hashing & Cache Invalidation Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** PWA Frontend, Static Server, Service Worker Cache

---

## 1. Problem Statement
When frontend updates are deployed to the POS web server, mobile tablet browsers may serve stale JavaScript (`exporter.js`, `api.js`) or CSS styles cached in browser storage or Service Worker caches.

---

## 2. Solution: Content-Based Fingerprinting

Static assets are fingerprinted with a content hash during build/packaging:

```html
<!-- Example index.html reference -->
<script type="module" src="/js/exporter.v4_2_4.min.js"></script>
<link rel="stylesheet" href="/css/styles.a1f2b3c4.css">
```

### Dynamic Service Worker Invalidation
The Service Worker cache name is bumped on each build:
```javascript
const CACHE_NAME = 'jayraldines-pwa-v4.2.4';
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    ))
  );
});
```\n