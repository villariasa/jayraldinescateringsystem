# PWA Service Worker Offline Caching Strategy

## 1. Cache Tiers
- **Static Assets (`cache-first`)**: HTML, CSS, JS bundles, and static SVG icons.
- **Menu Catalogs (`stale-while-revalidate`)**: Dish photos and package definitions.
- **Mutations (`network-first with IndexedDB queue`)**: Booking submissions and order selections.
