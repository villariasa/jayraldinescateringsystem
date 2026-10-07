# New Client Changes — Test Checklist

> **Companion to:** `NEW_CLIENT_CHANGES_PLAN.md`
> **Date:** 2026-10-07
> **Apps:** `Catering_Present` (Desktop, PySide6 + SQLite) and `Tablet_PWA` (kiosk PWA + sync server)
> **How to use:** Run each test case in order. Mark **PASS / FAIL**. "Expected" is the behavior *after* the planned changes are applied. Where a case says *(regression)*, it must still work exactly as before.

### Pre-test setup (do this FIRST)
- [ ] **Back up both databases** before testing any migration (desktop `catering.db` + its backup, tablet browser DB + backend SQLite).
- [ ] Record the current counts before upgrade: number of bookings, customers, menu items, packages, expenses. (Used in §0 below to prove data survived.)
- [ ] Note the desktop app version and tablet app version under test.

---

## 0. Data integrity after migration (run immediately after upgrading an EXISTING database)

| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 0.1 | Upgrade an existing (populated) desktop DB, then open the app | App opens with no error; all pre-upgrade bookings, customers, menu items, packages, expenses are present and match the counts recorded in setup | ☐ |
| 0.2 | Open an old booking created before the upgrade | It opens; package, dishes, pax, totals, payment status all unchanged | ☐ |
| 0.3 | Check the new columns exist on old rows | Old bookings show empty/default Pickup time, Drop-off time, No. of sets, and a sensible default Order Type (not an error) | ☐ |
| 0.4 | Tablet: upgrade an existing tablet, open the kiosk | Existing local orders/bookings still present; no blank/reset database | ☐ |
| 0.5 | Tablet: run a LAN sync after upgrade | Sync completes; no new-column errors; records still flow tablet↔desktop | ☐ |
| 0.6 | Re-run the upgrade twice (restart app twice) | No duplicate columns/tables, no crash — migration is idempotent | ☐ |

---

## 1. Admin password bug (Request #4)

### Desktop
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 1.1 | Change the admin password to a new value (e.g. `CateringPass#2026`). Log out. | Password change saved | ☐ |
| 1.2 | Try to log in as `admin` with the OLD/default password `admin` | **Login REJECTED** (this is the bug being fixed) | ☐ |
| 1.3 | Try `admin123`, `Admin123!`, `Admin123` | All **REJECTED** | ☐ |
| 1.4 | Log in with the NEW password `CateringPass#2026` | **Accepted** | ☐ |
| 1.5 | After the failed attempts in 1.2–1.3, log in again with the new password | Still works — i.e. the failed `admin` attempts did **not** reset/overwrite the password | ☐ |
| 1.6 | *(recovery path)* Run `main.py --reset-admin`, set a password, log in with it | Works — intended recovery still functions | ☐ |
| 1.7 | *(regression)* Normal valid login for a non-admin user | Works as before | ☐ |

### Tablet
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 1.8 | Set a custom admin passcode in tablet settings, then lock/unlock with it | Accepted | ☐ |
| 1.9 | Try unlocking with `12345678` after a custom passcode is set | **Rejected** | ☐ |
| 1.10 | On a fresh/cleared tablet (no passcode set), confirm it does not silently accept `12345678` | Forces an explicit passcode setup (per plan) | ☐ |

---

## 2. Double-booking same day (Request #5)

### Desktop
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 2.1 | Create a booking: Customer **Juan Dela Cruz**, date **2026-11-15**, time **2:00 PM** (afternoon), same occasion. Save. | Booking #1 saved with its own ref | ☐ |
| 2.2 | Create a SECOND booking: same customer **Juan Dela Cruz**, same date **2026-11-15**, time **6:00 PM** (evening), same occasion. Save. | **A NEW separate booking #2 is created** (different ref) — this is the fix | ☐ |
| 2.3 | Open the calendar/booking list for 2026-11-15 | **Both** bookings appear (afternoon + evening) | ☐ |
| 2.4 | Create a third booking identical to #1 (same customer, date, AND time) | Behaves per client decision: either blocked as a true duplicate, or allowed — confirm matches the agreed rule | ☐ |
| 2.5 | *(regression)* Two bookings, same date, DIFFERENT customers | Both save (as before) | ☐ |
| 2.6 | Edit booking #2's time and save | Saves without collapsing into #1 | ☐ |

### Tablet
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 2.7 | On tablet, create two same-day orders for the same customer (different times), then sync to desktop | Both orders exist on tablet AND both appear on desktop after sync | ☐ |

---

## 3. New fields: Pickup time, Drop-off time, Number of sets (Request #6)

### Desktop
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 3.1 | Create a booking; set Pickup time, Drop-off time, and No. of sets | All three fields are visible and editable in the booking form | ☐ |
| 3.2 | Save, reopen the booking | The three values persist exactly as entered | ☐ |
| 3.3 | Print / preview the order slip or booking agreement | The three new values appear on the printout (confirm with client where they should show) | ☐ |
| 3.4 | Edit the three values and save | Updated values persist | ☐ |

### Tablet
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 3.5 | In the kiosk wizard, enter Pickup time, Drop-off time, No. of sets | Fields present and editable | ☐ |
| 3.6 | Confirm the order, then sync to desktop | Values saved on tablet AND carried to desktop via sync | ☐ |

---

