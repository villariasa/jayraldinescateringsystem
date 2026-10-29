# Thermal Receipt Printing Canvas Rendering & ESC/POS Formatting

> **Target Version:** v2.7.5  
> **Status:** Software Engineering Spec  
> **Date:** October 29, 2026  
> **Audience:** Desktop App Developers, Mobile Engineers

---

## 1. Dynamic Canvas Rendering
To ensure razor-sharp typography and logo rendering on 58mm and 80mm thermal receipt heads:
- Render receipt DOM node offscreen onto an HTML5 `<canvas>` at 203 DPI (8 dots/mm).
- Convert grayscale pixel matrix to 1-bit monochrome bitmap using Floyd-Steinberg error diffusion dithering.

## 2. ESC/POS Command Pipeline
- Generate standard ESC/POS raster byte stream:
  - `ESC @` (Initialize printer)
  - `GS v 0` (Print raster bit image)
  - `ESC d 3` (Feed 3 lines)
  - `GS V 66 0` (Partial paper cut)
