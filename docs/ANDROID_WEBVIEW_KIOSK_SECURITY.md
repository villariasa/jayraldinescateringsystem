# Android WebView Kiosk Security Specifications

## 1. Security Architecture
The Android native wrapper (`com.jayraldines.cateringsystem`) implements comprehensive WebView sandboxing:

- **Asset Loader Protection**: Uses `androidx.webkit.WebViewAssetLoader` to serve web resources over secure virtual origins (`https://appassets.androidplatform.net/assets/`).
- **FileProvider Isolation**: Implements secure `androidx.core.content.FileProvider` for handling camera intent photos and document downloads without granting global storage access.
- **Immersive Pinning**: Intercepts back navigation and system gesture triggers to maintain continuous kiosk uptime.
