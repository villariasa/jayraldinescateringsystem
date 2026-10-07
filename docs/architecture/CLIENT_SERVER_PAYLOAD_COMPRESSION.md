# Client-Server Sync Payload Compression & Gzip Negotiation

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Network Transport, LAN Sync Server, PWA Client

---

## 1. Context & Motivation
During initial catalog synchronizations, mobile tablets download full dish catalogs, package matrices, and recent customer records. Uncompressed JSON payloads can exceed 4 MB.

Implementing transparent `Content-Encoding: gzip` compression reduces sync payloads by 75–85%, minimizing latency over congested 2.4 GHz venue Wi-Fi networks.

---

## 2. HTTP Protocol Negotiation

1. **Client Request Headers:**
   ```http
   GET /api/v2/catalog/sync HTTP/1.1
   Host: 192.168.1.100:5001
   Accept-Encoding: gzip, deflate
   ```
2. **Server Response:**
   ```http
   HTTP/1.1 200 OK
   Content-Type: application/json; charset=utf-8
   Content-Encoding: gzip
   Vary: Accept-Encoding
   ```

---

## 3. Thresholds & CPU Optimization
- Payloads smaller than 1,024 bytes bypass compression to avoid CPU compression overhead.
- Default compression level set to `gzip Level 6` (optimal balance of speed and ratio).\n