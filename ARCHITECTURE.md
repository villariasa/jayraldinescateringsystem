# Jayraldine's Catering System — Architecture Overview

## System Topography
Jayraldine's Catering System implements a hybrid local-first and client-server database topology. The system operates with a high-performance PostgreSQL central server while supporting offline SQLite stations.

- Central PostgreSQL Database Server (Port 5432)
- Threaded Connection Pooling (5–32 workers)
- Offline Tablet Kiosk & Auto-Sync Engine (Port 8085)
- Isolated Process Theme Rendering Engine (60 FPS)
