# Jayraldine's Catering System — Release Notes v4.2.1
**Release Date:** September 14, 2026  
**Build Target:** Desktop Windows Installer (.EXE) & Tablet Android Kiosk (.APK)  

## Key Enhancements & Fixes
- **Live Database Master Sync**: Fully integrated PostgreSQL as the authoritative source for packages, dishes, and customers.
- **Base64 Image Streaming**: Package banners and dish photos stream seamlessly over Ngrok / Cloudflare tunnels into tablet SQLite storage.
- **Automated GitHub Actions CI/CD**: Automatic Windows `.exe` and Android `.apk` installer compilation upon repository push.
- **Subnet Auto-Discovery**: Rapid zero-config LAN discovery across Wi-Fi and hotspot subnets.
