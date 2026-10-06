# Menu Item Modal Redesign & Package Modal Alignment Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Menu Catalog, UI Layout, Dialog Architecture

---

## 1. Context & Motivation

In previous iterations, the Menu Item Dialog (`MenuItemDialog`) placed image upload widgets in a non-standard vertical stack below text descriptions. In contrast, the Package Dialog (`PackageDialog`) showcased an intuitive, professional layout featuring:
- A dedicated **left-hand media pane** for image previews, upload buttons, and placeholder illustrations.
- A **right-hand multi-attribute form** for category selection, dish pricing, cost analysis, and dietary badges.

To achieve UI consistency across the desktop application, the Menu Modal layout is redesigned to directly follow the structural layout of the Package Modal.

---

## 2. Layout Architecture

### 2.1 Side-by-Side Spatial Distribution

```
+------------------------------------------------------------------------+
| [Header] Edit Dish / Add New Menu Item                     [x] Close   |
+------------------------------------------------------------------------+
| [Left Pane: 38% Width]               | [Right Pane: 62% Width]         |
| +----------------------------------+ | Dish Name:                      |
| |                                  | | [ Lechon Belly Roll           ] |
| |    Dish Image Preview            | | Category:                       |
| |    (Aspect Ratio 4:3, Rounded)   | | [ Pork Specials             v ] |
| |                                  | | Base Price (PHP): Cost/Pax:   |
| +----------------------------------+ | [ 450.00        ] [ 210.00    ] |
| [ Upload Photo ] [ Remove Photo ]    | Serving Size / Description:     |
| Dimensions: 800x600 recommended     | [ Marinated roast pork belly..] |
| Max Size: 5 MB (JPEG/PNG/WebP)      | Dietary Badges & Allergens:     |
|                                      | [x] Pork [ ] Halal [x] Gluten   |
+------------------------------------------------------------------------+
| [Footer]                                                               |
| [ Delete Item ]                             [ Cancel ] [ Save Dish ]   |
+------------------------------------------------------------------------+
```

### 2.2 Image Handling Standard

1. **Aspect Ratio & Display:**
   - Image canvas pinned at 4:3 ratio with fixed minimum dimensions (240px wide by 180px high).
   - `Qt.KeepAspectRatioByExpanding` with center cropping to maintain sharp, non-distorted culinary imagery.
2. **Local Storage of Media:**
   - Saved images are stored under `assets/images/dishes/` and referenced via local paths rather than inline base64 database strings.
3. **Empty State:**
   - A modern SVG culinary icon and subtle dashed border guide the user to drag-and-drop or click to browse.
