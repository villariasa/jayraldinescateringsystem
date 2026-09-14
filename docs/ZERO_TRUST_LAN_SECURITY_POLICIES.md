# Zero-Trust LAN Security & API Authorization Policies

## 1. Network Boundary Controls
- **CORS Restrictions**: Explicit origin validation on API endpoints preventing unauthorized browser injection.
- **Rate Throttling**: Leaky bucket rate limiter enforcing a maximum of 60 requests/minute per client IP.
- **Port Isolation**: PostgreSQL raw port 5432 bound to localhost (`127.0.0.1`), exposed externally only via port 8000 API middleware.
