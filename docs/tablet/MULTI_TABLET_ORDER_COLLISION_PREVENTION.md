# Multi-Tablet Concurrent Order Creation & Collision Prevention Protocol

> **Target Version:** v4.2.5  
> **Status:** Distributed Systems Spec  
> **Date:** October 8, 2026  
> **Audience:** Backend Sync Developers, Mobile Engineers

---

## 1. Concurrent Write Hazard
Two staff members on separate tablets may simultaneously book the same venue hall for the same calendar date and time.

## 2. Optimistic Concurrency & Reservation Leases
1. **Temporary Soft Lease (5-Minute Hold):**
   - When a tablet enters Step 1 and picks a date, it requests a temporary soft reservation lease:
     `POST /api/leases/acquire { date: "2026-12-15", time: "18:00", tablet_id: "TB-02" }`
2. **Conflict Notification:**
   - If a peer tablet attempts to pick the same date/time, the UI displays: *"Date currently being held by Station 2 (Expires in 3m 40s)"*.
3. **Commit or Auto-Release:**
   - Completing checkout converts lease to permanent booking; exiting or timeout releases the lease automatically.
