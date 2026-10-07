# Android WebView SurfaceView & Canvas Rendering Optimization

> **Target Version:** v1.2.8  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Android Runtime, WebView Performance

---

## 1. WebView Settings
To eliminate input lag during fast item additions:
```java
WebSettings webSettings = webView.getSettings();
webSettings.setRenderPriority(WebSettings.RenderPriority.HIGH);
webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);
webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
```\n