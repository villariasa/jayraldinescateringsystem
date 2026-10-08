# Mobile Touch Target 48px Ergonomic Standards & Field UX

> **Target Version:** v4.2.5  
> **Status:** UI/UX Specification  
> **Date:** October 8, 2026  
> **Audience:** Tablet Frontend Developers, UI Designers

---

## 1. Mobile Tablet Ergonimics in Fast-Paced Banquets
Waitstaff operating tablets often have wet hands, wear service gloves, or input data while walking.

## 2. Touch Target Dimensional Rules
- **Minimum Interactive Size:** Strictly **48px × 48px** bounding box for all buttons, toggles, and stepper controls (`+` / `-`).
- **Padding Spacing:** Minimum 8px gutter separation between adjacent buttons to eliminate accidental tap errors.
- **Active State Feedback:** Immediate CSS `:active` visual state (10% scale depression + color contrast shift) within 16ms of touch event to confirm interaction.
