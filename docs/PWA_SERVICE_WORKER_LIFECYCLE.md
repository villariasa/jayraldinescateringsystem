# PWA Service Worker Lifecycle & Offline Asset Management

## 1. Cache Storage Strategy
The progressive web application incorporates a multi-tier caching hierarchy:

- **Static Shell Assets**: Cache-First strategy for core JS (`sql-wasm.js`, `lottie.min.js`, `jspdf.umd.min.js`), CSS stylesheets, and icon fonts.
- **Dynamic API Sync**: Network-First with fallback to local in-browser SQLite database for all operational queries.
- **Lifecycle Events**: Immediate `skipWaiting()` and `clients.claim()` activation upon service worker script updates.
