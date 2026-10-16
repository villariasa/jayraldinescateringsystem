# Change Request — Add "Food and Services" Category

> **Date:** 2026-10-15
> **Status:** Proposed / Not yet implemented
> **Apps affected:** Desktop (`Catering/`), Tablet Kiosk PWA (`Tablet_PWA/`), Android APK mirror (`Tablet_Android_APK/`)
> **Modules affected:** Menu / Package Definition · Booking Wizard · Reports & Sales Analytics

---

## 1. Summary

Today a menu **package** can be flagged in the Menu section so that, during booking,
the user picks between these **Order Types**:

| Current | Order Type keys (`flowType`) |
|---------|------------------------------|
| Package | `package` |
| Food Set | `food_set` (backed by `pkg_is_set = 1`) |
| Food Tray | `food_tray` |

This change adds a **4th category: "Food and Services"**, handled exactly like the
existing Food Set / Food Tray flags. After this change the booking module (both
Desktop and Tablet Kiosk) offers **4 choices**:

> **Package · Food Set · Food Tray · Food and Services**

Because a new business category is introduced, the **Reports module** — specifically
the *Orders by Category per Month* bar graph that currently tags categories in
**yellow** and **red** — gains a **new bar/series for "Food and Services" with its own
color tag**.

---

## 2. Part A — Menu / Package Definition (flag the package)

Goal: when the owner/client defines a package in the Menu section, they can flag it as
**"Food and Services"**, the same way a package is flagged as *Food Set* / *Food Tray*
today.

### 2.1 Tablet Kiosk PWA (`Tablet_PWA/`)

The kiosk already stores a per-package boolean `pkg_is_set` to flag Food Sets. Mirror
that pattern with a new flag for Food and Services.

| File | Change |
|------|--------|
| `Tablet_PWA/backend/schema.py` | Add column `pkg_is_food_service INTEGER DEFAULT 0` to the `packages` table (same place as `pkg_is_set` at line ~87), and add it to the idempotent `ALTER TABLE … ADD COLUMN` migration list (near line ~342: `("packages", "pkg_is_food_service", "INTEGER DEFAULT 0")`). |
| `Tablet_PWA/backend/app.py` | Add the same column to the live-DB migration (`ALTER TABLE packages ADD COLUMN IF NOT EXISTS pkg_is_food_service …`, near line ~540) and include it in the package upsert/sync statements (near lines ~779 and ~812, alongside `pkg_is_set`). |
| `Tablet_PWA/backend/repository.py` | In the packages serializer (near line ~107) add `"is_food_service": bool(r.get("pkg_is_food_service") or 0)`. |
| `Tablet_PWA/frontend/js/settings.js` | In the package add/edit form (Menu section), add a **"Food and Services"** toggle/checkbox next to the existing *Food Set* flag; send `pkg_is_food_service` on save. |
| `Tablet_PWA/frontend/js/api.js` | Carry `pkg_is_food_service` / `is_food_service` through the package create/update/sync payloads (same handling as `pkg_is_set`). |
| `Tablet_Android_APK/app/src/main/assets/js/*` | Apply the identical JS changes — this folder is a mirror of `Tablet_PWA/frontend/js/` (`settings.js`, `api.js`, `wizard.js`, `state.js`, `exporter.js`, `sqlite.js`). |

> **Mutual exclusivity rule:** a package should carry **at most one** of
> `pkg_is_set` / `pkg_is_food_service` (a package is either a Food Set *or* Food and
> Services *or* a plain package). Enforce this in the settings form when toggling.

### 2.2 Desktop app (`Catering/jayraldines_catering/`)

The desktop `packages` table is managed through MariaDB stored procedures and does not
yet carry the Food Set / Food Tray flag column, so add the category explicitly.

| File | Change |
|------|--------|
| Database (MariaDB) | Add a column to `packages`, e.g. `pkg_category ENUM('package','food_set','food_tray','food_service') DEFAULT 'package'` (or a nullable `is_food_service TINYINT`). Update stored procedures `sp_add_package` and `sp_update_package` to accept and persist it. |
| `Catering/jayraldines_catering/utils/repository.py` | `get_all_packages()` (line ~249) — add the new column to the `SELECT` and to the returned dict (e.g. `"category": r["pkg_category"]`). `add_package()` (line ~306) and `update_package()` (line ~324) — pass the new value through `callproc_out` / `callproc_void` `in_params`. |
| `Catering/jayraldines_catering/ui/menu_page.py` | In `PackageDialog` (class at line ~283) add a **"Food and Services"** option to the package form (a `QComboBox` of Package / Food Set / Food Tray / Food and Services, or a `QCheckBox`), include it in the `_collect()` result dict and prefill it in edit mode. |

---

## 3. Part B — Booking Module (4 order-type choices)

### 3.1 Tablet Kiosk PWA (`Tablet_PWA/frontend/js/wizard.js`)

