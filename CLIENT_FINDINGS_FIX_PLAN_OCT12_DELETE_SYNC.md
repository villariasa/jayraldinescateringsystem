# Follow-up Finding — Deletions on Tablet don't propagate to Desktop/PC

**Date:** 2026-10-12
**Companion to:** `CLIENT_FINDINGS_FIX_PLAN_OCT12.md`
**Source of truth for tablet code:** `Tablet_PWA/frontend/js/` (mirror edits to `Tablet_PWA/backend/dist/.../frontend/js/` and `Tablet_Android_APK/app/src/main/assets/js/`, or rebuild).

### Complaint
> "The client deletes entries on the tablet — I don't know what they delete, whether it's a booking menu or what — but it did not delete on the PC / desktop app."

### One-line root cause
The tablet↔desktop sync is **additive / upsert-only**. A deletion channel exists for **exactly one thing — whole bookings** (via a localStorage tombstone queue). **Every other delete is invisible on the wire**, so the record lives on forever on the PC.

---

## What actually happens (confirmed)

All tablet deletes are **hard deletes** in `Tablet_PWA/frontend/js/repository.js`, but only `deleteBooking` records a tombstone for sync:

| Tablet delete | file:line | Tombstone recorded? | Reaches desktop? |
|---|---|---|---|
| `deleteBooking` | `repository.js:1092-1116` | ✅ localStorage queue `jayraldines_deleted_booking_refs` (`:1097-1104`) | ✅ yes |
| `deleteCustomer` | `repository.js:106-110` | ❌ none | ❌ no |
| `deletePackage` | `repository.js:345-351` | ❌ none | ❌ no |
| `deleteMenuItem` | `repository.js:526-531` | ❌ none | ❌ no |
| `deleteOccasion` | `repository.js:1238-1241` | ❌ none | ❌ no |

Because `getPendingSyncRecords` (`repository.js:974-1011`) only ever does `SELECT * FROM …` for rows that **still exist**, a hard-deleted customer/package/menu/occasion simply **vanishes from the tablet and is never mentioned to the server**. The server has no way to know it was deleted.

There is **no expense concept on the tablet** (grep for "expense" in `Tablet_PWA/frontend/js/` returns nothing) — expenses are desktop-only, so "expense" is not what the client deleted.

### The single existing delete channel (bookings) — for reference / the pattern to copy
- Transport: `api.js performLanSync` sends `deleted_booking_refs` (`api.js:1089,1100`); clears the queue on `deleted_booking_refs_handled` (`api.js:1103-1107`).
- Server: `db_sync_server.py perform_server_sync` processes them at `:1828-1858` — deletes `booking_menu_items`/`booking_additional_charges`/`invoices`/`bookings` and writes a `deleted_records` tombstone (`:1839-1854`); resurrection guard at `:1870-1873`; response flags `:2383-2384`.
- Reverse (desktop→tablet): server returns merged `deleted_booking_refs` (`:2383`); tablet `purgeDeletedBookings` (`api.js:1130-1131` → `repository.js:1243-1255`) hard-deletes them locally.

So the whole mechanism to copy already exists — it is just wired for bookings only.

---

## Second, related hole — removing a child from an ALREADY-SYNCED booking

Even for bookings, the server's child-row importer is gated by **`if not existing_b:` at `db_sync_server.py:1877`**. The re-insert of `menu_items` / `additional_charges` (`:1969-1994+`) runs **only when the booking doesn't yet exist on the server**. So if the tablet **edits an already-synced booking** and removes a menu item or an add-on, the booking row "syncs" but the removed child is **never deleted on the PC**. If the client's "deleted entry" was a dish or add-on inside an existing booking, this is the exact cause — not the table-level deletes above.

---

## Third, related hole — reverse direction (desktop delete → tablet orphan)

Master-data pull does DELETE-all-then-reinsert (`repository.js:1118-1130` → `sqlite.js:500-632`), but every block is guarded by `length > 0` (`repository.js:1122`, `sqlite.js:504/533/598`). If the desktop deletes the **last** package or menu item (server sends an empty list), the guard **skips the DELETE** and the tablet keeps an orphan. Occasions are INSERT-OR-REPLACE only (`repository.js:1182-1195`) and never reconciled, so desktop occasion deletes never reach the tablet either.

