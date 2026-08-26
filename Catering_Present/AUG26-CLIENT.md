Implement the following final client-requested changes in the **Jayraldine’s Catering System**. The previous issues are already working correctly, so **do not unnecessarily modify existing working features**. Focus only on the changes below and make sure existing data and functionality are not broken.

## 1. Deleted or Cancelled Orders Must Not Remain in Billing

Currently, when an order is deleted or cancelled, its billing amount may remain in the Billing/Ledger records.

Fix this properly:

* When an order is **deleted**, all billing-related records connected to that order must also be removed or properly updated.
* The amount must **not remain as unpaid, paid, or outstanding** in Billing or Ledger after the order is deleted.
* If an order is **cancelled**, its financial status must be handled properly so that it does not incorrectly appear as an active unpaid billing.
* Make sure deleting an order does not leave orphan billing records or incorrect balances.
* Test this carefully because the client may cancel an order, and the system must not show the cancelled order amount as still unpaid.

**Important:** Maintain proper database relationships and transaction handling so the order, billing, payment, and ledger records remain consistent.

---

## 2. Add Receipt Printing for Orders and Payments

Add a printable receipt feature.

The receipt should clearly display relevant information such as:

* Customer name
* Order/Event details
* Order total amount
* Additional charges
* Discounts, if applicable
* Down payment amount
* Other payments
* Remaining balance
* Payment date
* Payment status

The system should allow the user to print a receipt after a payment or down payment is recorded.

The receipt should clearly show the financial breakdown so the customer and the catering owner can understand the amount paid and the remaining balance.

---

## 3. Improve Additional Charges / Additional Items

Add a clearer **Additional Charges / Additional Items** section inside the order details.

The user must be able to add additional charges to an existing order, for example:

* ₱300 additional charge for changing the menu
* Additional lechon
* Additional food/menu items
* Extra services
* Other custom charges

Each additional item must include:

* Description/Reason
* Amount
* Date added
* User who added it, if available

These additional charges must:

* Be clearly displayed in the order details.
* Be included in the total billing amount.
* Be visible in the Billing and Ledger records.
* Allow the user to review exactly why the order total increased.

For example:

**Original Order Total:** ₱10,000
**Additional Charge:** Menu Change – ₱300
**Additional Item:** Lechon – ₱2,500
**Updated Total:** ₱12,800

The additional charges must remain visible as separate entries and must not simply merge into the total without any explanation.

---

## 4. Fix Incorrect Unpaid Ledger Entry After Import/Sync

There is an issue where an old payment record from the previous month can appear as:

**₱0 Unpaid**

in the Ledger after importing or syncing data.

Example:

* On Uncle's laptop, the customer was not yet marked as paid.
* On another PC, the customer is already marked as paid.
* After importing/syncing, the Ledger may incorrectly create or retain a **₱0 Unpaid** entry.

Fix the import/sync logic so that:

* The latest and correct payment status is preserved.
* A customer who is already fully paid must not have a ₱0 unpaid record.
* Duplicate or conflicting ledger entries must not be created.
* Payment status must be reconciled correctly during import.
* Existing ledger entries should be updated instead of blindly creating duplicate records when they represent the same transaction/order.

Use proper unique identifiers and conflict handling for imported payment and ledger records.

---

## 5. Export: Add Month Selection

Currently, export should allow the user to choose which month to export.

Add a month/year selection before exporting data.

The user should be able to select:

* Month
* Year

Then export only the relevant records for that selected month.

For example:

**Export Data for:** August 2026

The export should only contain records within the selected month and year.

If applicable, apply this selection consistently to reports and export functions.

---

## 6. Record and Display Payment Dates

Add proper payment date tracking.

For down payments, store:

* Date when the customer paid the down payment
* Amount paid
* Payment status

For succeeding/full payments, store:

* Date when each payment was made
* Amount paid
* Payment type, if applicable

Display the payment dates in the Ledger.

Example:

| Date         | Customer   | Transaction            | Amount  | Status |
| ------------ | ---------- | ---------------------- | ------- | ------ |
| Aug 10, 2026 | Customer A | Down Payment           | ₱5,000  | Paid   |
| Aug 15, 2026 | Customer A | Full/Remaining Payment | ₱10,000 | Paid   |

Do not overwrite the original down payment date when another payment is made. Each payment should have its own payment record and date.

---

## 7. Improve Notifications and Daily Activity Logging — IMPORTANT

This is one of the most important requests.

Add a more detailed notification and activity logging system.

The system should track important actions such as:

* Who added an order
* Who edited an order
* Who deleted or cancelled an order
* Who added an additional charge
* Who added a down payment
* Who recorded a payment
* Who approved a payment, if approval exists
* Who approved or rejected an action
* Who changed an order status

Each notification/log should include:

* User/staff name
* Action performed
* Related customer name
* Related order/event
* Amount, when applicable
* Date and time

Example notifications:

* **John added a new order for Maria Santos – ₱15,000**
* **John recorded a down payment from Maria Santos – ₱5,000**
* **John added an additional charge: Menu Change – ₱300**
* **John recorded a full payment from Maria Santos – ₱10,000**
* **John approved the payment of Maria Santos**
* **John cancelled the order of Maria Santos**

Create a proper **Daily Activity Report / Daily Audit Log**.

The purpose is so Uncle can see exactly what was done during the day.

The daily report should include:

* Date
* Time
* User
* Action
* Customer
* Order/Event
* Amount, if applicable
* Additional details

Example:

**DAILY ACTIVITY REPORT — August 26, 2026**

* 9:15 AM — John added an order for Customer A
* 10:30 AM — John recorded a ₱5,000 down payment from Customer B
* 11:20 AM — John added a ₱300 menu change charge to Customer C
* 2:00 PM — John recorded a ₱8,000 payment from Customer D
* 3:15 PM — John cancelled the order of Customer E

The system must allow the daily activity report/log to be **exported**.

The exported daily report will be sent to Uncle so he can review what actions were performed that day.

Add a date selector so the user can export:

* Today's activity
* A specific date
* If practical, a custom date range

This feature is very important because the owner needs a daily summary of:

* Who added orders
* Who made down payments
* Who made payments
* Who approved actions
* What additional charges were added
* What staff/users did during the day

---

## Important Development Rules

* Do not break the existing working features.
* Preserve existing orders, customers, billing, payment, and ledger data.
* Make database changes through proper migrations where possible.
* Use transactions for financial operations to prevent partial or inconsistent records.
* Prevent duplicate payment and ledger entries.
* Ensure deleting or cancelling an order does not leave incorrect financial balances.
* Ensure imported data uses proper conflict detection and synchronization.
* Test all calculations carefully.
* All totals, balances, additional charges, down payments, and payments must remain accurate.
* Keep the UI consistent with the existing application design.

Before considering the task complete, test these scenarios:

1. Create an order → add additional charge → check billing total.
2. Add down payment → verify payment date in Ledger.
3. Add full payment → verify remaining balance and payment history.
4. Delete an order → confirm its billing amount does not remain.
5. Cancel an order → confirm no incorrect outstanding balance remains.
6. Import an older version of data → confirm a fully paid customer does not become ₱0 unpaid.
7. Export a selected month → confirm only that month’s records are included.
8. Perform several actions in one day → export the daily activity report and verify all actions are included.
9. Confirm each activity shows the correct user, action, customer, amount, date, and time.
10. Confirm existing working functionality is not broken.


## CRITICAL: Smart Data Import and Billing/Payment Conflict Resolution

This is a **critical feature** and must be handled carefully.

The system has multiple devices, such as a PC and a laptop. These devices may have the same customer/order records but different payment and billing states because one device may contain newer transactions.

### Example Problem

A customer may have the following situation:

**Laptop database:**

* Order Total: ₱10,000
* Payment Status: Unpaid
* Remaining Balance: ₱10,000

But on the **PC**, the same customer/order may already have:

* Order Total: ₱10,000
* Down Payment: ₱5,000
* Payment Status: Partial
* Remaining Balance: ₱5,000