Add the 4th entry to the `ORDER_TYPES` array (currently at line ~1487):

```js
const ORDER_TYPES = [
  { key: "package",      label: "Packages",          desc: "Choose a buffet tier package" },
  { key: "food_tray",    label: "Food Tray",         desc: "Mix &amp; match menu items only" },
  { key: "food_set",     label: "Food Set",          desc: "Predefined Sets A–E" },
  { key: "food_service", label: "Food and Services", desc: "Package with added services" },  // NEW
];
```

Then thread the new `flowType === "food_service"` branch through every place that
already branches on `food_set` / `food_tray`, including:

- `wizard.js` line ~1481 default `flowType`, summary rendering (lines ~643–654),
  quantity label/hint (lines ~1536–1539), the order-type button handler (line ~1844+),
  and the step-validation / totals logic (lines ~2031–2040).
- `Tablet_PWA/frontend/js/state.js` — extend the `flowType` comment/handling (line ~14)
  so the draft recognizes `food_service`.
- Load a `foodServiceCache` (packages with `is_food_service === true`) the same way
  `foodSetsCache` is built from `is_set` (line ~1416), and render the matching picker
  for the `food_service` flow.

> Decide the pax model: Food and Services should most likely use **No. of Pax** (like a
> package), not **No. of Sets** — so keep the `food_set` set-counting branches gated on
> `food_set` only.

### 3.2 Desktop app (`Catering/jayraldines_catering/components/booking_modal.py`)

The booking modal currently exposes a two-segment toggle **"Packages / Custom Menu"**
(buttons at line ~483) and stores `menu_type` (line ~773). Add the new category so the
booking offers all four choices:

- Extend the order-type selector (segment buttons or a combo) to include **Food Set**,
  **Food Tray**, and **Food and Services** in addition to **Packages**.
- When **Food and Services** is chosen, filter `self._db_packages`
  (`repo.get_all_packages()`, line ~506) to those whose new `category == "food_service"`.
- Persist the chosen category with the booking (set `menu_type = "food_service"` and
  store it on the booking record so Reports can read it back).

---

## 4. Part C — Reports Module (new bar + color tag)

Target: the **Orders by Category per Month** bar graph where categories are currently
tagged **yellow** and **red**. Add a **new bar/series for "Food and Services"** with its
own distinct color tag.

### 4.1 Classification engine

Update the package classifier in
`docs/ACTUAL_SALES_EVALUATION_CATEGORY_BREAKDOWN.md` → `classify_booking_package()` and
its implementation so Food-and-Services bookings resolve to the new category instead of
falling through to a generic bucket:

```python
def classify_booking_package(pkg_name, occasion, category=None):
    if category == "food_service" or "food and service" in (pkg_name or "").lower():
        return "Food and Services"          # NEW category
    ...
```

### 4.2 Desktop chart (`Catering/jayraldines_catering/ui/reports_page.py`)