---

## Fix plan

### A. Tablet → Desktop deletes for customers / packages / menu items / occasions
Mirror the booking tombstone pattern exactly:

1. **Record the tombstone on delete.** In `deleteCustomer` (`repository.js:106-110`), `deletePackage` (`:345-351`), `deleteMenuItem` (`:526-531`), `deleteOccasion` (`:1238-1241`), before/after the hard DELETE, push the record's id into a localStorage queue (one per type), same shape as `deleteBooking` at `:1097-1104` (`jayraldines_deleted_customer_ids`, `…_package_ids`, `…_menu_item_ids`, `…_occasion_names`).
2. **Send them on the wire.** Add `deleted_customer_ids` / `deleted_package_ids` / `deleted_menu_item_ids` / `deleted_occasion_names` to the `performLanSync` payload (`api.js:1086-1101`), and clear each on its handled-flag (pattern at `api.js:1103-1107`).
3. **Process them on the server.** Add branches alongside `db_sync_server.py:1828-1858`: for each incoming id, delete the row (and its dependents — e.g. a package also clears `package_items`, `entity_images`) and write a `deleted_records` tombstone with a new `dr_table` value per type.
4. **Extend the resurrection guard.** `db_sync_server.py:1870-1873` is booking-specific; add equivalent guards so a tombstoned customer/package/menu/occasion is not re-created by a later upsert from another device.
5. **Return + purge on the tablet (reverse propagation).** Echo the handled ids back (pattern at `:2383-2384`) and add tablet-side purge calls like `purgeDeletedBookings` so a delete done on one tablet/PC also clears other tablets.

> **Decision needed — referential safety.** Deleting a package or menu item that is referenced by existing bookings can orphan those bookings' line items. Before hard-deleting, decide: (a) block the delete if referenced, (b) soft-delete / deactivate (set `is_active=0`) instead of hard delete, or (c) cascade. Recommend **soft-delete/deactivate for packages & menu items** (they're catalog data referenced historically) and hard-delete only for unreferenced customers/occasions. This also sidesteps most resurrection-guard complexity. Confirm with the client.

### B. Child-row removal on already-synced bookings
Change the `if not existing_b:` gate at `db_sync_server.py:1877` so that for an **existing** booking the server **reconciles** children instead of ignoring them: delete `booking_menu_items` / `booking_additional_charges` rows that are no longer in the incoming payload, then upsert the rest. (This overlaps with Finding 1 in the companion plan, which already calls for moving add-on ingestion out of the `if not existing_b:` branch — do both together.)

### C. Reverse-direction orphans (desktop delete → tablet)
1. Remove or rework the `length > 0` guards (`repository.js:1122`, `sqlite.js:504/533/598`) so an **empty** server list still clears the corresponding tablet table (distinguish "nothing to sync this round" from "the authoritative set is now empty" — e.g. a server flag indicating a full authoritative snapshot).
2. Reconcile occasions like other master data (`repository.js:1182-1195`) instead of INSERT-OR-REPLACE only, so desktop occasion deletes propagate.

---

## First step before coding — identify WHAT the client actually deleted
The client "doesn't know what they deleted." Narrow it fast, because the fix differs:
- **A dish/add-on inside an existing booking** → Fix **B** (the `if not existing_b:` gate). Most likely culprit given the phrasing "booking menu."
- **A whole booking** → should already work; if it didn't, check the localStorage queue (`jayraldines_deleted_booking_refs`) was actually sent and the sync completed.
- **A customer / package / menu item / occasion** → Fix **A**.

Ask the client, or reproduce: delete each kind of entry on the tablet, sync, and watch which one survives on the PC. Then prioritize that fix first.

## Verify (once fixed)
For each entry type: create on tablet → sync (confirm present on PC) → delete on tablet → sync → **confirm it's gone on the PC**. Reverse: delete on PC → sync → confirm gone on tablet (including the "delete the last row" edge case). For bookings: remove one dish from an already-synced booking → sync → confirm that dish is gone on the PC while the booking remains.
