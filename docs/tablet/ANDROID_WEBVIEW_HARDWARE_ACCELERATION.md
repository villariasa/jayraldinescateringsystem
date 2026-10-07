# Android WebView Hardware Acceleration & Memory Optimization

> **Target Version:** v1.2.8  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Android APK, GPU Acceleration, Performance

---

## 1. Configuration in AndroidManifest.xml
```xml
<application
    android:hardwareAccelerated="true"
    android:largeHeap="true"
    android:allowBackup="false">
    ...
</application>
```
Enables GPU rasterization for smooth 60fps table scrolling and modals.\n