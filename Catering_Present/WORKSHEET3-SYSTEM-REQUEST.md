# PC 317 — Systems Analysis and Design
## Worksheet No. 3: System Request

**Course / Subject:** PC 317 — Systems Analysis and Design
**Worksheet No.:** Worksheet No. 3 (System Request)
**Project Title:** Jayraldine's Catering Management System (Desktop Hub & Mobile Tablet Client)
**Proponents / Student Names:** BSIT Capstone Project Group (Jayraldine's Catering System Team)
**Target Organization:** Jayraldine's Catering Services
**Date:** Academic Year 2025-2026

---

## SYSTEM REQUEST: JAYRALDINE'S CATERING MANAGEMENT SYSTEM

### 1. Project Sponsor

• Primary Sponsor: Business Owner / Management of Jayraldine's Catering Services.
• Technical Proponents: BSIT Capstone Student Project Proponents.
• Lead Contact Person: Business Owner in coordination with the Lead Student System Analyst / Developer.

### 2. Business Need

This project was initiated to replace Jayraldine's Catering's inefficient, paper-based manual operations and fragmented tools (Excel spreadsheets, paper logs, phone messaging apps) with a centralized, automated Catering Management & Mobile Tablet System.
Key operational challenges prompting this system request include:
• Overbooking & Capacity Risks: Lack of automated safeguards led to scheduling conflicts and overbooking beyond daily kitchen/pax limits (max daily pax capacity).
• Revenue Leakage & Uncollected Payments: Absence of strict downpayment enforcement before booking confirmation exposed the business to cancelled events and unpaid receivables.
• Kitchen Coordination Bottlenecks: Kitchen staff relied on vague text notes without structured, per-dish itemized task checklists, causing preparation errors and delivery delays.
• Manual Client Communications: Confirmations and receipts were generated manually, leading to missed client updates, delayed billing, and lack of professional record-keeping.
• Financial Invisibility: Business tracking focused strictly on gross revenue without logging operational expenses (food cost, labor, transport, utilities), preventing accurate net profit calculation.
• Slow Off-site Client Intake: Inability to capture bookings and display package options interactively during client consultations away from the main office.

### 3. Business Requirements

The system delivers a comprehensive dual-client ecosystem (Desktop PC Hub + Mobile Tablet Client) with the following core business capabilities currently implemented:
A. Dual-Client Architecture & Data Synchronization:
• Desktop PC Hub (PySide6 + PostgreSQL/SQLite): Full administrative control, deep financial analytics, comprehensive audit logs, DB backup/restore, and master data management.
• Mobile/Tablet POS Client (PySide6 / Android APK): Touch-first order entry wizard designed for fast customer registration, interactive package/menu selection, dynamic charge/discount calculations, and digital terms acceptance.
• Offline Capability & Offline-to-PC Sync: Tablet operates standalone using local SQLite storage. Supports master data import (.db or .xlsx) from PC and seamless 1-click database merging into the main PC hub without overwriting or duplicating existing records.
B. Booking & Capacity Enforcement:
• Complete Booking Lifecycle: Manage bookings from Pending → Confirmed → In Progress → Completed → Cancelled.
• Automated Capacity Hard Block: Automatically checks total booked guest count against daily limits (default max 600 pax) and blocks new bookings if capacity is exceeded.
• Downpayment Enforcement: Enforces a configurable minimum downpayment percentage (default 30%) before a booking status can be set to Confirmed.
• Cancellation Audit: Captures structured cancellation reasons for reporting and quality control.
C. Interactive Kitchen Kanban & Dish Task Checklists:
• Kitchen Kanban Board: Visual order tracking across states (Queued → Preparing → In Progress → Ready → Delivered → Done).
• Per-Dish Task Checklist: Itemized task breakdown (kitchen_tasks) auto-generated per dish, allowing kitchen staff to check off preparation steps in real time.
D. Billing, Invoices & Financial Management:
• Automated Invoicing: Real-time balance calculations (Unpaid, Partial, Paid) with instant receipt and invoice generation.
• Multi-Category Expense Logging: Records operational costs under categorized heads (Food Cost, Labor, Transport, Utilities, Equipment, Other).
• Net Profit Analytics: Dashboard KPI metrics displaying real-time Net Profit (Revenue minus Expenses).
E. Multi-Channel Client Notifications:
• Branded Email Notifications (SMTP): Automated transmission of PDF invoices and formal payment receipts directly to client email addresses.
• SMS Notifications (Semaphore API): Instant automated SMS booking confirmations sent to client mobile numbers.
• In-App Event Alerts: Built-in notification bell panel and toast popups alerting staff 24 hours, 30 minutes, and at event start time.
F. Customer Relationship Management (CRM) & Loyalty Program:
• Customer Loyalty Tiers: Automatic customer classification into Bronze (1–2 events), Silver (3–5), Gold (6–9), and VIP (10+ events) tiers based on booking history.
• Customer Follow-Up Reminders: Task scheduler for client outreach and anniversary/re-booking reminders.
G. Terms & Conditions Compliance:
• Digital Terms Acknowledgment: Integrated contract terms wizard with mandatory customer digital signature/acknowledgment and schema versioning (ta_version).
H. System Administration, Security & Auditing:
• Comprehensive Audit Trail: Logs user actions, affected tables, timestamps, and JSON snapshots of pre/post modifications (audit_logs).
• Single-Click Database Backup & Restore: Built-in utility to export and restore database SQL dumps (pg_dump/psql) for disaster recovery.

### 4. Business Value

The implemented system provides high tangible and intangible value to Jayraldine's Catering:
Tangible Value:
• 100% Elimination of Double-Bookings & Overbooking: Hard pax capacity constraints prevent booking beyond operational capacity.
• Guaranteed Upfront Cash Flow: 30% downpayment enforcement eliminates unpaid client cancellations and no-show financial risks.
• 60% Faster Client Booking Intake: Touch-optimized Tablet wizard cuts order placement time from 20+ minutes down to 5-8 minutes.
• Complete Profit Visibility: Real-time net profit tracking isolates high-cost operational categories and improves gross margins.
• Paper & Printing Cost Reduction: Digital PDF invoice generation, email dispatch, and SMS confirmations significantly reduce physical paperwork costs.
Intangible Value:
• Enhanced Professional Brand Image: Automated instant SMS confirmations, branded PDF receipts, and tablet-based order taking boost customer trust.
• Improved Kitchen Coordination & Accuracy: Itemized dish checklists reduce kitchen preparation errors and missing menu items during events.
• Stronger Customer Retention: Automated loyalty tier badges and follow-up reminders encourage repeat client bookings.
• Total Accountability & Data Security: Comprehensive audit logs and single-click DB backup guarantee data integrity and operational oversight.

### 5. Special Issues or Constraints

• Project Context & Scope: Developed as an academic BSIT Capstone Project tailored specifically to the operational workflow of Jayraldine's Catering Services.
• Technical Environment: Hybrid architecture utilizing Python 3.11, PySide6 (Qt for Python), PostgreSQL for the main PC hub, and standalone SQLite for the mobile/tablet client.
• Third-Party Dependencies: Automated notifications rely on active SMTP internet connection for email dispatch and Semaphore API credentials for SMS dispatch.
• Hardware Compatibility: Desktop PC management hub runs on standard Windows/Linux PCs; Mobile POS app builds to standalone Android APKs and touch-screen tablets.
• Academic Review: Requires formal evaluation and approval by the Capstone Defense Panel per university academic standards.
