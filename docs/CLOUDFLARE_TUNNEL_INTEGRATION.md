# Cloudflare Zero Trust Tunnel Integration Guide

## 1. Architectural Model
Cloudflare Tunnel (`cloudflared`) connects the local Jayraldine's Catering Sync Server (running on `0.0.0.0:8000`) to Cloudflare's global edge network via encrypted outgoing TLS tunnels, eliminating port forwarding and public IP requirements.

```
[ Local Database PC ]
  ├── PostgreSQL (Port 5432)
  ├── Sync Daemon (Port 8000)
  └── cloudflared tunnel
          │ (Encrypted Outbound Tunnel)
          ▼
[ Cloudflare Global Edge ]
          │ (Custom Domain HTTPS)
          ▼
[ Android APK & Tablet PWA ]
```

## 2. Advantages Over Traditional Tunnels
- **Zero Interstitial Banners**: Immediate WebSocket and REST JSON communication with no click-through friction.
- **Permanent Hostname**: Direct binding to `https://kiosk.jayraldinescatering.com` or temporary quick tunnels (`*.trycloudflare.com`).
- **Access Policies**: Optional Zero Trust access rules, IP whitelisting, and geographic rate limiting.
