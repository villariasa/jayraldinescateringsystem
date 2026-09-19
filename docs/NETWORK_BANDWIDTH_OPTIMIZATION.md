# LAN HTTP Streaming & Bandwidth Optimization Guide

## 1. Image Optimization Standards
- **Format**: WebP compression with 90% quality factor.
- **Max Dimensions**: 1920x1080 for hero banners; 600x400 for menu item thumbnails.
- **Lazy Loading**: Native `loading="lazy"` attribute applied to all catalog images.

## 2. HTTP Server Caching
The LAN HTTP server on port 8000 implements `Cache-Control: public, max-age=86400` on static web assets, drastically reducing Wi-Fi congestion during multi-terminal banquet operations.
