# Tablet Kiosk Screen Orientation & Touch Gesture Rejection

## 1. Kiosk Display Configurations
- **Fixed Landscape Orientation**: Screen orientation locked to `SCREEN_ORIENTATION_LANDSCAPE` in Android manifest.
- **Edge Gesture Rejection**: Multi-touch edge swipe rejection to prevent accidental exit from kiosk web view.
- **Stay Awake Mode**: `FLAG_KEEP_SCREEN_ON` enabled during operating store hours.
