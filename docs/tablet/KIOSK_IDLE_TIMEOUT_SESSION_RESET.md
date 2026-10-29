# Kiosk Idle Session Timeout & Data Privacy Reset

> **Target Version:** v2.7.5  
> **Status:** Security & UX Standard  
> **Date:** October 29, 2026  
> **Audience:** Frontend Engineers, Security Officers

---

## 1. Purpose
In public showroom kiosk mode, unattended partially completed bookings expose customer contact details and event addresses.

## 2. Timeout Architecture
- **Inactivity Timer:** Set to 120 seconds of zero pointer/touch interaction.
- **Warning Overlay (T minus 15 seconds):** Modal displays:
  > "Are you still there? Your booking session will reset in 15 seconds."
- **Reset Sequence:**
  - Clear session storage and transient memory cache (`wizardDraftBooking`).
  - Animate transition back to idle promotional attract loop / Welcome Screen.
  - Retain zero identifiable customer data in DOM memory.
