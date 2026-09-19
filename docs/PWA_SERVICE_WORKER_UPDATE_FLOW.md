# Progressive Web App Service Worker Update Lifecycle

## 1. Auto-Update Detection
The Service Worker periodically checks for updated asset hashes. When a new release is detected:
1. New assets are downloaded in the background (`install` phase).
2. The Service Worker calls `skipWaiting()`.
3. The application triggers a subtle notification prompt or reloads automatically during idle hours.
