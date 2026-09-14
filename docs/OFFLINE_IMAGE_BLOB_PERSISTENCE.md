# Offline Image Blob Persistence & Camera Capture Pipeline

## 1. Device Capture Architecture
Enables tablet camera photo attachment for proof of venue payment, custom setup photos, and signed contracts:

- **HTML5 File API**: Intercepts `input[type=file]` triggers via Android WebChromeClient.
- **Client Compression**: Downscales captured camera photos in canvas buffers before database storage.
- **Persistent Binary Storage**: Stores image blobs inside SQLite `entity_images` table with instant base64 extraction.
