# Tablet Offline Dish Placeholder Image Caching Standard

> **Target Version:** v1.2.8  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Offline UX, PWA Asset Cache, Image Fallback

---

## 1. Fallback Strategy
If network disconnects and dish image is not present in local cache:
1. `<img>` `onerror` handler captures missing asset.
2. Automatically swaps `src` to local SVG culinary placeholder `assets/img/dish_placeholder.svg`.
3. Avoids broken image icons on tablet catalog view.\n