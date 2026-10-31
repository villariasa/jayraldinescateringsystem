# Client-Side Dish Image Lazy Loading & Memory Caching

## Strategy:
- Native `loading="lazy"` attribute applied to all menu item catalog cards.
- Cached thumbnails stored in Web Storage Cache API with 7-day stale-while-revalidate policy.
