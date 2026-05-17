# JAYRALDINE'S CATERING MANAGEMENT SYSTEM

**A Capstone Project**
**Presented to the Faculty of the College of Information Technology**
**Cebu Technological University**

---

**In Partial Fulfillment of the Requirements for the Degree of**
**Bachelor of Science in Information Technology**

---

**Submitted by:**

[Student Name/s]

**Submitted to:**

[Instructor / Adviser Name]

**Date Submitted:**

May 2026

---

---

## CHAPTER 1

---

## 1.2 Introduction

### 1.2.1 Background of the Study

The catering industry is a dynamic and service-intensive sector that demands a high degree of operational coordination among multiple departments including booking management, kitchen preparation, client communication, billing, and business analytics. For small to medium-sized catering enterprises, the manual administration of these interdependent processes often leads to inefficiencies, scheduling conflicts, missed communications, and inaccurate financial records. As digital solutions become increasingly accessible, the adoption of specialized management software has emerged as a practical approach to streamline these operations and support sustainable business growth.

Jayraldine's Catering is a local catering enterprise that has historically relied on traditional, paper-based systems and informal digital tools such as spreadsheets and messaging applications to manage its daily operations. While these methods have served the business in its early stages, the increasing volume of client bookings, the complexity of coordinating kitchen tasks across multiple events, and the growing expectation of professional client communication have exposed significant limitations in the existing approach. Bookings were tracked without automated conflict detection, kitchen staff had no structured checklist to follow during preparation, clients received no automated confirmation messages upon booking approval, and the business had no integrated means of generating receipts or tracking net profit against operational expenses.

This capstone project was conceived in direct response to these identified operational gaps. The proponents worked closely with the catering business owner to document pain points, prioritize features, and develop a desktop application purpose-built for Jayraldine's Catering. The resulting system, the Jayraldine's Catering Management System, is a fully integrated desktop application developed using Python with the PySide6 graphical user interface framework and PostgreSQL as the relational database management system. The system covers the full lifecycle of a catering event — from the initial client inquiry and booking request, through kitchen preparation, invoice generation, and payment collection, to post-event reporting and business performance analysis.

The development of this system is grounded in the principles of software engineering, database design, and human-computer interaction. It reflects the proponents' applied learning in information technology and their commitment to producing a solution that delivers measurable value to a real-world business context.

---

### 1.2.2 Statement of the Problem

Prior to the development of this system, Jayraldine's Catering faced a set of recurring operational problems that limited the efficiency and professionalism of its service delivery. These problems were identified through direct consultation with the business owner and observation of the existing workflow. The specific problems addressed by this study are as follows:

1. **Absence of date conflict detection and capacity enforcement.** The business had no mechanism to prevent the acceptance of bookings that exceeded the maximum daily guest capacity. Multiple bookings on the same date could collectively surpass the kitchen and service team's physical limits, resulting in compromised service quality and client dissatisfaction.

2. **Lack of downpayment enforcement before booking confirmation.** Bookings were confirmed without verifying whether the client had submitted the required minimum downpayment. This exposed the business to financial risk from uncommitted clients who might cancel without consequence.

3. **No automated client notification system.** Upon approving a booking, the staff had no integrated tool to automatically send confirmation messages to clients via email or SMS. This created communication gaps and increased the risk of miscommunication regarding event details.

4. **No structured kitchen preparation workflow.** Kitchen staff received only a general description of the items to prepare for each event. There was no per-dish task checklist, no stage-based Kanban tracking, and no mechanism to monitor preparation progress across multiple concurrent orders.

5. **No integrated billing and receipt generation.** Invoices were manually prepared, and there was no built-in capability to generate branded receipt documents or deliver them to clients electronically via email.

6. **Inability to track net profit.** While revenue from bookings and invoices could be tallied informally, there was no system for logging operational expenses by category. This made it impossible to calculate net profit, assess cost efficiency, or support informed business decisions.

7. **No customer loyalty tracking or follow-up reminder system.** Repeat clients were not recognized or rewarded, and staff had no structured tool to schedule and track follow-up reminders for prospective or returning clients.

8. **Absence of an audit trail.** There was no record of who approved or cancelled bookings, who issued invoices, or what changes were made to financial records. This created accountability gaps and made it difficult to investigate discrepancies.

These problems collectively motivated the development of a unified management system designed to automate, enforce, and monitor all critical operations of the catering business.

---

### 1.2.3 Objectives of the Study

The primary objective of this study is to design, develop, and deploy a desktop-based Catering Management System for Jayraldine's Catering that addresses the identified operational problems and enhances the overall efficiency, accuracy, and professionalism of the business.

Specifically, this study aims to:

1. **Develop an Orders and Bookings module** that enables staff to receive, record, approve, and manage client booking requests, with automated enforcement of date capacity limits and minimum downpayment requirements before confirmation.

2. **Implement an automated client notification system** that sends booking confirmation messages to clients via email and SMS upon booking approval, and supports manual resending of confirmations at any time.

3. **Design and implement a Kitchen Management module** featuring a Kanban-style order tracking board with six preparation stages (Queued, Preparing, In Progress, Ready, Delivered, Done), and per-order task checklists that are automatically generated from booked items.

4. **Build an integrated Billing and Invoicing module** that tracks invoice status (Unpaid, Partial, Paid), supports payment recording, and enables the generation and delivery of branded receipt documents in PDF format via print or email.

5. **Create an Expense Tracking and Profit Analysis module** that allows the business to log operational expenses by category and automatically calculate net profit against total revenue.

6. **Implement a Customer Relationship Management module** with loyalty tier tracking (Bronze, Silver, Gold, VIP) automatically updated based on confirmed booking history, and a follow-up reminder system visible on the Dashboard.

7. **Develop a full audit logging system** that records every significant action performed in the system — including booking approvals, cancellations, invoice transactions, and kitchen status changes — with actor identification, timestamps, and old/new value tracking.

8. **Provide a reporting and analytics module** that presents business performance metrics through charts and KPI cards, with export capabilities to PDF, Excel, and CSV formats.

9. **Establish a database backup and restore facility** within the application that allows authorized staff to create and restore full database backups without requiring external tools.

