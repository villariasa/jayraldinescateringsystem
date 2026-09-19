# Standalone Android Tablet APK LAN Distribution Specification

## 1. Executive Summary
The Jayraldine's Catering system serves compiled standalone Android APK packages directly to client tablets via the host PC's HTTP Sync Server on port 8000.

## 2. Delivery Architecture
- **Host Endpoint**: `http://<server-ip>:8000/download-apk` and `http://<server-ip>:8000/jayraldines_catering_v2.1.4.apk`.
- **MIME & Headers**: Streams binary archive using `Content-Type: application/vnd.android.package-archive` and `Content-Disposition: attachment; filename="jayraldines_catering_v2.1.4.apk"`.
- **Chunked Transfer**: Reads file in 64KB buffers to avoid memory spikes on the PC host.

## 3. In-App Suppression Protocol
When the application is executing within the installed Android APK environment:
- JavaScript inspects `window.AndroidNative`, user agent tokens (`JayraldinesAPK`), and host origin (`appassets.androidplatform.net`).
- In-app download buttons in the navigation dropdown and Settings connection modal are completely hidden to avoid redundant installation prompts.