## 4. New order flow — Order Type branching (Requests #1 & #2)

> Flow under test (from `new-plan-1.jpeg`): MAIN → SELECT ORDER TYPE → Food Tray / Packages / Food Set.

### Routing
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 4.1 | Start a new order; the order-type screen appears | Three choices visible: **Food Tray**, **Packages**, **Food Set** | ☐ |
| 4.2 | Choose **Food Tray** | Goes **directly to the MENU** — the Packages step is **skipped** | ☐ |
| 4.3 | Choose **Packages** | Shows package selection, then the menu (current behavior) | ☐ |
| 4.4 | Choose **Food Set** | Shows predefined Sets, then asks **"How many sets?"** | ☐ |

### Food Set details
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 4.5 | On the Food Set screen, confirm the sets shown | **Set A–E** appear, each card listing its dishes (per `food-order-sample.jpeg`) | ☐ |
| 4.6 | Verify Set A dishes | Humba, Lumpia Shanghai, Chopsuey, Bam-i | ☐ |
| 4.7 | Verify Set B dishes | Pork Steak, Chicken Cordon Bleu, Bam-i, Fish Fillet w/ lemon sauce | ☐ |
| 4.8 | Verify Set C dishes | Beef Kalderita, Buttered Chicken, Fish Fillet w/ tartar sauce, Pancit Guisado | ☐ |
| 4.9 | Verify Set D dishes | Pork Spareribs, Crab Relleno, Bam-i, Korean Chicken | ☐ |
| 4.10 | Verify Set E dishes | Beef Steak, Fried Chicken, Spaghetti, Lumpia Shanghai | ☐ |
| 4.11 | Choose **multiple different sets** in one order (e.g. Set A + Set C) | Both are added as separate set lines | ☐ |
| 4.12 | Choose the **same set more than once** (e.g. 2× Set A) | Quantity 2 of Set A is accepted (repeatable sets) | ☐ |
| 4.13 | Set a quantity per set (e.g. 2× Set A, 1× Set C) | Totals reflect each set × its quantity | ☐ |
| 4.14 | **Customize** a chosen set (swap/choose dishes per the rules) | Customization saved for that specific set line only | ☐ |
| 4.15 | Confirm/save the Food Set order | Saves with all sets, quantities, and customizations intact | ☐ |
| 4.16 | Reopen the saved Food Set order | All sets/quantities/customizations reload correctly | ☐ |
| 4.17 | Print the order for a Food Set booking | Printout lists each set, its quantity, and its dishes | ☐ |

### Both apps + regression
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 4.18 | Repeat 4.1–4.17 on **both** desktop and tablet | Same behavior on both | ☐ |
| 4.19 | Sync a tablet-created Food Set order to desktop | All sets/quantities/customizations arrive intact on desktop | ☐ |
| 4.20 | *(regression)* Open an OLD booking made before this feature | Still displays correctly (no sets, uses old package/dish data) | ☐ |
| 4.21 | *(regression)* Create a plain Packages order the old way | Works exactly as before | ☐ |
| 4.22 | Confirm the event type (Wedding/Birthday/etc.) is still captured separately from Order Type | Both are recorded (per plan §0.2 decision) | ☐ |

---

## 5. Ledger date filter (Request #3)

### Desktop
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 5.1 | Open the Billing page → **Ledger** tab | A date filter with **Today / This Week / This Month / This Year** is present | ☐ |
| 5.2 | Select **Today** | Ledger shows only today's transactions | ☐ |
| 5.3 | Select **This Week** | Shows only this week's (correct week boundaries) | ☐ |
| 5.4 | Select **This Month** | Shows only this month's | ☐ |
| 5.5 | Select **This Year** | Shows only this year's | ☐ |
| 5.6 | Cross-check a known-dated payment against each filter | It appears only in the periods that contain its date | ☐ |
| 5.7 | Switch filters back and forth | Table refreshes correctly each time; no stale rows | ☐ |
| 5.8 | *(regression)* Cash Flow and Reports period filters | Still work as before | ☐ |

---

## 6. Expense categories — rename + add custom (Request #7)

### Desktop
| # | Steps | Expected | P/F |
|---|-------|----------|-----|
| 6.1 | Expenses page → **Manage Categories** → rename a category (e.g. "Labor" → "Staff Wages") | Rename succeeds; existing expenses under "Labor" now show "Staff Wages" | ☐ |
| 6.2 | Add a new custom category (e.g. "Marketing") | Appears in the category list | ☐ |
| 6.3 | Add an expense and pick the new "Marketing" category | Saves under Marketing | ☐ |
| 6.4 | Use the add-expense **"+ New"** quick-add to create a category inline | Category created and selected | ☐ |
| 6.5 | Try to delete the default **"Other"** category | Blocked (protected) | ☐ |
| 6.6 | Delete a deletable category with existing expenses | Those expenses reassign to "Other" (or chosen target); none lost | ☐ |
| 6.7 | Category filter dropdown on the expenses list | Reflects the renamed/added categories | ☐ |

---

## 7. Final sign-off
- [ ] All PASS, or every FAIL logged with steps-to-reproduce.
- [ ] Data-integrity section (§0) fully PASS on a real populated database.
- [ ] Tablet↔desktop sync verified for every new field/feature (4.19, 2.7, 3.6, 0.5).
- [ ] Backups confirmed before and kept after testing.
