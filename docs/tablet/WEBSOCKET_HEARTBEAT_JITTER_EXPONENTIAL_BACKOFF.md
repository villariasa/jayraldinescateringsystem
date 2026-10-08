# Tablet LAN Sync WebSocket Heartbeat & Exponential Backoff Reconnect

> **Target Version:** v4.2.5  
> **Status:** Network Resilience Spec  
> **Date:** October 8, 2026  
> **Audience:** Backend & Mobile Sync Developers

---

## 1. Unstable Field Wi-Fi Conditions
Field routers in banquet halls experience packet drops and momentary power disruptions.

## 2. Exponential Backoff Formula with Random Jitter
Reconnection attempts follow truncated exponential backoff to prevent thundering herd crashes against the desktop server:

$$t_{	ext{retry}} = \min(t_{	ext{max}}, t_{	ext{base}} 	imes 2^{	ext{attempt}}) \pm 	ext{jitter}$$

- $t_{	ext{base}} = 1.0	ext{ sec}$, $t_{	ext{max}} = 30.0	ext{ sec}$.
- Jitter: random float between $\pm 0.25 	imes t_{	ext{retry}}$.
- Continuous ping-pong heartbeat interval: **15.0 seconds**; connection marked dead after 3 consecutive missed pongs.
