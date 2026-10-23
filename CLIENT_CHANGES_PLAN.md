# Client Changes: Downpayment/On-Process Billing (Desktop) + Tablet Wizard Rework

## Context

The client (catering business) requested:
1. **Desktop** — a true "Downpayment" metric: money paid on bookings *not yet fully paid*. Once a booking is fully paid, its downpayment amount moves into revenue/Total Received (e.g. 20k booking, 10k paid → downpayment 10k, revenue 0; fully paid → downpayment 0, revenue 20k).
2. **Billing** — a new "On Process" category (payment/order being processed, not yet counted as received) with a new 5-card header: **Down Payment, Unpaid Balance, On Process, Total Received, Active Events** (dropping "Total (received+unpaid)").
3. **Booking** — a manual "ON PROCESS" flag staff can toggle, filterable in Billing (user confirmed: a NEW manual flag, not reusing payment-verification).
4. **Tablet** — move Terms & Conditions from before the wizard to the end; add a "How did you hear about us?" survey as the final step (stored, synced, shown on desktop, plus a report chart); make the package-inclusions (Menu) step user-friendly via tap-to-swap + visible quotas + selections tray (user confirmed approach).

**Key facts from exploration:**
- Desktop app = `Catering_Present/jayraldines_catering/` (PySide6, dual SQLite/Postgres via `utils/db.py`). `Catering/` is a STALE copy — do not edit.
- Tablet JS is **byte-identical** between `Tablet_PWA/frontend/js/` and `Tablet_Android_APK/app/src/main/assets/js/` — every change goes in BOTH; the only backend is `Tablet_PWA/backend/app.py` (FastAPI).
- Postgres migrations live as idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` blocks in desktop `utils/db.py` and tablet backend `app.py` (the `.sql` file in `Catering/` is old — not live).

## Part 0 — Money semantics (one definition, used everywhere)

For non-cancelled bookings, `paid = COALESCE(bk_amount_paid,0)` (invoice-side: `inv_amount_paid`), `total = bk_total_amount`:

| Bucket | Definition |
|---|---|
| Fully paid | `total > 0 AND paid >= total` (matches `compute_invoice_status()` in `utils/db.py:24-38`, i.e. `inv_status='Paid'`) |
| **Total Received / Revenue** | `SUM(total)` over fully-paid bookings, excluding on-process |
| **Down Payment** | `SUM(paid)` over NOT-fully-paid bookings NOT flagged on-process |
| **On Process** | `SUM(paid)` over bookings with `bk_on_process=1` (excluded from both buckets above) |
| **Unpaid Balance** | `SUM(total - paid)` over not-fully-paid (unchanged) |

Invariant: Down Payment + On Process + Total Received = all cash collected. All buckets are derived live from flags + paid amounts — clearing the on-process flag automatically moves money to the right bucket; nothing is stored per-bucket.

## Part 1 — `bk_on_process` flag (desktop)

**Why a separate column, not a `bk_status` value:** status enum is baked into tabs (`booking_page.py:1194`), colors, stored procs, and sync; a flag is orthogonal (a CONFIRMED booking can be on-process).

1. **Migrations** (additive, both engines):
   - `utils/sqlite_schema.py`: add `bk_on_process INTEGER DEFAULT 0` to bookings CREATE TABLE (~:222) and to the `cols_to_add` migration list (~:721). Also add `bk_survey_source TEXT DEFAULT ''` (Part 4).
   - `utils/db.py` Postgres bootstrap ALTER blocks (:469-476 and :619-632): `bk_on_process INT DEFAULT 0`, `bk_survey_source TEXT DEFAULT ''`.
2. **Repository** (`utils/repository.py`): new `set_booking_on_process(db_id, flag)` — direct UPDATE following the `bk_color_theme` pattern (:2443-2446) + `write_audit_log`. Add `COALESCE(b.bk_on_process,0) AS on_process` to booking fetchers: `get_all_bookings` (:1676), `get_bookings_page` (:1698), `get_bookings_any_status` (:6274).
3. **Booking page UI** (`ui/booking_page.py`): "ON PROCESS" badge (violet #A78BFA) next to the status badge in `_create_booking_card()` (~:2451); toggle action button in the actions row (~:2500-2510), gated by `can_edit`, → `repo.set_booking_on_process` → reload + toast.

## Part 2 — Billing: 5 cards + On Process filter

Files: `ui/billing_page.py`, `utils/repository.py`.

1. **`get_invoices_summary()` (:2699-2762)**: add `LEFT JOIN bookings b ON b.bk_id = i.inv_booking_id`; compute with mutually-exclusive CASEs (check `bk_on_process=1` FIRST):
   - `on_process` = SUM(paid) where flagged
   - `total_received` = SUM(paid) where `inv_status='Paid'` and not flagged (replaces the all-payments sum at :2726; remove/retire the payment_records period query :2740-2756 after checking its dashboard caller :3575)
   - `down_payment` = SUM(paid) where `inv_status != 'Paid'` and not flagged
   - `total_pending`, `events_count` unchanged. Keep old dict keys for compatibility.
   - Accept `paid_status == "on_process"` → `AND COALESCE(b.bk_on_process,0)=1`.
2. **Invoice rows**: `_INVOICE_ROW_SQL` (:2544-2570) + `get_invoices_page` (:2596) + `search_invoices` (:2637): add the JOIN + `on_process` column; map in `_rows_to_invoice_dicts` (:2573); handle the `"on_process"` filter branch (no date-window, like "unpaid").
3. **Cards** (:1180-1255): replace 4 with 5 — DOWN PAYMENT (amber), UNPAID BALANCE, ON PROCESS (violet), TOTAL RECEIVED (green), ACTIVE EVENTS. Delete `_dp4` (:1233-1242). Update `_apply_header_kpis()` (:1451-1497) + label-suffix loop (:1490-1495). **Gotcha:** the header sometimes falls back to a `_summary` computed client-side from visible rows — make that fallback compute the same 5 numbers row-wise (Part 0 math) or the cards flicker between definitions.
4. **Filter combo** (:1309-1317): add "On Process" item; `_on_filter_changed` (:1403) treats it like "unpaid" (clear date window).
5. **Invoice card** (:1727-1836): "ON PROCESS" badge next to the "Unverified" badge logic (:1821-1824).

## Part 3 — Dashboard semantics

1. **`get_downpayment_received()` (:3492-3511)**: add exclusions — not fully paid, `bk_on_process=0`, exclude only CANCELLED (keep COMPLETED-but-unpaid bookings counted). Use `COALESCE(NULLIF(bk_amount_paid,0), NULLIF(bk_down_payment,0), 0)` as `paid_expr` for legacy rows.
2. **`get_dashboard_kpis()` (:3514-3600)**: `total_revenue`/`weekly_revenue` = SUM(total) over fully-paid (currently full totals regardless of paid state, :3588/:3595); `downpayment_received` = Part 0 definition — make `get_downpayment_received()` the single source, delete the duplicated inline sums/fallback (:3591/:3597). `all_time_net_income` follows automatically.
3. **`get_dashboard_kpis_filtered()` (:3603+)**: same CASE expressions in the period query (:3614-3620).
4. **View `v_dashboard_kpis`** (`utils/sqlite_schema.py:453-462`): add fully-paid + non-cancelled conditions to `weekly_revenue`; self-migrates (DROP/CREATE). Grep db.py for a Postgres equivalent and mirror.
5. **UI** (`ui/dashboard_page.py`): `_kpi_downpayment` card already exists (:1127) — just verify key wiring in refresh handler (:1648-1702) and update trend captions ("Partial payments — not yet fully paid" / "Fully paid bookings").

## Part 4 — Tablet: Terms at end + Survey (both JS copies!)

Files: `{Tablet_PWA/frontend, Tablet_Android_APK/app/src/main/assets}/js/{wizard.js, app.js, sqlite.js, repository.js, api.js}` + `Tablet_PWA/backend/app.py` + desktop display/report.

1. **New step order** — `STEPS` (wizard.js:9-16) → 8 steps: Customer · Event & Package · Menu · Charges · Billing · Preview · **7 Terms** · **8 Survey & Confirm**. Add cases in `renderStep()` (:763-773). Step 6 Preview's "Confirm & Save" button (:3044-3052) becomes "Next: Terms & Conditions". Refactor `openBookingConfirmationDrawer()` / `#btn-final-confirm-order` handler (:3128-3184) / `renderReceipt()` out of the Preview closure to module level so Step 8 can invoke them (`wizard.draft` is already module-shared).
2. **`renderStepTerms(card)`**: port `openTermsModal()` body (app.js:1092-1151) — scroll box (~55vh), scroll-to-bottom unlocks `#terms-ack`, Next ("I Agree — Continue") disabled until checked; sets `d.termsAccepted`, `d.termsVersion`. Pre-unlock on re-entry.
3. **`renderStepSurvey(card)`**: "How did you hear about us?" — 6 checkboxes (multi-select, optional): Word of Mouth / Personal Referral · Social Media · Search Engine · Online Advertising or Media · Events & Local Community · Online Reviews & Recommendations. Stores `d.surveySources`. Primary button "Confirm & Save Booking" → guard termsAccepted → confirmation drawer → receipt.
4. **Remove pre-wizard modal**: swap ALL `openTermsModal()` callers to `startOrderWizard()` — app.js **:913, :1236, :1309, :1529, :1562, :1713, :1753** (7 sites — missing one resurfaces the old modal); delete `openTermsModal`.
5. **Persistence**: payload (:3134-3170) → `terms_version: d.termsVersion`, `survey_source: JSON.stringify(d.surveySources||[])`. sqlite.js: column in bookings CREATE (:90-118) + try/catch ALTER in migration block (:371-386). repository.js `createOrder` (:695-708): add column+param. Verify api.js `placeOrder` (:890-910) doesn't strip the field.
6. **Sync**: backend app.py ALTER block (:532-543): add `bk_survey_source TEXT DEFAULT ''` AND `bk_on_process INT DEFAULT 0` (so tablet-first sync doesn't predate desktop migration); bookings INSERT (:650-669): add column + `b.get("bk_survey_source","")`.
7. **Desktop display + report**:
   - Booking modal (`components/booking_modal.py`): read-only "Heard about us" row (parse JSON, join ", ", tolerate legacy/empty).
   - Reports (`ui/reports_page.py`): new repo fn `get_survey_source_breakdown()` — SELECT raw values, **parse/count in Python** (avoids SQLite-vs-Postgres JSON SQL); new `SurveySourceChart` cloned from `OccasionBreakdownChart` (:626), added to layout + refresh path.

## Part 5 — Menu inclusions UX (wizard.js:2117-2760 + css/styles.css, both copies)

1. **Tap-to-swap**: `canAdd()` full-bucket branch (:2608-2611) stops rejecting with a toast; instead the click handler opens `openSwapSheet(newItem, bucket)` (via existing `openModal`): lists that bucket's current selections, tap one to replace → "Swapped A → B" toast. Bucket limit 1 → auto-swap, no sheet. Same treatment for the food-set replacement variant (:2256-2326, :2569-2592).
2. **Visible quotas**: upgrade bucket pills (:2357-2364) to mini progress bars (fill width + ✓ at full) inside the sticky filter bar (`.kiosk-menu-sticky-filter-bar`) so they stay visible while scrolling; extend `updateCounts()` (:2560-2566).
3. **Selections tray**: sticky collapsible tray above the footer — "Your selections (k/N)" chips grouped by bucket, each with ✕ to remove; refreshed inside `updateCounts()` (`window._updateStep3Counts` :2594). New CSS: `.kiosk-selection-tray`, `.bucket-progress`, `.swap-sheet-row` reusing existing tokens.
4. `goNextStep()` validation (:2615-2622) unchanged.

## Order of work

1. Migrations (all additive): sqlite_schema.py, db.py Postgres ALTERs, tablet sqlite.js, backend app.py ALTER block.
2. Desktop repository math (Parts 2.1-2.2, 3.1-3.4, set_booking_on_process, fetchers).
3. Desktop UI (billing cards/filter/badge, booking toggle/badge, dashboard captions, booking-modal survey row, reports chart).
4. Tablet wizard restructure (steps 7/8, remove pre-modal, payload) — edit PWA copy, then copy changed files to APK assets; rebuild APK (`build_apk.sh`).
5. Tablet menu UX (independent; can land separately).
6. Backend sync INSERT column.

## Risks

- **Dual DB engines** — all new SQL must run on SQLite AND Postgres (COALESCE/CAST patterns only; no JSON SQL functions).
- **Duplicated tablet assets** — after editing, `md5sum` changed files across both copies to confirm parity.
- **Revenue redefinition is user-visible** — dashboard revenue/net income will drop for datasets with partials; flag to client. Reports `v_report_kpis` (sqlite_schema.py:473-479) may also need aligning — confirm scope with client.
- **Billing `_summary` dual-source** (server summary vs client row fallback) must implement identical math.
- Old bookings have NULL/empty flag & survey — all UI must tolerate.

## Verification

1. Boot fresh + existing SQLite DB (migration idempotency); repeat Postgres LAN mode.
2. Scenario: booking 20k, pay 10k → Dashboard downpayment +10k / revenue +0; pay rest → downpayment −10k / revenue +20k. Toggle on-process → amount moves Down Payment → On Process and back.
3. Billing: Down + On Process + Received = total cash collected; "On Process" filter shows only flagged; badges render.
4. Tablet: full wizard run offline (Terms at step 7, survey at 8) → booking saved with survey + terms ack → lan-sync → row in Postgres with `bk_survey_source` → desktop modal shows it → reports chart counts it.
5. Menu step: full 2-limit bucket + tap third dish → swap sheet; limit-1 auto-swap; tray ✕ updates pills; Next validation still gates.
