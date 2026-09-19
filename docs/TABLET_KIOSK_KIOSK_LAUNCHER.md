# Android Dedicated Device Mode (COSU) & Kiosk Launcher Specification

## 1. Dedicated Kiosk Mode
The Jayraldine's Catering tablet app utilizes Android's Lock Task API (`startLockTask()`) to prevent guests from:
- Accessing the Android home screen or app drawer.
- Pulling down the notification shade or quick settings.
- Adjusting Wi-Fi or Bluetooth configurations.

## 2. Auto-Boot Configuration
Configured with a `BOOT_COMPLETED` broadcast receiver to automatically launch the kiosk app upon device power-up.
