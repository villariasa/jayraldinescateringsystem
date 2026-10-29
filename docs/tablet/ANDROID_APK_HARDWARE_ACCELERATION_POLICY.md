# Android WebView APK Hardware Acceleration & Rendering Policy

> **Target Version:** v2.7.5  
> **Status:** Mobile Architecture Standard  
> **Date:** October 29, 2026  
> **Audience:** Android APK Developers, Performance Engineers

---

## 1. Hardware Layer Configuration
To ensure 60 FPS scrolling through extensive photo menus on low-power MediaTek / Rockchip tablet processors:
- Enable hardware acceleration globally in `AndroidManifest.xml`:
  ```xml
  <application android:hardwareAccelerated="true" ...>
  ```
- Configure WebSettings on the main WebView:
  ```java
  webSettings.setRenderPriority(WebSettings.RenderPriority.HIGH);
  webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);
  webSettings.setDomStorageEnabled(true);
  webSettings.setDatabaseEnabled(true);
  ```

## 2. GPU Overdraw Elimination
Avoid deep CSS box-shadow nesting and unconstrained backdrop filters on low-end hardware.
