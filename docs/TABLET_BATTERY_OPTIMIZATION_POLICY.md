# Tablet Kiosk Battery Health & Thermal Management Policies

## 1. Operating Parameters
- **Display Timeout**: Ambient dimming after 3 minutes of customer inactivity.
- **Wake Lock Management**: Acquires `PARTIAL_WAKE_LOCK` only during active order sync transactions.
- **Thermal Throttling Guard**: Reduces Lottie animation frame rates to 30fps if device battery temperature exceeds $42^{\circ}\text{C}$.
