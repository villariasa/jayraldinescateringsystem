# PC 317 — Systems Analysis and Design
## Worksheet No. 3: System Request

**Date:**

**Student Names:**
1.
2.
3.
4.

---

## System Request — Jayraldine's Catering Management System

**Project Sponsor:** The Business Owner of Jayraldine's Catering, in coordination with the proponents (BSIT capstone student group)

**Business Need:**
This project was initiated to eliminate the operational inefficiencies caused by Jayraldine's Catering's reliance on manual, paper-based records and disconnected tools (spreadsheets, messaging apps) for managing bookings, kitchen coordination, client communication, and finances. The growing volume of bookings and the increasing complexity of coordinating multiple events exposed the business to scheduling conflicts, missed client communications, and inaccurate financial tracking — problems the business needed to resolve to remain efficient and professional.

**Business Requirements:**
The system must provide the following capabilities:
- Booking management with automated date/capacity conflict detection (hard block beyond max daily pax)
- Enforcement of minimum downpayment before a booking can be confirmed
- A structured, per-dish kitchen task checklist (Kanban board: Queued → Preparing → In Progress → Ready → Delivered → Done)
- Automated booking confirmation notifications to clients via SMS/email
- Automated generation and emailing of receipts/invoices to clients
- Expense logging and net profit calculation (revenue vs. cost of goods/operations)
- Customer loyalty tracking (Bronze/Silver/Gold/VIP tiers) and follow-up reminders
- An audit log recording who changed what and when
- Dashboard analytics and exportable reports (PDF, Excel, CSV)
- Database backup/restore capability

**Business Value:**
- Eliminates double-booking and over-capacity events through automated conflict/capacity checks
- Reduces missed or unpaid bookings through downpayment enforcement
- Improves kitchen efficiency and reduces preparation errors via structured task checklists
- Improves client experience and professionalism through automated confirmations and receipts
- Enables accurate, real-time visibility into net profit rather than revenue-only tracking
- Improves customer retention through loyalty tracking and follow-ups
- Improves accountability and traceability of staff actions via the audit log
- Consolidates previously disconnected tools (spreadsheets, messaging apps, paper logs) into one centralized, reliable system

**Special Issues or Constraints:**
- This is a capstone/academic project developed by BSIT proponents in direct consultation with the business owner over a structured ~6-month development timeline
- The system is single-machine/desktop-based (Python + PySide6 + PostgreSQL) — not a multi-branch or cloud/networked deployment
- Requires panel approval as part of the academic capstone process (per the worksheet's objective #2)
- Dependent on third-party services for notifications: SMTP for email, Semaphore API for SMS
