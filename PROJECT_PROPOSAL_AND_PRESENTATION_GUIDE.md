# 🍽️ JAYRALDINE'S CATERING MANAGEMENT & SELF-SERVICE KIOSK SYSTEM
## Formal Project Proposal & Functional Specification Document

---

## 1. Project Background & Business Case

* **Client**: Jayraldine's Catering Services (Cebu, Philippines).
* **Project Classification**: Integrated Catering ERP & Self-Service Kiosk System.
* **System Scope**: Dual-Platform Solution (Windows PC Back-Office Management Suite + 100% Offline Tablet/Mobile Field Kiosk).
* **Project Goal**: Automate and modernize end-to-end catering operations — replacing manual paperwork with automated client ordering, live financial estimations, downpayment enforcement, kitchen preparation workflows, expense tracking, AI business forecasting, and comprehensive reporting.

---

## 2. Operational Problems vs. Proposed System Solutions

| Current Manual Operational Challenge | Proposed System Solution |
| :--- | :--- |
| **Manual Headcount & Math Calculation Errors** | Automated mathematical engine computing exact base totals, per-pax rates, custom add-ons, downpayment percentages, and balance ledgers without human error. |
| **Unmonitored Expenses & Blind Profit Margins** | Integrated Cost of Goods Sold (COGS), labor, transport, and utility expense tracking deducting directly from gross revenue to calculate true Net Profit. |
| **Double Bookings & Venue Capacity Overload** | Automated event date conflict detection and daily capacity hard-blocking (e.g. max 600 pax/day). |
| **Remote Venue Disconnectivity** | 100% Offline-First architecture running self-contained SQLite engines on local hardware with zero internet dependency. |
| **Consultation & Ordering Bottlenecks** | Self-service guided touch ordering flow reducing client consultation time from 45 minutes to under 5 minutes. |

---

## 3. Proposal Topic Breakdown for 3 Presenters

---

### 📌 PRESENTER 1: Project Scope, System Architecture & Executive Oversight

#### Core Topics to Present:
* **Dual-Platform System Architecture**:
  * **PC Desktop Workstation (`Catering_Present`)**: Executive control center for administration, master catalog setup, invoicing, kitchen operations, and financial auditing.
  * **Portable Field Kiosk (`Tablet_PWA` / APK)**: Standalone, offline client ordering terminal used during bridal fairs, food tastings, and on-site consultations.
  * **2-Way Synchronization**: Seamless data sync between field tablets and back-office computers via master Excel templates and SQLite database exports.
* **Executive Dashboard & Real-Time Business KPIs**:
  * Live monitoring of Total Gross Revenue, Total Operating Expenses, Net Profit Margins, and Active Bookings.
  * Pipeline tracking categorized by Inquiries, Confirmed Events, In-Preparation, Completed, and Cancelled bookings.
* **Capacity Governance & Scheduling Protection**:
  * Automated capacity validation preventing overbooking beyond kitchen production capacity limits.
* **Customer CRM & Loyalty Engine**:
  * Client booking history tracking with automated loyalty tiers (*Bronze, Silver, Gold, VIP*) and scheduled follow-up reminder logs.

---

### 📌 PRESENTER 2: Client Ordering Subsystem, Sales Workflows & Billing Automation

#### Core Topics to Present:
* **Guided 6-Step Client Ordering Engine**:
  * **Step 1 (Client Identification)**: Returning customer search + separated Cebu Barangay/City dropdown and street address fields.
  * **Step 2 (Event Schedule & Buffet Package)**: Touch occasion selector (*Weddings, Birthdays, Debuts, Corporate, Baptisms*) + **Package Details & Inclusions Viewer** displaying food rates and standard equipment inclusions (*chafing dishes, table skirting, servers, floral centerpieces*).
  * **Step 3 (Categorized Menu Selection)**: Structured food catalog grouped by dish types (*Beef, Pork, Chicken, Seafood, Pasta, Desserts, Beverages*) with sticky top category navigation.
  * **Step 4 (Add-ons & Equipment Upselling)**: One-tap add-on selections for high-margin items (*Whole Lechon platters, Dessert bars, Sound & Lighting rentals*).
  * **Step 5 (Billing & Legal Terms)**: Real-time deposit calculator, payment channel tracking (*Cash, GCash, Bank Transfer*), and legally binding terms acknowledgement.
  * **Step 6 (Pre-Booking Verification & Instant PDF Receipt)**: Verification summary before submission + automated offline itemized PDF receipt generation saved directly to device storage.