Or the PC may already have:

* Total: ₱10,000
* Paid: ₱10,000
* Status: Paid
* Remaining Balance: ₱0

When importing **ALL DATA from the laptop into the PC**, the old **Unpaid** billing data from the laptop must **NOT overwrite** the newer **Partial or Paid** status on the PC.

### Required Import Logic

The import system must intelligently merge data.

It must:

* Identify the same customer/order using a stable unique identifier.
* Compare records from the imported database and the existing database.
* Detect which record contains the newest financial information.
* Preserve valid payments already recorded on the destination PC.
* Never downgrade a payment status from **Paid → Partial → Unpaid** because an older database is imported.
* Never remove an existing payment just because the imported database does not contain that payment.
* Merge missing payments from the imported database when they are legitimate new transactions.
* Prevent duplicate payments when the same transaction already exists on both devices.
* Recalculate the billing status after the import based on the complete payment history.

### Payment Status Priority

Do not simply trust the imported billing status text.

The system should calculate the actual financial status based on:

**Total Order Amount - Total Valid Payments**

Then determine:

* If remaining balance = total amount → **Unpaid**
* If some amount has been paid but balance remains → **Partial**
* If total valid payments >= total amount → **Paid**

Example:

| Device | Imported/Existing Status |   Total | Payments |
| ------ | ------------------------ | ------: | -------: |
| Laptop | Unpaid                   | ₱10,000 |       ₱0 |
| PC     | Partial                  | ₱10,000 |   ₱5,000 |

After import:

**Result: Partial — ₱5,000 Paid — ₱5,000 Remaining**

Another example:

| Device | Status |   Total | Payments |
| ------ | ------ | ------: | -------: |
| Laptop | Unpaid | ₱10,000 |       ₱0 |
| PC     | Paid   | ₱10,000 |  ₱10,000 |

After import:

**Result: Paid — ₱10,000 Paid — ₱0 Remaining**

The imported **Unpaid** status must not overwrite the existing **Paid** transaction.

### Important: Payments Must Be Merged, Not Replaced

When importing all data:

* Do NOT delete all existing billing/payment data and replace it with imported data.
* Do NOT blindly overwrite the destination database.
* Do NOT allow older Unpaid records to remove newer Partial or Paid records.

Instead, merge the transaction history.

The final billing result must be calculated using the combined valid transaction/payment records after duplicate detection.

### Import Timestamp and Conflict Detection

Each important record should contain:

* `created_at`
* `updated_at`
* Unique record ID
* Device/source identifier if necessary

During import, compare records based on:

1. Stable unique ID
2. Payment transaction identity
3. Updated timestamp
4. Existing payment history

If the imported record is older than the existing record, it must not overwrite newer financial information.

### Critical Import Test

Test this exact scenario:

#### Laptop Database

Customer A:

* Order Total: ₱20,000
* Status: Unpaid
* Payments: ₱0

#### PC Database

Same Customer A and same Order:

* Order Total: ₱20,000
* Down Payment: ₱10,000
* Status: Partial
* Remaining: ₱10,000

Then import **ALL DATA from Laptop into PC**.

Expected result:

* Customer A must remain **Partial**
* ₱10,000 payment must remain
* Remaining balance must remain ₱10,000
* Laptop's old Unpaid status must NOT overwrite the PC

Second test:

#### Laptop Database

Customer B:

* Order Total: ₱15,000
* Status: Unpaid

#### PC Database

Same Customer B:

* Order Total: ₱15,000
* Paid: ₱15,000
* Status: Paid

After importing Laptop → PC:

Expected result:

* Customer B must remain **Paid**
* Existing payment must not disappear
* No ₱0 Unpaid ledger entry should be created
* Remaining balance must remain ₱0

### Final Rule

**Importing all data must never downgrade or erase valid financial progress that already exists on the destination device.**

The import process must intelligently merge:

* Orders
* Billing
* Payments
* Down payments
* Additional charges
* Ledger records

The final billing status must always be based on the actual latest valid transaction data, not simply on whichever database was imported last.
