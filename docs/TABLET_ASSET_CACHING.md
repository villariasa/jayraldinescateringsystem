# Tablet Kiosk Service Worker Asset Caching Guide

## 1. Cache-First Strategy
The tablet Progressive Web App implements a cache-first Service Worker policy for all static assets:
- UI JavaScript modules (`app.js`, `api.js`, `repository.js`).
- CSS stylesheets and web fonts.
- Menu package thumbnails and branding banners.

## 2. Background Revalidation
Assets are served immediately from browser cache while an async network fetch checks ETags for newer revisions.