---

### 1.2.4 Significance of the Study

The development of the Jayraldine's Catering Management System holds significance at multiple levels — for the business itself, for its clients, for the academic proponents, and for future researchers in the same domain.

**For Jayraldine's Catering (Business Owner and Staff).** The system directly eliminates the most pressing operational inefficiencies experienced by the business. Staff will benefit from a centralized platform that unifies all aspects of catering management — from booking intake to kitchen coordination to financial reporting — reducing the reliance on multiple disconnected tools. The enforcement of capacity limits and downpayment requirements protects the business from overbooking and uncommitted client risks. The automated notification features improve the professionalism of client communication, while the billing and receipt generation tools reduce manual paperwork. The expense tracking and net profit reporting features give the owner real-time visibility into business performance, enabling data-driven decisions.

**For Clients of Jayraldine's Catering.** Clients benefit from a more responsive and organized service experience. Automated booking confirmation messages ensure that clients are informed promptly upon approval. Professionally generated receipts and invoices delivered via email provide clients with reliable documentation of their transactions.

**For the Proponents.** This project represents a comprehensive application of the knowledge and skills acquired throughout the Bachelor of Science in Information Technology program. It offered practical experience in full-stack desktop application development, relational database design, stored procedure programming, user interface design, and software project management. The constraints encountered during development — particularly those related to real-world data validation, concurrent event handling, and user experience design — provided valuable problem-solving experience that extends beyond the academic context.

**For Future Researchers and Developers.** This study contributes a documented reference for the development of desktop-based management systems for small and medium enterprises in the service sector. The architecture, database design, and feature set documented herein may serve as a foundation or comparative reference for future capstone projects addressing similar business domains.

---

## 1.3 Scope and Limitations

### 1.3.1 Scope

The Jayraldine's Catering Management System is a single-machine, desktop-based application designed to operate within the internal workflow of Jayraldine's Catering. The scope of the system encompasses the following functional areas:

**1. Orders and Bookings Management.**
The system supports the full booking lifecycle: creation of new booking records, editing of pending bookings, approval with automated downpayment and capacity validation, cancellation with reason recording, and tracking of booking status through the states PENDING, CONFIRMED, COMPLETED, and CANCELLED. Each booking stores the client name, event date, event time, number of guests (pax), occasion type, venue, selected menu package or custom items, payment mode, and downpayment amount. The system generates a unique booking reference number for each record (e.g., BKG-001).

**2. Date Capacity Management.**
The system enforces a configurable maximum daily guest capacity (default: 600 pax). A booking cannot be confirmed if the cumulative guest count for the same event date — including the booking being confirmed — would exceed this limit. The capacity threshold is visually represented on the Calendar module using color-coded indicators (green, amber, red).

**3. Downpayment Policy Enforcement.**
The system enforces a configurable minimum downpayment percentage (default: 30%). A booking cannot be confirmed if the amount paid is less than the calculated minimum downpayment. An administrative override toggle (Allow Zero Downpayment) can be enabled in the Settings module to bypass this check when necessary.

**4. Client Notification.**
Upon booking confirmation, the system automatically sends a booking confirmation message to the client via email (using the SMTP protocol) and/or SMS (using the Semaphore SMS gateway API), provided that the respective credentials are configured in the Settings module. A manual resend button is available for each confirmed booking.

**5. Calendar Scheduling.**
The system provides a monthly calendar view displaying all confirmed bookings. Each day cell shows the total guest count and number of events, with color-coded capacity indicators. Staff can click any day to view the full event list, and can add, edit, or remove manual schedule events (e.g., setup and teardown tasks) for any date.

**6. Kitchen Order Management.**
The system automatically creates a kitchen order entry for every confirmed booking. Orders are tracked through six preparation stages on a Kanban board: Queued, Preparing, In Progress, Ready, Delivered, and Done. Each kitchen order card displays the client name, guest count, menu items, event name, and a task checklist. Tasks are automatically generated from the booked menu items, and staff may add custom tasks, toggle task completion, or remove tasks. Orders can be advanced forward or returned to a previous stage.

**7. Billing and Invoicing.**
The system supports the creation and management of invoices linked to clients. Each invoice tracks the total amount, amount paid, and automatically calculates its status (Unpaid, Partial, or Paid). Staff can record multiple partial payments against an invoice. The system can generate a branded PDF receipt and either save it to disk (Print Receipt) or send it to the client's email address (Email Receipt). Receipt send events are logged.

**8. Customer Relationship Management.**
The system maintains a customer database with profiles including name, contact number, email, and address. Each customer's total confirmed and completed booking count is tracked, and a loyalty tier (Bronze, Silver, Gold, VIP) is automatically assigned based on this count. Staff can add follow-up reminder entries per customer, specifying a date and note. Reminders due on the current date appear on the Dashboard alert card.

**9. Expense and Profit Tracking.**
The system allows staff to log business expenses under six categories: Food Cost, Labor, Transport, Utilities, Equipment, and Other. The Reports module aggregates total revenue from invoices and total expenses to calculate and display net profit, both in tabular and chart form.

**10. Reporting and Analytics.**
The Reports module displays KPI summary cards and interactive charts including monthly income (bar chart), payment method distribution (pie chart), top menu items by order frequency, and customer order frequency. Reports can be filtered by time period (Today, This Week, This Month, This Year, All Time) and exported in PDF, Excel, or CSV format.

**11. Notification System.**
The system runs a background scheduler that polls for upcoming confirmed events every 10 seconds. Automated toast notifications are triggered at three intervals: 24 hours before the event, 30 minutes before the event, and at the exact event start time. Notifications are persisted in the database and viewable through the notification bell panel in the top bar.

**12. Audit Logging.**
All significant system actions are automatically recorded in the audit log, including: booking approvals and cancellations, invoice creation and payment updates, and kitchen order status changes. Each log entry includes the actor (staff member), the action performed, the affected table and record, and the old and new values where applicable. The audit log is viewable in the Settings module.

