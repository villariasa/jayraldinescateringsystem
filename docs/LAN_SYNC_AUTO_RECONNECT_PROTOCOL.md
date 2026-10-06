# LAN Database Sync Server Auto-Reconnect & Heartbeat Protocol

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Networking, LAN Sync Server, Client Sync Engine

---

## 1. Context

Catering commissary and front-desk POS terminals operate over a local wireless LAN (e.g. `192.168.1.x`). Due to router congestion, intermittent microwave interference, or tablet sleep states, tablets may periodically lose connection to the desktop server.

This specification defines the **exponential backoff heartbeat** and **mutation replay queue** that guarantees zero transaction loss.

---

## 2. Heartbeat & Discovery Mechanism

1. **UDP Broadcast Discovery (Port 5002):**
   - The desktop server broadcasts an announcement packet every 5 seconds:
     ```json
     { "service": "jayraldines_pos_sync", "version": "4.2.3", "port": 5001, "timestamp": 1791278400 }
     ```
2. **TCP Health Probe (Port 5001):**
   - Tablets ping `GET /api/v2/ping` every 10 seconds.
   - If ping fails, status indicator switches to **Amber (Reconnecting)** and retries at 1s, 2s, 4s, 8s, up to 30s.

---

## 3. Offline Mutation Queue & Resolution

When offline:
1. All order creations and payment recordings are stored locally in **IndexedDB** (`pending_mutations_store`).
2. Each record has a client-generated UUID (`client_mutation_id`) and monotonic sequence timestamp.
3. Upon reconnecting, mutations are posted to `/api/v2/sync/push_mutations`.
4. The server executes transactions using idempotency keys, eliminating duplicate entry risks.