* **Billing, Invoicing & Notification System**:
  * Automated official commercial invoice generation (`INV-XXXX`), payment milestone tracking, and partial balance ledgers.
  * Automated booking confirmations and PDF invoices dispatched via Email (SMTP) and SMS (Semaphore API).
  * Minimum downpayment enforcement (e.g. 30%) blocking event confirmation without verified deposit.

---

### 📌 PRESENTER 3: Financial Management, Expense Tracking, AI Forecasting & Kitchen Operations

#### Core Topics to Present:
* **Cash Flow & Expense Tracking (Net Profit Calculation)**:
  * Real-time Cash Inflow vs. Outflow tracking with net liquidity balances.
  * Itemized expense recording categorized by Cost of Goods Sold (COGS), Food Ingredients, Labor/Waitstaff Wages, Fuel/Transport, Utility Overheads, and Equipment Rentals.
  * Automated formula: `Gross Revenue - Total Operating Expenses = True Net Profit`.
* **AI Intelligence & Business Forecasting**:
  * **AI Demand & Volume Forecasting**: Machine learning predictions on seasonal booking spikes, peak holiday months, and expected guest volume.
  * **Smart Ingredient & Portion Estimator**: Automated calculations predicting raw food material requirements based on pax count and selected dishes to prevent food waste.
  * **Menu Engineering Analytics**: Intelligent analysis highlighting top-selling high-margin items and underperforming dishes.
* **Kitchen Operations & Task Breakdown (Kanban Workflow)**:
  * Real-time preparation pipeline (*Pending, Cooking, Plating, Ready for Transport, Dispatched*).
  * Interactive per-dish task checklist ensuring standard recipe execution and zero missed menu items.
* **Audit Governance, Reporting & Data Privacy**:
  * Comprehensive analytics: Monthly/Annual revenue comparisons, package sales distribution, and payment method charts.
  * Complete audit logs recording actor identity, action type, timestamps, and JSON data states.
  * 100% offline data ownership with zero third-party cloud vulnerabilities and zero recurring monthly fees.

---

## 4. Complete System Functional Module Matrix

| Module | Core Functionality | Platform |
| :--- | :--- | :--- |
| **Executive Dashboard** | Real-time KPIs, Revenue, Net Profit, Capacity alerts, Recent Activity | PC Back-Office |
| **Booking & Kiosk Wizard** | 6-step guided ordering, package selection, downpayment calculation | PC + Tablet Kiosk |
| **Calendar & Scheduling** | Visual event timeline, date conflict detection, daily capacity load | PC Back-Office |
| **Menu & Package Catalog** | CRUD packages, pax price matrix, dish categories, photo management | PC + Tablet Kiosk |
| **Billing & Invoicing** | Invoice generation, downpayment enforcement, balance collection | PC + Tablet Kiosk |
| **Receipt & Notifications** | PDF receipt generation, SMTP email dispatcher, SMS gateway | PC + Tablet (PDF) |
| **Cash Flow Tracker** | Inflow/Outflow tracking, payment method breakdown, net balance | PC Back-Office |
| **Expense & COGS Manager** | Food costs, labor wages, logistics, utilities, Net Profit margin | PC Back-Office |
| **AI Demand & Forecaster** | Pax forecasting, ingredient quantity estimator, menu insights | PC Back-Office |
| **Kitchen Kanban & Checklist**| Visual preparation cards, per-dish task checklist, order dispatch | PC Back-Office |
| **Customer CRM & Loyalty** | Booking history, automated loyalty tiers (Bronze to VIP), follow-ups | PC + Tablet Kiosk |
| **Reports & Financial Analytics**| Revenue charts, package sales breakdown, PDF/Excel export | PC Back-Office |
| **Security, Audit & Backups** | Full change audit logs, 1-click DB backup/restore, Excel data sync | PC + Tablet Kiosk |

---

## 5. Technical Specifications & Architecture

* **Back-Office PC System**: Native Python/Qt Desktop Application compiled to Windows executable (`.exe`).
* **Tablet Kiosk App**: HTML5 / JavaScript / CSS + Client-Side SQLite WASM + Standalone Android APK (`.apk`, 7.1 MB).
* **Offline Capability**: 100% self-contained database engine; zero internet connection required for ordering, querying, or receipt printing.
* **Image Engine**: Full HD $1920 	imes 1440$ bicubic image processor with WebP/JPEG compression.
* **Data Security & Privacy**: Stored locally on physical business hardware; zero third-party cloud data leaks or monthly subscription fees.