**13. Settings and Configuration.**
The Settings module allows authorized staff to configure: business information (name, address, contact, email), booking and capacity policy (minimum downpayment percentage, allow-zero-downpayment toggle, maximum daily pax), email SMTP credentials, Semaphore SMS API key, application appearance (dark/light theme), and database backup and restore operations.

**14. Database Backup and Restore.**
The system provides built-in database backup (via `pg_dump`) and restore (via `psql`) functionality accessible from the Settings module, allowing staff to create and recover from full database backups without external tools.

---

### 1.3.2 Limitations

While the Jayraldine's Catering Management System addresses a broad range of operational needs, the following limitations are acknowledged:

1. **Single-machine desktop deployment.** The system is designed for installation and operation on a single workstation. It does not support simultaneous access by multiple users over a network. There is no web-based or mobile interface. All data is stored in a local PostgreSQL database instance.

2. **No raw ingredient inventory tracking.** The system does not manage raw ingredient stock levels, supplier procurement, or recipe-level ingredient consumption. Menu items are treated as named dishes without component-level inventory tracking.

3. **No online booking portal.** The system does not provide a client-facing online booking interface. All bookings are entered by staff on behalf of clients who contact the business through other channels (phone, in-person, messaging).

4. **No multi-user role-based access control.** The system does not enforce differentiated access rights between user roles (e.g., administrator versus kitchen staff versus cashier). All users of the installed application have access to all modules.

5. **SMS delivery depends on third-party API.** The SMS notification feature requires a valid Semaphore API key and an active internet connection. The system does not support SMS delivery through alternative gateways. If the API key is not configured or the internet is unavailable, SMS notifications are silently skipped.

6. **Email delivery depends on SMTP configuration.** Email notification and receipt delivery require valid SMTP server credentials. The system supports standard SMTP authentication (including Gmail App Passwords) but does not provide its own mail server.

7. **PDF receipt and report generation requires reportlab.** The PDF export feature depends on the `reportlab` Python library. If this library is not installed in the runtime environment, PDF generation will be unavailable.

8. **Limited to the Philippine context.** The system's design, default settings, and terminology reflect the operational context of a Philippine-based catering business. Currency is displayed in Philippine Peso (₱) format. Date and time formats follow local conventions.

9. **No payment gateway integration.** The system records payment amounts manually entered by staff. It does not integrate with any electronic payment gateway, point-of-sale terminal, or banking API.

10. **Backup and restore require PostgreSQL client utilities.** The database backup and restore features invoke `pg_dump` and `psql` command-line tools. These must be present in the system's PATH for the feature to function. On systems where PostgreSQL is installed with non-standard paths, these commands may need to be located manually.

---

## 1.4 Methodology

The development of the Jayraldine's Catering Management System followed an iterative, requirements-driven development approach. The proponents conducted structured interviews with the catering business owner to identify and prioritize operational pain points, then translated these into a formal Product Requirements Document (PRD). Development proceeded in prioritized feature batches, with each batch followed by a review session with the stakeholder to validate behavior against the stated requirements. This approach allowed for continuous refinement of both functional logic and user interface design based on real feedback.

The system was architected as a three-tier desktop application: a PySide6-based presentation layer, a Python business logic layer, and a PostgreSQL database layer. All database interactions are mediated through stored procedures (PostgreSQL functions and procedures), providing a clean separation between application logic and data persistence. The database access layer (`utils/db.py`) exposes a minimal public API — `execute()`, `fetchall()`, `fetchone()`, `callproc_out()`, `callproc_void()`, and `callproc_cursor()` — ensuring that no SQL is written directly in the UI layer.

Data modeling was performed using entity-relationship diagramming at both the conceptual and physical levels. The conceptual ERD captures the high-level business entities and their relationships, while the physical ERD specifies the precise table structures, column types, constraints, foreign keys, and indexes that were implemented in PostgreSQL.

---

### 1.4.1 ERD Conceptual Model

The conceptual entity-relationship model of the Jayraldine's Catering Management System identifies the following primary entities and their relationships:

- **Customer** — represents a client of the catering business. A customer may have zero or more bookings, zero or more invoices, and zero or more follow-up reminders.
- **Booking** — represents a catering event request. Each booking belongs to one customer and may correspond to one kitchen order and one or more invoices. A booking references one occasion type and one menu package (optional).
- **Package** — represents a pre-defined catering package with a fixed price per pax. A package may be associated with many bookings. A package may include many menu items.
- **Menu Item** — represents an individual dish or service offering. A menu item may belong to many packages and may appear in many bookings as a custom selection.
- **Kitchen Order** — represents the kitchen preparation record for a confirmed booking. Each kitchen order belongs to exactly one booking. A kitchen order has zero or more kitchen tasks.
- **Kitchen Task** — represents a single preparation checklist item for a kitchen order. Each task belongs to one kitchen order.
- **Invoice** — represents a billing record. An invoice is associated with one customer and one booking (optionally). An invoice tracks total amount, amount paid, and payment status.
- **Expense** — represents an operational cost entry. Each expense has a category, amount, description, and date.
- **Notification** — represents a system-generated alert for an upcoming event. Each notification references one booking.
- **Calendar Event** — represents a manually scheduled entry on a specific date (not tied to a booking).
- **Audit Log** — records every significant system action with actor, action type, affected table, record identifier, and old/new values.
- **Receipt Log** — records each instance of a receipt being printed or emailed, linked to an invoice.
- **Confirmation Log** — records each instance of a booking confirmation being sent via email or SMS, linked to a booking.
- **Business Info** — a singleton configuration record storing business details, policy parameters, SMTP credentials, and SMS API key.
- **Customer Follow-Up** — a reminder entry associated with a customer, with a scheduled follow-up date and completion flag.

[IMAGE PLACEHOLDER — ERD Conceptual Model diagram showing all entities, attributes, and relationships as described above]

---

### 1.4.2 Data Dictionary

The following tables describe the structure of each database table implemented in the Jayraldine's Catering Management System.

---

