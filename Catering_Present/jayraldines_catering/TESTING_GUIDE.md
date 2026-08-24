# 📋 Jayraldine's Catering System — Manual Testing & Verification Guide

This document provides step-by-step instructions to verify that payment calculations, down payments, remaining balances, order statuses, data exports, and diagnostic reports are operating correctly.

---

## 🧪 Test Scenario 1: Zero Down Payment Booking (Unpaid Status)

**Goal:** Ensure a booking with ₱0 down payment is **NOT** automatically marked as "Fully Paid".

1. Open the application (`./run.sh` or executable).
2. Click **+ New Booking** on the Dashboard or Bookings page.
3. Fill in customer details (e.g. *Juan Dela Cruz*, `09171234567`, Cebu City).
4. Select an event date and occasion (e.g. Birthday, 100 pax).
5. Set the Total Amount to **₱50,000.00**.
6. Set Down Payment / Amount Paid to **₱0.00**.
7. Save the booking.

### Expected Results:
* [x] **Status:** Displays `Unpaid` (or `Pending`).
* [x] **Amount Paid:** Displays **₱0.00**.
* [x] **Remaining Balance:** Displays **₱50,000.00** (Full amount due).
* [x] **Billing / Invoices Page:** Shows Invoice status as `Unpaid` with ₱50,000.00 balance due.

---

## 🧪 Test Scenario 2: Partial Down Payment Booking (Partial Status)

**Goal:** Verify correct calculation of `Total Amount - Down Payment = Remaining Balance`.

1. Click **+ New Booking**.
2. Enter details (e.g. *Maria Santos*, `09189876543`, Mandaue City).
3. Set Total Amount to **₱100,000.00**.
4. Enter a Down Payment of **₱30,000.00** (via GCash or Cash).
5. Save the booking.

### Expected Results:
* [x] **Status:** Displays `Partial` (or `Pending`).
* [x] **Amount Paid:** Displays **₱30,000.00**.
* [x] **Remaining Balance:** Displays **₱70,000.00** (`₱100,000 - ₱30,000`).

---

## 🧪 Test Scenario 3: Flexible Payment on Booking Confirmation

**Goal:** Verify that upon approving/confirming a booking, you can choose to record no payment, enter a custom down payment amount (or use 25%/50% preset buttons), or mark as fully paid.

1. Select a pending booking (e.g. Total Amount: ₱100,000.00).
2. Click **Approve / Confirm Booking**.
3. Observe the payment options in the approval modal:
   * **Option A:** `No payment received today` -> Confirms booking, balance remains ₱100,000.00.
   * **Option B:** `Record Down Payment / Custom Amount` -> Enables typing any custom amount (or click `[25% DP]` / `[50% DP]` preset buttons).
   * **Option C:** `Mark as FULLY PAID` -> Automatically fills the remaining ₱100,000.00 balance.
4. Select **Option B** (`Record Down Payment`), click `[50% DP]` (sets amount to ₱50,000.00), choose Payment Method (e.g. GCash), and click **Confirm & Approve Booking**.

### Expected Results:
* [x] **Status:** Booking status changes to `CONFIRMED`.
* [x] **Invoice Status:** Changes to `Partial`.
* [x] **Amount Paid:** Shows **₱50,000.00**.
* [x] **Remaining Balance:** Shows **₱50,000.00**.

---

## 🧪 Test Scenario 4: Adding an Additional Payment / Instalment

**Goal:** Verify that subsequent payments add up to update the balance dynamically.

1. Open the **Billings & Invoices** page (or click *Record Payment* on the booking).
2. Find Maria Santos's invoice (Balance: ₱70,000.00).
3. Add a payment of **₱40,000.00**.
4. Save the payment.

### Expected Results:
* [x] **Total Amount Paid:** Updates from ₱30,000.00 to **₱70,000.00** (`₱30,000 + ₱40,000`).
* [x] **Remaining Balance:** Updates from ₱70,000.00 to **₱30,000.00** (`₱100,000 - ₱70,000`).
* [x] **Status:** Remains `Partial` (since ₱30,000 is still unpaid).

---

## 🧪 Test Scenario 5: Full Payment Completion

**Goal:** Verify an order transitions to "Fully Paid" **ONLY** when Total Paid >= Total Amount.

1. Add the final payment of **₱30,000.00** to Maria Santos's booking.
2. Save the payment.

### Expected Results:
* [x] **Total Amount Paid:** Displays **₱100,000.00**.
* [x] **Remaining Balance:** Displays **₱0.00**.
* [x] **Status:** Automatically transitions to **`Fully Paid`** (or `Paid`).

---

## 🧪 Test Scenario 6: Bookings & Invoices Data Export (CSV/Excel)

**Goal:** Ensure exported files contain full customer contact, venue, occasion, time, and balance columns without missing or blank data.

1. Go to the **Bookings** page and click the **Export** button (or click **Export Report** on the Dashboard).
2. Choose **Bookings & Orders Directory**, select **CSV** or **Excel** format, and save the file.
3. Open the downloaded file in Excel or a text reader.

### Expected Results:
* [x] **Contact Number:** Populated with phone numbers (Column C).
* [x] **Venue / Location:** Populated with venue name (Column F).
* [x] **Occasion:** Populated with event type e.g. Wedding/Birthday (Column G).
* [x] **Event Time:** Populated with event time (Column E).
* [x] **Down Paid (₱):** Shows correct amount paid (Column J).
* [x] **Balance (₱):** Shows correct remaining balance (Column K).
* [x] **Payment Mode:** Shows Cash, GCash, Bank Transfer, etc. (Column L).

---

## 🧪 Test Scenario 7: Remote Support Diagnostic Report

**Goal:** Verify system diagnostic export for troubleshooting laptop compatibility.

1. Go to **Settings** -> Click **Export Diagnostic Report** (or run diagnostic from top menu).
2. Check your **Desktop**. A file named `Jayraldines_Diagnostic_Report_YYYYMMDD_HHMMSS.txt` will be created.
3. Open the file and verify it contains:
   * System & OS Architecture (e.g. Windows 11 x64)
   * Python, PySide6, and Qt versions
   * `Qt6Charts.dll` presence status
   * Database table record counts
   * Recent application logs

---

## Summary Checklist

| Test Item | Pass Criteria |
|-----------|---------------|
| **Zero Down Payment** | Shows `Unpaid` & Full Balance |
| **Partial Down Payment** | `Total - Down Payment = Balance` |
| **Approval Checkbox** | Unchecked by default; preserves balance |
| **Payment Recalculation** | Sums all payment records accurately |
| **Fully Paid Transition** | Triggers ONLY when Balance = ₱0.00 |
| **Export Data** | All columns (Contact, Venue, Balance) populated |
