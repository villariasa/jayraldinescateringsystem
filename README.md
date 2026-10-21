# <img src="icons/sparkles.svg" width="28" height="28" align="center" /> Jayraldine's Catering System — Enterprise Ecosystem

<div align="center">

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Desktop_GUI-PySide6_(Qt)-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PySide6"/>
  <img src="https://img.shields.io/badge/Tablet_Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Tablet_UI-Vanilla_PWA-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript"/>
  <img src="https://img.shields.io/badge/Mobile-Android_APK-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android"/>
  <img src="https://img.shields.io/badge/Primary_DB-PostgreSQL_16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Local_Cache-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
</p>

**A mission-critical catering management suite with multi-workstation desktop operations, offline self-service tablet kiosks, and hybrid database LAN synchronization.**

</div>

---

## <img src="icons/cpu-chip.svg" width="22" height="22" align="center" /> System Architecture & Topography

Jayraldine's Catering System implements a hybrid local-first and client-server database topology. It guarantees zero operational downtime even during complete internet or network outages.

```
                              ┌─────────────────────────────────────────┐
                              │       Central Server / Primary PC       │
                              │  PostgreSQL (Port 5432) + Sync Engine   │
                              └───────────────────▲─────────────────────┘
                                                  │
                   ┌──────────────────────────────┴──────────────────────────────┐
                   │ Local Area Network (LAN) / Hotspot Sync                     │
                   ▼                                                             ▼
     ┌───────────────────────────┐                                 ┌───────────────────────────┐
     │   Cashier / Admin Desktop │                                 │   Self-Service Kiosk / PWA│
     │      (PySide6 / Qt)       │                                 │    (FastAPI + SQLite DB)  │
     │ • Bookings & Calendar     │                                 │ • Customer Self-Ordering  │
     │ • Invoice & PDF Reports   │                                 │ • Interactive Menu Brower │
     │ • Real-time DB Sync Client│                                 │ • Thermal Slip Printing   │
     └───────────────────────────┘                                 └─────────────┬─────────────┘
                                                                                 │
                                                                                 ▼
                                                                   ┌───────────────────────────┐
                                                                   │ Android Tablet Kiosk (APK)│
                                                                   │ WebView Wrapper Native App│
                                                                   └───────────────────────────┘
```

---

## <img src="icons/swatch.svg" width="22" height="22" align="center" /> Key Components

### 1. Enterprise Desktop Application (`Catering_Present/jayraldines_catering/`)
- <img src="icons/check-badge.svg" width="16" height="16" align="center" /> Built with **PySide6 (Qt)** featuring hardware-accelerated theme rendering.
- <img src="icons/check-badge.svg" width="16" height="16" align="center" /> Comprehensive booking lifecycle: inquiry, down payment, package selection, contract generation, and balance settlement.
- <img src="icons/check-badge.svg" width="16" height="16" align="center" /> Robust report generator: automated PDF receipts, billing statements, event calendar export, and sales analytics.
- <img src="icons/bolt.svg" width="16" height="16" align="center" /> Multi-client LAN synchronization engine (`utils/client_sync.py` & `utils/db_sync_server.py`).

### 2. Tablet Kiosk & Self-Service Ordering (`Tablet_PWA/`)
- <img src="icons/cpu-chip.svg" width="16" height="16" align="center" /> **Backend:** FastAPI microservice managing local SQLite transactions on port `8085`.
- <img src="icons/window.svg" width="16" height="16" align="center" /> **Frontend:** Responsive, touch-optimized Progressive Web App (PWA) with offline-first local storage caching.
- <img src="icons/printer.svg" width="16" height="16" align="center" /> Direct thermal POS receipt printing support (58mm/80mm).

### 3. Android Tablet Native Wrapper (`Tablet_Android_APK/`)
- <img src="icons/globe-alt.svg" width="16" height="16" align="center" /> Lightweight Android WebView bridge packaging the kiosk frontend for dedicated counter tablets.
- <img src="icons/lock-closed.svg" width="16" height="16" align="center" /> Auto-booting kiosk lock mode with local network discovery.

---

## <img src="icons/archive-box.svg" width="22" height="22" align="center" /> Repository Layout

```
jayraldinescateringsystem/
├── Catering_Present/               # Active desktop application (PySide6 / Qt)
│   └── jayraldines_catering/
│       ├── components/            # Modals, sidebars, topbars, and custom widgets
│       ├── ui/                    # Core screens (Bookings, Menu, Customers, Reports)
│       └── utils/                 # Repositories, auth, theme engine, and PDF exporters
├── Tablet_PWA/                    # Self-service tablet kiosk system
│   ├── backend/                   # FastAPI local server & SQLite manager
│   └── frontend/                  # Touchscreen PWA interface (HTML5 / Vanilla JS)
├── Tablet_Android_APK/            # Native Android wrapper project
├── icons/                         # Tailwind Heroicons suite
├── docs/                          # In-depth architectural specifications and manuals
├── ARCHITECTURE.md                # System topology and threading documentation
├── FILE_GUIDE.md                  # Quick-reference codebase routing map
└── run_desktop.bat                # Windows quick launcher for desktop app
```

---

## <img src="icons/rocket-launch.svg" width="22" height="22" align="center" /> Getting Started

### Desktop Management Application

```bash
# 1. Ensure Python 3.10+ is installed
python --version

# 2. Install requirements
pip install -r Catering_Present/requirements.txt

# 3. Launch application
run_desktop.bat
# or directly via python:
python Catering_Present/jayraldines_catering/main.py
```

### Tablet Kiosk (FastAPI)

```bash
# Navigate to Tablet backend
cd Tablet_PWA/backend

# Run local kiosk server
python -m uvicorn main:app --host 0.0.0.0 --port 8085 --reload
```

---

## <img src="icons/lock-closed.svg" width="22" height="22" align="center" /> Security & RBAC

- <img src="icons/shield-check.svg" width="16" height="16" align="center" /> Multi-tier role-based access control (Admin, Cashier, Kitchen Staff).
- <img src="icons/lock-closed.svg" width="16" height="16" align="center" /> Secure credential hashing and audited transaction histories.
- <img src="icons/document-text.svg" width="16" height="16" align="center" /> Complete documentation available in [`docs/`](./docs/) and [`FILE_GUIDE.md`](./FILE_GUIDE.md).

---

## <img src="icons/document-text.svg" width="22" height="22" align="center" /> License

Proprietary © Medy Villarias. All rights reserved.
