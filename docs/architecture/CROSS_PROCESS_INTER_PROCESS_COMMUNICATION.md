# Cross-Process Inter-Process Communication (IPC) Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** PySide6 Desktop, Local Sync Daemon, Background Print Spooler

---

## 1. Scope
The desktop application splits computationally intensive background tasks (LAN HTTP server, thermal print spooler, auto-backup daemon) into isolated helper processes to ensure the PySide6 UI thread never lags.

---

## 2. IPC Communication Channels

1. **Local Named Pipes / Unix Domain Sockets:**
   - Path: `/tmp/jayraldines_pos.sock` (Linux) or `\\.\pipe\jayraldines_pos` (Windows).
   - Fast, low-latency binary serialization using `QLocalServer` and `QLocalSocket`.
2. **Standard Message Protocol:**
   - 4-byte big-endian payload length header followed by UTF-8 encoded JSON command.

```
+-------------------+-----------------------------------------+
| Length (4 Bytes)  | Payload JSON (Length bytes)             |
| 0x00 0x00 0x01 0x2A | {"cmd": "SPOOL_PRINT", "job_id": 412}   |
+-------------------+-----------------------------------------+
```\n