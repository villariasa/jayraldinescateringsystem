# Tablet Android APK Native Printing & Storage Bridge Specification

> **Target Version:** v1.2.7  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Android Native Bridge, Java WebView Interface, Thermal Printing

---

## 1. Overview

The Tablet Android APK wraps the responsive web interface inside an optimized Android `WebView`. For receipt and contract generation, JavaScript invokes native Java methods via `@JavascriptInterface` bridges.

This document formalizes the native file storage and ESC/POS thermal printing contracts between the web frontend and Android Java runtime.

---

## 2. JavascriptInterface Bridge API

```java
public class WebAppInterface {
    Context mContext;

    @JavascriptInterface
    public void saveBase64File(String base64Data, String filename, String mimeType) {
        // Asynchronously decode and write to Downloads directory
    }

    @JavascriptInterface
    public void printEscPosReceipt(String rawEscPosCommands) {
        // Transmit direct bytes to paired Bluetooth thermal printer
    }

    @JavascriptInterface
    public boolean isPrinterConnected() {
        // Check Bluetooth socket connection status
        return BluetoothThermalPrinter.isConnected();
    }
}
```

---

## 3. Storage Optimization for Large Files

For contracts exceeding 10 MB, passing entire base64 strings across `evaluateJavascript` or the JavascriptInterface boundary causes GC pauses in the Dalvik/ART virtual machine.

1. **Chunked Stream Protocol:** Large files are sent in 256 KB base64 chunks (`saveBinaryChunk(chunkIndex, totalChunks, data)`).
2. **Scraped Blob URI:** Alternatively, the webview downloads directly to `Environment.DIRECTORY_DOWNLOADS` using Android's native `DownloadManager`.
