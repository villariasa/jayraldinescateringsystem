# Offline Order Queue Transaction Log & Recovery Protocol

> **Target Version:** v2.7.5  
> **Status:** Reliability Specification  
> **Date:** October 29, 2026  
> **Audience:** Mobile Engineers, Backend Architects

---

## 1. Offline Persistence Engine
When network connectivity is disrupted during a remote catering booking:
- Orders are serialized into local IndexedDB (`offline_bookings_store`) with UUID v4 idempotency keys.
- Each payload includes cryptographic SHA-256 digest of customer details, selected sets, and deposit status.

## 2. Automatic Synchronization Loop
- A service worker background sync event triggers when network connectivity resumes.
- HTTP `POST /api/v3/sync/bookings` processes queue in strict FIFO order.
- In case of collision, the central PostgreSQL timestamp determines record authority, with tablet changes preserved as an audit revision.
