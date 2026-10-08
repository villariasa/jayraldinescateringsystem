# High-Contrast Outdoor Sunlight Mode for Kiosk Tablets

> **Target Version:** v4.2.5  
> **Status:** UI Specification  
> **Date:** October 8, 2026  
> **Audience:** Mobile Frontend Developers

---

## 1. Ambient Glare Problem Statement
Tablets deployed at beach weddings (Mactan resorts) or outdoor garden parties suffer severe display washout under direct tropical sunlight (up to 100,000 lux).

## 2. Sunlight High-Contrast Theme Specs
- **Background:** Pure solid `#FFFFFF` (eliminating subtle dark glassmorphism).
- **Text:** High-contrast `#000000` with bold typographic font weights (700+).
- **Primary Action Buttons:** `#D32F2F` or `#0052CC` with 3px solid black borders.
- **Ambient Light Sensor API:** Automatically toggle sunlight mode if device ambient sensor reports `> 25,000 lux`.