The reports charts use `QBarSet` with fixed colors — e.g. amber/**yellow** `#F59E0B`
and crimson/**red** `#E11D48` (see lines ~249, ~353, ~537). For the Orders-by-Category
chart, add a third `QBarSet("Food and Services")` and give it a **new tag color** that
is visually distinct from the existing yellow and red, for example:

| Category | Tag color |
|----------|-----------|
| (existing) | Yellow `#F59E0B` |
| (existing) | Red `#E11D48` |
| **Food and Services (NEW)** | **Teal `#06B6D4`** *(or Indigo `#6366F1`)* |

Add the series to the `QBarSeries`, extend the legend, and feed it from the per-month
category counts returned by the repository (add a `food_service` bucket to whichever
`repo.get_*` query backs this chart, grouped by month).

### 4.3 Kiosk / exports

If the kiosk produces category breakdowns in exports
(`Tablet_PWA/frontend/js/exporter.js`), add the **Food and Services** bucket there too so
exported reports stay consistent with the Desktop chart.

---

## 5. Data Model / Migration Notes

- **Kiosk (SQLite):** new column `packages.pkg_is_food_service INTEGER DEFAULT 0`, added
  via the existing idempotent migration helpers — safe on existing databases
  (defaults to 0, so all current packages remain uncategorized/plain).
- **Desktop (MariaDB):** new `packages.pkg_category` (or `is_food_service`) column +
  stored-procedure updates. Existing rows default to `package`.
- No destructive migration — all changes are additive.

---

## 6. Files-to-Touch Checklist

**Kiosk PWA + Android mirror**
- [ ] `Tablet_PWA/backend/schema.py`
- [ ] `Tablet_PWA/backend/app.py`
- [ ] `Tablet_PWA/backend/repository.py`
- [ ] `Tablet_PWA/frontend/js/settings.js`
- [ ] `Tablet_PWA/frontend/js/api.js`
- [ ] `Tablet_PWA/frontend/js/wizard.js`
- [ ] `Tablet_PWA/frontend/js/state.js`
- [ ] `Tablet_PWA/frontend/js/exporter.js`
- [ ] `Tablet_Android_APK/app/src/main/assets/js/*` (mirror the JS changes)

**Desktop**
- [ ] MariaDB `packages` column + `sp_add_package` / `sp_update_package`
- [ ] `Catering/jayraldines_catering/utils/repository.py`
- [ ] `Catering/jayraldines_catering/ui/menu_page.py`
- [ ] `Catering/jayraldines_catering/components/booking_modal.py`
- [ ] `Catering/jayraldines_catering/ui/reports_page.py`
- [ ] `docs/ACTUAL_SALES_EVALUATION_CATEGORY_BREAKDOWN.md` (classifier)

---

## 4A. Part D — (Tablet Kiosk) Fix Food Set Selection Consistency

> **App:** Tablet Kiosk PWA only (`Tablet_PWA/`) + Android mirror
> **Type:** Bug fix / UX consistency
> **File:** `Tablet_PWA/frontend/js/wizard.js`

### Reported behavior

When booking a **Food Set**, the number of sets a client can actually select does **not
stay consistent** with the **No. of Sets** they entered:

- Set *No. of Sets* = **1** → client can select **1** set. ✅
- Change *No. of Sets* = **5** → client can select **5** sets. ✅
- But **sometimes** after setting *No. of Sets* = **5**, the client **cannot select any
  set at all** (or cannot reach 5) — selection just stops responding.

The result is confusing and not user-friendly: there are times the client simply "can't
select the number of sets" they asked for, with no clear reason shown.

### Root cause (as found in the code)

The Food Set target and the set picker share state through `d.event.numSets`, and that
value drifts out of sync:

1. **Two separate "No. of Sets" inputs.** In the Food Set flow the visible field is
   `#e-pax` (labeled *No. of Sets*, line ~1536–1537) while a second `#e-num-sets` input
   also exists (line ~1572–1574). Only `#e-pax` gets the Food Set change listener
   (`handleSetQtyInput`, lines ~1909–1920), so the two can disagree about the target.
2. **The selection gate reads the (possibly stale) target.** `handleAddSet()` blocks
   adding when `setSelectionsTotalQty(d) >= Number(d.event.numSets || 0)` (lines
   ~1115–1120, repeated at ~1189–1194). If `d.event.numSets` was not updated to 5 (left
   at 1, or reset to 0), the cap is wrong and selection is blocked early — "can't select
   5 sets."
3. **Re-render re-seeds the target from state.** On every `refreshList()` the input
   value falls back to `d.event.numSets || setSelectionsTotalQty(d) || 1` (line ~1537,
   ~1574). When `numSets` has been coerced down to the current selection count, the
   effective target equals what's already selected, so **every further tap is blocked**
   → the picker appears frozen / inconsistent.
4. **The block is a silent toast.** When the cap is hit the user only gets a transient
   `toast("Target limit of X set(s) reached…")` (lines ~1118, ~1192) with no persistent
   "X of Y selected" counter, so the stop looks random.

### Required fix

- **Single source of truth.** Use `d.event.numSets` as the only target. Remove the
  duplicate `#e-num-sets` input in the Food Set flow (or bind the same
  `handleSetQtyInput` to both so they can never disagree).
- **Never silently lower the target.** On re-render, seed the input from the user's
  declared `d.event.numSets` only; do **not** fall back to `setSelectionsTotalQty(d)`
  (the current selection count) when a target was explicitly entered — that is what
  locks the picker.
- **Keep the cap in step with the declared number.** Changing *No. of Sets* must update
  `d.event.numSets` immediately (and re-enable `+` buttons); the client must always be
  able to select exactly up to the number they typed.
- **Visible, persistent feedback.** Replace the one-off toast with a sticky counter on
  the picker, e.g. **"Selected 3 of 5 sets"**, and disable the `+` / card tap only when
  `total === target`, so the limit is obvious instead of surprising.

### Acceptance (this fix)

- Entering *No. of Sets* = N (for any N from 1 to the max) always allows selecting
  exactly N sets — repeatably, including after changing N up or down and after
  navigating back/forward in the wizard.
- A persistent "Selected X of N sets" indicator is shown on the Food Set picker.
- Selection never silently stops before reaching N.

---

## 7. Acceptance Criteria

1. In the **Menu** section (Desktop + Kiosk) a package can be flagged **Food and
   Services**, mutually exclusive with Food Set / Food Tray.
2. In the **Booking** module (Desktop + Kiosk) the order-type selector shows **4
   choices**: Package, Food Set, Food Tray, **Food and Services**, and picking Food and
   Services shows only packages flagged as such.
3. A booking created as **Food and Services** is saved with that category.
4. In **Reports → Orders by Category per Month**, a **new bar/series "Food and
   Services"** appears with a **distinct color tag** (not yellow, not red), and its
   monthly counts match the bookings flagged Food and Services.
5. Existing packages and bookings are unaffected (default to their current category).
