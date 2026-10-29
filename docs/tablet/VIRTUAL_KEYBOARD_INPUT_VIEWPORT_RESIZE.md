# Android Virtual Keyboard Viewport Resizing & Input Focus Policy

> **Target Version:** v2.7.5  
> **Status:** UX Implementation Spec  
> **Date:** October 29, 2026  
> **Audience:** Android APK Developers, Frontend Leads

---

## 1. Problem Statement
On 10-inch Android kiosk tablets in landscape orientation, the virtual keyboard consumes up to 55% of vertical viewport height, obscuring form fields and primary action buttons.

## 2. Resolution Architecture
1. **Window Soft Input Mode:** Configure Android manifest activity with:
   ```xml
   android:windowSoftInputMode="adjustResize|stateHidden"
   ```
2. **Visual Viewport API:** In `wizard.js`, register `window.visualViewport.addEventListener('resize', handleViewportResize)` to scroll the active input smoothly into the upper 40% margin of the visible area.
3. **Auto-Scroll Action:** Floating CTA action bars adjust `bottom` position dynamically based on `window.visualViewport.height`.
