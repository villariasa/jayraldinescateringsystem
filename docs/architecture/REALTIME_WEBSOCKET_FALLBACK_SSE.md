# Real-Time WebSocket Architecture with Server-Sent Events (SSE) Fallback

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Realtime Dispatch, Kitchen Display, Waiter Tablet

---

## 1. Overview
When a new order slip is finalized at the cashier, kitchen and dispatch tablets must update immediately without manual refreshes.

This specification details the dual-transport real-time architecture:
1. **Primary Transport:** Bi-directional WebSockets (`ws://`) for instant notification and acknowledgments.
2. **Fallback Transport:** HTTP Server-Sent Events (`SSE`) for environments where proxy or firewall rules block WebSocket upgrade handshakes.

---

## 2. Handshake & Channel Subscriptions

```
[Tablet Frontend] ----------------- WebSocket Handshake ----------------> [POS Server]
[Tablet Frontend] <---------------- Connection Established ------------ [POS Server]
[Tablet Frontend] ------ SUBSCRIBE: channel="kitchen_display" ---------> [POS Server]

(Upon order confirmation):
[POS Server] -------- EVENT: "NEW_ORDER_DISPATCHED" (Payload JSON) ----> [Tablet Frontend]
[Tablet Frontend] ---- ACK: event_id="evt_8192" ------------------------> [POS Server]
```

---

## 3. Reconnection Policies
- Automatic exponential retry: 500ms, 1s, 2s, 4s up to 15s.
- Automatic fallback to SSE if WebSocket connection fails three consecutive times.\n