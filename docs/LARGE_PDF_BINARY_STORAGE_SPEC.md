# Large PDF & Contract Document Binary Storage Specification

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Document Storage, SQLite/PostgreSQL Engine, Sync Protocol

---

## 1. Executive Summary

Catering contracts and event booking agreements frequently include scanned pages, signed contracts, client identity documentation, and high-resolution photo attachments, often reaching file sizes between **15 MB and 30 MB** per document.

Historically, base64 data-URIs were used to serialize contracts across JSON endpoints and database columns. While convenient for small files (<500 KB), encoding an 18 MB PDF into base64 introduces severe performance penalties:
1. **Payload Explosion:** Base64 increases binary size by ~33.3%, inflating an 18 MB file to ~24 MB of ASCII text.
2. **Memory Overhead:** Qt's `QTextDocument` and webview DOM engines allocate separate string buffers, decoding trees, and pixel rasters, easily consuming >150 MB RAM per document and causing UI thread freezes.
3. **Database Bloat:** Writing tens of megabytes into SQLite WAL logs degrades write performance and increases checkpoint lock latency.

This specification details the transition from base64 string storage to **direct binary filesystem storage** with relative path indexing and streaming transport.

---

## 2. Architecture Overview

### 2.1 File Storage Hierarchy

Contract documents are persisted on the local filesystem under an isolated document repository rather than embedded in SQLite text fields:

```
app_data/
├── documents/
│   ├── contracts/
│   │   ├── 2026/
│   │   │   ├── 10/
│   │   │   │   ├── CT-20261006-0012.pdf
│   │   │   │   └── CT-20261006-0013.pdf
│   ├── attachments/
│   │   └── ID-20261006-0012-front.jpg
└── database/
    └── catering_main.db
```

### 2.2 Database Schema Update

The `contracts` and `booking_attachments` tables store metadata and relative disk paths:

| Column Name | Type | Description |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Unique contract identifier |
| `booking_id` | INTEGER | Foreign key referencing `bookings(id)` |
| `file_name` | TEXT | Original client filename |
| `file_rel_path` | TEXT | Relative path on disk (e.g. `documents/contracts/2026/10/...`) |
| `file_size_bytes` | INTEGER | Exact file size in bytes |
| `sha256_hash` | TEXT | SHA-256 checksum for corruption verification |
| `mime_type` | TEXT | Standard MIME type (`application/pdf`) |
| `created_at` | TIMESTAMP | Record creation timestamp |

---

## 3. Upload & Ingestion Pipeline

### 3.1 Streaming Ingestion (Chunked Transfer)

1. Client uploads file using standard `multipart/form-data` or a streaming binary HTTP endpoint (`PUT /api/v2/documents/upload/{booking_id}`).
2. The server reads the stream in **64 KB chunks** (`shutil.copyfileobj` or Python `aiofiles` / chunked socket reader) directly into a temporary file on disk.
3. SHA-256 hash is computed progressively during the read loop without loading the entire 18 MB into memory.
4. On upload completion, the temporary file is moved to its permanent target path via atomic file rename (`os.replace`).
5. A lightweight record with the relative path is committed to the database.

---

## 4. Desktop Viewing Optimization

In the desktop app (`PySide6`), large multi-page contracts are viewed using native document components rather than embedding base64 into `QTextBrowser`:

1. **`QPdfDocument` and `QPdfView`**: PySide6's QtPdf module loads the file path directly from disk, rendering only visible pages at runtime with minimal memory footprint.
2. **On-Demand Page Rendering**: If using an image-based preview dialog, pages are rendered one at a time and cached as temporary raster files (`file://.../temp_page_1.png`) rather than generating huge `data:image/png;base64` HTML tags.

---

## 5. Security & Retention

- **Path Traversal Protection:** All relative paths are sanitized using `os.path.abspath` and checked to ensure they reside strictly within the designated storage directory.
- **Automated Backup:** Daily WAL backups archive document folders into incremental tarballs while preserving checksum integrity.