#### Table: `bookings`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique booking identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| booking_ref | Human-readable booking reference | VARCHAR(20) | BKG-NNN | Unique | Yes | — | — |
| customer_id | Reference to the customer who made the booking | INTEGER | — | Valid customer ID | Yes | FK | customers |
| customer_name | Name of the customer (denormalized for display) | TEXT | — | — | Yes | — | — |
| event_date | Date of the catering event | DATE | YYYY-MM-DD | — | Yes | — | — |
| event_time | Time of the catering event | TIME | HH:MM | — | No | — | — |
| pax | Number of guests | INTEGER | — | ≥ 1 | Yes | — | — |
| occasion | Type of event occasion | TEXT | — | — | No | — | — |
| venue | Location of the event | TEXT | — | — | No | — | — |
| package_id | Reference to selected catering package | INTEGER | — | Valid package ID | No | FK | packages |
| items_desc | Description of menu items selected | TEXT | — | — | No | — | — |
| payment_mode | Mode of payment | TEXT | — | — | No | — | — |
| total_amount | Total billing amount agreed upon | NUMERIC(12,2) | — | ≥ 0 | Yes | — | — |
| amount_paid | Amount already paid as downpayment | NUMERIC(12,2) | — | ≥ 0 | Yes | — | — |
| status | Current booking status | booking_status ENUM | — | PENDING, CONFIRMED, COMPLETED, CANCELLED | Yes | — | — |
| cancellation_reason | Reason recorded when booking is cancelled | TEXT | — | — | No | — | — |
| created_at | Timestamp when the booking was created | TIMESTAMP | — | — | Yes | — | — |
| updated_at | Timestamp of last update | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `customers`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique customer identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| name | Full name of the customer | TEXT | — | — | Yes | — | — |
| contact_number | Customer's contact/mobile number | TEXT | — | — | No | — | — |
| email | Customer's email address | TEXT | — | — | No | — | — |
| address | Customer's physical address | TEXT | — | — | No | — | — |
| total_events | Count of confirmed and completed bookings | INTEGER | — | ≥ 0 | Yes | — | — |
| loyalty_tier | Auto-assigned loyalty tier | loyalty_tier ENUM | — | Bronze, Silver, Gold, VIP | Yes | — | — |
| status | Customer account status | TEXT | — | Active, Inactive | Yes | — | — |
| created_at | Timestamp when the record was created | TIMESTAMP | — | — | Yes | — | — |
| updated_at | Timestamp of last update | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `customer_follow_ups`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique follow-up identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| customer_id | Reference to the associated customer | INTEGER | — | Valid customer ID | Yes | FK | customers |
| follow_up_date | Date when follow-up action is due | DATE | YYYY-MM-DD | — | Yes | — | — |
| note | Description of the follow-up task | TEXT | — | — | No | — | — |
| is_done | Whether the follow-up has been completed | BOOLEAN | — | true/false | Yes | — | — |
| created_at | Timestamp when the follow-up was added | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `menu_items`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique menu item identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| name | Name of the dish or service | TEXT | — | — | Yes | — | — |
| description | Brief description of the item | TEXT | — | — | No | — | — |
| category | Category of the menu item | TEXT | — | — | No | — | — |
| package_tier | Associated package tier label | TEXT | — | — | No | — | — |
| price | Unit price of the item | NUMERIC(10,2) | — | ≥ 0 | Yes | — | — |
| status | Availability status of the item | TEXT | — | Available, Unavailable, Seasonal, Out of Stock | Yes | — | — |
| created_at | Timestamp when the item was added | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `packages`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique package identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| name | Package name | TEXT | — | — | Yes | — | — |
| description | Package description | TEXT | — | — | No | — | — |
| price_per_pax | Price charged per guest | NUMERIC(10,2) | — | ≥ 0 | Yes | — | — |
| min_pax | Minimum number of guests for the package | INTEGER | — | ≥ 1 | No | — | — |
| created_at | Timestamp when the package was created | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `invoices`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique invoice identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| invoice_ref | Human-readable invoice reference | VARCHAR(20) | INV-NNN | Unique | Yes | — | — |
| customer_id | Reference to the associated customer | INTEGER | — | Valid customer ID | Yes | FK | customers |
| customer_name | Customer name (denormalized for display) | TEXT | — | — | Yes | — | — |
| event_date | Date of the catering event | DATE | YYYY-MM-DD | — | No | — | — |
| total_amount | Total invoice amount | NUMERIC(12,2) | — | ≥ 0 | Yes | — | — |
| amount_paid | Total amount received to date | NUMERIC(12,2) | — | ≥ 0 | Yes | — | — |
| status | Computed payment status | TEXT | — | Unpaid, Partial, Paid | Yes | — | — |
| created_at | Timestamp when the invoice was created | TIMESTAMP | — | — | Yes | — | — |
| updated_at | Timestamp of last update | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `kitchen_orders`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique kitchen order identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| booking_id | Reference to the associated booking | INTEGER | — | Valid booking ID | Yes | FK | bookings |
| client_name | Client name for display on Kanban card | TEXT | — | — | Yes | — | — |
| pax | Number of guests for this order | INTEGER | — | ≥ 1 | Yes | — | — |
| event_name | Name/occasion of the event | TEXT | — | — | No | — | — |
| items_desc | Menu items description string | TEXT | — | — | No | — | — |
| status | Current kitchen preparation stage | TEXT | — | Queued, Preparing, In Progress, Ready, Delivered, Done | Yes | — | — |
| created_at | Timestamp when the kitchen order was created | TIMESTAMP | — | — | Yes | — | — |
| updated_at | Timestamp of last status update | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `kitchen_tasks`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique task identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| order_id | Reference to the associated kitchen order | INTEGER | — | Valid kitchen order ID | Yes | FK | kitchen_orders |
| task_label | Description of the preparation task | TEXT | — | — | Yes | — | — |
| is_done | Whether the task has been completed | BOOLEAN | — | true/false | Yes | — | — |
| sort_order | Display order of the task within the card | INTEGER | — | ≥ 0 | Yes | — | — |
| updated_at | Timestamp of last update | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `calendar_events`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique calendar event identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| event_date | Date of the scheduled event | DATE | YYYY-MM-DD | — | Yes | — | — |
| title | Event title or label | TEXT | — | — | Yes | — | — |
| note | Additional description or notes | TEXT | — | — | No | — | — |
| created_at | Timestamp when the event was created | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `notifications`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique notification identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| booking_id | Reference to the associated booking | INTEGER | — | Valid booking ID | No | FK | bookings |
| title | Short notification title | TEXT | — | — | Yes | — | — |
| message | Full notification message text | TEXT | — | — | Yes | — | — |
| type | Notification trigger type | TEXT | — | 1_day, 30_min, now | Yes | — | — |
| is_read | Whether the notification has been read | BOOLEAN | — | true/false | Yes | — | — |
| created_at | Timestamp when the notification was generated | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `expenses`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique expense identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| category | Expense category | expense_category ENUM | — | Food Cost, Labor, Transport, Utilities, Equipment, Other | Yes | — | — |
| description | Description of the expense | TEXT | — | — | No | — | — |
| amount | Expense amount | NUMERIC(10,2) | — | ≥ 0 | Yes | — | — |
| expense_date | Date the expense was incurred | DATE | YYYY-MM-DD | — | Yes | — | — |
| created_at | Timestamp when the record was entered | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `audit_logs`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique audit log entry identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| actor | Name or identifier of the staff who performed the action | TEXT | — | — | Yes | — | — |
| action | Type of action performed | TEXT | — | APPROVE, CANCEL, CREATE, UPDATE, STATUS_CHANGE | Yes | — | — |
| table_name | Name of the affected database table | TEXT | — | — | Yes | — | — |
| record_id | Primary key of the affected record | INTEGER | — | ≥ 1 | Yes | — | — |
| old_value | Previous state of the record (before change) | JSONB | — | — | No | — | — |
| new_value | New state of the record (after change) | JSONB | — | — | No | — | — |
| created_at | Timestamp when the log entry was written | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `receipt_log`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique receipt log identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| invoice_id | Reference to the invoice for which receipt was sent | INTEGER | — | Valid invoice ID | Yes | FK | invoices |
| method | Delivery method used | TEXT | — | print, email | Yes | — | — |
| sent_at | Timestamp when the receipt was delivered | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `confirmation_log`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Unique confirmation log identifier | INTEGER | Auto-increment | ≥ 1 | Yes | PK | — |
| booking_id | Reference to the associated booking | INTEGER | — | Valid booking ID | Yes | FK | bookings |
| method | Notification channel used | TEXT | — | email, sms | Yes | — | — |
| sent_at | Timestamp when the confirmation was sent | TIMESTAMP | — | — | Yes | — | — |

