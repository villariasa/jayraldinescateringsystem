# Android Kiosk Barcode Scanner Camera Permissions & Fallback Policy

> **Target Version:** v4.2.5  
> **Status:** Mobile Android Spec  
> **Date:** October 8, 2026  
> **Audience:** Android APK Developers, System Admin

---

## 1. Dedicated Hardware vs Camera Emulation
Kiosk tablets read customer booking QR codes and payment vouchers:
- **Primary:** Dedicated hardware 2D barcode scanner connected via USB OTG (acts as virtual keyboard wedge HID device).
- **Secondary (Camera Fallback):** WebRTC `getUserMedia()` video stream processed via ZXing-WASM library.

## 2. Android Enterprise Permission Lock
In kiosk device-owner mode:
- Camera permissions are pre-granted via `DevicePolicyManager.setPermissionGrantState()` so users never encounter OS permission prompts.
