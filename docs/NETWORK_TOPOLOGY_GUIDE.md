# LAN Multi-Terminal Network Topology Guide

## 1. Network Diagram
```
                      [ Wi-Fi Router / Switch ]
                                  |
         +------------------------+------------------------+
         |                                                 |
[ Workstation PC (Server) ]                     [ Handheld Android Tablets ]
  - PostgreSQL (5432)                             - Tablet PWA (Browser)
  - Sync Server (8000)                            - Native APK (WebView)
  - Main PySide6 App                              - Local SQLite / IDB
```

## 2. Static IP Recommendation
The server machine hosting PostgreSQL and the Sync HTTP daemon must be assigned a DHCP reservation or static IP address (e.g., `192.168.1.10`) to guarantee permanent reachability across service shifts.