---

#### Table: `business_info`

| Attribute Name | Contents | Type | Format | Range | Required | PK/FK | FK Referenced Table |
|---|---|---|---|---|---|---|---|
| id | Singleton record identifier | INTEGER | — | Always 1 | Yes | PK | — |
| business_name | Registered business name | TEXT | — | — | No | — | — |
| owner_name | Name of the business owner | TEXT | — | — | No | — | — |
| contact_number | Business contact number | TEXT | — | — | No | — | — |
| email | Business email address | TEXT | — | — | No | — | — |
| address | Physical address of the business | TEXT | — | — | No | — | — |
| min_downpayment_pct | Minimum required downpayment as a percentage | NUMERIC(5,2) | — | 0–100 | Yes | — | — |
| allow_zero_downpayment | Toggle to bypass downpayment check | BOOLEAN | — | true/false | Yes | — | — |
| max_daily_pax | Maximum total guests allowed per day | INTEGER | — | ≥ 1 | Yes | — | — |
| smtp_host | SMTP server hostname | TEXT | — | — | No | — | — |
| smtp_port | SMTP server port number | INTEGER | — | 1–65535 | No | — | — |
| smtp_user | SMTP account username | TEXT | — | — | No | — | — |
| smtp_pass | SMTP account password or app password | TEXT | — | — | No | — | — |
| sms_api_key | Semaphore SMS API key | TEXT | — | — | No | — | — |
| updated_at | Timestamp of last settings update | TIMESTAMP | — | — | Yes | — | — |

---

### 1.4.3 ERD Physical Model

The physical entity-relationship model extends the conceptual model by specifying the exact PostgreSQL implementation details: column data types, NOT NULL and DEFAULT constraints, primary key sequences, foreign key references with ON DELETE behavior, enumerated type declarations, and index definitions.

Key physical model decisions include:

- **Enumerated types** (`booking_status`, `loyalty_tier`, `expense_category`) are declared as PostgreSQL `CREATE TYPE ... AS ENUM` constructs, enforcing domain integrity at the database engine level.
- **Automatic timestamp updates** on the `updated_at` columns of `bookings`, `customers`, and `invoices` are implemented via PostgreSQL trigger functions using `BEFORE UPDATE` triggers.
- **Loyalty tier recalculation** is triggered automatically after any update to `bookings.status` via a `AFTER UPDATE` trigger that calls the `sp_recalculate_loyalty()` stored procedure.
- **Foreign key constraints** are defined with `ON DELETE CASCADE` where child records have no independent meaning (e.g., `kitchen_tasks` cascading from `kitchen_orders`), and with `ON DELETE RESTRICT` where referential integrity must be explicitly managed (e.g., `bookings` referencing `customers`).
- **Indexes** are defined on frequently queried foreign key columns and filter predicates (e.g., `bookings.event_date`, `bookings.status`, `notifications.is_read`) to support performant query execution.

[IMAGE PLACEHOLDER — ERD Physical Model diagram showing all tables, column names, data types, constraints, primary keys, foreign keys, and relationships]

---

## 1.5 Development Tools and Technologies

### 1.5.1 PostgreSQL

PostgreSQL is an open-source, object-relational database management system (ORDBMS) known for its standards compliance, extensibility, reliability, and feature richness. For this project, PostgreSQL version 14 or later was used as the exclusive data persistence layer.

PostgreSQL was selected for the following reasons:

- **Stored Procedures and Functions.** The system's business logic is largely implemented in the database layer through PostgreSQL stored procedures (using PL/pgSQL), enabling transactional consistency and reducing the risk of logic duplication across the application layer.
- **Enumerated Types.** PostgreSQL's native `ENUM` type support allows domain constraints such as booking status and loyalty tiers to be enforced directly at the database level, preventing invalid state transitions from being persisted.
- **Trigger Functions.** Automatic loyalty tier recalculation and timestamp management are implemented via database triggers, ensuring that business rules are enforced regardless of the application layer pathway.
- **JSONB Support.** The `audit_logs` table uses PostgreSQL's `JSONB` column type to store structured old/new value snapshots, enabling rich change tracking without requiring a separate change log table structure.
- **pg_dump / psql Utilities.** The built-in command-line backup (`pg_dump`) and restore (`psql`) utilities are leveraged directly by the application's backup and restore features, providing reliable and complete database snapshots without requiring third-party tools.
- **psycopg2 Driver.** PostgreSQL is accessed from Python via the `psycopg2` driver, the de facto standard PostgreSQL adapter for Python, which provides connection pooling support, prepared statement execution, and dictionary-based cursor results through its `RealDictCursor` extension.

---

### 1.5.2 Python

Python is a high-level, interpreted, general-purpose programming language renowned for its readability, extensive standard library, and vibrant ecosystem of third-party packages. Python version 3.11 or later was used for all application development in this project.

Python was chosen for the following reasons:

- **PySide6 Compatibility.** PySide6, the official Qt for Python binding, requires Python 3.8 or later and integrates seamlessly with modern Python packaging and virtual environment workflows.
- **psycopg2 Integration.** The `psycopg2` library provides a mature, well-documented PostgreSQL interface for Python applications.
- **reportlab for PDF Generation.** The `reportlab` library enables programmatic generation of branded PDF receipts and reports with precise layout control.
- **openpyxl for Excel Export.** The `openpyxl` library provides full Excel (.xlsx) file generation capabilities including cell styling, column width adjustment, and multi-sheet workbooks.
- **smtplib / email (Standard Library).** Python's built-in `smtplib` module, combined with the `email` package, provides complete SMTP email composition and delivery capability without external dependencies.
- **requests for SMS API.** The `requests` library is used to make HTTP POST requests to the Semaphore SMS gateway API, enabling SMS notification delivery.
- **threading for Non-Blocking Operations.** Python's `threading` module is used to perform the database connection attempt in a background thread during application startup, preventing the splash screen from freezing while the connection is established.
- **os and subprocess.** Standard library modules `os` and `subprocess` are used to invoke `pg_dump` and `psql` for database backup and restore operations.

---

### 1.5.3 PySide6 (Qt for Python)

PySide6 is the official Python binding for the Qt framework, developed and maintained by The Qt Company. It provides access to the full Qt 6 widget toolkit, enabling the development of professional-grade, cross-platform desktop graphical user interfaces.

PySide6 was selected for the following reasons:

- **Rich Widget Set.** Qt provides a comprehensive set of native-looking UI components including tables, list views, dialogs, combo boxes, date pickers, tab widgets, and scroll areas — all of which are extensively used in the Jayraldine's Catering Management System.
- **Fusion Style.** The application uses Qt's built-in "Fusion" platform style, which provides a consistent, modern appearance across operating systems regardless of the host platform's native widget theme.
- **Qt Style Sheets (QSS).** The dark and light themes are implemented using Qt Style Sheets, a CSS-like styling language that allows comprehensive visual customization of all Qt widgets. The system ships with two QSS theme files (`main.qss` for dark mode, `light.qss` for light mode) that are dynamically applied at runtime.
- **Signal/Slot Architecture.** Qt's signal/slot event system enables clean, decoupled communication between UI components. This is used extensively for inter-module communication (e.g., notifying the notification panel of new alerts, updating the dashboard when bookings are approved).
- **QTimer for Background Polling.** The notification scheduler uses `QTimer` to fire a polling event every 10 seconds within the Qt event loop, enabling non-blocking periodic checks for upcoming events without requiring a separate OS-level thread.
- **Cross-Platform Support.** While the primary deployment target is Windows, PySide6's cross-platform architecture ensures that the application can be compiled and run on Linux and macOS without significant code changes.
- **PyInstaller Compatibility.** The application can be packaged into a standalone Windows executable using PyInstaller, with PySide6's plugin architecture correctly bundled via the `--collect-all PySide6` directive and custom plugin path resolution implemented in `main.py`.

---

### 1.5.4 System Architecture

The Jayraldine's Catering Management System follows a three-tier desktop application architecture:

**Tier 1 — Presentation Layer (UI)**
The presentation layer consists of nine page modules (`ui/dashboard_page.py`, `ui/booking_page.py`, `ui/customers_page.py`, `ui/menu_page.py`, `ui/calendar_page.py`, `ui/kitchen_page.py`, `ui/billing_page.py`, `ui/reports_page.py`, `ui/settings_page.py`) unified within a main window frame (`ui/main_window.py`). Shared UI components (sidebar navigation, topbar with notification bell and theme toggle, toast notification widget, notification panel, booking modal, filter popover, customer search dropdown, and address search) are implemented as reusable classes in the `components/` directory.

**Tier 2 — Business Logic Layer**
Business logic is distributed between the Python application layer and the PostgreSQL stored procedure layer:
- In the Python layer: form validation, dialog orchestration, state management, PDF/Excel/CSV generation, email composition, SMS dispatch, background scheduling, and audit trail invocation.
- In the database stored procedure layer: booking status transition enforcement (including downpayment and capacity checks), loyalty tier calculation, kitchen order auto-creation, invoice status derivation, audit log writing, and all multi-step transactional operations.

**Tier 3 — Data Layer**
The data layer is a local PostgreSQL instance running the `jayraldines_catering` database. The `utils/db.py` module provides the sole access point to the database from the application. It implements a singleton connection pattern with auto-reconnect capability. Configuration is read from environment variables with safe defaults. The public API surface is intentionally minimal: `execute()` for DML without return data, `fetchall()` and `fetchone()` for parameterized SELECT queries returning dictionary results, `callproc_out()` for stored procedures with OUT parameters, `callproc_void()` for procedures without return values, and `callproc_cursor()` for procedures returning a REFCURSOR.

