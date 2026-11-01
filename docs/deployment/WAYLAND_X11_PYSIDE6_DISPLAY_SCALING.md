# Wayland & X11 PySide6 Display Server Scaling Parameters

## 1. High-DPI Environment Flags
```bash
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_ENABLE_HIGHDPI_SCALING=1
export QT_SCALE_FACTOR=1.25
```
For native Wayland compositors (GNOME, Sway), `QT_QPA_PLATFORM=wayland;xcb` ensures crisp vector font rendering across touchscreen monitors.
