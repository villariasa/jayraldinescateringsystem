# OpenAPI 3.1 REST API Schema Specification

## 1. Core Endpoints
- `GET /api/sync/lan-status`: Host health check, database engine identity, and active connection metrics.
- `POST /api/sync/lan-sync`: Bidirectional synchronization of bookings, customers, packages, dishes, and images.
- `GET /test`: Visual HTML diagnostic dashboard for network troubleshooting.
