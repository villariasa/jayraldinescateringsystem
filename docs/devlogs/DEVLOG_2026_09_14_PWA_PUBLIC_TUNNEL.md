# Development Log: Public HTTPS Tunneling & Ngrok Integration
**Date:** September 14, 2026  
**Author:** Medy B. Villarias  
**Component:** Network / Sync Server / Tablet Kiosk PWA  

## Overview
Implemented public HTTPS remote tunneling architecture using Ngrok and Cloudflare Tunnels to bridge standalone tablet kiosk devices and remote laptops with the central PostgreSQL catering database over the public internet.

## Key Technical Achievements
- Integrated `ngrok-skip-browser-warning` custom headers into all PWA fetch calls to bypass free-tier interstitial pages.
- Created resilient URI resolvers in `_getSyncBaseUrls` to preserve HTTPS protocols without forcing port 8000 on cloud proxy endpoints.
- Auto-bound background synchronization timers to network visibility and window focus events.
- Successfully verified bidirectional order push and menu catalog pull across wide-area networks.
