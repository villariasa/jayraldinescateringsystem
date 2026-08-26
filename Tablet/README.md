# Jayraldine's Catering — Tablet App

A small, touch-first order-entry client for tablets, per `Tablet-mode.md`.
Lives as a sibling to `Catering_Present/`:

```
jayraldinescateringsystem/
├── Catering_Present/
│   └── jayraldines_catering/     ← the main PC app
└── Tablet/                       ← this app
```

## What this app does (and doesn't)

**Does:** Customer entry (new/existing) → Package/Menu selection → Additional
charges/discounts → Billing (down payment) → Order Preview → Terms &
Conditions acknowledgement → Confirm → Print Receipt → Export order data
back to the PC.

**Does not:** full business management (that stays on the PC — reports,
cash flow, expenses, inventory, staff activity logs, etc.). See
`Tablet-mode.md` section 8 for the intended scope boundary.

## Why it shares the PC's database schema

The tablet's local SQLite database uses the **exact same table/column
names** as the PC app for every table that needs to move between the two
(`customers`, `bookings`, `invoices`, `payment_records`,
`booking_additional_charges`, `booking_menu_items`, `terms_acknowledgements`,
`packages`, `menu_items`, `package_items`). That means:

- **Tablet → PC**: the tablet's local `.db` file *is* the export. Open it on
  the PC via **Settings → "Merge Backup File Into This Database"** — no
  separate export format, no translation step. The PC's existing merge logic
  (never downgrades a payment/status, dedupes by content, adds only new
  records) handles it automatically.
- **PC → Tablet**: on the PC, **Settings → "Export Tablet Master Data..."**
  produces a small `.db` file with just packages/menu items/prices. Import
  it on the tablet via **Home → "Import Master Data"**.
- **Excel alternative**: master data can also be hand-edited and imported as
  a `.xlsx` workbook — tap **Home → "Download Excel Template"** for a
  pre-filled starter file (`Packages` sheet + `Menu Items` sheet), edit it in
  Excel, then import it the same way. "Import Master Data" accepts either
  `.db` or `.xlsx`/`.xlsm` — it auto-detects by file extension.

Historical orders are safe from master-data updates because
`booking_menu_items` / `bk_base_total` / `booking_additional_charges` store
a **snapshot** of the price/name at order time — they don't reference
`packages`/`menu_items` live, so re-importing master data never changes an
already-placed order's total.

## Terms & Conditions

The actual Terms & Conditions text (from `SERVICE INFORMATION.docx`) lives
in `utils/terms.py` as `TERMS_TEXT`, versioned via `CURRENT_TERMS_VERSION`.
**Bump `CURRENT_TERMS_VERSION`** (and `version.py: TERMS_VERSION`) any time
the business changes this text — never edit old accepted text in place, since
`terms_acknowledgements.ta_version` records exactly which version each order
agreed to.

`utils/terms.py` also carries the Evaluation Survey questions from the same
source document (`EVALUATION_SURVEY_QUESTIONS`), unused for now — reserved
for a future post-event feedback feature, not part of the current scope.

## Testing locally (before deploying to an actual tablet)

You can run and click through the entire app on a regular Linux or Windows
desktop first — no Android device needed for functional testing.

### Linux

```bash
cd Tablet
./setup/setup_linux.sh
```

### Windows

```bat
cd Tablet
setup\setup_windows.bat
```

Both scripts create an isolated virtual environment (`.venv/`), install
`requirements.txt` (PySide6 + reportlab), and launch `main.py`. Re-run the
same script any time — it reuses the existing venv and just updates deps.

On first launch with an empty database, go to **Home → "Import Master
Data"** using a file exported from the PC app (Settings → "Export Tablet
Master Data..." on the PC) before creating orders, otherwise the Package
step will have nothing to select.

### Manual run (if you already have a venv/PySide6 installed)

```bash
cd Tablet
pip install -r requirements.txt
python3 main.py
```

## Building an Android APK

Can be built from Linux, Windows, or macOS — the Android SDK/NDK/JDK
toolchain is the same on every host, so `pyside6-android-deploy` works
identically regardless of which OS you build from.

### Linux

```bash
export ANDROID_SDK_ROOT=/path/to/Android/sdk
export ANDROID_NDK_ROOT=/path/to/Android/sdk/ndk/<version>
export JAVA_HOME=/path/to/jdk-17
./setup/build_android.sh
```

### Windows

```bat
set ANDROID_SDK_ROOT=C:\Users\you\AppData\Local\Android\Sdk
set ANDROID_NDK_ROOT=%ANDROID_SDK_ROOT%\ndk\<version>
set JAVA_HOME=C:\Program Files\Java\jdk-17
setup\build_android.bat
```

Run `setup\setup_windows.bat` at least once first — `build_android.bat`
reuses whichever environment it created (conda env or `.venv`).

See the comment block at the top of `setup/build_android.sh` /
`setup\build_android.bat` for full prerequisites — both wrap PySide6's
official `pyside6-android-deploy` tool, which needs the Android SDK/NDK/JDK
installed separately first. This is a one-time setup per build machine.

Either way, the output is a `.apk` you can side-load onto a tablet for
testing with `adb install -r <path-to-apk>` — no Play Store step needed
while iterating.

## Versioning

`version.py` tracks:
- `VERSION` (semantic `MAJOR.MINOR.PATCH`) — bump `MAJOR` for anything that
  changes the shared schema in a way that would break compatibility with an
  older PC build's merge logic.
- `SCHEMA_VERSION` — informational, mirrors the local SQLite schema shape.
- `TERMS_VERSION` — must match `utils/terms.py: CURRENT_TERMS_VERSION`.

## Directory layout

```
Tablet/
├── main.py                  Entry point
├── version.py                Version metadata
├── requirements.txt
├── ui/
│   ├── main_window.py        Top-level window (Home <-> Order Wizard)
│   ├── home_view.py           Orders list, Import/Export, staff name
│   └── order_wizard.py       The full Customer -> ... -> Export wizard
├── utils/
│   ├── db.py                  SQLite connection layer
│   ├── sqlite_schema.py       Schema (mirrors PC's shared tables exactly)
│   ├── repository.py         Business logic (customers, orders, billing)
│   ├── importer.py           Master data import + order "export" (= local db)
│   ├── exporter.py            Receipt PDF generation
│   ├── terms.py               Terms & Conditions text + version
│   ├── session.py             Current staff name (persisted via QSettings)
│   └── logger.py
└── setup/
    ├── setup_linux.sh
    ├── setup_windows.bat
    ├── build_android.sh
    └── build_android.bat
```