**Application Startup Sequence**
On launch, the application executes the following startup sequence:
1. On Windows, a named Win32 mutex (`Global\JayraldinesCateringMutex`) is acquired to prevent duplicate instances.
2. A `QApplication` is initialized with the Fusion platform style.
3. A splash screen is displayed with a staged progress indicator.
4. The dark theme QSS is applied.
5. The database connection attempt is dispatched on a background thread with an 8-second timeout.
6. The main window module is imported during the wait period to maximize perceived startup speed.
7. Upon completion of the database thread (connected or timed out), the main window is instantiated and displayed, and the splash screen is closed.

[IMAGE PLACEHOLDER — System Architecture diagram showing the three-tier structure: Presentation Layer (PySide6 UI), Business Logic Layer (Python + PostgreSQL Stored Procedures), and Data Layer (PostgreSQL)]

---

## 1.6 Project Timeline (Gantt Chart)

The development of the Jayraldine's Catering Management System was carried out over a structured development timeline spanning approximately six months. The project phases proceeded as follows:

**Phase 1 — Requirements Gathering and Analysis (Weeks 1–3)**
The proponents conducted structured interviews with the catering business owner to document existing workflows, identify pain points, and define system requirements. A Product Requirements Document (PRD) was prepared listing all features, organized by priority and complexity. Initial wireframes were sketched for key modules.

**Phase 2 — Database Design and Initial Setup (Weeks 4–6)**
The entity-relationship diagram was designed at both the conceptual and physical levels. The PostgreSQL database schema was created, including all table definitions, enumerated types, constraints, foreign keys, and initial stored procedures for core booking and customer operations.

**Phase 3 — Core Module Development (Weeks 7–12)**
The foundational application modules were implemented in priority order: Orders & Bookings, Customers, Menu, Calendar, and Kitchen. The main window navigation structure, sidebar, topbar, and theme system were established. The database access layer (`utils/db.py`) was finalized.

**Phase 4 — Advanced Feature Development (Weeks 13–18)**
The higher-complexity features were implemented: downpayment enforcement, capacity hard block, cancellation reason tracking, kitchen task checklist, billing and invoicing with PDF receipt generation, email notification via SMTP, SMS notification via Semaphore, expense tracking, and net profit reporting.

**Phase 5 — Analytics, Notifications, and Audit (Weeks 19–22)**
The notification scheduler, toast alert system, notification bell panel, audit logging system, customer loyalty tiers with PostgreSQL trigger, and follow-up reminder system were implemented. Dashboard charts and KPI cards were completed.

**Phase 6 — Testing, Refinement, and Documentation (Weeks 23–26)**
End-to-end testing was performed against all stated requirements. UI refinements were made based on stakeholder feedback. The database backup/restore feature was implemented and tested. All documentation — SYSTEM_FLOW.md, PRD, and this manuscript — was finalized.

[IMAGE PLACEHOLDER — Gantt Chart showing all six development phases with weekly timeline bars across the project duration]

---

## 1.7 Expected Outputs (Screenshots)

This section presents the major interface screens of the Jayraldine's Catering Management System, illustrating the visual design and functionality of each module.

---

**Dashboard**

The Dashboard provides a real-time business overview upon login. It displays KPI summary cards for today's events, pending bookings, weekly revenue, and outstanding unpaid balance. The lower section presents four analytics charts: monthly income (bar chart), payment method distribution (pie chart), top menu items by order count, and customer order frequency. Below the charts, an upcoming events card lists all confirmed bookings due within the next 7 days, each showing a countdown timer and a "Mark as Completed" action. A follow-ups alert card lists customers with follow-up reminders due today.

[IMAGE PLACEHOLDER — Screenshot of the Dashboard module in dark mode, showing KPI cards, charts, and upcoming events section]

---

**Orders and Bookings**

The Orders & Bookings page presents all bookings in a searchable, filterable table. Each row displays the booking reference, customer name, event date, pax count, occasion, status badge, and amount paid versus total amount. Action buttons on each row allow staff to approve (PENDING only), cancel (with reason dialog), resend confirmation (CONFIRMED only), edit (PENDING only), or delete a booking. The "New Booking" button opens the booking modal. A filter popover allows filtering by status, date range, and occasion type.

[IMAGE PLACEHOLDER — Screenshot of the Orders and Bookings page showing the booking table with status badges and action buttons]

[IMAGE PLACEHOLDER — Screenshot of the New Booking modal showing all input fields and the menu package selector]

---

**Customers**

The Customers page lists all client records with their name, contact number, email, total events count, and loyalty tier badge (Bronze, Silver, Gold, or VIP). The search bar filters the list in real time. Clicking a customer row expands a detail panel showing full profile information, follow-up reminders, and a button to add a new follow-up.

[IMAGE PLACEHOLDER — Screenshot of the Customers page showing the customer list with loyalty tier badges and follow-up section]

---

**Menu**

The Menu page is divided into two tabs: Menu Items and Packages. The Menu Items tab displays all dishes with their category, price, and status badge (Available, Unavailable, Seasonal, Out of Stock). The Packages tab lists all catering packages with their price per pax and minimum pax requirements. Both tabs support search filtering and CRUD operations.

[IMAGE PLACEHOLDER — Screenshot of the Menu page showing the Menu Items tab with status badges]

---

**Calendar**

The Calendar displays a full monthly view with a cell for each day. Days with confirmed bookings show the total pax count with a color-coded background (green, amber, or red based on capacity utilization). Clicking any day opens a side panel listing all confirmed bookings for that day, a capacity status label, and a "Manage Day Schedule" button for adding or removing manual events.

[IMAGE PLACEHOLDER — Screenshot of the Calendar module showing a month with color-coded day cells and the day detail side panel open]

---

**Kitchen**

The Kitchen module presents a Kanban board with six column stages: Queued, Preparing, In Progress, Ready, Delivered, and Done. Each confirmed booking appears as a card in the Queued column upon creation. Cards display the client name, pax count, event name, items description, and a task checklist with checkboxes. Staff can advance a card to the next stage (Forward button) or return it to the previous stage (Back button). Each card also allows adding custom tasks, toggling task completion, and deleting tasks.

[IMAGE PLACEHOLDER — Screenshot of the Kitchen Kanban board showing multiple order cards across different stage columns with task checklists visible]

---

**Billing**

The Billing page lists all invoices with their reference number, customer name, event date, total amount, amount paid, and status badge (Unpaid, Partial, Paid). The "New Invoice" button opens an invoice creation form. The printer icon on each row opens a save dialog to generate and save a PDF receipt. The email icon prompts for a customer email address and sends the PDF receipt. An edit button opens the invoice form to record additional payments.

[IMAGE PLACEHOLDER — Screenshot of the Billing page showing the invoice list with status badges and action icons]

[IMAGE PLACEHOLDER — Screenshot of a generated PDF receipt showing the branded receipt layout with business name, invoice details, and payment summary]

---

**Reports**

The Reports page contains three tabs: Overview, Expenses, and Profit. The Overview tab displays KPI summary cards (total bookings, total pax, total revenue, unpaid amount) with a period filter selector and export buttons (PDF, Excel, CSV). The Expenses tab shows a list of logged expenses with a form to add new entries and a category-wise summary. The Profit tab shows a net profit breakdown comparing total revenue against total expenses.

[IMAGE PLACEHOLDER — Screenshot of the Reports Overview tab showing KPI cards, period filter, and export buttons]

[IMAGE PLACEHOLDER — Screenshot of the Reports Expenses tab showing the expense log and add-expense form]

---

**Settings**

The Settings page is organized into sections: Business Information, Booking & Capacity Policy, Email (SMTP) Configuration, SMS Configuration (Semaphore), Appearance, Database Backup & Restore, Occasions Management, and Audit Log. Each section presents editable fields with save buttons. The Audit Log section displays the 50 most recent logged actions in a scrollable table with actor, action, table, record, and timestamp columns.

[IMAGE PLACEHOLDER — Screenshot of the Settings page showing the Business Information section and Booking Policy section]

[IMAGE PLACEHOLDER — Screenshot of the Settings Audit Log section showing recent logged actions in a table]

---

## 1.8 Conclusion

### 1.8.1 Summary

The Jayraldine's Catering Management System was developed as a comprehensive, integrated desktop application designed to address the specific operational challenges of a small catering business operating in the Philippine context. Through structured requirements gathering, systematic database design, and iterative feature implementation, the proponents produced a fully functional system that delivers measurable improvements across all identified problem areas.

The system successfully fulfills all stated objectives: it enforces date capacity limits and minimum downpayment requirements before booking confirmation, preventing overbooking and protecting the business from uncommitted reservations; it automates client communication through both email and SMS upon booking approval; it provides kitchen staff with a structured Kanban workflow and per-order task checklists to coordinate multi-event preparation; it enables the generation and delivery of branded receipt documents to clients; it tracks operational expenses and calculates net profit, giving the business owner real-time financial visibility; it automatically recognizes and rewards repeat clients through a loyalty tier system; and it maintains a complete audit trail of all significant system actions.

The technical implementation demonstrates a sound application of relational database design principles, with business rules enforced at the database layer through PostgreSQL stored procedures, triggers, and enumerated types. The use of PySide6 as the graphical user interface framework produced a professional, responsive desktop application with a polished dark-mode default theme, a clean navigation structure, and consistent visual design across all nine modules.

The data dictionary documents fifteen database tables covering every operational domain of the system. The three-tier architecture — with a PySide6 presentation layer, a Python-and-PostgreSQL business logic layer, and a local PostgreSQL data layer — provides a clean separation of concerns that facilitates future maintenance and feature expansion.

While the system operates as a single-machine desktop application without multi-user network access or raw ingredient inventory tracking, these limitations are consistent with the current scale and operational context of the business. The system's modular design and well-structured codebase provide a solid foundation for future enhancements, including potential network-accessible deployment, role-based access control, and integration with external payment platforms.

In conclusion, the Jayraldine's Catering Management System represents a practical, fully realized capstone project that applies academic knowledge in information technology to solve real business problems. It demonstrates proficiency in full-stack desktop application development, PostgreSQL database design, event-driven GUI programming, and software project management, and delivers a solution that the catering business can immediately deploy and benefit from in its daily operations.

---

## 1.9 References

Below are the key references and resources consulted during the design, development, and documentation of the Jayraldine's Catering Management System, formatted in APA style.

---

PostgreSQL Global Development Group. (2023). *PostgreSQL 15 documentation*. The PostgreSQL Global Development Group. https://www.postgresql.org/docs/15/

The Qt Company. (2023). *PySide6 documentation: Qt for Python*. The Qt Company Ltd. https://doc.qt.io/qtforpython-6/

Python Software Foundation. (2023). *Python 3.11 documentation*. Python Software Foundation. https://docs.python.org/3.11/

ReportLab Inc. (2023). *ReportLab open-source PDF toolkit user guide* (Version 4.0). ReportLab Inc. https://www.reportlab.com/docs/reportlab-userguide.pdf

Gazoni, E., & Clark, C. (2023). *openpyxl — A Python library to read/write Excel 2010 xlsx/xlsm files*. https://openpyxl.readthedocs.io/

Reitz, K., & Chiang, C. (2023). *Requests: HTTP for humans*. https://requests.readthedocs.io/

Psycopg Team. (2023). *Psycopg 2.9 documentation*. https://www.psycopg.org/docs/

Semaphore Philippines. (2023). *Semaphore SMS API documentation*. Semaphore. https://semaphore.co/docs

Sommerville, I. (2016). *Software engineering* (10th ed.). Pearson Education Limited.

Connolly, T., & Begg, C. (2014). *Database systems: A practical approach to design, implementation, and management* (6th ed.). Pearson Education Limited.

Lutz, M. (2013). *Learning Python* (5th ed.). O'Reilly Media.

Eck, D. J. (2022). *Introduction to programming using Python* (Version 3). Hobart and William Smith Colleges. http://math.hws.edu/javanotes/

Cebu Technological University. (2024). *Capstone project manuscript guide and template*. CTU College of Information Technology.

---

*End of Manuscript — Jayraldine's Catering Management System*
